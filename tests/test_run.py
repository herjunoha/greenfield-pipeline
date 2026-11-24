import copy
import json
import sys

import yaml

from conftest import CANONICAL, run_gf, suite_dict, write_canonical, write_suite


def setup(project, server, data=None, env=None):
    write_canonical(project)
    write_suite(project, data)
    (project / "greenfield" / "environments.yaml").write_text(yaml.safe_dump({"environments": [
        {"name": "local", "base_url": server, "state_url": "/state", **(env or {})}]}), encoding="utf-8")


def runs_dir(project):
    return project / "greenfield" / "runs"


def verdicts(project, run_id):
    return json.loads((runs_dir(project) / run_id / "verdicts.json").read_text(encoding="utf-8"))


def record_of(project, run_id):
    path = runs_dir(project) / run_id / "cases" / "AC-1__TC-01.json"
    return json.loads(path.read_text(encoding="utf-8"))


def go(project, *extra):
    r = run_gf(project, "run", *extra)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout.strip()


def verdict(project, run_id):
    run_gf(project, "score", run_id)
    return verdicts(project, run_id)["acs"]["AC-1"]["verdict"]


def test_check_then_run_then_score_to_green(project, server):
    setup(project, server)
    assert run_gf(project, "check").returncode == 0
    run_id = go(project)
    scored = run_gf(project, "score", run_id)
    assert scored.returncode == 0, scored.stderr
    assert "AC-1  pass" in scored.stdout and "full=true" in scored.stdout
    assert verdicts(project, run_id)["acs"]["AC-1"] == {"verdict": "pass", "cases": {"TC-01": "pass"}}
    run = runs_dir(project) / run_id
    assert (run / "cases" / "AC-1__TC-01.json").is_file() and (run / "scores" / "AC-1__TC-01.json").is_file()
    assert json.loads((run / "run.json").read_text(encoding="utf-8"))["suites"]["AC-1"]


def test_a_wrong_expected_value_is_red(project, server):
    data = suite_dict()
    data["cases"][0]["steps"][0]["expect"][0]["value"] = 200
    setup(project, server, data)
    assert verdict(project, go(project)) == "fail"


def test_a_final_check_the_driver_cannot_read_fails_end_to_end(project, server):
    setup(project, server)
    envfile = project / "greenfield" / "environments.yaml"
    env = yaml.safe_load(envfile.read_text(encoding="utf-8"))
    del env["environments"][0]["state_url"]
    envfile.write_text(yaml.safe_dump(env), encoding="utf-8")
    assert verdict(project, go(project)) == "fail"


def test_a_dead_server_is_error_not_red(project):
    setup(project, "http://127.0.0.1:9")
    assert verdict(project, go(project)) == "error"


def test_check_and_run_refuse_a_check_with_no_from(project, server):
    data = suite_dict()
    del data["cases"][0]["steps"][0]["expect"][0]["from"]
    setup(project, server, data)
    r = run_gf(project, "check")
    assert r.returncode == 1 and "needs from:" in r.stdout
    assert run_gf(project, "run").returncode == 1
    assert not list(runs_dir(project).iterdir())


def test_check_and_run_refuse_an_unconfirmed_example(project, server):
    data = suite_dict()
    data["cases"][0]["final_check"][0]["from"] = "example:EX-2"
    setup(project, server, data)
    r = run_gf(project, "check")
    assert r.returncode == 1 and "EX-2 is not confirmed" in r.stdout
    assert run_gf(project, "run").returncode == 1


def test_score_refuses_when_an_example_is_unconfirmed_after_the_run(project, server):
    setup(project, server)
    run_id = go(project)
    canon = project / "greenfield" / "requirements" / "links.canonical.yaml"
    data = yaml.safe_load(canon.read_text(encoding="utf-8"))
    data["examples"][0]["confirmed_by"] = ""
    canon.write_text(yaml.safe_dump(data), encoding="utf-8")
    r = run_gf(project, "score", run_id)
    assert r.returncode == 2 and "EX-1 is not confirmed" in r.stderr


