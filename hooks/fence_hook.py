"""Claude Code hook adapter for the fence. `pre` answers allow or ask; `post` logs an accepted ask.
Fails closed: inside a greenfield-pipeline project, any error asks instead of allowing."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))


def _ask(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "ask",
        "permissionDecisionReason": f"greenfield-pipeline fence: {reason}"}}))


def main(mode: str) -> int:
    raw = sys.stdin.read()
    call = {}
    try:
        call = json.loads(raw) if raw.strip() else {}
        from gp import fence
        found = fence.matches(call)
    except Exception as exc:
        try:
            from gp.project import find_project
            if find_project(call.get("cwd") or "."):
                _ask(f"the fence failed ({type(exc).__name__}); the owner decides")
        except Exception:
            pass
        return 0
    if not found:
        return 0
    rule, reason = found[0]
    if mode == "pre":
        _ask(f"[{rule}] {reason}")
    elif mode == "post":
        from gp.project import find_project
        project = find_project(call.get("cwd") or ".")
        if project:
            entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rule": rule,
                     "tool": call.get("tool_name"), "target": str(
                         (call.get("tool_input") or {}).get("file_path")
                         or (call.get("tool_input") or {}).get("command") or "")[:300]}
            with open(project / "greenfield" / "acceptances.jsonl", "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(entry) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "pre"))
