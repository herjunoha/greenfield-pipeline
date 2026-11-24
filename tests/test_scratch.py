"""Check 4 and check 6 of plan section 12, driven through the real commands on acme-linkr: a scratch run from a
skeleton to done with red first on every AC, and the independence check. The build here is the fixture's reference
implementation standing in for ed: this proves the engine's mechanics, not a model's behaviour."""
import json
import shutil
import subprocess
import sys

import yaml
from pathlib import Path

from conftest import FIXTURES, edit_canonical, leak_words, run_gf, write_suite
from linkr_suites import suites
from test_code import commit
from test_env import free_port, git, skeleton_env, write_env
from test_fence import set_fence

REFERENCE = FIXTURES / "acme-linkr" / "reference"


def gp(project, *args):
    r = run_gf(project, *args)
    assert r.returncode == 0, f"gp {' '.join(args)}\n{r.stdout}{r.stderr}"
    return r.stdout.strip()


def states(project):
    return {r["id"]: r["state"] for r in json.loads(run_gf(project, "acs", "--json").stdout)["acs"]}


def verdicts(project, run_id):
    path = project / "greenfield" / "runs" / run_id / "verdicts.json"
    return {ac: v["verdict"] for ac, v in json.loads(path.read_text(encoding="utf-8"))["acs"].items()}


def skeleton_project(project):
    """The overlay, an empty product repo with the walking skeleton committed, and an environment for it."""
    shutil.copytree(FIXTURES / "acme-linkr" / "greenfield", project / "greenfield", dirs_exist_ok=True)
    gp(project, "product", "init")
    product = project / "product"
    shutil.copy(FIXTURES / "acme-linkr" / "product" / "app.py", product / "app.py")
    (product / ".gitignore").write_text((product / ".gitignore").read_text(encoding="utf-8") + "*.db\n", encoding="utf-8")
    commit(project, "feat: the walking skeleton")
    set_fence(project, code_repos=[{"path": "product", "runner": "process", "trunk": "main"}])
    write_env(project, **skeleton_env(free_port(), cwd=str(product), state_url="/state"),
              )
    env = yaml.safe_load((project / "greenfield" / "environments.yaml").read_text(encoding="utf-8"))
    env["environments"][0]["start"] = f'"{sys.executable}" app.py --port ' + env["environments"][0]["start"].split("--port ")[1]
    (project / "greenfield" / "environments.yaml").write_text(yaml.safe_dump(env), encoding="utf-8")


def write_all_suites(project):
    for ac, data in suites(sys.executable).items():
        write_suite(project, data, name=ac)


def approve_suites(project):
    for ac in suites(sys.executable):
        gp(project, "review", "suite", ac, "--by", "rex", "--verdict", "approve")
        gp(project, "accept-line", f"suite:{ac}")


def build_reference(project, mutate=None):
    product = project / "product"
    for name in ("app.py", "linkr.py", "test_app.py"):
        text = (REFERENCE / name).read_text(encoding="utf-8")
        if mutate and name == "app.py":
            text = mutate(text)
        (product / name).write_text(text, encoding="utf-8")


def own_unit_tests(project):
    return subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=project / "product", capture_output=True, text=True)


def full_run(project):
    gp(project, "build")
    run_id = gp(project, "run")
    gp(project, "score", run_id)
    return run_id


def test_scratch_run_from_skeleton_to_done_with_red_first_on_every_ac(project):
    skeleton_project(project)
    assert "orphans: none" in gp(project, "acs")                                   # the audit, zero orphans
    write_all_suites(project)
    gp(project, "check")                                                           # clean before anything runs
    approve_suites(project)
    gp(project, "preflight")
    assert set(states(project).values()) == {"ready"}

    red = full_run(project)                                                        # against the skeleton
    assert set(verdicts(project, red).values()) == {"fail"}, verdicts(project, red)
    assert set(states(project).values()) == {"red"}

    build_reference(project)
    assert own_unit_tests(project).returncode == 0
    commit(project, "feat: the eight ACs")
    green = full_run(project)
    assert set(verdicts(project, green).values()) == {"pass"}, verdicts(project, green)
    assert set(states(project).values()) == {"green"}                              # green is not yet done

    gp(project, "review", "run", green, "--by", "rex", "--verdict", "approve")
    edit_canonical(project, lambda d: d["project"].update(status="approved"))
    gp(project, "accept-line", "canonical")
    assert set(states(project).values()) == {"done"}, run_gf(project, "acs").stdout
    gp(project, "check")                                                           # no dirty build, no secret, no gap
    words = leak_words()                                       # private, outside the plugin; skipped when not set
    if words:
        def forms(base):                       # a machine path as it appears plain, posix and JSON-escaped once or twice
            plain = str(base)
            return (plain, base.as_posix(), json.dumps(plain)[1:-1], json.dumps(json.dumps(plain)[1:-1])[1:-1])

        where = [f for base in (project, Path.home()) for f in forms(base)]      # the machine's own paths are not the plugin's

        def body(path):
            text = path.read_text(encoding="utf-8")
            for form in where:
                text = text.replace(form, "")
            return text.lower()
        assert not [p for p in (project / "greenfield" / "runs").rglob("*.json") if any(w in body(p) for w in words)]


def test_independence_a_planted_blind_spot_passes_the_builders_tests_and_turns_its_ac_red(project):
    skeleton_project(project)
    write_all_suites(project)
    approve_suites(project)
    red = full_run(project)
    assert set(verdicts(project, red).values()) == {"fail"}

    # The builder's check accepts anything that is not ftp. Its own unit tests (https ok, ftp refused) still pass,
    # but the canonical says only http and https, so a javascript address must be refused.
    build_reference(project, lambda text: text.replace('return url.startswith(("http://", "https://"))',
                                                       'return not url.startswith("ftp:")'))
    assert own_unit_tests(project).returncode == 0
    commit(project, "feat: the eight ACs, with a blind spot")
    run = full_run(project)
    result = verdicts(project, run)
    assert result["AC-4"] == "fail" and all(v == "pass" for ac, v in result.items() if ac != "AC-4"), result
    assert states(project)["AC-4"] == "red" and "done" not in states(project).values()
