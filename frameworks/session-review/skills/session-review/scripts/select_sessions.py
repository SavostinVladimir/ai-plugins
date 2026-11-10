#!/usr/bin/env python3
"""Выбирает журналы по времени событий, не раскрывая содержимое диалогов."""

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import sys
from uuid import UUID


DEFAULT_ROOT = Path.home() / ".o3-cli/o3_plugin_agent/codex/sessions"
EVENT_TYPES = {"session_meta", "turn_context", "response_item", "event_msg",
               "compacted", "world_state"}
BLOCKED_NAMES = {".config", ".ssh", ".gnupg", ".netrc", ".pypirc", ".kube",
                 ".zsh_history", ".bash_history", ".mozilla", ".pki", ".vscode",
                 ".cursor", ".idea"}
HOME_BLOCKS = (
    ".cargo/credentials.toml", ".docker/config.json", ".cache/JetBrains",
    ".local/share/JetBrains", ".local/share/keyrings", "Library/Keychains",
    "Library/Cookies", "Library/Application Support/Google/Chrome",
    "Library/Application Support/Firefox", "Library/Application Support/BraveSoftware",
    "Library/Application Support/Microsoft Edge", "Library/Safari",
    "Library/Application Support/Code", "Library/Application Support/JetBrains",
    "Library/Caches/JetBrains", "Library/Logs/JetBrains", "Library/Messages",
    "Library/Mail",
)


def restricted(path):
    if any(part in BLOCKED_NAMES or part == ".env" or part.startswith(".env.")
           for part in path.parts):
        return True
    for relative in HOME_BLOCKS:
        blocked = Path.home() / relative
        if path == blocked or blocked in path.parents:
            return True
    preferences = Path.home() / "Library/Preferences"
    return any(candidate.parent == preferences and candidate.name.startswith("jetbrains")
               for candidate in (path, *path.parents))


def parse_time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise ValueError("expected an ISO 8601 timestamp or YYYY-MM-DD") from None
    if len(value) == 10:
        result = result.replace(tzinfo=timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("timestamps must include a timezone")
    return result.astimezone(timezone.utc)


def interval(days=None, since=None, until=None, now=None):
    end = parse_time(until) if until else (now or datetime.now(timezone.utc))
    if days is not None and (since is not None or until is not None):
        raise ValueError("--days cannot be combined with --since or --until")
    if days is not None and (not math.isfinite(days) or days <= 0):
        raise ValueError("--days must be positive and finite")
    try:
        start = parse_time(since) if since else end - timedelta(days=days if days is not None else 7)
    except OverflowError:
        raise ValueError("requested period is too large") from None
    if start > end:
        raise ValueError("--since must not be later than --until")
    return start, end


def select_sessions(root, since, until):
    result = {"since": since.isoformat(), "until": until.isoformat(),
              "sessions": [], "diagnostics": [], "coverage_complete": True}
    root = Path(os.path.abspath(Path(root).expanduser()))

    def diagnostic(path, kind, message, line=None):
        item = {"file": str(path), "kind": kind, "message": message}
        if line is not None:
            item["line"] = line
        result["diagnostics"].append(item)
        result["coverage_complete"] = False

    if restricted(root):
        diagnostic(root, "restricted_path", "sessions root is in a restricted location")
        return result
    try:
        if any(path.is_symlink() for path in (root, *root.parents)):
            diagnostic(root, "symlink", "sessions root must not traverse symlinks")
            return result
        if not root.is_dir():
            diagnostic(root, "root_unavailable", "sessions root does not exist or is not a directory")
            return result
    except OSError:
        diagnostic(root, "root_unavailable", "cannot access sessions root")
        return result

    def walk_error(error):
        diagnostic(error.filename or root, "read_error", "cannot list directory")

    for directory, directories, files in os.walk(root, followlinks=False, onerror=walk_error):
        parent = Path(directory)
        retained = []
        for name in sorted(directories):
            path = parent / name
            if restricted(path):
                diagnostic(path, "restricted_path", "restricted directory skipped")
            elif path.is_symlink():
                diagnostic(path, "symlink", "symlink directory skipped")
            else:
                retained.append(name)
        directories[:] = retained

        for name in sorted(files):
            if not (name.startswith("rollout-") and name.endswith(".jsonl")):
                continue
            path = parent / name
            if restricted(path) or path.is_symlink():
                diagnostic(path, "skipped_file", "restricted or symlink file skipped")
                continue
            selected = False
            session_id = None
            try:
                # O_NOFOLLOW закрывает подмену самого файла ссылкой между проверкой и открытием.
                descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(descriptor, "rb") as stream:
                    before = os.fstat(stream.fileno())
                    for number, raw in enumerate(stream, 1):
                        if not raw.strip():
                            continue
                        try:
                            event = json.loads(raw.decode("utf-8"))
                        except (ValueError, UnicodeError):
                            diagnostic(path, "invalid_json", "line is not valid UTF-8 JSON", number)
                            continue
                        if not isinstance(event, dict):
                            diagnostic(path, "invalid_event", "event must be a JSON object", number)
                            continue
                        event_type = event.get("type")
                        if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
                            diagnostic(path, "unknown_event_type", "unrecognized event type", number)
                        try:
                            stamp = parse_time(event.get("timestamp"))
                        except (ValueError, AttributeError):
                            diagnostic(path, "invalid_timestamp", "event timestamp missing or invalid", number)
                            continue
                        if event_type == "session_meta":
                            payload = event.get("payload")
                            if isinstance(payload, dict) and isinstance(payload.get("id"), str):
                                try:
                                    session_id = str(UUID(payload["id"]))
                                except ValueError:
                                    pass
                        elif since <= stamp <= until:
                            selected = True
                    after = os.fstat(stream.fileno())
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        diagnostic(path, "changed_file", "session file changed during scanning")
            except OSError:
                diagnostic(path, "read_error", "cannot read session file")
            if selected:
                item = {"file": str(path)}
                if session_id is not None:
                    item["session_id"] = session_id
                result["sessions"].append(item)
    result["sessions"].sort(key=lambda item: item["file"])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--days", type=float)
    parser.add_argument("--since", help="inclusive ISO 8601 timestamp; YYYY-MM-DD means 00:00 UTC")
    parser.add_argument("--until", help="inclusive ISO 8601 timestamp; YYYY-MM-DD means 00:00 UTC")
    args = parser.parse_args(argv)
    try:
        since, until = interval(args.days, args.since, args.until)
    except ValueError as error:
        parser.error(str(error))
    result = select_sessions(args.sessions_root, since, until)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result["coverage_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
