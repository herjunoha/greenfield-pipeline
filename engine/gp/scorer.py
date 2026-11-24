"""The scorer (plan section 5): checks over a JSON observation, whatever produced it.
Rules it never bends: a path it cannot read fails (only `absent` passes on a missing path); a driver error is
`error`, never `fail` (red means an assertion failed on reachable software); a rule check nobody judged is
`pending`, never a pass. It reads driver output and tim's judgment files only, never the builder's notes."""
from __future__ import annotations

import re

from . import jsonschema_lite, paths
from .paths import MISSING
from .suite import Case

CASE_ORDER = ("fail", "error", "not-run", "pending", "manual", "pass")   # AC verdict takes the first present


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _same(a, b) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def evaluate(check: dict, root) -> tuple[bool, object, str]:
    """-> (ok, actual, detail). Raises nothing: an unreadable path is a failed check."""
    op, expected = check["op"], check.get("value")
    actual = paths.get(root, check["path"])
    if actual is MISSING:
        return (op == "absent"), None, "path not readable" if op != "absent" else "path absent"
    if op == "absent":
        return False, actual, "path is present"
    if op == "exists":
        return True, actual, ""
    if op == "eq":
        return _same(actual, expected), actual, ""
    if op == "ne":
        return not _same(actual, expected), actual, ""
    if op in ("contains", "not_contains"):
        if isinstance(actual, (str, list, dict)) and (not isinstance(actual, str) or isinstance(expected, str)):
            return (expected in actual) == (op == "contains"), actual, ""
        return False, actual, f"{op} cannot apply to {type(actual).__name__}"
    if op == "matches":
        if not isinstance(actual, str):
            return False, actual, "matches needs a string"
        return re.search(str(expected), actual) is not None, actual, ""
    if op == "count":
        if not isinstance(actual, (list, dict, str)):
            return False, actual, "count needs a list, object or string"
        return len(actual) == expected, len(actual), ""
    if op in ("lt", "lte", "gt", "gte"):
        if not _num(actual):
            return False, actual, f"{op} needs a number"
        ok = {"lt": actual < expected, "lte": actual <= expected, "gt": actual > expected,
              "gte": actual >= expected}[op]
        return ok, actual, ""
    if op == "schema":
        errors = jsonschema_lite.validate(actual, expected)
        return not errors, actual, "; ".join(errors[:3])
    return False, actual, f"unknown op {op}"


def _judged(judgments: dict | None, step: int, rule: str):
    """True, False, or None when nobody judged it. Majority of `votes` when several runs voted."""
    for entry in (judgments or {}).get("rules", []):
        if entry.get("step") == step and entry.get("rule") == rule:
            votes = entry.get("votes")
            if votes:
                return sum(bool(v) for v in votes) * 2 > len(votes)
            return bool(entry["pass"]) if "pass" in entry else None
    return None


def score_case(case: Case, record: dict | None, judgments: dict | None = None) -> dict:
    out = {"case": case.id, "severity": case.severity, "type": case.type, "checks": [], "error": None}
    if record is None:
        return {**out, "status": "not-run"}
    error = record.get("error")
    if record.get("manual") or str(error or "").startswith("manual step"):
        return {**out, "status": "manual", "error": error}
    observed = record.get("steps") or []
    state = {"state": record.get("final_state") if isinstance(record.get("final_state"), dict) else {}}
    results, missing = [], False
    for n, step in enumerate(case.steps):
        root = observed[n].get("observed") if n < len(observed) and isinstance(observed[n], dict) else None
        if root is None:
            missing = True
            continue
        for chk in step["expect"]:
            if "rule" in chk:
                verdict = _judged(judgments, n, chk["rule"])
                results.append({"where": f"step {n}", "rule": chk["rule"], "ok": verdict,
                                "detail": "not judged" if verdict is None else ""})
            else:
                ok, actual, detail = evaluate(chk, root)
                results.append({"where": f"step {n}", "path": chk["path"], "op": chk["op"], "from": chk.get("from"),
                                "ok": ok, "actual": actual, "detail": detail})
    if not error and not missing:
        for chk in case.final_check:
            ok, actual, detail = evaluate(chk, state)
            results.append({"where": "final_check", "path": chk["path"], "op": chk["op"], "from": chk.get("from"),
                            "ok": ok, "actual": actual, "detail": detail})
    out["checks"] = results
    if case.expect == "observe":
        return {**out, "status": "observed", "error": error}
    if any(r["ok"] is False for r in results):
        status = "fail"
    elif error or missing:
        status = "error"
        out["error"] = error or "the driver returned no observation for a step"
    elif any(r["ok"] is None for r in results):
        status = "pending"
    else:
        status = "pass"
    return {**out, "status": status}


def ac_verdict(case_results: list[dict]) -> str:
    scored = [r["status"] for r in case_results if r["status"] != "observed"]
    for status in CASE_ORDER:
        if status in scored:
            return {"not-run": "incomplete"}.get(status, status)
    return "unscored"
