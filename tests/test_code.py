import json

import yaml

from conftest import run_gf
from test_env import git
from test_fence import set_fence

PIN = "flask==3.0.0\n"


def repo_project(project, files=None, registries=True):
    """A project with a committed product repo (runner: process accepted) holding `files`."""
    run_gf(project, "product", "init")
    set_fence(project, code_repos=[{"path": "product", "runner": "process", "trunk": "main"}],
              registries=[{"name": "pypi", "host": "pypi.org"}] if registries else [])
    for name, text in (files or {}).items():
        (project / "product" / name).write_text(text, encoding="utf-8")
    if files:
        commit(project, "add files")
    return project / "product"


def commit(project, message="change"):
    git(project / "product", "add", "-A")
    git(project / "product", "commit", "-m", message)
    return git(project / "product", "rev-parse", "HEAD")


def deps_row(project, name="flask", license_="MIT", registry="pypi.org", item="I-1"):
    path = project / "greenfield" / "deps.tsv"
    path.write_text(path.read_text(encoding="utf-8") + f"{name}\t3.0.0\t{license_}\t{registry}\t{item}\n", encoding="utf-8")


def check(project, *args):
    r = run_gf(project, "check", *args)
    return r.returncode, r.stdout


# --- product repo and builds --------------------------------------------------------------------------------

