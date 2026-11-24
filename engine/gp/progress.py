"""AC state, derived from files (plan 3, 4.5, 7.4); nothing is stored twice. `done` is earned: a reviewed and
accepted suite, a full run of exactly that suite on the current build with every check green, a review of that run
by someone other than its builder, red seen before the first green, an approved baseline, no open assumption."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import acceptance, builds, reviews


class Facts:
    """What the project's files say, read once."""

    def __init__(self, root: Path, data: dict):
        self.root = root
        self.runs = load_runs(root)
        self.builds = builds.read(root)
        self.reviews = reviews.entries(root)
        self.approved = data["project"].get("status") == "approved" and acceptance.accepted(root, "canonical")


def load_runs(root: Path) -> list[dict]:
    out = []
    for folder in sorted((root / "greenfield" / "runs").glob("*")):
        path = folder / "verdicts.json"
        if not path.is_file():
            continue
        try:
            verdicts = json.loads(path.read_text(encoding="utf-8"))
            meta = json.loads((folder / "run.json").read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        out.append({"name": folder.name, "full": bool(verdicts.get("full")), "acs": verdicts.get("acs") or {},
                    "build_ids": verdicts.get("build_ids") or {}, "suites": meta.get("suites") or {},
                    "preflight_ok": bool((meta.get("preflight") or {}).get("ok")),
                    "sha": hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()})
    return out


def verdict(run: dict, ac: str) -> str:
    return run["acs"][ac]["verdict"]


def red_first(history: list[dict], ac: str) -> bool:
    """Red means an assertion failed on reachable software: a fail verdict from a run whose preflight was ok. A
    connection error or a driver error is not red. The first green must have a red before it."""
    for run in history:
        if verdict(run, ac) == "pass":
            return False
        if verdict(run, ac) == "fail" and run["preflight_ok"]:
            return True
    return True                                   # no green yet: nothing to be first about


def state(facts: Facts, ac: str, suite, suite_state: str, assumed: bool) -> tuple[str, list[str]]:
    """(state, what still stops `done`). States: assumed, no-suite, stale, in-review, ready, red, green, done."""
    root = facts.root
    if assumed:
        return "assumed", []
    if suite is None:
        return "no-suite", []
    if suite_state != "current":
        return "stale", []
    reviewed = reviews.approved(root, "suite", ac, reviews.subject_sha(root, "suite", ac), facts.reviews)
    if not (reviewed and acceptance.accepted(root, f"suite:{ac}")):
        return "in-review", [("rex has not approved this suite version" if not reviewed else
                              "the owner has not accepted this suite version")]
    history = [r for r in facts.runs if ac in r["acs"]]
    mine = [r for r in history if r["suites"].get(ac) == suite.sha]
    if not mine:
        return "ready", []
    if verdict(mine[-1], ac) == "fail":
        return "red", []
    missing = []
    fulls = [r for r in mine if r["full"]]
    last = fulls[-1] if fulls else None
    if last is None:
        missing.append("no full run of this suite yet")
    else:
        if verdict(last, ac) != "pass":
            missing.append(f"the latest full run is {verdict(last, ac)}, not pass")
        for comp, now in facts.builds.items():
            if (last["build_ids"].get(comp) or {}).get("commit") != (now or {}).get("commit"):
                missing.append(f"the run is not on the current build of {comp}")
        if not reviews.approved(root, "run", last["name"], last["sha"], facts.reviews):
            missing.append(f"rex has not reviewed run {last['name']}")
    if not red_first(history, ac):
        missing.append("never seen red before its first green (red first)")
    if not facts.approved:
        missing.append("the baseline is not approved")
    return ("done", []) if not missing else ("green", missing)
