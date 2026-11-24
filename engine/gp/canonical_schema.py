"""The canonical requirement's schema (plan 4.1, 4.2). Plate writes the file; this refuses what is malformed and
never invents a value. A missing `source` on a requirement is not a schema error: the audit reports it as an
orphan. An example that is not confirmed is legal (a proposal); suites just cannot cite it."""
from __future__ import annotations

import datetime
import re
from pathlib import Path

from .suite import DIMENSIONS

TIER1 = ("http", "cli", "browser", "manual")
TIER2 = ("mobile", "desktop", "embedded", "other")        # need a driver from a pack; manual until then
DATA_CLASSES = ("personal", "financial", "health", "children", "biometric", "credentials", "none")
BASELINE_NEEDS = ("authentication", "data_retention", "rough_load", "accessibility", "supported_platforms",
                  "backup")
EXAMPLE_SOURCES = ("sponsor-confirmed", "sponsor-document", "agent")
AC_RE, EX_RE, ROLE_RE = re.compile(r"^AC-\d+$"), re.compile(r"^EX-\d+$"), re.compile(r"^[a-z][a-z0-9_-]*$")
_PROJECT = {"name", "objectives", "out_of_scope", "assumptions", "timeline", "surfaces", "glossary",
            "data_classes", "regulated", "status"}
_REQ = {"id", "statement", "acceptance", "dimension", "surface", "source", "baseline"}
_EX = {"id", "rule", "given", "expect", "source", "confirmed_by", "confirmed_on", "serves"}


def _unknown(obj: dict, allowed: set, where: str, out: list) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        out.append(f"{where}: unknown keys {extra}")


def _text(obj: dict, key: str, where: str, out: list) -> str:
    value = obj.get(key)
    if isinstance(value, str) and value.strip():
        return value
    out.append(f"{where}: {key} is required")
    return ""


def _strings(obj: dict, key: str, where: str, out: list) -> list:
    value = obj.get(key) or []
    if isinstance(value, list) and all(isinstance(v, str) and v.strip() for v in value):
        return value
    out.append(f"{where}: {key} must be a list of non-empty strings")
    return []


def _rows(obj: dict, key: str, where: str, out: list) -> list:
    value = obj.get(key) or []
    if not isinstance(value, list):
        out.append(f"{where}: {key} must be a list")
        return []
    return value


def _surfaces(proj: dict, root: Path | None, out: list) -> set:
    names = set()
    rows = _rows(proj, "surfaces", "project", out)
    if not rows:
        out.append("project: at least one surface is required")
    for i, row in enumerate(rows):
        where = f"project.surfaces[{i}]"
        if not isinstance(row, dict):
            out.append(f"{where}: must be a mapping")
            continue
        _unknown(row, {"name", "kind", "interface"}, where, out)
        name = _text(row, "name", where, out)
        if name in names:
            out.append(f"{where}: duplicate surface {name!r}")
        names.add(name)
        if row.get("kind") not in TIER1 + TIER2:
            out.append(f"{where}: kind {row.get('kind')!r} is not one of {', '.join(TIER1 + TIER2)}")
        iface = row.get("interface")
        if iface is None:
            continue
        if not isinstance(iface, str) or ".." in iface or iface.startswith(("/", "\\")) or ":" in iface:
            out.append(f"{where}: interface must be a file name under design/contracts/ or null")
        elif root is not None and not (root / "greenfield" / "design" / "contracts" / iface).is_file():
            out.append(f"{where}: interface {iface} is not under greenfield/design/contracts/ (null until shape)")
    return names


def _glossary(proj: dict, out: list) -> None:
    seen = set()
    for i, row in enumerate(_rows(proj, "glossary", "project", out)):
        where = f"project.glossary[{i}]"
        if not isinstance(row, dict):
            out.append(f"{where}: must be a mapping")
            continue
        _unknown(row, {"term", "meaning", "source", "confirmed"}, where, out)
        term = _text(row, "term", where, out).lower()
        _text(row, "meaning", where, out)
        _text(row, "source", where, out)
        if not isinstance(row.get("confirmed"), bool):
            out.append(f"{where}: confirmed must be true or false")
        if term in seen:
            out.append(f"{where}: duplicate term {term!r}")
        seen.add(term)


