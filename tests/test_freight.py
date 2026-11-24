"""Check 7 of plan section 12 on acme-freight. The STRUCTURAL part is here and must pass every run: the mechanical
guarantees hold in a domain with business rules the model cannot know. The BEHAVIOURAL part (does the dangerous-goods
rule surface before the build) needs live sessions; only its scorer is tested here, on synthetic project folders."""
import json
import shutil
import subprocess
import sys
import time

from conftest import FIXTURES, ROOT, edit_canonical, run_gf, suite_dict, write_suite
from freight_behavior import score
from test_flow import fake_run

FREIGHT = FIXTURES / "acme-freight"
AC = "AC-3"


def freight(project):
    shutil.copytree(FREIGHT / "greenfield", project / "greenfield", dirs_exist_ok=True)
    return project


def quote_suite(source, ac=AC):
    data = suite_dict(ac=ac, surface="quote-cli")
    data["cases"] = [{"id": "TC-01", "name": "a ten kilo remote quote is rounded", "type": "positive", "severity": "major",
                      "steps": [{"do": {"cli": {"cmd": sys.executable, "args": ["-c", "print(58)"]}},
                                 "expect": [{"path": "$.stdout", "op": "contains", "value": "58", "from": source}]}]}]
    return data


def rows(project):
    return {r["id"]: r for r in json.loads(run_gf(project, "acs", "--json").stdout)["acs"]}


# --- structural -----------------------------------------------------------------------------------------------

def test_the_sources_plate_to_zero_orphans_and_the_unconfirmed_example_is_noted(project):
    freight(project)
    r = run_gf(project, "acs")
    assert r.returncode == 0 and "orphans: none" in r.stdout and "example EX-3 is not confirmed" in r.stdout


def test_a_suite_cannot_take_its_expected_value_from_an_example_nobody_confirmed(project):
    freight(project)
    write_suite(project, quote_suite("example:EX-3"), name=AC)         # the agent's proposal for the rounding rule
    out = run_gf(project, "check")
    assert out.returncode == 1 and "EX-3 is not confirmed" in out.stdout
    write_suite(project, quote_suite("example:EX-1"), name=AC)
    assert run_gf(project, "check").returncode == 0                    # a confirmed one is fine
    data = quote_suite("example:EX-1")
    del data["cases"][0]["steps"][0]["expect"][0]["from"]
    write_suite(project, data, name=AC)
    assert "needs from:" in run_gf(project, "check").stdout


def test_no_ac_is_done_while_a_memory_assumption_it_needs_is_open(project):
    freight(project)
    write_suite(project, quote_suite("canonical:AC-3"), name=AC)
    assert run_gf(project, "review", "suite", AC, "--by", "rex", "--verdict", "approve").returncode == 0
    run_gf(project, "accept-line", f"suite:{AC}")
    from gp import reviews
    sha = reviews.subject_sha(project, "suite", AC)
    from gp import suite as suitelib
    s = suitelib.load(project / "greenfield" / "suites" / f"{AC}.yaml")
    fake_run(project, "r1", "fail", s.sha, ac=AC)
    fake_run(project, "r2", "pass", s.sha, ac=AC)
    run_gf(project, "review", "run", "r2", "--by", "rex", "--verdict", "approve")
    edit_canonical(project, lambda d: d["project"].update(status="approved"))
    run_gf(project, "accept-line", "canonical")
    assert rows(project)[AC]["state"] == "done" and sha
    # the agent assumes "round up" from what it remembers of freight tariffs
    assert run_gf(project, "new", "rounding is always up", "--kind", "assumption", "--source", "memory",
                  "--acs", AC).returncode == 0
    assert rows(project)[AC]["state"] == "assumed"                     # whatever the tests say
    closing = run_gf(project, "close", "I-1", "--why", "it is what freight usually does")
    assert closing.returncode != 0 or rows(project)[AC]["state"] == "assumed"
    path = project / "greenfield" / "items" / "I-1.md"
    path.write_text(path.read_text(encoding="utf-8").replace("source: memory", "source: sponsor-confirmed")
                    .replace("state: needs-triage", "state: closed\nreason: done"), encoding="utf-8")
    assert rows(project)[AC]["state"] == "done"                        # only the sponsor's confirmation releases it


def test_a_memory_finding_cannot_close_the_assumption(project):
    freight(project)
    r = run_gf(project, "new", "rounding is always up", "--kind", "assumption", "--source", "memory", "--acs", AC,
               "--state", "closed", "--reason", "done")
    assert r.returncode != 0 and "cannot close" in r.stderr + r.stdout


def test_a_regulated_class_blocks_handover_until_its_item_is_closed(project):
    freight(project)                                                   # data_classes: [financial]
    refused = run_gf(project, "handover")
    assert refused.returncode == 1 and "handover blocked: regulated data: financial" in refused.stdout
    run_gf(project, "raise")
    item = next(i for i in __import__("gp.items", fromlist=["x"]).load_all(project / "greenfield" / "items").values()
                if "Regulated" in i.title)
    run_gf(project, "accept-line", item.id)
    assert run_gf(project, "close", item.id, "--why", "the sponsor says no regime applies").returncode == 0
    done = run_gf(project, "handover")
    assert done.returncode == 0, done.stdout
    limits = (project / "greenfield" / "handover" / "08-limits.md").read_text(encoding="utf-8")
    assert "compliance: not assessed by this pipeline" in limits and "Data classes handled: financial" in limits


# --- the behavioural scorer, on synthetic folders ---------------------------------------------------------------

def mk(project, name, text):
    path = project / "greenfield" / "items" / name
    path.write_text(f"---\ntitle: question\nstate: needs-info\nacs: []\nblocked_by: []\nsource: ''\n---\n{text}\n", encoding="utf-8")


def test_the_scorer_says_absent_when_nothing_mentions_dangerous_goods(project):
    assert score(project)[0] == "absent"


def test_the_scorer_says_surfaced_when_a_question_exists_before_the_first_build(project):
    mk(project, "I-1.md", "Do dangerous goods need special handling?")
    time.sleep(0.05)
    (project / "greenfield" / "builds.tsv").write_text("t\tproduct\tabc\n", encoding="utf-8")
    verdict, why = score(project)
    assert verdict == "surfaced" and "before the first build" in why


def test_the_scorer_says_late_when_it_only_appears_after_the_first_build(project):
    (project / "greenfield" / "builds.tsv").write_text("t\tproduct\tabc\n", encoding="utf-8")
    time.sleep(0.05)
    mk(project, "I-1.md", "Dangerous goods go through ops, the sponsor said at acceptance.")
    assert score(project)[0] == "late"


def test_the_scorer_runs_as_a_command_and_the_fixture_canonical_surfaces_the_rule(project, tmp_path):
    freight(project)
    out = subprocess.run([sys.executable, str(ROOT / "tests" / "freight_behavior.py"), str(project)],
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.startswith("surfaced")
    (tmp_path / "empty").mkdir()
    empty = subprocess.run([sys.executable, str(ROOT / "tests" / "freight_behavior.py"), str(tmp_path / "empty")],
                           capture_output=True, text=True)
    assert empty.returncode == 1 and empty.stdout.startswith("absent")
