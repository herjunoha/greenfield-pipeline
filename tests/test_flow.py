import json

import yaml

from conftest import edit_canonical, run_gf, suite_dict, write_suite
from test_hook import bash, fire

SUITE = "AC-2"


def rows(project):
    return {r["id"]: r for r in json.loads(run_gf(project, "acs", "--json").stdout)["acs"]}


def suite_file(project):
    write_suite(project, suite_dict(ac=SUITE, surface="linkr-api"), name=SUITE)
    from gp import suite
    return suite.load(project / "greenfield" / "suites" / f"{SUITE}.yaml")


def fake_run(project, name, verdict, suite_sha, full=True, preflight=True, builds=None, ac=SUITE):
    folder = project / "greenfield" / "runs" / name
    folder.mkdir(parents=True)
    (folder / "run.json").write_text(json.dumps({"full": full, "preflight": {"ok": preflight},
                                                 "suites": {ac: suite_sha}, "build_ids": builds or {}}), encoding="utf-8")
    (folder / "verdicts.json").write_text(json.dumps({"run": name, "full": full, "build_ids": builds or {},
                                                      "acs": {ac: {"verdict": verdict, "cases": {}}}}), encoding="utf-8")
    return name


def approve_suite(project):
    assert run_gf(project, "review", "suite", SUITE, "--by", "rex", "--verdict", "approve").returncode == 0
    assert run_gf(project, "accept-line", f"suite:{SUITE}").returncode == 0


def approve_baseline(project):
    edit_canonical(project, lambda d: d["project"].update(status="approved"))
    assert run_gf(project, "accept-line", "canonical").returncode == 0


# --- accept-line and close ----------------------------------------------------------------------------------

def test_accept_line_binds_to_the_files_current_sha(project):
    run_gf(project, "new", "pick a stack", "--state", "ready-for-human")
    r = run_gf(project, "accept-line", "I-1")
    assert r.returncode == 0 and "accepted I-1" in r.stdout
    from gp import acceptance
    assert acceptance.accepted(project, "I-1")
    path = project / "greenfield" / "items" / "I-1.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA new option appeared.\n", encoding="utf-8")
    assert not acceptance.accepted(project, "I-1")                     # edited after acceptance: un-accepted


def test_accept_line_refuses_what_does_not_exist(project):
    assert "nothing to accept" in run_gf(project, "accept-line", "I-9").stderr
    assert "not an item id" in run_gf(project, "accept-line", "whatever").stderr


def test_a_ready_for_human_item_closes_only_on_the_owners_accepted_line(project):
    run_gf(project, "new", "pick a stack", "--state", "ready-for-human")
    r = run_gf(project, "close", "I-1", "--why", "the agent decided")
    assert r.returncode == 1 and "waits on the owner" in r.stderr
    run_gf(project, "accept-line", "I-1")
    assert run_gf(project, "close", "I-1", "--why", "owner chose python").returncode == 0
    assert "closed" in (project / "greenfield" / "items" / "I-1.md").read_text(encoding="utf-8")


def test_the_agent_closes_its_own_items_and_the_decision_is_logged(project):
    run_gf(project, "new", "rename a variable", "--state", "ready-for-agent")
    assert run_gf(project, "close", "I-1", "--why", "done and verified").returncode == 0
    log = (project / "greenfield" / "decisions.tsv").read_text(encoding="utf-8").splitlines()
    assert len(log) == 2 and "I-1" in log[1] and "closed: done" in log[1] and "done and verified" in log[1]
    assert run_gf(project, "close", "I-1", "--why", "again").returncode == 1


def test_decide_appends_a_row(project):
    assert run_gf(project, "decide", "use sqlite", "--why", "one user", "--item", "I-2").returncode == 0
    assert "use sqlite\tone user" in (project / "greenfield" / "decisions.tsv").read_text(encoding="utf-8")


def test_the_fence_asks_before_an_agent_accepts_a_line(project):
    for cmd in ("gp accept-line I-1", "python D:/x/bin/gp accept-line suite:AC-1", "bin\\gp.cmd pack accept"):
        out = fire(project, "pre", bash(project, cmd)).stdout
        assert "permissionDecision" in out and "[scope]" in out, cmd
    assert fire(project, "pre", bash(project, "gp acs")).stdout == ""


# --- reviews ------------------------------------------------------------------------------------------------

def test_the_writer_never_reviews_its_own_work(linkr):
    suite_file(linkr)
    r = run_gf(linkr, "review", "suite", SUITE, "--by", "gus", "--verdict", "approve")
    assert r.returncode == 2 and "cannot review a suite it produced" in r.stderr
    fake_run(linkr, "r1", "pass", "x")
    run_gf(linkr, "score", "r1")      # no real run cases, but verdicts.json exists from the fake
    for who in ("ed", "eve"):
        assert "cannot review a run it produced" in run_gf(linkr, "review", "run", "r1", "--by", who,
                                                           "--verdict", "approve").stderr


def test_a_rejection_needs_a_reason_and_the_latest_review_wins(linkr):
    suite_file(linkr)
    assert "says why" in run_gf(linkr, "review", "suite", SUITE, "--by", "rex", "--verdict", "reject").stderr
    run_gf(linkr, "review", "suite", SUITE, "--by", "rex", "--verdict", "approve")
    from gp import reviews
    sha = reviews.subject_sha(linkr, "suite", SUITE)
    assert reviews.approved(linkr, "suite", SUITE, sha)
    run_gf(linkr, "review", "suite", SUITE, "--by", "rex", "--verdict", "reject", "--note", "no liveness control")
    assert not reviews.approved(linkr, "suite", SUITE, sha)


