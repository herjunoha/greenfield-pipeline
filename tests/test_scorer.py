import pytest

from gp import scorer, suite
from gp.paths import MISSING, PathError, get, parse


def chk(op, value=None, path="$.v", **kw):
    return {"path": path, "op": op, "value": value, **kw}


@pytest.mark.parametrize("check,root,ok", [
    (chk("eq", 5), {"v": 5}, True),
    (chk("eq", 1), {"v": True}, False),          # a boolean is not the number 1
    (chk("eq", True), {"v": 1}, False),
    (chk("ne", 5), {"v": 6}, True),
    (chk("contains", "ell"), {"v": "hello"}, True),
    (chk("contains", 2), {"v": [1, 2]}, True),
    (chk("contains", "k"), {"v": {"k": 1}}, True),
    (chk("not_contains", "z"), {"v": "hello"}, True),
    (chk("matches", "^h.*o$"), {"v": "hello"}, True),
    (chk("matches", "x"), {"v": 5}, False),
    (chk("exists"), {"v": None}, True),           # present and null is present
    (chk("absent"), {"v": 1}, False),
    (chk("count", 2), {"v": [1, 2]}, True),
    (chk("count", 3), {"v": [1, 2]}, False),
    (chk("lt", 5), {"v": 4}, True),
    (chk("lte", 5), {"v": 5}, True),
    (chk("gt", 5), {"v": 5}, False),
    (chk("gte", 5), {"v": 5}, True),
    (chk("gt", 0), {"v": True}, False),           # a boolean is not a number
    (chk("schema", {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}}),
     {"v": {"a": 1}}, True),
    (chk("schema", {"type": "object", "required": ["a"]}), {"v": {}}, False),
    (chk("schema", {"type": "integer"}), {"v": True}, False),
])
def test_ops(check, root, ok):
    assert scorer.evaluate(check, root)[0] is ok


@pytest.mark.parametrize("op", ["eq", "ne", "contains", "not_contains", "matches", "exists", "count", "lt", "lte",
                                "gt", "gte", "schema"])
def test_an_unreadable_path_fails_every_op_except_absent(op):
    ok, _, detail = scorer.evaluate(chk(op, 1 if op != "schema" else {"type": "integer"}, path="$.nope"), {"v": 1})
    assert ok is False and "not readable" in detail


def test_absent_passes_on_a_missing_path():
    assert scorer.evaluate(chk("absent", path="$.nope"), {"v": 1})[0] is True


def test_paths():
    doc = {"a": [{"b": 1}, {"b": 2}], "x y": 3}
    assert get(doc, "$.a[1].b") == 2 and get(doc, "$.a[-1].b") == 2 and get(doc, "$['x y']") == 3
    assert get(doc, "$.a[5]") is MISSING and get(doc, "$.a.b") is MISSING and get(doc, "$") == doc
    for bad in ("a.b", "$..a", "$.a[", ""):
        with pytest.raises(PathError):
            parse(bad)


# --- case scoring -------------------------------------------------------------------------------------------

def case_from(steps, final=None, expect="score"):
    return suite.parse({"ac": "AC-1", "baseline_sha": "b", "contract_sha": "c", "surface": "s",
                        "dimension": "functional", "cases": [{
                            "id": "TC-01", "name": "n", "type": "positive", "severity": "major", "expect": expect,
                            "steps": steps, "final_check": final or []}]}).cases[0]


def step(*checks):
    return {"do": {"http": {"path": "/"}}, "expect": list(checks)}


STATUS_200 = {"path": "$.status", "op": "eq", "value": 200, "from": "structural"}


def record(status=200, error=None, steps=1, final_state=None):
    return {"steps": [{"observed": {"status": status}} for _ in range(steps)], "error": error,
            "final_state": final_state or {}}


def test_pass_and_fail():
    c = case_from([step(STATUS_200)])
    assert scorer.score_case(c, record(200))["status"] == "pass"
    assert scorer.score_case(c, record(500))["status"] == "fail"


def test_a_final_check_path_the_driver_cannot_read_fails():
    c = case_from([step(STATUS_200)], final=[{"path": "$.state.links", "op": "eq", "value": 1, "from": "structural"}])
    result = scorer.score_case(c, record(200, final_state={}))
    assert result["status"] == "fail"
    assert result["checks"][-1]["where"] == "final_check" and result["checks"][-1]["ok"] is False
    # and it does not read null as a pass
    c2 = case_from([step(STATUS_200)], final=[{"path": "$.state.links", "op": "ne", "value": 5, "from": "structural"}])
    assert scorer.score_case(c2, record(200, final_state={}))["status"] == "fail"
    assert scorer.score_case(c, record(200, final_state={"links": 1}))["status"] == "pass"


def test_a_driver_error_is_an_error_not_a_fail():
    c = case_from([step(STATUS_200)])
    result = scorer.score_case(c, {"steps": [], "error": "step 0: ConnectionRefusedError", "final_state": {}})
    assert result["status"] == "error" and "Connection" in result["error"]


def test_error_after_a_failed_assertion_is_still_a_fail():
    c = case_from([step(STATUS_200), step(STATUS_200)])
    assert scorer.score_case(c, record(500, error="boom", steps=1))["status"] == "fail"


def test_a_step_with_no_observation_is_an_error():
    c = case_from([step(STATUS_200), step(STATUS_200)])
    assert scorer.score_case(c, record(200, steps=1))["status"] == "error"


def test_a_rule_check_nobody_judged_is_pending():
    c = case_from([step({"rule": "the response exposes no internal id"})])
    assert scorer.score_case(c, record())["status"] == "pending"
    yes = {"rules": [{"step": 0, "rule": "the response exposes no internal id", "pass": True}]}
    no = {"rules": [{"step": 0, "rule": "the response exposes no internal id", "pass": False}]}
    assert scorer.score_case(c, record(), yes)["status"] == "pass"
    assert scorer.score_case(c, record(), no)["status"] == "fail"


def test_judge_votes_take_the_majority():
    c = case_from([step({"rule": "r"})])
    two_of_three = {"rules": [{"step": 0, "rule": "r", "votes": [True, False, True]}]}
    one_of_three = {"rules": [{"step": 0, "rule": "r", "votes": [True, False, False]}]}
    assert scorer.score_case(c, record(), two_of_three)["status"] == "pass"
    assert scorer.score_case(c, record(), one_of_three)["status"] == "fail"


def test_observe_manual_and_not_run():
    c = case_from([step(STATUS_200)], expect="observe")
    assert scorer.score_case(c, record(500))["status"] == "observed"
    c = case_from([step(STATUS_200)])
    assert scorer.score_case(c, {"manual": True, "error": "manual step, needs the owner", "steps": []})["status"] == "manual"
    assert scorer.score_case(c, None)["status"] == "not-run"


def test_ac_verdict_priority():
    def v(*statuses):
        return scorer.ac_verdict([{"status": s} for s in statuses])
    assert v("pass", "pass") == "pass"
    assert v("pass", "fail", "error") == "fail"
    assert v("pass", "error", "pending") == "error"
    assert v("pass", "not-run") == "incomplete"
    assert v("pass", "manual") == "manual"
    assert v("observed") == "unscored" and v("pass", "observed") == "pass"
