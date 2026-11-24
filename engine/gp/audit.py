"""The audit behind `gp acs` (plan 4.1, 4.2): schema, orphans, shas, assumptions, regulated data, baseline needs.
`problems` refuse (exit 1); `notes` inform and never fail, because work may start on a draft."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import canonical, canonical_schema, items as itemlib, progress, suitecheck

BENIGN = ("personal", "credentials", "none")      # classes that raise no regulated-data item


@dataclass
class Report:
    data: dict | None = None
    problems: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    blockers: list = field(default_factory=list)     # what stops handover (step 6 reads this)
    raises: list = field(default_factory=list)       # items `gp raise` would mint


def sha12(raw: bytes | str) -> str:
    raw = raw.encode("utf-8") if isinstance(raw, str) else raw
    return hashlib.sha256(raw).hexdigest()[:12]


def load(root: Path) -> tuple[dict | None, list[str]]:
    files = sorted((root / "greenfield" / "requirements").glob("*.canonical.yaml"))
    if not files:
        return None, []
    if len(files) > 1:
        return None, ["one canonical per project, found " + ", ".join(f.name for f in files)]
    try:
        data = yaml.safe_load(files[0].read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, [f"{files[0].name}: not valid YAML ({exc})"]
    problems = canonical_schema.check(data, root)
    return (data if isinstance(data, dict) else None), [f"{files[0].name}: {p}" for p in problems]


def ac_sha(req: dict) -> str:
    keys = ("statement", "acceptance", "dimension", "surface")
    return sha12(json.dumps({k: req.get(k) for k in keys}, sort_keys=True, ensure_ascii=False))


def contract_sha(root: Path, data: dict, surface: str) -> str:
    row = next((s for s in data["project"]["surfaces"] if s.get("name") == surface), None)
    iface = (row or {}).get("interface")
    if not iface:
        return "none"
    path = root / "greenfield" / "design" / "contracts" / iface
    return sha12(path.read_bytes().replace(b"\r\n", b"\n")) if path.is_file() else "missing"


def source_problem(source, root: Path, items: dict) -> str | None:
    """A requirement's source is a file under greenfield/sources/ (optionally #anchor) or a closed item that
    recorded an accepted decision. Anything else is an orphan."""
    source = str(source or "").strip()
    if not source:
        return "no source"
    found = re.match(r"^item:(I-\d+)$", source)
    if found:
        item = items.get(found.group(1))
        ok = item is not None and item.state == "closed" and item.reason == "done"
        return None if ok else f"{source} is not a closed item"
    name = source.split("#", 1)[0]
    if not name or ".." in name or ":" in name or name.startswith(("/", "\\")):
        return f"source {source!r} is not a file under greenfield/sources/ or an item"
    if not (root / "greenfield" / "sources" / name).is_file():
        return f"source {name} is not under greenfield/sources/"
    return None


def open_assumptions(items: dict) -> dict[str, list[str]]:
    """AC id -> assumption items it depends on that are not closed done. A wontfix keeps the AC assumed:
    dropping a fact is not proving it."""
    out: dict[str, list[str]] = {}
    for item in items.values():
        if item.kind == "assumption" and not (item.state == "closed" and item.reason == "done"):
            for ac in item.acs:
                out.setdefault(ac, []).append(item.id)
    return out


def regulated_triggers(data: dict) -> list[str]:
    proj = data["project"]
    classes = sorted({c for c in proj.get("data_classes") or [] if c not in BENIGN})
    return classes + sorted(set(proj.get("regulated") or []))


def regulated_source(triggers: list[str]) -> str:
    return "canonical:regulated:" + "+".join(triggers)


def _notes(data: dict, items: dict) -> list[str]:
    notes = []
    for ex in data.get("examples") or []:
        if not canonical.confirmed(ex):
            notes.append(f"example {ex.get('id')} is not confirmed; suites cannot cite it")
    unconfirmed = [g["term"] for g in data["project"].get("glossary") or [] if not g.get("confirmed")]
    for req in data["requirements"]:
        text = f"{req.get('statement')} {req.get('acceptance')}"
        for term in unconfirmed:
            if re.search(rf"\b{re.escape(term)}\b", text, re.I):
                notes.append(f"{req['id']} uses the unconfirmed term {term!r}; the sponsor confirms it before suites use it")
    for need, why in baseline_gaps(data, items):
        notes.append(f"baseline need {need}: {why}")
    return notes


def baseline_gaps(data: dict, items: dict) -> list[tuple[str, str]]:
    stated = {r.get("baseline") for r in data["requirements"]}
    raised = {i.source for i in items.values()}
    return [(n, "no AC states it and no item holds it (gp raise)") for n in canonical_schema.BASELINE_NEEDS
            if n not in stated and f"baseline:{n}" not in raised]


def raise_plan(data: dict, items: dict) -> list[dict]:
    plan = []
    triggers = regulated_triggers(data)
    held = {i.source for i in items.values()}
    if triggers and regulated_source(triggers) not in held:
        plan.append({"title": "Regulated data: name the regime or confirm none applies", "state": "ready-for-human",
                     "source": regulated_source(triggers), "body": REGULATED_BRIEF.format(what=", ".join(triggers))})
    for need, _ in baseline_gaps(data, items):
        plan.append({"title": f"Baseline need: {need.replace('_', ' ')}", "state": "needs-triage",
                     "source": f"baseline:{need}", "body": BASELINE_STUB.format(need=need)})
    return plan


def run(root: Path) -> Report:
    report = Report()
    report.data, report.problems = load(root)
    if report.data is None or report.problems:
        return report
    data = report.data
    items = itemlib.load_all(root / "greenfield" / "items")
    assumed, suites, facts = open_assumptions(items), suitecheck.suites(root, data), progress.Facts(root, data)
    for req in data["requirements"]:
        why = source_problem(req.get("source"), root, items)
        if why:
            report.problems.append(f"{req['id']}: orphan, {why}")
        suite_state, suite = suites.get(req["id"], ("none", None))
        state, missing = progress.state(facts, req["id"], suite, suite_state, bool(assumed.get(req["id"])))
        report.rows.append({"id": req["id"], "dimension": req["dimension"], "surface": req["surface"],
                            "baseline_sha": ac_sha(req), "contract_sha": contract_sha(root, data, req["surface"]),
                            "suite": suite_state, "state": state, "missing": missing,
                            "assumptions": assumed.get(req["id"], [])})
    report.notes = _notes(data, items)
    triggers = regulated_triggers(data)
    held = [i for i in items.values() if i.source == regulated_source(triggers)]
    if triggers and not any(i.state == "closed" and i.reason == "done" for i in held):
        report.blockers.append("regulated data: " + ", ".join(triggers) + " (item open or not yet raised)")
    report.raises = raise_plan(data, items)
    return report


REGULATED_BRIEF = """\
**What.** The software handles data in a class that is often regulated ({what}), or the sponsor named a regime.
Name the regime that applies, or confirm that none does.

**Why now.** The data model and the controls around this data are designed from it, and the handover must state
what was and was not assessed.

**Options.**
- Name the regime(s): the design then adds the controls they require, each as an AC.
- Confirm none applies: recorded as the sponsor's statement with its date; nothing is added.

**The agent's pick.** None. The agent cannot know which regime governs the sponsor's data, and a guess from
memory would only be an assumption (source: none).

**If wrong.** A regime found late means rework of the design and the builds around this data.

**If nobody answers.** Work continues on a draft baseline. Handover stays blocked, and the limits page says
compliance was not assessed by this pipeline.
"""
BASELINE_STUB = """\
Baseline need: {need}. No source specified it. Plate: write the full brief here (what, why now, the options and
what each changes, the agent's pick with its source, what breaks if the pick is wrong, what happens if nobody
answers), then move this item to ready-for-human. A stated or accepted answer becomes an AC with
`baseline: {need}`.
"""
