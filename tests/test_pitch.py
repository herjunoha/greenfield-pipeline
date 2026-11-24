"""The `pitch` plugin that lives beside the core (pitch/): structure, cross-references, the statement fixture against
its spec, and the seam to the core: a statement plated by the hand-off mapping must pass `gp acs` with no orphan."""
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from conftest import ROOT, run_gf
from test_pack import acme  # noqa: F401  (the fixture that builds a project with a pack)
from test_plugin import front

PITCH = ROOT / "pitch"
FIX = ROOT / "tests" / "fixtures" / "acme-freight" / "pitch"
SKILLS = sorted((PITCH / "skills").glob("*/SKILL.md"))
USER_INVOKED = {"problem-to-solution", "proof-of-concept", "retro"}
SKILL_CAP = 175   # problem-to-solution is the core skill and carries both templates
REFERENCES = {"rules.md", "solution-statement-spec.md", "drafting-contract.md", "handoff.md"}


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_manifest_and_marketplace_list_both_plugins():
    manifest = json.loads(text(PITCH / ".claude-plugin" / "plugin.json"))
    assert manifest["name"] == "pitch" and manifest["version"]
    market = json.loads(text(ROOT / ".claude-plugin" / "marketplace.json"))
    assert {p["name"]: p["source"] for p in market["plugins"]} == {"greenfield-pipeline": "./", "pitch": "./pitch"}


def test_the_six_skills_and_four_references_exist():
    assert {p.parent.name for p in SKILLS} == {"deal-factor", "problem-to-solution", "business-proposal",
                                                "pitch-deck", "proof-of-concept", "retro"}
    assert {p.name for p in (PITCH / "references").glob("*.md")} == REFERENCES


@pytest.mark.parametrize("path", SKILLS, ids=lambda p: p.parent.name)
def test_skill_frontmatter_size_and_pointers(path):
    meta, body = front(path), text(path)
    assert meta["name"] == path.parent.name and meta["description"]
    assert bool(meta.get("disable-model-invocation")) == (path.parent.name in USER_INVOKED)
    assert len(body.splitlines()) <= SKILL_CAP
    assert "../../references/rules.md" in body
    for ref in re.findall(r"\.\./\.\./references/([\w-]+\.md)", body):
        assert (PITCH / "references" / ref).is_file(), f"{path.parent.name} points at a missing {ref}"


def test_the_drafting_skills_point_at_the_contract_and_restate_none_of_it():
    for name in ("business-proposal", "pitch-deck"):
        body = text(PITCH / "skills" / name / "SKILL.md")
        assert "../../references/drafting-contract.md" in body
        assert "Pre-flight" not in body.replace("its pre-flight", "").replace("pre-flight, placeholders", "")


def test_rules_has_exactly_four_numbered_rules():
    rules = re.findall(r"^\d+\. \*\*", text(PITCH / "references" / "rules.md"), re.M)
    assert len(rules) == 4


def test_every_gp_command_and_skill_the_pitch_files_name_exists():
    from gp import cli
    known = set(next(a for a in cli.build_parser()._actions if a.dest == "command").choices)
    named, skills_named = set(), set()
    for path in [*SKILLS, *(PITCH / "references").glob("*.md")]:
        body = text(path)
        named |= set(re.findall(r"`gp ([a-z][a-z-]*)", body))
        skills_named |= set(re.findall(r"`greenfield-pipeline:([a-z-]+)`", body))
    assert named - known == set(), f"pitch files name commands that do not exist: {named - known}"
    core = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    assert skills_named - core == set(), f"pitch files name core skills that do not exist: {skills_named - core}"


def test_no_pitch_text_names_a_pricing_figure_or_a_person():
    for path in [*SKILLS, *(PITCH / "references").glob("*.md"), FIX / "solution-statement.md"]:
        assert not re.search(r"[$€£]\s?\d|\b(?:USD|IDR|EUR)\s?\d", text(path)), path


# --- the statement fixture against its spec -----------------------------------------------------------------

STATEMENT = text(FIX / "solution-statement.md")
HEADINGS = ["Outcome", "Problem statement", "Domain", "Worked examples", "Solution elements", "Why us", "Assumptions",
            "Data and regulation", "Scope boundaries", "Commitments", "Gaps (internal, never client-facing)",
            "Traceability index"]


def section(name: str) -> str:
    match = re.search(rf"^## {re.escape(name)}\n(.*?)(?=^## |\Z)", STATEMENT, re.S | re.M)
    assert match, f"statement has no section {name}"
    return match.group(1)


