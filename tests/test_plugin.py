"""The plugin's own files: worker tool limits, skill and agent frontmatter, and that every `gp` command the
instructions mention exists. Instructions that name a command that is gone are how a pipeline rots quietly."""
import json
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
GENERIC_TOOLS = {"Read", "Write", "Edit", "Glob", "Grep", "Bash", "PowerShell"}


def front(path: Path) -> dict:
    match = re.match(r"\A---\n(.*?)\n---\n", path.read_text(encoding="utf-8").replace("\r\n", "\n"), re.S)
    assert match, f"{path.name}: no frontmatter"
    return yaml.safe_load(match.group(1))


def agents():
    return sorted((ROOT / "agents").glob("*.md"))


def skills():
    return sorted((ROOT / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("path", agents(), ids=lambda p: p.stem)
def test_agent_frontmatter_and_generic_tools(path):
    meta = front(path)
    assert meta["name"] == path.stem and meta["description"].strip() and meta["model"] in ("opus", "sonnet", "haiku")
    tools = {t.strip() for t in str(meta["tools"]).split(",")}
    assert tools <= GENERIC_TOOLS, f"{path.stem} names a platform tool: {tools - GENERIC_TOOLS}"


def test_worker_tool_limits_match_their_role():
    tools = {p.stem: {t.strip() for t in str(front(p)["tools"]).split(",")} for p in agents()}
    assert tools["tim-the-triager"] == {"Read", "Write", "Glob", "Grep"}          # a judge cannot run anything
    for reviewer in ("rex-the-reviewer", "eve-the-executor"):
        assert "Edit" not in tools[reviewer]                                       # never repairs what it checks
    assert "Edit" in tools["ed-the-engineer"] and "PowerShell" not in tools["gus-the-generator"]


@pytest.mark.parametrize("path", skills(), ids=lambda p: p.parent.name)
def test_skill_frontmatter(path):
    meta = front(path)
    assert meta["name"] == path.parent.name and len(meta["description"]) > 40


def test_every_part_and_the_entry_skill_exists():
    assert {p.parent.name for p in skills()} >= {"deliver", "plate", "shape", "design", "build", "verify"}


def test_every_gf_command_the_instructions_name_exists():
    from gp import cli
    parser = cli.build_parser()
    known = set(next(a for a in parser._actions if a.dest == "command").choices)
    named = set()
    for path in [*agents(), *skills()]:
        named |= set(re.findall(r"`gp ([a-z][a-z-]*)", path.read_text(encoding="utf-8")))
    assert named - known == set(), f"instructions name commands that do not exist: {named - known}"


def test_no_company_or_personal_word_anywhere_in_the_plugin():
    """Plan section 12, check 1. The denylist is private and kept outside the plugin (GP_LEAK_DENYLIST names the file).
    The creator's own name, as plugin.json's author, is the one attribution the owner chose to include."""
    from conftest import leak_words
    words = leak_words()
    if words is None:
        pytest.skip("GP_LEAK_DENYLIST is not set: the leak test needs the private denylist")
    creator = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("author", {}).get("name", "")
    hits = []
    for path in ROOT.rglob("*"):
        if path.is_file() and not {".git", "__pycache__", ".pytest_cache"} & set(path.parts)                 and path.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".tsv", ".txt", ".cmd", ""}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            text = (text.replace(creator, "") if creator else text).lower()
            hits += [f"{path.relative_to(ROOT)}: {w}" for w in words if w in text]
    assert hits == []
