import json
import socket
import subprocess
import sys

import yaml

from conftest import FIXTURES, run_gf, suite_dict, write_suite
from test_fence import set_fence

ID = ["-c", "user.name=t", "-c", "user.email=t@localhost"]


def git(repo, *args):
    done = subprocess.run(["git", *ID, "-C", str(repo), *args], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def alive(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def write_env(project, **changes):
    env = {"name": "local", "kind": "local", "runner": "process"}
    env.update(changes)
    (project / "greenfield" / "environments.yaml").write_text(yaml.safe_dump({"environments": [env]}), encoding="utf-8")


def skeleton_env(port, **extra):
    probe = f"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:{port}/health').read().decode())"
    return {"start": f'"{sys.executable}" product/app.py --port {port}',
            "health": {"cmd": f'"{sys.executable}" -c "{probe}"', "expect": '"status": "ok"', "timeout": 20},
            "base_url": f"http://127.0.0.1:{port}", **extra}


def skeleton(project, port=None):
    """acme-linkr's walking skeleton: a committed product repo, a process runner the owner accepted, an env."""
    port = port or free_port()
    run_gf(project, "product", "init")
    (project / "product" / "app.py").write_text((FIXTURES / "acme-linkr/product/app.py").read_text(encoding="utf-8"),
                                                encoding="utf-8")
    git(project / "product", "add", "-A")
    git(project / "product", "commit", "-m", "feat: the walking skeleton")
    set_fence(project, code_repos=[{"path": "product", "runner": "process", "trunk": "main"}],
              registries=[{"name": "pypi", "host": "pypi.org"}])
    write_env(project, **skeleton_env(port))
    return port


# --- preflight ----------------------------------------------------------------------------------------------

def test_the_skeleton_passes_preflight_and_the_process_is_stopped(project):
    port = skeleton(project)
    r = run_gf(project, "preflight")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "preflight ok" in r.stdout and not alive(port)
    record = json.loads((project / "greenfield" / "preflight.json").read_text(encoding="utf-8"))
    assert record["ok"] is True and "health" in record["checks"]


def test_a_start_that_exits_fails_preflight_with_the_reason(project):
    skeleton(project)
    write_env(project, start=f'"{sys.executable}" -c "import sys;sys.exit(3)"',
              health={"cmd": f'"{sys.executable}" -c "print(1)"', "expect": "never", "timeout": 5})
    r = run_gf(project, "preflight")
    assert r.returncode == 1 and "exited with code 3" in r.stdout
    assert json.loads((project / "greenfield" / "preflight.json").read_text(encoding="utf-8"))["ok"] is False


def test_health_that_never_matches_fails_after_its_timeout(project):
    port = skeleton(project)
    env = skeleton_env(port)
    env["health"]["expect"] = "will-not-appear"
    env["health"]["timeout"] = 2
    write_env(project, **env)
    r = run_gf(project, "preflight")
    assert r.returncode == 1 and "did not match" in r.stdout and not alive(port)


def test_credential_names_are_checked_never_their_values(project):
    port = skeleton(project)
    write_env(project, **skeleton_env(port, env_names=["APP_TOKEN"]))
    r = run_gf(project, "preflight")
    assert r.returncode == 1 and "not set: APP_TOKEN" in r.stdout
    r = run_gf(project, "preflight", env={"APP_TOKEN": "s3cr3t-value-123"})
    assert r.returncode == 0 and "s3cr3t-value-123" not in r.stdout + r.stderr


def test_env_names_must_be_names_not_values(project):
    skeleton(project)
    write_env(project, env_names=["token=abc123"])
    assert "env_names must be a list of variable names" in run_gf(project, "check").stdout


def test_a_container_runner_with_no_runtime_fails_with_the_reason(project):
    port = skeleton(project)
    write_env(project, **skeleton_env(port, runner="container"))
    r = run_gf(project, "preflight", env={"GP_CONTAINER_RUNTIME": "no-such-runtime-xyz"})
    assert r.returncode == 1 and "container runtime: none found" in r.stdout and "runner: process" in r.stdout
    assert "start is a container command" in r.stdout and not alive(port)


def test_a_process_runner_needs_the_owner_to_have_accepted_it_in_the_fence(project):
    port = skeleton(project)
    set_fence(project, code_repos=[{"path": "product", "runner": "container"}])
    write_env(project, **skeleton_env(port))
    assert "runner: process needs every code_repos entry" in run_gf(project, "check").stdout
    assert run_gf(project, "preflight").returncode == 2


def test_production_remote_and_non_loopback_environments_are_refused(project):
    write_env(project, kind="local", base_url="http://staging.example.net")
    assert "reached on loopback" in run_gf(project, "check").stdout
    write_env(project, kind="remote", base_url="http://shared.example.net")
    assert "not in fence.yaml remote_hosts" in run_gf(project, "check").stdout
    set_fence(project, remote_hosts=["shared.example.net"])
    assert run_gf(project, "check").returncode == 0
    write_env(project, kind="remote", base_url="https://api.prod.example.com")
    set_fence(project, remote_hosts=["api.prod.example.com"])
    assert "looks like production" in run_gf(project, "check").stdout
    write_env(project, kind="production")
    assert "production is never listed" in run_gf(project, "check").stdout


def test_a_double_needs_its_provenance(project):
    write_env(project, doubles=["payments"])
    assert "double 'payments' needs doubles/payments/PROVENANCE.md" in run_gf(project, "check").stdout
    folder = project / "greenfield" / "doubles" / "payments"
    folder.mkdir()
    (folder / "PROVENANCE.md").write_text("Source: vendor docs\nDate: 2026-11-13\nDoes not model: refunds\n",
                                          encoding="utf-8")
    assert run_gf(project, "check").returncode == 0


def test_run_starts_the_environment_records_the_preflight_and_stops_it(linkr):
    project = linkr
    port = skeleton(project)
    data = suite_dict(surface="linkr-api")
    data["cases"][0]["steps"] = [{"do": {"http": {"path": "/health"}},
                                  "expect": [{"path": "$.status", "op": "eq", "value": 200, "from": "structural"}]}]
    data["cases"][0]["final_check"] = []
    write_suite(project, {**data, "ac": "AC-1", "dimension": "functional"})
    r = run_gf(project, "run")
    assert r.returncode == 0, r.stdout + r.stderr
    meta = json.loads((project / "greenfield" / "runs" / r.stdout.strip() / "run.json").read_text(encoding="utf-8"))
    assert meta["preflight"]["ok"] is True and not alive(port)


def test_a_run_is_refused_when_preflight_fails_and_leaves_no_run(linkr):
    project = linkr
    port = skeleton(project)
    env = skeleton_env(port)
    env["health"].update(expect="nope", timeout=1)
    write_env(project, **env)
    write_suite(project, suite_dict(ac="AC-1", surface="linkr-api"))
    r = run_gf(project, "run")
    assert r.returncode == 1 and "preflight failed" in r.stdout
    assert not list((project / "greenfield" / "runs").iterdir())


# --- reset --------------------------------------------------------------------------------------------------

def two_case_cli_suite(project):
    case = lambda n: {"id": f"TC-0{n}", "name": "the tool exits 0", "type": "positive", "severity": "major",  # noqa: E731
                      "steps": [{"do": {"cli": {"cmd": sys.executable, "args": ["-c", "print(1)"]}},
                                 "expect": [{"path": "$.exit_code", "op": "eq", "value": 0, "from": "structural"}]}]}
    data = suite_dict(ac="AC-7", surface="linkr-cli")
    data["cases"] = [case(1), case(2)]
    write_suite(project, data, name="AC-7")


def test_reset_runs_before_every_case(linkr):
    project = linkr
    two_case_cli_suite(project)
    write_env(project, reset=f'"{sys.executable}" -c "open(\'resets.txt\',\'a\').write(\'x\')"')
    r = run_gf(project, "run")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (project / "resets.txt").read_text(encoding="utf-8") == "xx"


def test_a_failing_reset_is_an_error_for_the_case_not_a_fail(linkr):
    project = linkr
    two_case_cli_suite(project)
    write_env(project, reset=f'"{sys.executable}" -c "import sys;sys.exit(4)"')
    run_id = run_gf(project, "run").stdout.strip()
    record = json.loads((project / "greenfield" / "runs" / run_id / "cases" / "AC-7__TC-01.json").read_text(encoding="utf-8"))
    assert "reset failed (exit 4)" in record["error"] and record["steps"] == []
    run_gf(project, "score", run_id)
    verdicts = json.loads((project / "greenfield" / "runs" / run_id / "verdicts.json").read_text(encoding="utf-8"))
    assert verdicts["acs"]["AC-7"]["verdict"] == "error"


def test_a_reset_that_trips_the_fence_is_not_run(linkr):
    project = linkr
    two_case_cli_suite(project)
    (project / "greenfield" / "evidence" / "keep.txt").write_text("evidence", encoding="utf-8")
    write_env(project, reset="rm -rf greenfield/evidence")
    run_id = run_gf(project, "run").stdout.strip()
    record = json.loads((project / "greenfield" / "runs" / run_id / "cases" / "AC-7__TC-01.json").read_text(encoding="utf-8"))
    assert "reset not run: fence [delete-data]" in record["error"]
    assert (project / "greenfield" / "evidence" / "keep.txt").is_file()
