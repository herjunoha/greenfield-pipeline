"""The shape rules of `gp check` (plan 4.3): once a design exists it stays short, covers the parts a builder needs,
names every surface, and its decisions are logged. Whether it adds anything the canonical does not ask for is
rex's call, not a rule."""
from __future__ import annotations

import re
from pathlib import Path

from . import audit

REQUIRED = ("components", "data", "runtime", "stack", "alternatives")
MAX_LINES = 120                                   # about two pages


def check(root: Path) -> list[str]:
    path = root / "greenfield" / "design" / "architecture.md"
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    out = []
    if len(text.splitlines()) > MAX_LINES:
        out.append(f"design/architecture.md is {len(text.splitlines())} lines; two pages is about {MAX_LINES}")
    headings = " ".join(re.findall(r"(?im)^#+\s*(.+)$", text)).lower()
    missing = [word for word in REQUIRED if word not in headings]
    if missing:
        out.append(f"design/architecture.md has no heading for: {', '.join(missing)}")
    data, _ = audit.load(root)
    for surface in ((data or {}).get("project") or {}).get("surfaces") or []:
        if isinstance(surface, dict) and surface.get("name") and surface["name"].lower() not in text.lower():
            out.append(f"design/architecture.md never mentions the surface {surface['name']}")
    rows = (root / "greenfield" / "decisions.tsv").read_text(encoding="utf-8").splitlines()[1:] \
        if (root / "greenfield" / "decisions.tsv").is_file() else []
    if not [r for r in rows if r.strip()]:
        out.append("a design exists but decisions.tsv has no rows; every decision is logged (gp decide)")
    return out
