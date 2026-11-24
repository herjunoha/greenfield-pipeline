"""SessionStart hook: prints one line of pointers (the frontier, what waits, the live parts). Silent outside a project
and on any error: a status line must never get in the way of starting a session."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))


def main() -> int:
    try:
        raw = sys.stdin.read()
        cwd = (json.loads(raw) if raw.strip() else {}).get("cwd") or "."
        from gp import catchup
        from gp.project import find_project
        root = find_project(cwd)
        if root:
            print(catchup.session_line(root))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
