"""A lenient reader of what suites cite from the canonical: examples and requirement ids. The schema is
canonical_schema.py and the audit is audit.py; this module never judges the file as a whole."""
from __future__ import annotations

from pathlib import Path

import yaml

SOURCES = ("sponsor-confirmed", "sponsor-document")


def confirmed(example: dict) -> bool:
    """An example sets an expected business value only when a human confirmed it. `agent` is a proposal."""
    source = str(example.get("source") or "")
    valid = source in SOURCES or source.startswith("public:")
    return valid and bool(example.get("confirmed_by")) and bool(example.get("confirmed_on"))


def load(project: Path) -> dict:
    examples, requirements = {}, set()
    for path in sorted((project / "greenfield" / "requirements").glob("*.canonical.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for ex in data.get("examples") or []:
            if isinstance(ex, dict) and ex.get("id"):
                examples[ex["id"]] = ex
        for req in data.get("requirements") or []:
            if isinstance(req, dict) and req.get("id"):
                requirements.add(req["id"])
    return {"examples": examples, "requirements": requirements}
