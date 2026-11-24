"""Handover data (plan 4.7): everything the sponsor-facing documents are written from, read from the project's files.
It refuses while the canonical is invalid or a regulated-data item is open. It states what was NOT proven as plainly
as what was; `greenfield-pipeline` never claims compliance."""
from __future__ import annotations

import json
from pathlib import Path

from . import audit, builds, canonical_schema, environments, items as itemlib, packs, progress, reviews, suitecheck
from .project import load_fence


class HandoverError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


def _log(repo: Path, limit: int = 50) -> list[str]:
    try:
        return builds.git(repo, "log", f"-{limit}", "--pretty=format:%h %s").splitlines()
    except builds.BuildError:
        return []


def _previous(repo: Path, commit: str) -> str | None:
    try:
        return builds.git(repo, "rev-parse", "--verify", f"{commit}~1")
    except builds.BuildError:
        return None


def _latest_full(runs: list[dict], ac: str) -> dict | None:
    fulls = [r for r in runs if r["full"] and ac in r["acs"]]
    return fulls[-1] if fulls else None


def _tests(root: Path, run: dict | None, suites: dict) -> list[dict]:
    if run is None:
        return []
    out = []
    for ac, (_state, suite) in sorted(suites.items()):
        for case in (suite.cases if suite else []):
            path = root / "greenfield" / "runs" / run["name"] / "scores" / f"{ac}__{case.id}.json"
            status = json.loads(path.read_text(encoding="utf-8")).get("status") if path.is_file() else "not-run"
            out.append({"ac": ac, "case": case.id, "name": case.name, "type": case.type, "severity": case.severity,
                        "status": status, "run": run["name"]})
    return out


def data(root: Path) -> dict:
    report = audit.run(root)
    if report.data is None or report.problems:
        raise HandoverError(report.problems or ["no canonical requirement to hand over"])
    if report.blockers:
        raise HandoverError([f"handover blocked: {b}" for b in report.blockers])
    canon, folder = report.data, root / "greenfield"
    facts = progress.Facts(root, canon)
    suites = suitecheck.suites(root, canon)
    all_items = itemlib.load_all(folder / "items")
    pack_dir = Path(load_fence(root)["pack_path"]) if load_fence(root).get("pack_path") else packs.bundled()[packs.GENERIC]
    pack = packs.load(pack_dir)
    reqs = {r["id"]: r for r in canon["requirements"]}
    acs, latest = [], None
    for row in report.rows:
        run = _latest_full(facts.runs, row["id"])
        latest = run if run and (latest is None or run["name"] > latest["name"]) else latest
        acs.append({**row, "statement": reqs[row["id"]]["statement"], "acceptance": reqs[row["id"]]["acceptance"],
                    "run": run["name"] if run else None, "run_verdict": run["acs"][row["id"]]["verdict"] if run else None,
                    "build": {c: (b or {}).get("commit") for c, b in (run["build_ids"] if run else {}).items()},
                    "suite_reviewed": bool(reviews.approved(root, "suite", row["id"], reviews.subject_sha(root, "suite", row["id"])))
                    if suites.get(row["id"], ("none", None))[1] else False})
    repos = builds.repos(root)
    envs, _ = environments.load_all(root)
    doubles = sorted({d for e in envs for d in e.get("doubles") or []} |
                     {s.stand_in for _, s in suites.values() if s and s.stand_in != "none"})
    manual = sorted({a for a, (_, s) in suites.items() if s and s.manual} | {
        a["id"] for a in acs for surf in canon["project"]["surfaces"]
        if surf["name"] == a["surface"] and surf["kind"] in ("manual", *canonical_schema.TIER2)})
    assumptions = [{"id": i.id, "title": i.title, "tag": i.source, "state": i.state, "acs": i.acs}
                   for i in all_items.values() if i.kind == "assumption" and not (i.state == "closed" and i.reason == "done")]
    return {
        "project": {"name": canon["project"].get("name") or "project", "objectives": canon["project"].get("objectives") or [],
                    "out_of_scope": canon["project"].get("out_of_scope") or [], "approved": facts.approved,
                    "surfaces": canon["project"]["surfaces"], "glossary": canon["project"].get("glossary") or []},
        "roles": pack.get("roles") or {"owner": "owner", "sponsor": "sponsor"},
        "acs": acs, "tests": _tests(root, latest, suites), "examples": canon.get("examples") or [],
        "design": (folder / "design" / "architecture.md").read_text(encoding="utf-8")
        if (folder / "design" / "architecture.md").is_file() else "",
        "contracts": sorted(p.name for p in (folder / "design" / "contracts").glob("*") if p.is_file()),
        "decisions": [r for r in (folder / "decisions.tsv").read_text(encoding="utf-8").splitlines()[1:] if r.strip()],
        "releases": {r["component"]: _log(r["path"]) for r in repos},
        "rollback": {r["component"]: _previous(r["path"], (builds.read(root).get(r["component"]) or {}).get("commit", "HEAD"))
                     for r in repos},
        "limits": {"not_done": [{"id": a["id"], "state": a["state"], "stops": a["missing"]} for a in acs if a["state"] != "done"],
                   "manual": manual, "doubles": doubles, "assumptions": assumptions, "notes": report.notes,
                   "regimes": canon["project"].get("regulated") or [], "data_classes": canon["project"]["data_classes"]},
    }