def test_the_statement_has_every_section_in_spec_order():
    found = re.findall(r"^## (.+)$", STATEMENT, re.M)
    assert found == HEADINGS
    spec = text(PITCH / "references" / "solution-statement-spec.md")
    assert re.findall(r"^## (.+)$", spec.split("```markdown")[1].split("```")[0], re.M) == HEADINGS


def test_every_stated_problem_is_solved_scoped_out_or_a_gap_and_every_element_solves_one():
    problems = re.findall(r"^- (P\d+) .*\[stated\]", section("Problem statement"), re.M)
    solved = set(re.findall(r"^- Solves: (.+)$", section("Solution elements"), re.M)[0].replace(" ", "").split(","))
    for line in re.findall(r"^- Solves: (.+)$", section("Solution elements"), re.M):
        solved |= set(line.replace(" ", "").split(","))
    assert set(problems) <= solved
    elements = re.findall(r"^### (E\d+) ", section("Solution elements"), re.M)
    assert len(re.findall(r"^- Solves: ", section("Solution elements"), re.M)) == len(elements)


def test_demonstrated_needs_an_attestation_and_why_us_needs_a_basis():
    for line in re.findall(r"^- Proof evidence: (.+)$", section("Solution elements"), re.M):
        assert line.startswith(("pending", "failed")) or ("demonstrated" in line and "attested by" in line)
    for line in section("Why us").strip().splitlines():
        assert re.search(r"basis: O\d+|human \(", line), line


def test_a_rule_with_no_confirmed_example_is_a_gap():
    rules = re.findall(r"^- (R\d+) ", STATEMENT.split("### Rules")[1].split("## Worked")[0], re.M)
    examples = section("Worked examples")
    for rule in rules:
        if f"rule {rule} " not in examples:
            assert rule in section("Gaps (internal, never client-facing)"), f"{rule} has no example and is not a gap"


# --- the seam: the hand-off mapping against the core's own audit ---------------------------------------------

def plated_project(tmp_path):
    result = run_gf(tmp_path, "init", env={"GP_PACKS_DIR": str(tmp_path / "no-packs")})
    assert result.returncode == 0, result.stderr
    sources = tmp_path / "greenfield" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX / "solution-statement.md", sources / "solution-statement.md")
    target = tmp_path / "greenfield" / "requirements"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(FIX / "plated.canonical.yaml", target / "acme-freight.canonical.yaml")
    return tmp_path


def test_a_statement_plated_by_the_handoff_mapping_passes_the_audit_with_no_orphan(tmp_path):
    project = plated_project(tmp_path)
    out = run_gf(project, "acs").stdout
    assert "refused:" not in out and "orphans: none" in out, out


def test_the_plated_canonical_carries_the_statement_and_nothing_of_the_deal_lens():
    plated = yaml.safe_load(text(FIX / "plated.canonical.yaml"))
    assert {s["name"] for s in plated["project"]["surfaces"]} == set(re.findall(r"^- Surface: ([\w-]+) ", STATEMENT, re.M))
    assert {g["term"] for g in plated["project"]["glossary"]} == set(re.findall(r"^- ([\w ]+): .*source: client", section("Domain").split("### Rules")[0], re.M))
    assert len(plated["requirements"]) == len(re.findall(r"^### E\d+ ", STATEMENT, re.M))
    assert {e["source"] for e in plated["examples"]} == {"sponsor-confirmed"}
    flat = text(FIX / "plated.canonical.yaml").lower()
    assert "why us" not in flat and "rejected off-the-shelf" not in flat and "win theme" not in flat


# --- the pack files pitch reads ------------------------------------------------------------------------------

def test_pack_show_reads_a_pack_markdown_file_and_still_reads_yaml_keys(acme_pack):
    project, pack = acme_pack
    assert run_gf(project, "pack", "show", "offerings").stdout.strip().startswith("# Offerings")
    assert run_gf(project, "pack", "show", "language").stdout.strip() == "en"
    assert run_gf(project, "pack", "show", "nothing").returncode != 0


def test_pack_check_flags_a_redact_pattern_inside_offerings(acme):
    project, pack = acme(**{"pack": {"redact": [r"secret-client"]}, "offerings.md": "# Offerings\nsecret-client case\n"})
    out = run_gf(project, "pack", "check")
    assert "offerings.md matches the redact pattern" in out.stdout


@pytest.fixture
def acme_pack(acme):
    return acme(**{"offerings.md": "# Offerings: acme\nApproved by: owner, 2026-11-24\n"})
