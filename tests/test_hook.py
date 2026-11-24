import json
import subprocess

from conftest import HOOK


def fire(cwd, mode, payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([*HOOK, mode], input=raw, cwd=cwd, capture_output=True, text=True)


def bash(cwd, command):
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def test_pre_asks_with_the_documented_shape(project):
    r = fire(project, "pre", bash(project, "git push origin main"))
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse" and out["permissionDecision"] == "ask"
    assert "[outside-lane]" in out["permissionDecisionReason"]


def test_pre_is_silent_when_allowed(project):
    r = fire(project, "pre", bash(project, "git status"))
    assert (r.returncode, r.stdout) == (0, "")


def test_pre_is_silent_outside_a_project_even_for_bad_input(bare):
    assert fire(bare, "pre", bash(bare, "git push origin main")).stdout == ""
    assert fire(bare, "pre", "not json").stdout == ""


def test_unparseable_input_inside_a_project_fails_closed(project):
    r = fire(project, "pre", "not json")
    assert json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] == "ask"


def test_unreadable_fence_asks(project):
    (project / "greenfield" / "fence.yaml").write_text("{broken: [", encoding="utf-8")
    r = fire(project, "pre", bash(project, "ls"))
    assert "fence-unreadable" in r.stdout


def test_post_logs_an_accepted_ask_and_only_that(project):
    log = project / "greenfield" / "acceptances.jsonl"
    fire(project, "post", bash(project, "git status"))
    assert log.read_text(encoding="utf-8") == ""
    fire(project, "post", bash(project, "git push origin main"))
    entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert entry["rule"] == "outside-lane" and entry["tool"] == "Bash" and "git push" in entry["target"]
