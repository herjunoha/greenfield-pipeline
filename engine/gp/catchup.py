"""The catch-up (plan 10): what waits on the owner, decisions since the last catch-up, and Attention flags; pointers,
not a report. `session_line` is the one line the session-start hook prints."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import audit, budget, items, ladder

MARK = Path("greenfield") / "catchup.json"


def _since(root: Path) -> str:
    try:
        return json.loads((root / MARK).read_text(encoding="utf-8")).get("at", "")
    except (OSError, ValueError):
        return ""


def attention(root: Path) -> list[str]:
    """The Attention section rex writes at the top of each evidence README, minus the ones that say no flags."""
    out = []
    for path in sorted((root / "greenfield" / "evidence").glob("*/README.md")):
        found = re.search(r"(?ims)^##\s+attention\s*$(.*?)(?=^##\s|\Z)", path.read_text(encoding="utf-8"))
        text = " ".join(found.group(1).split()) if found else ""
        if text and not re.match(r"(?i)^(no flags|none)\b", text):
            out.append(f"{path.parent.name}: {text[:200]}")
    return out


def decisions_since(root: Path) -> list[str]:
    path, since = root / "greenfield" / "decisions.tsv", _since(root)
    rows = path.read_text(encoding="utf-8").splitlines()[1:] if path.is_file() else []
    return [r.replace("\t", " | ") for r in rows if r.strip() and r.split("\t")[0] > since]


def build(root: Path) -> list[str]:
    everything = items.load_all(root / "greenfield" / "items")
    waiting = [i for i in everything.values() if i.state in ("ready-for-human", "needs-info")]
    lines = [f"waiting on you ({len(waiting)}):", *[f"  {i.id} {i.state}  {i.title}" for i in waiting]]
    since = _since(root)
    lines += [f"decisions since {since or 'the start'}:", *[f"  {d}" for d in decisions_since(root)]]
    flags = attention(root)
    lines += [f"attention ({len(flags)}):", *[f"  {f}" for f in flags]]
    report = audit.run(root)
    if report.rows:
        counts: dict[str, int] = {}
        for row in report.rows:
            counts[row["state"]] = counts.get(row["state"], 0) + 1
        lines.append("acs: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())))
    lines += [f"ceiling reached: {h['what']}" for h in budget.reached(root)]
    lines.append("ladder: " + (", ".join(f"{p}={ladder.effective(root, p)[0]}" for p in sorted(ladder.permanent(root)
                                                                                          | ladder._session(root))) or "afk everywhere (default)"))
    return lines


def mark(root: Path) -> None:
    (root / MARK).write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}), encoding="utf-8")


def session_line(root: Path) -> str:
    everything = items.load_all(root / "greenfield" / "items")
    live = ladder.live_parts(root)
    waiting = sum(1 for i in everything.values() if i.state in ("ready-for-human", "needs-info"))
    return (f"greenfield-pipeline: {len(items.frontier(everything, live))} item(s) ready for the agent, {waiting} waiting on you; "
            f"live (hitl) parts: {', '.join(sorted(live)) or 'none'}. Run /greenfield-pipeline:catchup for the detail.")
