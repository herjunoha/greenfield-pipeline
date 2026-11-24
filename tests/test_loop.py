import json
import subprocess
import sys
from datetime import date, timedelta

import yaml

from conftest import HOOK, ROOT, run_gf
from test_code import repo_project, commit
from test_fence import set_fence
from test_hook import bash, fire
from test_flow import fake_run, suite_file


def decisions(project):
    return (project / "greenfield" / "decisions.tsv").read_text(encoding="utf-8")


def items_of(project):
    from gp import items
    return items.load_all(project / "greenfield" / "items")


# --- the ladder -----------------------------------------------------------------------------------------------

def test_every_part_is_afk_by_default(project):
    out = run_gf(project, "level").stdout
    assert out.count("\tafk\t(default)") == 7 and "build\tafk" in out


def test_a_hitl_part_makes_its_items_wait_for_the_owner(project):
    set_fence(project, ladder={"build": "hitl"})
    assert "(fence.yaml)" in next(l for l in run_gf(project, "level").stdout.splitlines() if l.startswith("build"))
    run_gf(project, "new", "build the skeleton", "--state", "ready-for-agent", "--part", "build")
    run_gf(project, "new", "write a suite", "--state", "ready-for-agent", "--part", "design")
    states = {i.title: i.state for i in items_of(project).values()}
    assert states == {"build the skeleton": "ready-for-human", "write a suite": "ready-for-agent"}
    assert run_gf(project, "next").stdout.strip().endswith("write a suite")


def test_an_existing_item_on_a_part_that_turns_hitl_is_worked_live_not_alone(project):
    run_gf(project, "new", "build the skeleton", "--state", "ready-for-agent", "--part", "build")
    assert "build the skeleton" in run_gf(project, "next").stdout and "worked live" not in run_gf(project, "next").stdout
    set_fence(project, ladder={"build": "hitl"})
    out = run_gf(project, "next").stdout
    assert "worked live with the owner: build is hitl" in out


def test_a_spoken_change_lasts_the_session_is_logged_and_never_loosens_the_owners_map(project):
    env = {"GP_SESSION": "s1"}
    assert run_gf(project, "level", "verify", "hitl", env=env).returncode == 0
    assert "verify\thitl\t(this session)" in run_gf(project, "level", env=env).stdout
    assert "ladder: verify -> hitl" in decisions(project)
    assert "verify\tafk\t(default)" in run_gf(project, "level", env={"GP_SESSION": "s2"}).stdout   # ended
    set_fence(project, ladder={"build": "hitl"})
    r = run_gf(project, "level", "build", "afk", env=env)
    assert r.returncode == 2 and "permanent choice" in r.stderr


def test_unattended_is_not_built_and_counts_as_hitl_and_a_bad_map_is_refused(project):
    set_fence(project, ladder={"build": "unattended"})
    assert "build\thitl\t(fence.yaml says unattended" in run_gf(project, "level").stdout
    set_fence(project, ladder={"building": "afk"})
    assert run_gf(project, "level").returncode == 2


def test_no_level_covers_a_one_way_door(project):
    set_fence(project, ladder={part: "afk" for part in ("plate", "probe", "shape", "design", "build", "verify", "handover")})
    for cmd, rule in (("git push origin main", "[outside-lane]"), ("gp accept-line I-1", "[scope]"),
                      ("curl https://api.prod.example.com/x", "[production]")):
        assert rule in fire(project, "pre", bash(project, cmd)).stdout, cmd


# --- the ceiling ----------------------------------------------------------------------------------------------

def stall_runs(project, count, cases=None):
    for n in range(count):
        fake_run_cases(project, f"r{n}", cases or {"TC-01": "fail"})


def fake_run_cases(project, name, cases, ac="AC-2", verdict=None):
    fake_run(project, name, verdict or ("pass" if set(cases.values()) == {"pass"} else "fail"), "x", ac=ac)
    path = project / "greenfield" / "runs" / name / "verdicts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["acs"][ac]["cases"] = cases
    path.write_text(json.dumps(data), encoding="utf-8")


