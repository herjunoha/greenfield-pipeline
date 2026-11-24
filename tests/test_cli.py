import re
from pathlib import Path

import yaml

from conftest import run_gf
from gp import project as proj


def make_pack(root: Path, name: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "pack.yaml").write_text(f"name: {name}\ncompany: {name}\nlanguage: en\n", encoding="utf-8")


def init(tmp_path, *args, packs=None, env=None):
    e = {"GP_PACKS_DIR": str(packs or tmp_path / "no-packs"), **(env or {})}
    return run_gf(tmp_path, "init", *args, env=e)


def fence_of(root):
    return yaml.safe_load((root / "greenfield" / "fence.yaml").read_text(encoding="utf-8"))


def test_init_scaffolds_the_layout(tmp_path):
    r = init(tmp_path)
    assert r.returncode == 0 and "pack: generic" in r.stdout
    for sub in proj.SUBDIRS:
        assert (tmp_path / "greenfield" / sub).is_dir()
    for name in proj.FILES:
        assert (tmp_path / "greenfield" / name).is_file()
    f = fence_of(tmp_path)
    assert f["pack"] == "generic" and re.fullmatch(r"[0-9a-f]{64}", f["pack_sha256"])


def test_init_twice_changes_nothing(tmp_path):
    init(tmp_path)
    before = (tmp_path / "greenfield" / "fence.yaml").read_text(encoding="utf-8")
    r = init(tmp_path)
    assert r.returncode == 0 and "already" in r.stdout
    assert (tmp_path / "greenfield" / "fence.yaml").read_text(encoding="utf-8") == before


def test_pack_resolution_order(tmp_path_factory):
    def case(packs, args=(), env=None):
        d = tmp_path_factory.mktemp("p")
        root = tmp_path_factory.mktemp("store")
        for p in packs:
            make_pack(root, p)
        r = init(d, *args, packs=root, env=env)
        return r, (fence_of(d)["pack"] if r.returncode == 0 else None)

    r, name = case(["acme"])
    assert name == "acme" and "the only installed pack" in r.stdout
    r, name = case(["a", "b"], env={"GP_PACK": "b"})
    assert name == "b" and "GP_PACK" in r.stdout
    r, name = case(["a", "b"])
    assert name == "generic" and "bundled generic pack" in r.stdout
    r, name = case(["a", "b"], args=["--pack", "a"], env={"GP_PACK": "b"})
    assert name == "a"
    r, _ = case([], args=["--pack", "missing"])
    assert r.returncode == 2 and "not found" in r.stderr


def test_pack_hash_changes_when_a_pack_file_changes(tmp_path_factory):
    from gp import packs
    store = tmp_path_factory.mktemp("s")
    make_pack(store, "acme")
    before = packs.sha256(store / "acme")
    (store / "acme" / "pack.yaml").write_text("name: acme\nlanguage: id\n", encoding="utf-8")
    assert packs.sha256(store / "acme") != before


def test_new_next_status(project):
    a = run_gf(project, "new", "Redirect a link", "--state", "ready-for-agent", "--acs", "AC-1,AC-2")
    b = run_gf(project, "new", "Pick a stack", "--state", "ready-for-human", "--blocked-by", "I-1")
    c = run_gf(project, "new", "Dependent", "--state", "ready-for-agent", "--blocked-by", "I-1")
    assert [a.stdout.strip(), b.stdout.strip(), c.stdout.strip()] == ["I-1", "I-2", "I-3"]
    assert run_gf(project, "next").stdout.splitlines() == ["I-1\tRedirect a link"]
    status = run_gf(project, "status").stdout
    assert "items: 3" in status and "ready-for-human: 1" in status and "I-2" in status
    assert (project / "greenfield" / "items" / "I-1.md").read_text(encoding="utf-8").startswith("---\n")


def test_new_refuses_a_closed_item_without_a_reason(project):
    r = run_gf(project, "new", "x", "--state", "closed")
    assert r.returncode != 0 and "reason" in r.stderr


def test_commands_outside_a_project_say_so(tmp_path):
    r = run_gf(tmp_path, "next")
    assert r.returncode != 0 and "gp init" in r.stderr


def test_doctor_lists_prerequisites(tmp_path):
    r = run_gf(tmp_path, "doctor")
    assert r.returncode == 0
    for word in ("PyYAML", "git", "container runtime", "Node"):
        assert word in r.stdout


def test_pack_show_reads_a_key(project):
    assert run_gf(project, "pack", "show", "name").stdout.strip() == "generic"
    assert "MIT" in run_gf(project, "pack", "show", "policy.licenses").stdout
    assert run_gf(project, "pack", "show", "nope").returncode != 0