def test_score_refuses_when_the_suite_changed_after_the_run(project, server):
    setup(project, server)
    run_id = go(project)
    data = suite_dict()
    data["cases"][0]["steps"][1]["expect"][0]["value"] = 301
    write_suite(project, data)
    r = run_gf(project, "score", run_id)
    assert r.returncode == 2 and "changed after this run" in r.stderr


def test_rule_checks_wait_for_tims_judgment(project, server):
    data = suite_dict()
    data["cases"][0]["steps"][0]["expect"].append({"rule": "the response exposes no internal id"})
    setup(project, server, data)
    run_id = go(project)
    assert verdict(project, run_id) == "pending"
    judged = runs_dir(project) / run_id / "judgments"
    judged.mkdir()
    (judged / "AC-1__TC-01.json").write_text(json.dumps(
        {"rules": [{"step": 0, "rule": "the response exposes no internal id", "pass": True}]}), encoding="utf-8")
    assert verdict(project, run_id) == "pass"


def test_a_subset_run_is_not_full(project, server):
    setup(project, server)
    write_suite(project, suite_dict(ac="AC-2"), name="AC-2")
    run_id = go(project, "--ac", "AC-1")
    run_gf(project, "score", run_id)
    assert verdicts(project, run_id)["full"] is False


def test_a_rerun_needs_a_reason_and_keeps_the_first_attempt(project, server):
    setup(project, server)
    run_id = go(project)
    again = run_gf(project, "run", "--into", run_id)
    assert again.returncode == 2 and "--rerun-reason" in again.stderr
    go(project, "--into", run_id, "--rerun-reason", "server was restarting")
    cases = runs_dir(project) / run_id / "cases"
    assert len(list((cases / "attempts").glob("AC-1__TC-01.*.json"))) == 1
    assert record_of(project, run_id)["rerun_reason"] == "server was restarting"


def cli_suite(cmd, args):
    data = suite_dict(surface="tool")
    data["cases"] = [{"id": "TC-01", "name": "the tool prints a summary", "type": "positive", "severity": "major",
                      "steps": [{"do": {"cli": {"cmd": cmd, "args": args}},
                                 "expect": [{"path": "$.exit_code", "op": "eq", "value": 0, "from": "structural"}]}]}]
    return data


def tool_canonical():
    data = copy.deepcopy(CANONICAL)
    data["requirements"][0]["surface"] = "tool"
    return data


def test_the_cli_driver_runs_end_to_end(project):
    write_canonical(project, tool_canonical())
    write_suite(project, cli_suite(sys.executable, ["-c", "print('ok')"]))
    assert verdict(project, go(project)) == "pass"


def test_a_case_that_trips_the_fence_is_not_run(project):
    write_canonical(project, tool_canonical())
    write_suite(project, cli_suite("rm", ["-rf", "greenfield/runs"]))
    run_id = go(project)
    record = record_of(project, run_id)
    assert record["fenced"] is True and "delete-data" in record["error"] and record["steps"] == []
    assert verdict(project, run_id) == "error"
    assert runs_dir(project).is_dir()


def test_a_production_base_url_is_not_an_environment(project):
    setup(project, "https://api.prod.example.com")
    r = run_gf(project, "run")
    assert r.returncode == 2 and "production" in r.stderr
    assert not list(runs_dir(project).iterdir())


def test_manual_suites_score_manual(project):
    data = suite_dict(manual=True)
    data["cases"] = [{"id": "TC-01", "name": "a person confirms the page reads well", "type": "positive",
                      "severity": "minor", "steps": [{"do": {"manual": {"instruction": "read the page"}}}]}]
    write_canonical(project)
    write_suite(project, data)
    assert verdict(project, go(project)) == "manual"
