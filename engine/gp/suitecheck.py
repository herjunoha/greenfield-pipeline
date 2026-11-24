"""A suite follows its AC (plan 4.3, 5.1): a changed statement or contract stales it until it is rewritten and
re-reviewed. Moved out of audit.py so each module stays inside its line budget."""
from __future__ import annotations

from pathlib import Path

from . import audit, suite as suitelib


def suite_problems(s, root: Path, data: dict | None) -> list[str]:
    if data is None:
        return [f"{s.ac}: no valid canonical to take baseline_sha and contract_sha from"]
    req = next((r for r in data.get("requirements") or [] if r.get("id") == s.ac), None)
    if req is None:
        return [f"{s.ac}: is not a requirement id in the canonical"]
    out = []
    if s.surface != req.get("surface"):
        out.append(f"{s.ac}: suite surface {s.surface!r} differs from the AC's {req.get('surface')!r}")
    if s.dimension != req.get("dimension"):
        out.append(f"{s.ac}: suite dimension {s.dimension!r} differs from the AC's {req.get('dimension')!r}")
    for label, have, now in (("baseline_sha", s.baseline_sha, audit.ac_sha(req)),
                             ("contract_sha", s.contract_sha, audit.contract_sha(root, data, req.get("surface")))):
        if have != now:
            out.append(f"{s.ac}: {label} is stale (suite {have}, now {now}); rewrite it from gp acs and have it re-reviewed")
    return out


def suites(root: Path, data: dict) -> dict:
    """AC id -> (state, Suite|None): none is absent, invalid cannot be read, stale follows a changed AC."""
    found = {}
    for path in sorted((root / "greenfield" / "suites").glob("*.yaml")):
        try:
            s = suitelib.load(path)
        except suitelib.SuiteError:
            found[path.stem] = ("invalid", None)
            continue
        found[s.ac] = ("stale" if suite_problems(s, root, data) else "current", s)
    return found