def _project(proj, root, out) -> set:
    if not isinstance(proj, dict):
        out.append("project is required and must be a mapping")
        return set()
    _unknown(proj, _PROJECT, "project", out)
    if proj.get("status") not in ("draft", "approved"):
        out.append("project: status must be draft or approved")
    for key in ("objectives", "out_of_scope", "assumptions", "regulated"):
        _strings(proj, key, "project", out)
    if not isinstance(proj.get("timeline") or "", (str, dict)):
        out.append("project: timeline must be text or a mapping")
    classes = _strings(proj, "data_classes", "project", out)
    if [c for c in classes if c not in DATA_CLASSES]:
        out.append(f"project: data_classes must come from {', '.join(DATA_CLASSES)}")
    if "none" in classes and len(classes) > 1:
        out.append("project: data_classes 'none' cannot sit beside another class")
    if not classes:
        out.append("project: data_classes is required (use [none] when the software handles no data)")
    _glossary(proj, out)
    return _surfaces(proj, root, out)


def _requirements(data: dict, surfaces: set, out: list) -> set:
    ids = set()
    rows = _rows(data, "requirements", "canonical", out)
    if not rows:
        out.append("canonical: requirements must hold at least one acceptance criterion")
    for i, row in enumerate(rows):
        where = f"requirements[{i}]"
        if not isinstance(row, dict):
            out.append(f"{where}: must be a mapping")
            continue
        _unknown(row, _REQ, where, out)
        rid = row.get("id")
        if not isinstance(rid, str) or not AC_RE.match(rid):
            out.append(f"{where}: id must look like AC-1")
        elif rid in ids:
            out.append(f"{where}: duplicate id {rid}")
        ids.add(rid)
        where = rid if isinstance(rid, str) else where
        _text(row, "statement", where, out)
        if "\n" in _text(row, "acceptance", where, out).strip():
            out.append(f"{where}: acceptance is one observable line")
        if row.get("dimension") not in DIMENSIONS:
            out.append(f"{where}: dimension must be one of {', '.join(DIMENSIONS)}")
        if row.get("surface") not in surfaces:
            out.append(f"{where}: surface {row.get('surface')!r} is not declared under project.surfaces")
        if row.get("baseline") is not None and row["baseline"] not in BASELINE_NEEDS:
            out.append(f"{where}: baseline must be one of {', '.join(BASELINE_NEEDS)}")
        if row.get("source") is not None and not isinstance(row["source"], str):
            out.append(f"{where}: source must be text")
    return ids


def _examples(data: dict, acs: set, out: list) -> None:
    seen = set()
    for i, row in enumerate(_rows(data, "examples", "canonical", out)):
        where = f"examples[{i}]"
        if not isinstance(row, dict):
            out.append(f"{where}: must be a mapping")
            continue
        _unknown(row, _EX, where, out)
        eid = row.get("id")
        if not isinstance(eid, str) or not EX_RE.match(eid):
            out.append(f"{where}: id must look like EX-1")
        elif eid in seen:
            out.append(f"{where}: duplicate id {eid}")
        seen.add(eid)
        where = eid if isinstance(eid, str) else where
        _text(row, "rule", where, out)
        for key in ("given", "expect"):
            if not isinstance(row.get(key), dict):
                out.append(f"{where}: {key} must be a mapping")
        source = str(row.get("source") or "")
        if source not in EXAMPLE_SOURCES and not re.match(r"^public:\S+$", source):
            out.append(f"{where}: source must be sponsor-confirmed, sponsor-document, public:<url> or agent")
        by = row.get("confirmed_by")
        if by is not None and not (isinstance(by, str) and ROLE_RE.match(by)):
            out.append(f"{where}: confirmed_by is a role (like sponsor), never a name")
        on = row.get("confirmed_on")
        if on is not None and not isinstance(on, datetime.date) and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(on)):
            out.append(f"{where}: confirmed_on must be a date (YYYY-MM-DD)")
        for ac in row.get("serves") or []:
            if ac not in acs:
                out.append(f"{where}: serves {ac}, which is not a requirement id")


def check(data, root: Path | None = None) -> list[str]:
    """Every schema problem, together. `root` lets surface interfaces be checked against the contracts folder."""
    if not isinstance(data, dict):
        return ["the canonical must be a mapping with project, requirements and examples"]
    out: list[str] = []
    _unknown(data, {"project", "requirements", "examples"}, "canonical", out)
    surfaces = _project(data.get("project"), root, out)
    acs = _requirements(data, surfaces, out)
    _examples(data, acs, out)
    return out