def test_runs_with_no_progress_on_one_ac_stop_that_line_and_raise_an_item(linkr):
    suite_file(linkr)
    stall_runs(linkr, 2)
    assert run_gf(linkr, "budget").returncode == 0
    stall_runs_more = fake_run_cases
    stall_runs_more(linkr, "r2", {"TC-01": "fail"})
    r = run_gf(linkr, "budget")
    assert r.returncode == 1 and "AC-2 has had 3 full runs in a row with no newly passing case" in r.stdout
    waiting = [i for i in items_of(linkr).values() if i.source == "budget:runs:AC-2"]
    assert len(waiting) == 1 and waiting[0].state == "ready-for-human" and "Ceiling reached: AC-2" in waiting[0].title
    assert "**The agent's pick.**" in waiting[0].body
    r = run_gf(linkr, "run", "--ac", "AC-2")
    assert r.returncode == 2 and "waits on the owner" in r.stderr
    assert len([i for i in items_of(linkr).values() if i.source == "budget:runs:AC-2"]) == 1       # not duplicated


def test_a_newly_passing_case_is_progress(linkr):
    fake_run_cases(linkr, "r0", {"TC-01": "fail", "TC-02": "fail"})
    fake_run_cases(linkr, "r1", {"TC-01": "pass", "TC-02": "fail"})
    fake_run_cases(linkr, "r2", {"TC-01": "pass", "TC-02": "fail"})
    assert run_gf(linkr, "budget").returncode == 0                      # r0 stalled once, r1 progressed, r2 stalled once
    fake_run_cases(linkr, "r3", {"TC-01": "pass", "TC-02": "fail"})
    fake_run_cases(linkr, "r4", {"TC-01": "pass", "TC-02": "fail"})
    assert run_gf(linkr, "budget").returncode == 1


def test_the_owner_raising_the_ceiling_in_the_fence_lets_the_line_run_again(linkr):
    stall_runs(linkr, 3)
    assert run_gf(linkr, "budget").returncode == 1
    set_fence(linkr, budget={"runs_per_ac": 5, "builds_total": 200, "deadline": None})
    assert run_gf(linkr, "budget").returncode == 0


