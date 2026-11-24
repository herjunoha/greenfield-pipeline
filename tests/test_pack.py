import json
import sys

import pytest
import yaml

from conftest import ROOT, run_gf
from test_hook import bash, fire

PHONE, EMAIL = "+62 812-3456-7890", "jane.doe@example.com"


def make_pack(tmp_path, **files):
    folder = tmp_path / "packs" / "acme"
    folder.mkdir(parents=True)
    data = yaml.safe_load((ROOT / "packs" / "generic" / "pack.yaml").read_text(encoding="utf-8"))
    data.update(name="acme", company="acme")
    data.update(files.pop("pack", {}))
    (folder / "pack.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    for name, text in files.items():
        (folder / name).write_text(text if isinstance(text, str) else yaml.safe_dump(text), encoding="utf-8")
    return folder


@pytest.fixture
def acme(tmp_path_factory):
    """A project initialised with a pack; the builder gets the pack folder back for editing."""
    def build(**files):
        base = tmp_path_factory.mktemp("acme")
        pack = make_pack(base, **files)
        project = base / "project"
        project.mkdir()
        r = run_gf(project, "init", "--pack", "acme", env={"GP_PACKS_DIR": str(base / "packs")})
        assert r.returncode == 0, r.stderr
        return project, pack
    return build


# --- check, tamper, loosening ---------------------------------------------------------------------------------

def test_the_generic_pack_passes_its_own_check(project):
    r = run_gf(project, "pack", "check")
    assert r.returncode == 0 and "0 problem(s)" in r.stdout


def test_a_pack_with_missing_keys_bad_regex_and_long_lessons_fails(acme):
    project, pack = acme(**{"lessons.md": "line\n" * 31})
    data = yaml.safe_load((pack / "pack.yaml").read_text(encoding="utf-8"))
    del data["stack"]
    data["redact"] = ["(["]
    (pack / "pack.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    out = run_gf(project, "pack", "check").stdout
    assert "missing stack" in out and "redact pattern '([' is not a valid regex" in out and "lessons.md is longer than 30" in out


def test_a_pack_file_edited_after_acceptance_asks_until_the_owner_accepts_again(acme):
    project, pack = acme()
    assert fire(project, "pre", bash(project, "echo hi")).stdout == ""
    (pack / "pack.yaml").write_text((pack / "pack.yaml").read_text(encoding="utf-8") + "# edited\n", encoding="utf-8")
    out = json.loads(fire(project, "pre", bash(project, "echo hi")).stdout)["hookSpecificOutput"]
    assert out["permissionDecision"] == "ask" and "a pack file changed since the owner accepted it" in out["permissionDecisionReason"]
    assert fire(project, "pre", {"tool_name": "Read", "tool_input": {"file_path": "x"}, "cwd": str(project)}).stdout == ""
    assert run_gf(project, "pack", "check").returncode == 1
    assert run_gf(project, "pack", "accept").returncode == 0
    assert fire(project, "pre", bash(project, "echo hi")).stdout == "" and run_gf(project, "pack", "check").returncode == 0


def test_gf_pack_accept_is_the_owners_to_run(project):
    assert "[scope]" in fire(project, "pre", bash(project, "gp pack accept")).stdout


def test_a_loosening_pack_rule_is_rejected_and_has_no_effect(acme):
    rules = {"rules": [{"id": "let-push", "match": "^git push", "action": "allow", "reason": "convenient"}]}
    project, pack = acme(**{"pause.yaml": rules})
    out = run_gf(project, "pack", "check").stdout
    assert "action 'allow' loosens the core list" in out
    assert "[outside-lane]" in fire(project, "pre", bash(project, "git push origin main")).stdout   # core still asks


def test_a_pack_can_add_a_pause_and_an_allowlist_exception(acme):
    rules = {"rules": [{"id": "no-curl", "match": r"\bcurl\b", "action": "ask", "reason": "use the team's http tool"},
                       {"id": "scripts", "match": r"^\./deploy-docs", "action": "ask", "unless_listed": "lanes",
                        "reason": "docs deploys go through a lane"}]}
    project, _ = acme(**{"pause.yaml": rules})
    assert run_gf(project, "pack", "check").returncode == 0
    out = fire(project, "pre", bash(project, "curl https://example.com")).stdout
    assert "[pack-no-curl]" in out and "use the team's http tool" in out
    assert fire(project, "pre", bash(project, "ls")).stdout == ""


# --- connectors: feeds, notify, numbering ---------------------------------------------------------------------

def feed_pack(acme, **extra):
    script = (f"import json\nprint(json.dumps([{{'title': 'Call {PHONE}', 'body': 'Reach {EMAIL} or {PHONE}. "
              f"Ticket ACME-4411. Token sk-abcdefghijklmnop1234.', 'source': 'inbox'}}]))\n")
    connectors = {"feeds": [{"name": "inbox", "command": [sys.executable, "feed.py"]}]}
    return acme(**{"feed.py": script, "connectors.yaml": connectors, "pack": {"redact": [r"ACME-\d+"]}, **extra})


def test_feed_notes_are_redacted_before_any_file_is_written(acme):
    project, _ = feed_pack(acme)
    r = run_gf(project, "feed")
    assert r.returncode == 0 and "1 needs-triage item(s)" in r.stdout
    item = (project / "greenfield" / "items" / "I-1.md").read_text(encoding="utf-8")
    assert "[phone]" in item and "[email]" in item and "[token]" in item and "[redacted]" in item
    for path in project.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            assert PHONE not in text and EMAIL not in text and "sk-abcdefghijklmnop1234" not in text, path.name


def test_a_feed_note_is_only_minted_once(acme):
    project, _ = feed_pack(acme)
    run_gf(project, "feed")
    assert "0 needs-triage item(s)" in run_gf(project, "feed").stdout


def test_notify_redacts_prints_by_default_and_speaks_once_per_turn(acme):
    project, _ = acme()
    r = run_gf(project, "notify", f"I-3 is waiting. Ask {EMAIL}", "--action", "answer the brief", "--turn", "t1")
    assert r.returncode == 0 and "[email]" in r.stdout and "Recommended action: answer the brief" in r.stdout
    again = run_gf(project, "notify", "second", "--action", "x", "--turn", "t1")
    assert again.returncode != 0 and "one message per agent turn" in again.stderr
    assert run_gf(project, "notify", "third", "--action", "x", "--turn", "t2").returncode == 0


def test_notify_can_pipe_to_the_packs_command(acme):
    project, pack = acme(**{"sink.py": "import sys\nopen('sent.txt', 'w').write(sys.stdin.read())\n",
                            "connectors.yaml": {"notify": {"command": [sys.executable, "sink.py"]}}})
    assert run_gf(project, "notify", "hello", "--action", "do it").returncode == 0
    assert "Recommended action: do it" in (pack / "sent.txt").read_text(encoding="utf-8")


def test_numbers_are_issued_in_sequence_and_the_fence_asks(project):
    assert run_gf(project, "number", "acceptance").stdout.strip().endswith("-001")
    assert run_gf(project, "number", "acceptance").stdout.strip().endswith("-002")
    assert run_gf(project, "number", "release").stdout.strip().endswith("-001")
    assert len((project / "greenfield" / "numbers.tsv").read_text(encoding="utf-8").splitlines()) == 3
    assert "[irreversible]" in fire(project, "pre", bash(project, "gp number acceptance")).stdout
