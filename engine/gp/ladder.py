"""The ladder (plan 7.3): how much of a kind of work the owner lets the agent do alone. It is the owner's, never
computed from a track record, and no level covers a one-way door: the fence is not read here and is not loosened by
any level. `hitl` makes the part's items worked live with the owner; `afk` (the default) lets the agent work alone and
show it in the catch-up. `unattended` is specified and not built in v1, so it is treated as `hitl`."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .items import PARTS
from .project import load_fence

LEVELS = ("hitl", "afk")
SESSION_FILE = Path("greenfield") / "session-level.json"


class LadderError(ValueError):
    pass


def session_token() -> str:
    return os.environ.get("GP_SESSION") or os.environ.get("CLAUDE_SESSION_ID") or "local"


def _session(root: Path) -> dict:
    path = root / SESSION_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:
        return {}
    return data.get("levels", {}) if data.get("session") == session_token() else {}     # ends with the session


def permanent(root: Path) -> dict:
    ladder = load_fence(root).get("ladder") or {}
    if not isinstance(ladder, dict):
        raise LadderError("fence.yaml ladder must be a map of part to level")
    for part, level in ladder.items():
        if part not in PARTS or level not in (*LEVELS, "unattended"):
            raise LadderError(f"fence.yaml ladder: {part!r}: {level!r} is not a part and a level "
                              f"({', '.join(PARTS)}; {', '.join(LEVELS)})")
    return ladder


def effective(root: Path, part: str) -> tuple[str, str]:
    """(level, where it came from). The session's spoken change outranks the fence's map, which outranks afk."""
    spoken = _session(root).get(part)
    if spoken:
        return spoken, "this session"
    level = permanent(root).get(part)
    if level == "unattended":
        return "hitl", "fence.yaml says unattended, which is specified and not built in v1"
    return (level, "fence.yaml") if level else ("afk", "default")


def live_parts(root: Path) -> set[str]:
    return {part for part in PARTS if effective(root, part)[0] == "hitl"}


def set_session(root: Path, part: str, level: str) -> None:
    """A spoken change ('watch build today'): lasts this session only, and is logged."""
    if part not in PARTS or level not in LEVELS:
        raise LadderError(f"level: part is one of {', '.join(PARTS)} and level one of {', '.join(LEVELS)}")
    if level == "afk" and permanent(root).get(part) in ("hitl", "unattended"):
        raise LadderError(f"{part} is hitl in fence.yaml, the owner's permanent choice; a spoken change cannot loosen it")
    path = root / SESSION_FILE
    data = {"session": session_token(), "levels": _session(root)}
    data["levels"][part] = level
    path.write_text(json.dumps(data), encoding="utf-8")
    row = "\t".join([datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "-", f"ladder: {part} -> {level}",
                     "spoken by the owner for this session", "", ""])
    with (root / "greenfield" / "decisions.tsv").open("a", encoding="utf-8", newline="\n") as f:
        f.write(row + "\n")
