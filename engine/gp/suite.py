"""Suite schema (plan section 5.1). `parse` is structural and needs no project; `verify` checks what a suite
cites against the project. Mechanical guarantees live here: no scored check without `from`, no `example:` that
is not confirmed, no scored case with nothing to check."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import canonical, jsonschema_lite, paths

OPS = ("eq", "ne", "contains", "not_contains", "matches", "exists", "absent", "count", "lt", "lte", "gt", "gte",
       "schema")
NO_VALUE = ("exists", "absent")
TYPES, SEVERITIES, EXPECTS = ("positive", "negative", "edge"), ("critical", "major", "minor"), ("score", "observe")
DIMENSIONS = ("functional", "security", "performance", "accessibility", "reliability")
FROM_RE = re.compile(r"^(structural|example:EX-\d+|contract:\S+|canonical:\S+)$")
_CHECK_KEYS = {"path", "op", "value", "from", "rule"}
_CASE_KEYS = {"id", "name", "type", "severity", "expect", "setup", "steps", "final_check"}
_SUITE_KEYS = {"ac", "baseline_sha", "contract_sha", "surface", "dimension", "stand_in", "manual", "cases",
               "judge_runs"}


class SuiteError(ValueError):
    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class Case:
    id: str
    name: str
    type: str
    severity: str
    expect: str = "score"
    setup: dict = field(default_factory=dict)
    steps: list = field(default_factory=list)          # [{"do": {...}, "expect": [check, ...]}]
    final_check: list = field(default_factory=list)

    @property
    def driver(self) -> str:
        return next(iter(self.steps[0]["do"]))


@dataclass
class Suite:
    ac: str
    surface: str
    dimension: str
    cases: list
    baseline_sha: str = ""
    contract_sha: str = ""
    stand_in: str = "none"
    manual: bool = False
    judge_runs: int = 1
    sha: str = ""


def _check(check, where: str, scored: bool, problems: list) -> None:
    if not isinstance(check, dict):
        return problems.append(f"{where}: a check must be a mapping")
    extra = set(check) - _CHECK_KEYS
    if extra:
        problems.append(f"{where}: unknown keys {sorted(extra)}")
    if "rule" in check:
        if set(check) != {"rule"} or not str(check["rule"]).strip():
            problems.append(f"{where}: a rule check is only {{rule: <one checkable sentence>}}")
        return
    op = check.get("op")
    if op not in OPS:
        return problems.append(f"{where}: op {op!r} is not one of {', '.join(OPS)}")
    try:
        paths.parse(check.get("path"))
    except paths.PathError as exc:
        problems.append(f"{where}: {exc}")
    if op not in NO_VALUE and "value" not in check:
        problems.append(f"{where}: op {op} needs a value")
    if op == "matches":
        try:
            re.compile(str(check.get("value")))
        except re.error as exc:
            problems.append(f"{where}: bad regex ({exc})")
    if op == "count" and not isinstance(check.get("value"), int):
        problems.append(f"{where}: count needs an integer value")
    if op in ("lt", "lte", "gt", "gte") and not isinstance(check.get("value"), (int, float)):
        problems.append(f"{where}: {op} needs a number")
    if op == "schema":
        problems += [f"{where}: {p}" for p in jsonschema_lite.unsupported(check.get("value"))]
    source = check.get("from")
    if scored and not source:
        problems.append(f"{where}: a scored check needs from: (example:EX-n, contract:<file>, canonical:<id> or structural)")
    elif source and not FROM_RE.match(str(source)):
        problems.append(f"{where}: from {source!r} is not example:EX-n, contract:<file>, canonical:<id> or structural")


def parse(data, sha: str = "") -> Suite:
    problems: list[str] = []
    if not isinstance(data, dict):
        raise SuiteError(["a suite must be a mapping"])
    ac = str(data.get("ac") or "")
    for key in sorted(set(data) - _SUITE_KEYS):
        problems.append(f"unknown suite key {key!r}")
    for key in ("ac", "baseline_sha", "contract_sha", "surface", "dimension", "cases"):
        if not data.get(key):
            problems.append(f"suite needs {key}")
    if data.get("dimension") and data["dimension"] not in DIMENSIONS:
        problems.append(f"dimension {data['dimension']!r} is not one of {', '.join(DIMENSIONS)}")
    runs = data.get("judge_runs", 1)
    if not isinstance(runs, int) or runs < 1:
        problems.append("judge_runs must be an integer of 1 or more")
    cases, seen = [], set()
    for raw in data.get("cases") or []:
        cid = str(raw.get("id") if isinstance(raw, dict) else "?")
        where = f"{ac}/{cid}"
        if not isinstance(raw, dict):
            problems.append(f"{where}: a case must be a mapping")
            continue
        problems += [f"{where}: unknown case key {k!r}" for k in sorted(set(raw) - _CASE_KEYS)]
        if cid in seen:
            problems.append(f"{where}: duplicate case id")
        seen.add(cid)
        for key, allowed in (("type", TYPES), ("severity", SEVERITIES)):
            if raw.get(key) not in allowed:
                problems.append(f"{where}: {key} must be one of {', '.join(allowed)}")
        expect = raw.get("expect", "score")
        if expect not in EXPECTS:
            problems.append(f"{where}: expect must be score or observe")
        scored = expect == "score"
        steps = []
        for n, step in enumerate(raw.get("steps") or []):
            do = step.get("do") if isinstance(step, dict) else None
            if not isinstance(do, dict) or len(do) != 1:
                problems.append(f"{where} step {n}: do needs exactly one driver key")
                continue
            checks = step.get("expect") or []
            for k, chk in enumerate(checks):
                _check(chk, f"{where} step {n} check {k}", scored, problems)
            steps.append({"do": do, "expect": checks})
        if not steps:
            problems.append(f"{where}: a case needs at least one step")
        elif len({next(iter(s["do"])) for s in steps}) > 1:
            problems.append(f"{where}: one case uses one driver; steps mix {sorted({next(iter(s['do'])) for s in steps})}")
        final = raw.get("final_check") or []
        for k, chk in enumerate(final):
            _check(chk, f"{where} final_check {k}", scored, problems)
            if isinstance(chk, dict) and "rule" in chk:
                problems.append(f"{where} final_check {k}: a rule check belongs on a step")
        if scored and not data.get("manual") and not any(c for s in steps for c in s["expect"]) and not final:
            problems.append(f"{where}: a scored case with no checks would pass on nothing")
        if steps:
            cases.append(Case(cid, str(raw.get("name") or ""), raw.get("type"), raw.get("severity"), expect,
                              raw.get("setup") or {}, steps, final))
    if problems:
        raise SuiteError(problems)
    return Suite(ac, data["surface"], data["dimension"], cases, str(data["baseline_sha"]),
                 str(data["contract_sha"]), str(data.get("stand_in") or "none"), bool(data.get("manual")),
                 runs, sha)


def load(path: Path) -> Suite:
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise SuiteError([f"{path.name}: not valid YAML ({exc})"]) from exc
    return parse(data, hashlib.sha256(raw).hexdigest())


def _checks(case: Case):
    for n, step in enumerate(case.steps):
        for chk in step["expect"]:
            yield f"step {n}", chk
    for chk in case.final_check:
        yield "final_check", chk


def verify(suite: Suite, project: Path) -> list[str]:
    """What the suite cites must exist: confirmed examples, contract files, canonical requirement ids."""
    found = canonical.load(project)
    contracts = project / "greenfield" / "design" / "contracts"
    problems = []
    for case in suite.cases:
        for where, chk in _checks(case):
            source = str(chk.get("from") or "")
            tag = f"{suite.ac}/{case.id} {where}"
            if source.startswith("example:"):
                ex = found["examples"].get(source[8:])
                if ex is None:
                    problems.append(f"{tag}: {source} is not in the canonical")
                elif not canonical.confirmed(ex):
                    problems.append(f"{tag}: {source} is not confirmed (needs a non-agent source, confirmed_by and confirmed_on)")
            elif source.startswith("contract:") and not (contracts / source[9:]).is_file():
                problems.append(f"{tag}: {source} is not under greenfield/design/contracts/")
            elif source.startswith("canonical:") and source[10:] not in found["requirements"]:
                problems.append(f"{tag}: {source} is not a requirement id in the canonical")
    return problems


def load_all(project: Path) -> list[Suite]:
    return [load(p) for p in sorted((project / "greenfield" / "suites").glob("*.yaml"))]
