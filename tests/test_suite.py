import copy

import pytest

from conftest import suite_dict, write_canonical
from gp import suite
from gp.suite import SuiteError


def problems(data):
    with pytest.raises(SuiteError) as exc:
        suite.parse(data)
    return " | ".join(exc.value.problems)


def first_step_checks(data):
    return data["cases"][0]["steps"][0]["expect"]


def test_the_base_suite_parses():
    s = suite.parse(suite_dict())
    assert s.ac == "AC-1" and s.cases[0].driver == "http" and s.stand_in == "none"


def test_a_scored_check_with_no_from_is_refused():
    data = suite_dict()
    del first_step_checks(data)[0]["from"]
    assert "needs from:" in problems(data)


def test_a_final_check_with_no_from_is_refused():
    data = suite_dict()
    del data["cases"][0]["final_check"][0]["from"]
    assert "final_check 0" in problems(data)


def test_observe_cases_need_no_from():
    data = suite_dict()
    data["cases"][0]["expect"] = "observe"
    del first_step_checks(data)[0]["from"]
    assert suite.parse(data).cases[0].expect == "observe"


def test_a_rule_check_needs_no_from():
    data = suite_dict()
    first_step_checks(data).append({"rule": "the response exposes no internal id"})
    assert suite.parse(data)


@pytest.mark.parametrize("bad", ["magic", "example:1", "contract:", "canonical:", "structural "])
def test_from_must_be_one_of_the_four_forms(bad):
    data = suite_dict()
    first_step_checks(data)[0]["from"] = bad
    assert "is not example" in problems(data)


def test_mechanical_refusals():
    cases = {
        "op": lambda d: first_step_checks(d)[0].update(op="roughly"),
        "needs a value": lambda d: first_step_checks(d)[0].pop("value"),
        "must start with": lambda d: first_step_checks(d)[0].update(path="status"),
        "bad regex": lambda d: first_step_checks(d)[1].update(value="(["),
        "count needs": lambda d: first_step_checks(d)[0].update(op="count", value="two"),
        "unknown keys": lambda d: first_step_checks(d)[0].update(note="x"),
        "unknown case key": lambda d: d["cases"][0].update(notes="x"),
        "unknown suite key": lambda d: d.update(owner="x"),
        "dimension": lambda d: d.update(dimension="vibes"),
        "type must be": lambda d: d["cases"][0].update(type="happy"),
        "judge_runs": lambda d: d.update(judge_runs=0),
        "suite needs cases": lambda d: d.update(cases=[]),
        "exactly one driver": lambda d: d["cases"][0]["steps"][0].update(do={"http": {}, "cli": {}}),
        "belongs on a step": lambda d: d["cases"][0]["final_check"].append({"rule": "x"}),
    }
    for needle, mutate in cases.items():
        data = copy.deepcopy(suite_dict())
        mutate(data)
        assert needle in problems(data), needle


def test_a_scored_case_with_nothing_to_check_is_refused():
    data = suite_dict()
    data["cases"][0]["steps"] = [{"do": {"http": {"path": "/"}}, "expect": []}]
    data["cases"][0]["final_check"] = []
    assert "pass on nothing" in problems(data)


def test_one_case_uses_one_driver_and_ids_are_unique():
    data = suite_dict()
    data["cases"][0]["steps"][1]["do"] = {"cli": {"cmd": "x"}}
    assert "steps mix" in problems(data)
    data = suite_dict()
    data["cases"].append(copy.deepcopy(data["cases"][0]))
    assert "duplicate case id" in problems(data)


def test_an_unsupported_schema_keyword_is_refused_not_ignored():
    data = suite_dict()
    first_step_checks(data)[0].update(op="schema", value={"type": "object", "oneOf": []})
    assert "oneOf" in problems(data)


def test_all_problems_are_reported_together():
    data = suite_dict(dimension="vibes")
    del first_step_checks(data)[0]["from"]
    data["cases"][0]["severity"] = "huge"
    with pytest.raises(SuiteError) as exc:
        suite.parse(data)
    assert len(exc.value.problems) >= 3


# --- verify against the project -----------------------------------------------------------------------------

def verify(project, data):
    return suite.verify(suite.parse(data), project)


def test_an_unconfirmed_example_is_refused(project):
    write_canonical(project)
    for ex in ("EX-2", "EX-3"):          # EX-2 source is agent, EX-3 has no confirmed_by
        data = suite_dict()
        data["cases"][0]["final_check"][0]["from"] = f"example:{ex}"
        out = verify(project, data)
        assert any(f"{ex} is not confirmed" in p for p in out), ex


def test_a_confirmed_example_a_known_requirement_and_a_present_contract_pass(project):
    write_canonical(project)
    assert verify(project, suite_dict()) == []


def test_unknown_example_requirement_and_contract_are_refused(project):
    write_canonical(project)
    data = suite_dict()
    data["cases"][0]["final_check"][0]["from"] = "example:EX-9"
    first_step_checks(data)[1]["from"] = "canonical:AC-99"
    first_step_checks(data)[0]["from"] = "contract:links.yaml"
    out = " | ".join(verify(project, data))
    assert "EX-9 is not in the canonical" in out and "AC-99" in out and "links.yaml" in out
    (project / "greenfield" / "design" / "contracts" / "links.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
    assert "links.yaml" not in " | ".join(verify(project, data))


def test_with_no_canonical_every_example_reference_is_refused(project):
    assert any("EX-1" in p for p in verify(project, suite_dict()))