def test_builds_are_counted_and_the_limit_stops_building(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    set_fence(project, budget={"runs_per_ac": 3, "builds_total": 2, "deadline": None})
    assert run_gf(project, "build").returncode == 0
    (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
    commit(project)
    assert run_gf(project, "build").returncode == 0
    (repo / "app.py").write_text("print(3)\n", encoding="utf-8")
    commit(project)
    r = run_gf(project, "build")
    assert r.returncode == 2 and "2 builds were recorded (the ceiling is 2)" in r.stderr
    assert any(i.source == "budget:builds" for i in items_of(project).values())
    assert len((project / "greenfield" / "builds.tsv").read_text(encoding="utf-8").splitlines()) == 2


def test_a_passed_deadline_stops_runs_and_builds(linkr):
    suite_file(linkr)
    past, future = date.today() - timedelta(days=1), date.today() + timedelta(days=30)
    set_fence(linkr, budget={"runs_per_ac": 3, "builds_total": 200, "deadline": past.isoformat()})
    assert "has passed" in run_gf(linkr, "run").stderr
    assert any(i.source == "budget:deadline" for i in items_of(linkr).values())
    set_fence(linkr, budget={"runs_per_ac": 3, "builds_total": 200, "deadline": future.isoformat()})
    assert run_gf(linkr, "budget").returncode == 0


def test_a_malformed_budget_is_refused_and_the_token_limit_is_not_pretended(project):
    out = run_gf(project, "budget")
    assert out.returncode == 0 and "token or cost spend is not visible" in out.stdout
    set_fence(project, budget={"runs_per_ac": 0})
    assert run_gf(project, "budget").returncode == 2


# --- catch-up and the session-start line ----------------------------------------------------------------------

def test_catchup_lists_what_waits_new_decisions_and_attention_flags(linkr):
    run_gf(linkr, "new", "pick a stack", "--state", "ready-for-human")
    run_gf(linkr, "decide", "use sqlite", "--why", "one user")
    for name, text in (("I-1", "## Attention\nThe suite has no liveness control on AC-3.\n\n## What changed\nx\n"),
                       ("I-2", "## Attention\nNo flags.\n")):
        folder = linkr / "greenfield" / "evidence" / name
        folder.mkdir(parents=True)
        (folder / "README.md").write_text(text, encoding="utf-8")
    out = run_gf(linkr, "catchup").stdout
    assert "waiting on you (1):" in out and "I-1 ready-for-human  pick a stack" in out
    assert "use sqlite | one user" in out and "I-1: The suite has no liveness control on AC-3." in out
    assert "I-2:" not in out and "ladder: afk everywhere (default)" in out
    again = run_gf(linkr, "catchup").stdout
    assert "use sqlite" not in again                                      # the marker moved
    run_gf(linkr, "decide", "use postgres", "--why", "scale")
    run_gf(linkr, "catchup", "--keep")
    assert "use postgres" in run_gf(linkr, "catchup").stdout              # --keep did not move it


def run_hook(cwd, payload):
    return subprocess.run([sys.executable, str(ROOT / "hooks" / "session_start.py")], input=payload, cwd=cwd,
                          capture_output=True, text=True)


def test_the_session_start_line_is_pointers_and_silent_elsewhere(project, bare):
    run_gf(project, "new", "write a suite", "--state", "ready-for-agent")
    run_gf(project, "new", "pick a stack", "--state", "ready-for-human")
    out = run_hook(project, json.dumps({"cwd": str(project)})).stdout
    assert "1 item(s) ready for the agent, 1 waiting on you" in out and "/greenfield-pipeline:catchup" in out
    assert run_hook(bare, json.dumps({"cwd": str(bare)})).stdout == ""
    assert run_hook(project, "not json").stdout.startswith("greenfield-pipeline:") or run_hook(project, "not json").returncode == 0
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert "session_start.py" in json.dumps(hooks["SessionStart"])


# --- retro ----------------------------------------------------------------------------------------------------

def lessons(project, text):
    (project / "greenfield" / "lessons.md").write_text(text, encoding="utf-8")


def test_a_retro_that_adds_to_the_pack_is_refused_and_one_that_trims_passes(project):
    lessons(project, "Check the contract before the suite.\nNever trust a clean preflight.\n")
    assert "retro begun" in run_gf(project, "retro", "begin").stdout
    lessons(project, "Check the contract before the suite.\nNever trust a clean preflight.\nA new line.\n")
    r = run_gf(project, "retro", "finish")
    assert r.returncode == 1 and "the pack grew from" in r.stdout
    lessons(project, "Check the contract first.\nNever trust a clean preflight.\n")
    r = run_gf(project, "retro", "finish")
    assert r.returncode == 0 and "the pack is no larger" in r.stdout and "\tretro\t" in decisions(project)
    assert run_gf(project, "retro", "finish").returncode == 2                       # nothing in progress


def test_lessons_stay_general_and_small(linkr):
    lessons(linkr, "x" * 400 + "\n" + "line\n" * 40)
    run_gf(linkr, "retro", "begin")
    lessons(linkr, "\n".join(["acme-linkr broke twice.", "Reach me at jane@example.com or +62 812-3456-7890."]
                             + ["l"] * 29) + "\n")
    out = run_gf(linkr, "retro", "finish").stdout
    assert "names 'acme-linkr', a sponsor or project specific" in out and "holds a phone number, email or token" in out
    assert "is 31 lines; the cap is 30" in out


def test_retro_works_on_an_installed_pack_not_the_plugin(tmp_path_factory):
    from test_pack import make_pack
    base = tmp_path_factory.mktemp("retro")
    pack = make_pack(base, **{"lessons.md": "Old lesson one.\nOld lesson two.\n"})
    project = base / "project"
    project.mkdir()
    assert run_gf(project, "init", "--pack", "acme", env={"GP_PACKS_DIR": str(base / "packs")}).returncode == 0
    assert "retro begun" in run_gf(project, "retro", "begin").stdout
    (pack / "lessons.md").write_text("Old lesson one.\nOld lesson two plus a lot more words added here.\n", encoding="utf-8")
    assert "the pack grew" in run_gf(project, "retro", "finish").stdout


def test_the_fence_asks_before_any_write_into_the_plugin(project):
    for sub in ("skills/plate/SKILL.md", "agents/ed-the-engineer.md", "drivers/drv_http.py", "packs/generic/pack.yaml"):
        payload = {"tool_name": "Write", "cwd": str(project), "tool_input": {"file_path": str(ROOT / sub), "content": "x"}}
        assert "[fence-edit]" in fire(project, "pre", payload).stdout, sub
    inside = {"tool_name": "Write", "cwd": str(project), "tool_input": {"file_path": str(project / "greenfield" / "lessons.md"),
                                                                       "content": "x"}}
    assert fire(project, "pre", inside).stdout == ""                    # the project's own files are the agent's
