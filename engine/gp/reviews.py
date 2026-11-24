"""Reviews (plan 4.3, 4.5, 7.4): rex reviews each suite version and each full run. A review is bound to the sha of
what it reviewed; the latest entry for that sha wins. The writer never reviews its own work."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

FILE = Path("greenfield") / "reviews.jsonl"
AUTHORS = {"suite": {"gus"}, "run": {"ed", "eve"}}      # who may NOT review that kind of thing


class ReviewError(ValueError):
    pass


def subject_sha(root: Path, kind: str, ref: str) -> str:
    if kind == "suite":
        path = root / "greenfield" / "suites" / f"{ref}.yaml"
    elif kind == "run":
        path = root / "greenfield" / "runs" / ref / "verdicts.json"
    else:
        raise ReviewError("a review is of a suite or a run")
    if not path.is_file():
        raise ReviewError(f"{kind} {ref}: nothing to review at {path.relative_to(root).as_posix()}"
                          + (" (score the run first)" if kind == "run" else ""))
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() if kind == "run" else \
        hashlib.sha256(path.read_bytes()).hexdigest()


def entries(root: Path) -> list[dict]:
    path = root / FILE
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def record(root: Path, kind: str, ref: str, by: str, verdict: str, note: str = "") -> dict:
    if verdict not in ("approve", "reject"):
        raise ReviewError("verdict is approve or reject")
    if by in AUTHORS.get(kind, ()):
        raise ReviewError(f"{by} cannot review a {kind} it produced; the review must come from someone else")
    if verdict == "reject" and not note.strip():
        raise ReviewError("a rejection says why (--note)")
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": kind, "ref": ref,
             "sha": subject_sha(root, kind, ref), "by": by, "verdict": verdict, "note": note}
    with (root / FILE).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def approved(root: Path, kind: str, ref: str, sha: str, all_entries: list[dict] | None = None) -> bool:
    mine = [e for e in (all_entries if all_entries is not None else entries(root))
            if e.get("kind") == kind and e.get("ref") == ref and e.get("sha") == sha]
    return bool(mine) and mine[-1].get("verdict") == "approve"
