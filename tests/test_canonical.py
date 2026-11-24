import copy
import datetime

import pytest
import yaml

from conftest import CANONICAL
from gp import canonical_schema as cs


def good():
    return copy.deepcopy(CANONICAL)


def problems(data, root=None):
    return " | ".join(cs.check(data, root))


MUTATIONS = {
    "status must be": lambda d: d["project"].update(status="final"),
    "unknown keys": lambda d: d["project"].update(owner="x"),
    "unknown keys ['extra']": lambda d: d.update(extra=1),
    "at least one surface": lambda d: d["project"].update(surfaces=[]),
    "kind 'robot'": lambda d: d["project"]["surfaces"][0].update(kind="robot"),
    "duplicate surface": lambda d: d["project"]["surfaces"].append(copy.deepcopy(d["project"]["surfaces"][0])),
    "interface must be a file name": lambda d: d["project"]["surfaces"][0].update(interface="../x.yaml"),
    "data_classes is required": lambda d: d["project"].update(data_classes=[]),
    "data_classes must come from": lambda d: d["project"].update(data_classes=["pii"]),
    "cannot sit beside": lambda d: d["project"].update(data_classes=["none", "health"]),
    "id must look like AC-1": lambda d: d["requirements"][0].update(id="R1"),
    "duplicate id AC-1": lambda d: d["requirements"][1].update(id="AC-1"),
    "dimension must be": lambda d: d["requirements"][0].update(dimension="vibes"),
    "is not declared under project.surfaces": lambda d: d["requirements"][0].update(surface="nowhere"),
    "acceptance is one observable line": lambda d: d["requirements"][0].update(acceptance="a\nb"),
    "statement is required": lambda d: d["requirements"][0].update(statement=""),
    "baseline must be one of": lambda d: d["requirements"][0].update(baseline="speed"),
    "at least one acceptance criterion": lambda d: d.update(requirements=[]),
    "id must look like EX-1": lambda d: d["examples"][0].update(id="E1"),
    "source must be sponsor-confirmed": lambda d: d["examples"][0].update(source="memory"),
    "never a name": lambda d: d["examples"][0].update(confirmed_by="Jane Doe"),
    "confirmed_on must be a date": lambda d: d["examples"][0].update(confirmed_on="tomorrow"),
    "serves AC-9": lambda d: d["examples"][0].update(serves=["AC-9"]),
    "given must be a mapping": lambda d: d["examples"][0].update(given="x"),
    "confirmed must be true or false": lambda d: d["project"].update(
        glossary=[{"term": "t", "meaning": "m", "source": "s", "confirmed": "yes"}]),
    "duplicate term": lambda d: d["project"].update(
        glossary=[{"term": "T", "meaning": "m", "source": "s", "confirmed": True},
                  {"term": "t", "meaning": "m", "source": "s", "confirmed": True}]),
}


def test_the_base_canonical_is_valid():
    assert cs.check(good()) == []


@pytest.mark.parametrize("needle", MUTATIONS)
def test_each_malformed_canonical_is_refused(needle):
    data = good()
    MUTATIONS[needle](data)
    assert needle in problems(data), needle


def test_a_non_mapping_is_refused_and_all_problems_come_together():
    assert "must be a mapping" in problems([])
    data = good()
    data["project"]["status"] = "final"
    data["requirements"][0]["dimension"] = "vibes"
    data["examples"][0]["id"] = "E1"
    assert len(cs.check(data)) >= 3


def test_an_unconfirmed_example_is_legal_it_is_a_proposal():
    assert cs.check(good()) == []                      # EX-2 is source agent, EX-3 has no confirmed_by


def test_tier_two_surfaces_are_declared_not_refused():
    data = good()
    data["project"]["surfaces"].append({"name": "app", "kind": "mobile", "interface": None})
    assert cs.check(data) == []


def test_a_requirement_with_no_source_is_not_a_schema_error_the_audit_calls_it_an_orphan():
    data = good()
    del data["requirements"][0]["source"]
    assert cs.check(data) == []


def test_yaml_dates_are_accepted():
    data = yaml.safe_load(yaml.safe_dump(good()))
    data["examples"][0]["confirmed_on"] = datetime.date(2026, 11, 13)
    assert cs.check(data) == []


def test_an_interface_must_exist_once_a_project_root_is_given(project):
    data = good()
    data["project"]["surfaces"][0]["interface"] = "links.yaml"
    assert "interface links.yaml is not under" in problems(data, project)
    (project / "greenfield" / "design" / "contracts" / "links.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
    assert cs.check(data, project) == []
