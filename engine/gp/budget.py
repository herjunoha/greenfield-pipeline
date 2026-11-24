"""The project ceiling (plan 7.5), on things the plugin can count: full runs with no progress on one AC, builds, and a
deadline. Reaching a limit raises a `ready-for-human` item and stops that line of work. The plugin cannot read token
spend reliably, so the owner sets a token or cost limit in their own harness or plan; this module does not pretend."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from . import items, progress
from .project import load_fence

DEFAULT = {"runs_per_ac": 3, "builds_total": 200, "deadline": None}
BRIEF = """\
**What.** {what}

**Why now.** The ceiling is the owner's: it stops this line of work so effort does not run on past what was agreed.

**Options.**
- Raise the ceiling: the owner edits `budget:` in fence.yaml (a higher budget is a loosening and needs rex's countersign).
- Change the approach: a different cut of the AC, a different design, or a question for the sponsor.
- Stop here and record the AC as not met on the limits page.

**The agent's pick.** Stop and ask: more of the same attempt is the one thing the numbers say is not working.

**If wrong.** Stopping early leaves an AC undelivered; continuing spends effort the owner did not agree to.

**If nobody answers.** {line} stays stopped. Other work continues.
"""


class BudgetError(ValueError):
    pass


def config(root: Path) -> dict:
    raw = load_fence(root).get("budget") or {}
    merged = {**DEFAULT, **(raw if isinstance(raw, dict) else {})}
    for key in ("runs_per_ac", "builds_total"):
        if not isinstance(merged[key], int) or merged[key] < 1:
            raise BudgetError(f"fence.yaml budget.{key} must be a whole number of at least 1")
    if merged["deadline"] is not None:
        try:
            merged["deadline"] = date.fromisoformat(str(merged["deadline"]))
        except ValueError:
            raise BudgetError("fence.yaml budget.deadline must be a date (YYYY-MM-DD) or null")
    return merged


def stalled(runs: list[dict], ac: str) -> int:
    """Consecutive full runs of this AC since a case last passed that had not passed before. A run whose latest
    verdict is a full pass has nothing stalled."""
    best, count = set(), 0
    for run in (r for r in runs if r["full"] and ac in r["acs"]):
        passed = {c for c, s in run["acs"][ac]["cases"].items() if s == "pass"}
        count = 0 if passed - best else count + 1
        best |= passed
        if run["acs"][ac]["verdict"] == "pass":
            count = 0
    return count


def builds_made(root: Path) -> int:
    path = root / "greenfield" / "builds.tsv"
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]) if path.is_file() else 0


def reached(root: Path, acs: list[str] | None = None) -> list[dict]:
    """Limits reached now. `acs` limits the per-AC check to those ACs; None means every AC with runs."""
    cfg, runs = config(root), progress.load_runs(root)
    out = []
    for ac in sorted({a for r in runs for a in r["acs"]} if acs is None else acs):
        n = stalled(runs, ac)
        if n >= cfg["runs_per_ac"]:
            out.append({"key": f"budget:runs:{ac}", "line": ac,
                        "what": f"{ac} has had {n} full runs in a row with no newly passing case (the ceiling is "
                                f"{cfg['runs_per_ac']})."})
    if builds_made(root) >= cfg["builds_total"]:
        out.append({"key": "budget:builds", "line": "building",
                    "what": f"{builds_made(root)} builds were recorded (the ceiling is {cfg['builds_total']})."})
    if cfg["deadline"] and date.today() > cfg["deadline"]:
        out.append({"key": "budget:deadline", "line": "all work",
                    "what": f"The deadline {cfg['deadline']} has passed."})
    return out


def raise_items(root: Path, hits: list[dict]) -> list[str]:
    folder, ids = root / "greenfield" / "items", []
    existing = {i.source: i for i in items.load_all(folder).values()}
    for hit in hits:
        held = existing.get(hit["key"])
        if held is None:
            held = items.mint(folder, title=f"Ceiling reached: {hit['line']}", state="ready-for-human",
                              source=hit["key"], body=BRIEF.format(what=hit["what"], line=hit["line"]))
        ids.append(held.id)
    return ids


def guard(root: Path, what: str, acs: list[str] | None = None) -> None:
    """Refuse the work a reached limit stops, after raising the item that asks the owner. `what` is run or build."""
    hits = reached(root, acs if what == "run" else [])
    stops = [h for h in hits if h["key"] != "budget:builds"] if what == "run" else hits
    if stops:
        ids = raise_items(root, stops)
        raise BudgetError("; ".join(f"{h['what']} Item {i} waits on the owner." for h, i in zip(stops, ids)))
