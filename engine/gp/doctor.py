"""gp doctor: what is installed and what each missing item disables (plan section 9.3)."""
from __future__ import annotations

import importlib.util
import shutil
import sys

from . import MIN_PYTHON


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def checks() -> list[tuple[str, bool, bool, str]]:
    """(name, required, present, what a missing item disables)"""
    py_ok = sys.version_info[:2] >= MIN_PYTHON
    return [
        (f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+", True, py_ok, "everything: the engine does not run"),
        ("PyYAML", True, _has_module("yaml"), "items, the fence, the canonical and packs"),
        ("git", True, shutil.which("git") is not None, "product repo, build ids and trunk checks"),
        ("container runtime (docker or podman)", False,
         bool(shutil.which("docker") or shutil.which("podman")),
         "runner: container; preflight asks the owner to accept runner: process"),
        ("browser automation library (playwright)", False, _has_module("playwright"), "the browser driver"),
        ("Node", False, shutil.which("node") is not None, "projects whose stack uses Node"),
    ]


def report() -> tuple[str, bool]:
    lines, ok = [], True
    for name, required, present, disables in checks():
        mark = "ok     " if present else ("MISSING" if required else "absent ")
        tail = "" if present else f"  -> disables: {disables}"
        lines.append(f"{mark} {name}{'' if required else ' (optional)'}{tail}")
        ok = ok and (present or not required)
    return "\n".join(lines), ok
