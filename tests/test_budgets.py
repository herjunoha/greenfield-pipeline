"""Size budgets as tests (plan section 9.3): growth is a decision, so a cap breach fails the build.
Raise a cap here, in the open, rather than letting a file creep. Initial values are set at step 1."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PY = 220
CAPS = {  # file name -> line cap, where it differs from the default
    "fence_rules.py": 340,   # the always-pause list: data-like, one matcher per entry
    "items.py": 175,   # + the assumption rule and the ladder part (steps 3, 7)
    "cli.py": 165,   # the command registry grows by one register() line per module
    "fence.py": 135,
    "suite.py": 210,
    "runner.py": 175,   # + the reset helper (step 4)
    "scorer.py": 130,
}
SKILL_CAP = 120
AGENT_CAP = 80


def lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize("path", sorted((ROOT / "engine" / "gp").glob("*.py")), ids=lambda p: p.name)
def test_engine_module_within_cap(path):
    cap = CAPS.get(path.name, DEFAULT_PY)
    assert lines(path) <= cap, f"{path.name} has {lines(path)} lines, cap {cap}"


@pytest.mark.parametrize("path", sorted((ROOT / "hooks").glob("*.py")), ids=lambda p: p.name)
def test_hook_within_cap(path):
    assert lines(path) <= 80


@pytest.mark.parametrize("path", sorted((ROOT / "drivers").glob("*.py")), ids=lambda p: p.name)
def test_driver_within_cap(path):
    assert lines(path) <= 90


@pytest.mark.parametrize("path", sorted((ROOT / "skills").glob("*/SKILL.md")), ids=lambda p: p.parent.name)
def test_skill_within_cap(path):
    assert lines(path) <= SKILL_CAP


@pytest.mark.parametrize("path", sorted((ROOT / "agents").glob("*.md")), ids=lambda p: p.name)
def test_agent_within_cap(path):
    assert lines(path) <= AGENT_CAP


def test_fence_and_pack_logic_are_separate_modules():
    names = {p.name for p in (ROOT / "engine" / "gp").glob("*.py")}
    assert {"fence.py", "fence_rules.py", "packs.py"} <= names
