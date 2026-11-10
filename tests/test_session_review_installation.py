import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest

from manager.cli import ROOT, main


class SessionReviewInstallationTests(unittest.TestCase):
    def test_package_lifecycle_with_installed_selector(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            catalog = base / "catalog"
            source = catalog / "frameworks/session-review"
            shutil.copytree(ROOT / "frameworks/session-review", source)
            home = base / "codex"

            def run(*arguments):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(
                        [*arguments, "--codex-home", str(home), "--json"],
                        root=catalog,
                    )
                data = json.loads(output.getvalue())
                self.assertEqual(code, 0, data)
                return data

            run("list")
            plan = run("plan", "session-review")
            self.assertEqual(len(plan["operations"][0]["models"]), 3)
            self.assertFalse(home.exists())

            home.mkdir()
            instructions = home / "AGENTS.md"
            original = b"Existing user instructions.\n"
            instructions.write_bytes(original)
            native = home / "config.toml"
            native.write_text('model = "existing-model"\n')
            native_original = native.read_bytes()

            run("install", "session-review")
            roles = list((source / "agents").glob("*.toml"))
            self.assertEqual(len(roles), 3)
            for role in roles:
                installed = home / "agents" / role.name
                self.assertEqual(installed.read_bytes(), role.read_bytes())
                config = tomllib.loads(installed.read_text())
                self.assertEqual(config["model"], "gpt-6-luna")
                self.assertEqual(config["model_reasoning_effort"], "high")

            skill = home / "skills/session-review"
            installed_text = (skill / "SKILL.md").read_text()
            self.assertIn(str(home / "agents"), installed_text)
            self.assertNotIn("{{agents_path}}", installed_text)

            for asset in (source / "skills/session-review").rglob("*"):
                if asset.is_file() and asset.name != "SKILL.md":
                    relative = asset.relative_to(source / "skills/session-review")
                    self.assertEqual((skill / relative).read_bytes(), asset.read_bytes())

            sessions = base / "sessions"
            sessions.mkdir()
            session = sessions / "rollout-example.jsonl"
            session.write_text(
                json.dumps({
                    "timestamp": "2026-11-09T12:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "task_started"},
                }) + "\n"
            )
            selected = subprocess.run(
                [sys.executable, str(skill / "scripts/select_sessions.py"),
                 "--sessions-root", str(sessions),
                 "--since", "2026-11-03", "--until", "2026-11-10"],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(json.loads(selected.stdout)["sessions"][0]["file"], str(session))

            self.assertEqual(run("install", "session-review")["changes"], [])
            self.assertEqual(run("check", "session-review")["packages"][0]["issues"], [])

            source_script = source / "skills/session-review/scripts/select_sessions.py"
            source_script.write_bytes(source_script.read_bytes() + "\n# Проверка обновления ресурса навыка.\n".encode())
            run("update", "session-review")
            self.assertEqual((skill / "scripts/select_sessions.py").read_bytes(), source_script.read_bytes())
            self.assertEqual(run("check", "session-review")["packages"][0]["issues"], [])

            run("uninstall", "session-review")
            self.assertFalse((skill / "SKILL.md").exists())
            self.assertFalse((skill / "scripts/select_sessions.py").exists())
            self.assertFalse(any((home / "agents").glob("session-*.toml")))
            self.assertEqual(instructions.read_bytes(), original)
            self.assertEqual(native.read_bytes(), native_original)
