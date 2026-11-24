"""Retro (plan 10): it writes the pack and the project, never the plugin, and leaves the pack no larger. The bundled
generic pack is part of the plugin, so retro then works on the project's own `greenfield/lessons.md` and `standards.md`.
`begin` snapshots the sizes; `finish` refuses when anything grew, a file is over its cap, or a lesson names the
sponsor's specifics (the project, a glossary term, a person's phone, email or token)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import audit, packcheck, packs, redact
from .project import load_fence

SNAPSHOT = Path("greenfield") / "retro-begin.json"
CAP = packcheck.CAP_LINES


class RetroError(ValueError):
    pass


def targets(root: Path) -> tuple[Path, str]:
    """The folder retro may write, and why. Never a folder inside the plugin."""
    pack = packcheck.pack_dir_of(load_fence(root)) or packs.bundled()[packs.GENERIC]
    if packs.plugin_root() in pack.resolve().parents:
        return root / "greenfield", "the generic pack is part of the plugin, so retro writes the project's own files"
    return pack, "the installed pack"


def measure(root: Path) -> dict:
    folder, _ = targets(root)
    files = {p.name: len(p.read_bytes()) for p in sorted(folder.rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts and p.suffix in (".md", ".yaml", ".yml", ".tsv", ".py")
             and (folder.name != "greenfield" or p.name in packcheck.CAPPED)}
    return {"bytes": sum(files.values()), "files": files,
            "lines": {n: len((folder / n).read_text(encoding="utf-8").splitlines()) for n in packcheck.CAPPED if (folder / n).is_file()}}


def begin(root: Path) -> dict:
    snap = {**measure(root), "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}
    (root / SNAPSHOT).write_text(json.dumps(snap), encoding="utf-8")
    return snap


def _specifics(root: Path) -> list[str]:
    data, _ = audit.load(root)
    words = {str((data or {}).get("project", {}).get("name") or "")}
    words |= {g["term"] for g in ((data or {}).get("project", {}).get("glossary") or []) if len(str(g.get("term"))) >= 4}
    return [w for w in words if len(w) >= 4]


def finish(root: Path) -> list[str]:
    path = root / SNAPSHOT
    if not path.is_file():
        raise RetroError("no retro in progress: run gp retro begin first")
    before, now, problems = json.loads(path.read_text(encoding="utf-8")), measure(root), []
    if now["bytes"] > before["bytes"]:
        problems.append(f"the pack grew from {before['bytes']} to {now['bytes']} bytes; retro leaves it no larger "
                        "(delete text that changes nothing before adding a line)")
    folder, _ = targets(root)
    for name in packcheck.CAPPED:
        if now["lines"].get(name, 0) > CAP:
            problems.append(f"{name} is {now['lines'][name]} lines; the cap is {CAP}")
        if (folder / name).is_file():
            text = (folder / name).read_text(encoding="utf-8")
            if sum(redact.clean(text)[1].values()):
                problems.append(f"{name} holds a phone number, email or token; lessons are general")
            problems += [f"{name} names {w!r}, a sponsor or project specific; lessons are general" for w in _specifics(root)
                         if re.search(rf"(?i)\b{re.escape(w)}\b", text)]
    if folder.name != "greenfield":
        problems += packcheck.check(folder)
    if not problems:
        path.unlink()
        row = "\t".join([datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "-", "retro",
                         f"pack {before['bytes']} -> {now['bytes']} bytes", "", "ok"])
        with (root / "greenfield" / "decisions.tsv").open("a", encoding="utf-8", newline="\n") as f:
            f.write(row + "\n")
    return problems
