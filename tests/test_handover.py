"""Handover and the quickstart case on acme-linkr, driven through the real commands after a full scratch run."""
import json
import sys

from conftest import edit_canonical, run_gf
from test_code import commit
from test_scratch import (approve_suites, build_reference, full_run, gp, own_unit_tests, skeleton_project,
                          write_all_suites)

README = """# acme-linkr

A small link shortener.

## Quickstart

```sh
"{py}" app.py --port $PORT
```
"""


def delivered(project, readme=True):
    """A project taken to done: skeleton, red, reference build, green, reviewed, baseline approved."""
    skeleton_project(project)
    write_all_suites(project)
    approve_suites(project)
    full_run(project)
    build_reference(project)
    if readme:
        (project / "product" / "README.md").write_text(README.format(py=sys.executable), encoding="utf-8")
    assert own_unit_tests(project).returncode == 0
    commit(project, "feat: the eight ACs")
    green = full_run(project)
    gp(project, "review", "run", green, "--by", "rex", "--verdict", "approve")
    edit_canonical(project, lambda d: d["project"].update(status="approved"))
    gp(project, "accept-line", "canonical")
    return green


def doc(project, name):
    return (project / "greenfield" / "handover" / name).read_text(encoding="utf-8")


def test_handover_writes_every_document_including_the_limits_page(project):
    delivered(project)
    out = gp(project, "handover")
    assert "08-limits.md" in out
    names = sorted(p.name for p in (project / "greenfield" / "handover").iterdir())
    assert names[0] == "01-requirements-baseline.md" and len(names) == 8
    for name in names:
        assert doc(project, name).startswith("> This document was drafted by an AI agent"), name
    limits = doc(project, "08-limits.md")
    assert "compliance: not assessed by this pipeline; regimes named by the sponsor: none" in limits
    assert "## Not done\n- none" in limits and "Doubles: not proven against the real service" in limits
    assert "AC-1" in doc(project, "03-acceptance-record.md") and "done" in doc(project, "03-acceptance-record.md")
    assert doc(project, "04-test-sheet.md").count("**pass**") == 8
    assert "Not met or not proven: none" in doc(project, "05-acceptance-certificate.md")
    assert "____________" in doc(project, "05-acceptance-certificate.md")                # unsigned
    assert "feat: the eight ACs" in doc(project, "06-release-notes.md") and "return to commit" in doc(project, "07-rollback-note.md")


def test_the_limits_page_says_what_stayed_unproven(project):
    delivered(project)
    gp(project, "new", "assumed rate limit", "--kind", "assumption", "--source", "memory", "--acs", "AC-6")
    edit_canonical(project, lambda d: d["project"].update(regulated=["PDPA"]))
    gp(project, "raise")
    r = run_gf(project, "handover")
    assert r.returncode == 1 and "handover blocked: regulated data: PDPA" in r.stdout            # the item is open
    assert not list((project / "greenfield" / "handover").iterdir())                           # nothing written
    from gp import items
    regulated = next(i for i in items.load_all(project / "greenfield" / "items").values() if "Regulated" in i.title)
    gp(project, "accept-line", regulated.id)
    gp(project, "close", regulated.id, "--why", "the sponsor named PDPA; controls become ACs later")
    gp(project, "handover")
    limits = doc(project, "08-limits.md")
    assert "regimes named by the sponsor: PDPA" in limits and "AC-6 is assumed" in limits
    assert "assumed rate limit (tag: memory" in limits


def test_no_handover_without_a_valid_canonical(project):
    r = run_gf(project, "handover")
    assert r.returncode == 1 and "no canonical requirement" in r.stdout


def test_handover_data_is_json_a_writer_can_use(project):
    delivered(project)
    data = json.loads(gp(project, "handover-data"))
    assert data["project"]["name"] == "acme-linkr" and data["roles"] == {"owner": "owner", "sponsor": "sponsor"}
    assert len(data["acs"]) == 8 and data["limits"]["not_done"] == [] and data["project"]["approved"] is True


# --- quickstart -----------------------------------------------------------------------------------------------

def test_the_readme_quickstart_passes_from_a_fresh_clone(project):
    delivered(project)
    out = gp(project, "quickstart")
    assert out == "quickstart ok"
    assert json.loads((project / "greenfield" / "quickstart.json").read_text(encoding="utf-8"))["ok"] is True


def test_a_quickstart_that_does_not_work_from_a_fresh_clone_fails(project):
    delivered(project)
    (project / "product" / "README.md").write_text(README.format(py=sys.executable).replace("app.py", "server.py"),
                                                   encoding="utf-8")
    commit(project, "docs: a wrong quickstart")
    gp(project, "build")
    r = run_gf(project, "quickstart")
    assert r.returncode == 1 and "quickstart failed" in r.stdout and "exited with code" in r.stdout


def test_no_quickstart_section_is_refused(project):
    delivered(project, readme=False)
    r = run_gf(project, "quickstart")
    assert r.returncode == 1 and "no `## Quickstart` section" in r.stdout