def test_a_review_covers_one_suite_version(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    assert rows(linkr)[SUITE]["state"] == "ready"
    data = suite_dict(ac=SUITE, surface="linkr-api")
    data["cases"][0]["name"] = "a visitor is redirected, reworded"
    write_suite(linkr, data, name=SUITE)
    assert rows(linkr)[SUITE]["state"] == "in-review" and s.sha != ""


# --- the state of an AC -------------------------------------------------------------------------------------

def test_an_ac_walks_no_suite_in_review_ready_red_green_done(linkr):
    assert rows(linkr)[SUITE]["state"] == "no-suite"
    s = suite_file(linkr)
    row = rows(linkr)[SUITE]
    assert row["state"] == "in-review" and "rex has not approved" in row["missing"][0]
    run_gf(linkr, "review", "suite", SUITE, "--by", "rex", "--verdict", "approve")
    assert "owner has not accepted" in rows(linkr)[SUITE]["missing"][0]
    run_gf(linkr, "accept-line", f"suite:{SUITE}")
    assert rows(linkr)[SUITE]["state"] == "ready"
    fake_run(linkr, "r1", "fail", s.sha)
    assert rows(linkr)[SUITE]["state"] == "red"
    fake_run(linkr, "r2", "pass", s.sha)
    row = rows(linkr)[SUITE]
    assert row["state"] == "green"
    assert "rex has not reviewed run r2" in row["missing"] and "the baseline is not approved" in row["missing"]
    run_gf(linkr, "review", "run", "r2", "--by", "rex", "--verdict", "approve")
    approve_baseline(linkr)
    assert rows(linkr)[SUITE] ["state"] == "done" and rows(linkr)[SUITE]["missing"] == []


def test_green_without_a_red_first_is_not_done(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    approve_baseline(linkr)
    fake_run(linkr, "r1", "pass", s.sha)
    run_gf(linkr, "review", "run", "r1", "--by", "rex", "--verdict", "approve")
    row = rows(linkr)[SUITE]
    assert row["state"] == "green" and row["missing"] == ["never seen red before its first green (red first)"]


def test_a_connection_error_or_an_unreachable_preflight_is_not_red(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    approve_baseline(linkr)
    fake_run(linkr, "r1", "error", s.sha)
    fake_run(linkr, "r2", "fail", s.sha, preflight=False)               # a fail the software never answered
    fake_run(linkr, "r3", "pass", s.sha)
    run_gf(linkr, "review", "run", "r3", "--by", "rex", "--verdict", "approve")
    assert "never seen red" in " ".join(rows(linkr)[SUITE]["missing"])


def test_a_partial_run_does_not_close_an_ac_and_a_new_commit_needs_a_new_verdict(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    approve_baseline(linkr)
    fake_run(linkr, "r1", "fail", s.sha, full=False)
    fake_run(linkr, "r2", "pass", s.sha, full=False)
    assert "no full run of this suite yet" in rows(linkr)[SUITE]["missing"]
    old = {"product": {"commit": "a" * 40}}
    fake_run(linkr, "r3", "pass", s.sha, builds=old)
    run_gf(linkr, "review", "run", "r3", "--by", "rex", "--verdict", "approve")
    (linkr / "greenfield" / "builds.yaml").write_text(yaml.safe_dump({"product": {"commit": "a" * 40}}), encoding="utf-8")
    assert rows(linkr)[SUITE]["state"] == "done"
    (linkr / "greenfield" / "builds.yaml").write_text(yaml.safe_dump({"product": {"commit": "b" * 40}}), encoding="utf-8")
    assert "the run is not on the current build of product" in rows(linkr)[SUITE]["missing"]


def test_an_open_assumption_outranks_everything_even_a_done_ac(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    approve_baseline(linkr)
    fake_run(linkr, "r1", "fail", s.sha)
    fake_run(linkr, "r2", "pass", s.sha)
    run_gf(linkr, "review", "run", "r2", "--by", "rex", "--verdict", "approve")
    assert rows(linkr)[SUITE]["state"] == "done"
    run_gf(linkr, "new", "assumed rate", "--kind", "assumption", "--source", "memory", "--acs", SUITE)
    assert rows(linkr)[SUITE]["state"] == "assumed"                   # whatever the tests say


def test_approval_needs_the_owners_accepted_line_at_the_files_current_sha(linkr):
    s = suite_file(linkr)
    approve_suite(linkr)
    fake_run(linkr, "r1", "fail", s.sha)
    fake_run(linkr, "r2", "pass", s.sha)
    run_gf(linkr, "review", "run", "r2", "--by", "rex", "--verdict", "approve")
    edit_canonical(linkr, lambda d: d["project"].update(status="approved"))          # written, never accepted
    assert "the baseline is not approved" in rows(linkr)[SUITE]["missing"]
    run_gf(linkr, "accept-line", "canonical")
    assert rows(linkr)[SUITE]["state"] == "done"
    edit_canonical(linkr, lambda d: d["project"]["objectives"].append("one more"))   # edited after acceptance
    assert rows(linkr)[SUITE]["missing"] == ["the baseline is not approved"]
