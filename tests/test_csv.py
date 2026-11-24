"""Check 5 of plan section 12: the scratch run again on a second shape, `acme-csv`: cli only, no network, results read
from captured files. It keeps the case model from being HTTP-shaped."""
import json
import shutil
import sys

import yaml

from conftest import FIXTURES, edit_canonical, run_gf, write_suite
from csv_suites import suites
from test_code import commit
from test_env import write_env
from test_fence import set_fence
from test_scratch import gp, states, verdicts

CSV = FIXTURES / "acme-csv"


def csv_project(project):
    shutil.copytree(CSV / "greenfield", project / "greenfield", dirs_exist_ok=True)
    gp(project, "product", "init")
    product = project / "product"
    shutil.copy(CSV / "product" / "csvsum.py", product / "csvsum.py")
    (product / ".gitignore").write_text((product / ".gitignore").read_text(encoding="utf-8") + "*.csv\n*.json\n", encoding="utf-8")
    commit(project, "feat: the walking skeleton")
    set_fence(project, code_repos=[{"path": "product", "runner": "process", "trunk": "main"}])
    health = f'"{sys.executable}" csvsum.py --version'
    write_env(project, cwd=str(product), health={"cmd": health, "expect": r"\d+\.\d+\.\d+", "timeout": 10})
    for ac, data in suites(sys.executable).items():
        write_suite(project, data, name=ac)
        gp(project, "review", "suite", ac, "--by", "rex", "--verdict", "approve")
        gp(project, "accept-line", f"suite:{ac}")


def run_all(project):
    gp(project, "build")
    run_id = gp(project, "run")
    gp(project, "score", run_id)
    return run_id


def test_a_cli_only_project_goes_from_skeleton_to_done_with_red_first(project):
    csv_project(project)
    assert "orphans: none" in gp(project, "acs")
    gp(project, "check")
    assert "preflight ok" in gp(project, "preflight")                     # a cli skeleton: no server, a health command
    red = run_all(project)
    assert set(verdicts(project, red).values()) == {"fail"}, verdicts(project, red)
    assert set(states(project).values()) == {"red"}

    shutil.copy(CSV / "reference" / "csvsum.py", project / "product" / "csvsum.py")
    commit(project, "feat: the four ACs")
    green = run_all(project)
    assert set(verdicts(project, green).values()) == {"pass"}, verdicts(project, green)
    gp(project, "review", "run", green, "--by", "rex", "--verdict", "approve")
    edit_canonical(project, lambda d: d["project"].update(status="approved"))
    gp(project, "accept-line", "canonical")
    assert set(states(project).values()) == {"done"}, run_gf(project, "acs").stdout
    gp(project, "check")


def test_nothing_in_this_project_is_http_shaped(project):
    csv_project(project)
    drivers = {step["do"].keys().__iter__().__next__() for data in suites(sys.executable).values()
               for case in data["cases"] for step in case["steps"]}
    assert drivers == {"cli"}
    run_id = run_all(project)
    cases = sorted((project / "greenfield" / "runs" / run_id / "cases").glob("*.json"))
    assert cases and all(json.loads(p.read_text(encoding="utf-8"))["driver"] == "cli" for p in cases)
    env = yaml.safe_load((project / "greenfield" / "environments.yaml").read_text(encoding="utf-8"))["environments"][0]
    assert "base_url" not in env and "state_url" not in env


def test_a_planted_blind_spot_in_the_summary_turns_its_ac_red(project):
    """Independence on the second shape: sums a text column's length instead of leaving it out would pass its own checks;
    here the builder forgets the header-only edge (rows 1 instead of 0), and AC-3 must be the one that goes red."""
    csv_project(project)
    run_all(project)
    broken = (CSV / "reference" / "csvsum.py").read_text(encoding="utf-8").replace(
        "return {\"rows\": rows,", "return {\"rows\": max(rows, 1),")
    assert broken != (CSV / "reference" / "csvsum.py").read_text(encoding="utf-8")
    (project / "product" / "csvsum.py").write_text(broken, encoding="utf-8")
    commit(project, "feat: the four ACs, with a blind spot")
    result = verdicts(project, run_all(project))
    assert result["AC-3"] == "fail" and result["AC-1"] == "pass" and result["AC-2"] == "pass", result
