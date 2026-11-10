import contextlib
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = (Path(__file__).resolve().parents[1] / "frameworks/session-review/skills/"
          "session-review/scripts/select_sessions.py")
SPEC = importlib.util.spec_from_file_location("select_sessions", SCRIPT)
selector = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "dont_write_bytecode", True):
    SPEC.loader.exec_module(selector)


class SessionReviewSelectorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        self.since = self.now - timedelta(days=7)

    def event(self, stamp, kind="event_msg", **payload):
        return {"timestamp": stamp.isoformat(), "type": kind, "payload": payload}

    def write_session(self, name, events):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
        return path

    def select(self):
        return selector.select_sessions(self.root, self.since, self.now)

    def cli(self, *arguments):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = selector.main(["--sessions-root", str(self.root), *arguments])
        return code, json.loads(output.getvalue())

    def test_old_directory_recent_event_and_metadata_only(self):
        selected = self.write_session("2020/01/01/rollout-old.jsonl", [
            self.event(self.since - timedelta(days=100), "session_meta",
                       id="01a1c0ad-fc52-7282-9632-74b35d40b2f4"),
            self.event(self.now),
        ])
        self.write_session("rollout-meta.jsonl", [self.event(self.now, "session_meta")])
        self.write_session("rollout-stale.jsonl", [self.event(self.since - timedelta(seconds=1))])
        result = self.select()
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["sessions"], [{"file": str(selected),
                         "session_id": "01a1c0ad-fc52-7282-9632-74b35d40b2f4"}])

    def test_default_cutoff_explicit_longer_period_and_boundaries(self):
        self.assertEqual(selector.interval(now=self.now), (self.since, self.now))
        self.assertEqual(selector.interval(days=30, now=self.now)[0], self.now - timedelta(days=30))
        selected = self.write_session("rollout-boundaries.jsonl", [
            self.event(self.since), self.event(self.now), self.event(self.now + timedelta(seconds=1)),
        ])
        self.assertEqual(self.select()["sessions"], [{"file": str(selected)}])
        self.write_session("rollout-future.jsonl", [self.event(self.now + timedelta(seconds=1))])
        old = self.write_session("rollout-old.jsonl", [self.event(self.now - timedelta(days=20))])
        code, result = self.cli("--since", "2026-10-10", "--until", "2026-11-10T12:00:00Z")
        self.assertEqual(code, 0)
        self.assertIn({"file": str(old)}, result["sessions"])
        self.assertEqual(len(result["sessions"]), 2)

    def test_no_cwd_or_dialogue_leaks_and_multiple_cwds_select_once(self):
        path = self.write_session("rollout-multiple.jsonl", [
            self.event(self.now, "session_meta", cwd="/secret-a"),
            self.event(self.now, "turn_context", cwd="/secret-b"),
            self.event(self.now, "turn_context", cwd="/secret-c"),
            self.event(self.now, message="private message"),
        ])
        result = self.select()
        self.assertEqual(result["sessions"], [{"file": str(path)}])
        encoded = json.dumps(result)
        self.assertNotIn("cwd", encoded)
        self.assertNotIn("secret-", encoded)
        self.assertNotIn("private message", encoded)

    def test_malformed_events_keep_valid_selection_and_report_safe_diagnostics(self):
        path = self.write_session("rollout-bad.jsonl", [
            ["private data"], {"type": "event_msg"},
            self.event(self.now, "new-type"), self.event(self.now),
        ])
        with path.open("ab") as stream:
            stream.write(b'{private malformed data}\n\xff\n')
        result = self.select()
        self.assertEqual(result["sessions"], [{"file": str(path)}])
        self.assertFalse(result["coverage_complete"])
        self.assertEqual([item["line"] for item in result["diagnostics"]], [1, 2, 3, 5, 6])
        self.assertNotIn("private data", json.dumps(result))
        self.assertNotIn("private malformed data", json.dumps(result))
        code, output = self.cli("--since", self.since.isoformat(), "--until", self.now.isoformat())
        self.assertEqual(code, 2)
        self.assertFalse(output["coverage_complete"])

    def test_missing_root_and_read_failures_are_not_empty_success(self):
        result = selector.select_sessions(self.root / "missing", self.since, self.now)
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["diagnostics"][0]["kind"], "root_unavailable")
        code, result = self.cli("--sessions-root", str(self.root / "missing"))
        self.assertEqual(code, 2)
        self.assertFalse(result["coverage_complete"])
        self.write_session("rollout-denied.jsonl", [self.event(self.now)])
        with patch.object(selector.os, "open", side_effect=PermissionError):
            result = self.select()
        self.assertEqual(result["diagnostics"][0]["kind"], "read_error")
        with patch.object(selector.os, "scandir", side_effect=PermissionError):
            result = self.select()
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["diagnostics"][0]["kind"], "read_error")

    def test_file_changed_during_read_has_incomplete_coverage(self):
        path = self.write_session("rollout-changing.jsonl", [self.event(self.now)])
        original_fstat = selector.os.fstat
        calls = 0

        def change_before_final_stat(descriptor):
            nonlocal calls
            calls += 1
            if calls == 2:
                with path.open("ab") as stream:
                    stream.write(b'{"private": "unreported dialogue"}\n')
            return original_fstat(descriptor)

        with patch.object(selector.os, "fstat", side_effect=change_before_final_stat):
            result = self.select()

        self.assertEqual(result["sessions"], [{"file": str(path)}])
        self.assertFalse(result["coverage_complete"])
        self.assertEqual(result["diagnostics"], [{
            "file": str(path), "kind": "changed_file",
            "message": "session file changed during scanning",
        }])
        self.assertNotIn("unreported dialogue", json.dumps(result))

    def test_symlinks_and_restricted_directories_are_not_read(self):
        target = self.write_session("source.jsonl", [self.event(self.now)])
        (self.root / "rollout-link.jsonl").symlink_to(target)
        (self.root / "linked-directory").symlink_to(self.root, target_is_directory=True)
        result = self.select()
        self.assertEqual(result["sessions"], [])
        self.assertFalse(result["coverage_complete"])
        with patch.object(selector.os, "walk", side_effect=AssertionError("must not inspect root")):
            result = selector.select_sessions(self.root / ".env.private", self.since, self.now)
        self.assertEqual(result["diagnostics"][0]["kind"], "restricted_path")

    def test_dates_and_timezone_offsets(self):
        self.assertEqual(selector.parse_time("2026-11-10"), self.now.replace(hour=0))
        self.assertEqual(selector.parse_time("2026-11-10T15:00:00+03:00"), self.now)
        start, end = selector.interval(until="2026-11-10T12:00:00Z")
        self.assertEqual((start, end), (self.since, self.now))

    def test_invalid_cli_periods_exit_two_without_scanning(self):
        cases = [
            ["--days", "0"], ["--days", "-1"], ["--days", "nan"],
            ["--days", "inf"], ["--days", "1e300"],
            ["--days", "1", "--since", "2026-11-01"],
            ["--days", "1", "--until", "2026-11-01"],
            ["--since", "2026-11-10T12:00:00"], ["--since", "invalid"],
            ["--since", "2026-11-11", "--until", "2026-11-10"],
        ]
        for arguments in cases:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with patch.object(selector, "select_sessions", side_effect=AssertionError("must not scan")):
                    with self.assertRaises(SystemExit) as error:
                        selector.main(arguments)
                self.assertEqual(error.exception.code, 2)

    def test_empty_file_is_complete_without_selection(self):
        (self.root / "rollout-empty.jsonl").write_text("")
        result = self.select()
        self.assertTrue(result["coverage_complete"])
        self.assertEqual(result["sessions"], [])


if __name__ == "__main__":
    unittest.main()