def test_product_init_makes_a_repo_and_leaves_the_fence_to_the_owner(project):
    fence = project / "greenfield" / "fence.yaml"
    before = fence.read_bytes()
    r = run_gf(project, "product", "init")
    assert r.returncode == 0 and "the engine never writes the fence" in r.stdout and "runner: container" in r.stdout
    assert git(project / "product", "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert ".env" in (project / "product" / ".gitignore").read_text(encoding="utf-8")
    assert fence.read_bytes() == before
    assert run_gf(project, "product", "init").returncode == 0          # idempotent


def test_a_build_records_the_clean_head(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    r = run_gf(project, "build")
    assert r.returncode == 0, r.stdout + r.stderr
    entry = yaml.safe_load((project / "greenfield" / "builds.yaml").read_text(encoding="utf-8"))["product"]
    assert entry["commit"] == git(repo, "rev-parse", "HEAD") and entry["dirty"] is False


def test_a_dirty_tree_is_never_a_build(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
    r = run_gf(project, "build")
    assert r.returncode == 2 and "dirty tree is never a build" in r.stderr
    assert yaml.safe_load((project / "greenfield" / "builds.yaml").read_text(encoding="utf-8")) == {}


def test_check_blocks_a_dirty_tree_and_a_dirty_recorded_build(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    assert check(project)[0] == 0
    (repo / "scratch.txt").write_text("x", encoding="utf-8")
    code, out = check(project)
    assert code == 1 and "uncommitted changes; a dirty tree is never a build" in out
    (repo / "scratch.txt").unlink()
    (project / "greenfield" / "builds.yaml").write_text(
        yaml.safe_dump({"product": {"commit": git(repo, "rev-parse", "HEAD"), "dirty": True}}), encoding="utf-8")
    assert "builds.yaml records a dirty build" in check(project)[1]


def test_a_build_goes_stale_when_head_moves(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    run_gf(project, "build")
    assert check(project)[0] == 0
    (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
    commit(project)
    assert "HEAD has moved" in check(project)[1]
    run_gf(project, "build")
    assert check(project)[0] == 0


def test_a_repo_that_is_not_declared_is_not_checked_and_one_that_is_not_a_repo_is_flagged(project):
    set_fence(project, code_repos=[{"path": "product", "runner": "process"}])
    assert "is not a git repo" in check(project)[1]


# --- lockfile, secrets, dependencies ------------------------------------------------------------------------

def test_a_manifest_without_a_lockfile_is_blocked(project):
    repo_project(project, {"package.json": json.dumps({"name": "x", "dependencies": {}})})
    code, out = check(project)
    assert code == 1 and "package.json has no lockfile" in out


def test_a_lockfile_clears_it_and_an_unpinned_requirements_file_does_not(project):
    repo_project(project, {"package.json": json.dumps({"name": "x"}), "package-lock.json": "{}"})
    assert check(project)[0] == 0
    (project / "product" / "requirements.txt").write_text("flask>=3\n", encoding="utf-8")
    commit(project)
    assert "requirements.txt line 1 is not pinned" in check(project)[1]


def test_a_secret_pattern_in_a_committed_file_is_blocked_without_echoing_it(project):
    key = "AKIA" + "QWERTYUIOPASDFGH"                       # twenty characters, shaped like an AWS key id
    repo_project(project, {"config.py": f'AWS = "{key}"\nPASSWORD = "hunter2hunter2"\n',
                           "key.pem": "-----BEGIN RSA PRIVATE KEY-----\nabc\n"})
    code, out = check(project)
    assert code == 1 and "config.py:1: looks like an AWS access key" in out
    assert "config.py:2: looks like a hard-coded credential" in out and "key.pem:1: looks like a private key" in out
    assert key not in out and "hunter2hunter2" not in out


def test_placeholders_and_example_env_files_are_not_secrets_but_a_committed_env_is(project):
    repo_project(project, {"config.py": 'API_KEY = "changeme-changeme"\nTOKEN = "${TOKEN_FROM_ENV}"\n',
                           ".env.example": "API_KEY=\n"})
    assert check(project)[0] == 0
    (project / "product" / ".env").write_text("API_KEY=real\n", encoding="utf-8")
    git(project / "product", "add", "-f", ".env")
    commit(project)
    assert ".env: an env file is committed" in check(project)[1]


def test_an_untracked_secret_is_not_a_committed_one(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    (repo / "notes.txt").write_text('password = "hunter2hunter2"\n', encoding="utf-8")
    assert "looks like" not in check(project)[1]


def test_an_undocumented_dependency_is_blocked_until_it_has_a_row(project):
    repo_project(project, {"requirements.txt": PIN})
    code, out = check(project)
    assert code == 1 and "dependency flask has no row in deps.tsv" in out
    run_gf(project, "new", "stack brief", "--state", "closed", "--reason", "done")
    deps_row(project)
    assert check(project)[0] == 0


def test_a_dependency_row_needs_a_declared_registry_and_a_license_under_policy(project):
    repo_project(project, {"requirements.txt": PIN})
    run_gf(project, "new", "stack brief", "--state", "ready-for-human")
    deps_row(project, registry="mirror.example.org")
    assert "came from mirror.example.org, which fence.yaml does not declare" in check(project)[1]
    path = project / "greenfield" / "deps.tsv"
    path.write_text(path.read_text(encoding="utf-8").split("flask")[0], encoding="utf-8")
    deps_row(project, license_="GPL-3.0")
    assert "license GPL-3.0, outside the pack's policy; item I-1 must be closed" in check(project)[1]
    close_item = project / "greenfield" / "items" / "I-1.md"
    close_item.write_text(close_item.read_text(encoding="utf-8").replace("state: ready-for-human", "state: closed\nreason: done"),
                          encoding="utf-8")
    assert check(project)[0] == 0                                         # the owner accepted the license


def test_unparsed_ecosystems_are_noted_not_silently_passed(project):
    repo_project(project, {"go.mod": "module x\n"})
    assert "go.mod dependencies are not parsed" in check(project)[1]


# --- a trunk merge needs a verdict on that exact commit ------------------------------------------------------

def write_verdict(project, commit_sha, full=True, verdict="pass", name="20261113T000000Z"):
    folder = project / "greenfield" / "runs" / name
    folder.mkdir(parents=True)
    (folder / "verdicts.json").write_text(json.dumps({
        "run": name, "full": full, "build_ids": {"product": {"commit": commit_sha}},
        "acs": {"AC-1": {"verdict": verdict, "cases": {}}}}), encoding="utf-8")


def test_a_merge_without_a_verdict_on_that_commit_is_blocked(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    git(repo, "checkout", "-b", "feature/a")
    (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
    tip = commit(project)
    code, out = check(project, "--merge", "feature/a")
    assert code == 1 and f"no full run on exactly that commit passed every AC" in out and tip[:8] in out


def test_only_a_full_all_pass_verdict_on_the_same_commit_lets_it_merge(project):
    repo = repo_project(project, {"app.py": "print(1)\n"})
    git(repo, "checkout", "-b", "feature/a")
    (repo / "app.py").write_text("print(2)\n", encoding="utf-8")
    tip = commit(project)
    write_verdict(project, tip, verdict="fail", name="r1")
    write_verdict(project, tip, full=False, name="r2")
    write_verdict(project, "0" * 40, name="r3")                          # a verdict on another commit
    assert check(project, "--merge", "feature/a")[0] == 1
    write_verdict(project, tip, name="r4")
    assert check(project, "--merge", "feature/a")[0] == 0
    (repo / "app.py").write_text("print(3)\n", encoding="utf-8")
    commit(project)                                                       # a new commit needs a new verdict
    assert check(project, "--merge", "feature/a")[0] == 1
