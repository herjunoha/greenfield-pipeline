"""The owner's decisions (plan 3, 7.4). `acceptances.jsonl` is append-only. A decision counts only when an entry holds
the target file at its CURRENT sha, so editing a file after it was accepted un-accepts it."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

FILE = Path("greenfield") / "acceptances.jsonl"


class AcceptError(ValueError):
    pass


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def target(root: Path, ref: str) -> Path:
    """`I-3` an item, `suite:AC-2` a suite, `canonical` the requirement file."""
    if ref.startswith("I-"):
        path = root / "greenfield" / "items" / f"{ref}.md"
    elif ref.startswith("suite:"):
        path = root / "greenfield" / "suites" / f"{ref[6:]}.yaml"
    elif ref == "canonical":
        found = sorted((root / "greenfield" / "requirements").glob("*.canonical.yaml"))
        path = found[0] if len(found) == 1 else root / "greenfield" / "requirements" / "(none).canonical.yaml"
    else:
        raise AcceptError(f"{ref!r} is not an item id, suite:<AC> or canonical")
    if not path.is_file():
        raise AcceptError(f"{ref}: there is nothing to accept at {path.relative_to(root).as_posix()}")
    return path


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


def record(root: Path, ref: str, by: str = "owner") -> dict:
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kind": "accept-line", "ref": ref,
             "sha": file_sha(target(root, ref)), "by": by}
    with (root / FILE).open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def accepted(root: Path, ref: str, sha: str | None = None) -> bool:
    """True when the owner accepted `ref` at `sha` (default: the file as it is now)."""
    try:
        sha = sha or file_sha(target(root, ref))
    except AcceptError:
        return False
    return any(e.get("kind") == "accept-line" and e.get("ref") == ref and e.get("sha") == sha for e in entries(root))
