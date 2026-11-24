"""The fence: decides allow or ask for one tool call. It acts only inside a project that has
greenfield/fence.yaml (plan section 7.1). The always-pause matchers live in fence_rules.py."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import packcheck
from .project import find_project, load_fence

SHELL_TOOLS = ("Bash", "PowerShell")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
_SPLIT = re.compile(r"&&|\|\||[;|\n]")
_PREFIX = re.compile(r"^(?:(?:sudo|time|nohup|command|exec|env)\s+|[A-Za-z_]\w*=\S*\s+)+")


@dataclass(frozen=True)
class Decision:
    action: str            # allow | ask
    rule: str = ""
    reason: str = ""


ALLOW = Decision("allow")


@dataclass
class Ctx:
    tool: str
    inp: dict
    cwd: Path
    project: Path
    fence: dict
    plugin_root: Path

    @property
    def cmd(self) -> str:
        return str(self.inp.get("command") or "") if self.tool in SHELL_TOOLS else ""

    @property
    def segments(self) -> list[str]:
        return [_PREFIX.sub("", s.strip()) for s in _SPLIT.split(self.cmd) if s.strip()]

    @property
    def path(self) -> Path | None:
        raw = self.inp.get("file_path") or self.inp.get("notebook_path")
        if self.tool not in WRITE_TOOLS or not raw:
            return None
        p = Path(str(raw))
        return (p if p.is_absolute() else self.cwd / p).resolve()

    @property
    def tokens(self) -> set[str]:
        leaf = re.sub(r"([a-z])([A-Z])", r"\1_\2", self.tool.split("__")[-1])
        return {t for t in re.split(r"[_\-\s]+", leaf.lower()) if t}

    def values(self) -> list[str]:
        out: list[str] = []

        def walk(node):
            if isinstance(node, dict):
                for v in node.values():
                    walk(v)
            elif isinstance(node, (list, tuple)):
                for v in node:
                    walk(v)
            elif isinstance(node, str):
                out.append(node)
        walk(self.inp)
        return out


def _locate(call: dict) -> tuple[Path, Path] | None:
    cwd = Path(call.get("cwd") or ".").resolve()
    project = find_project(cwd)
    if project is None:
        raw = (call.get("tool_input") or {}).get("file_path")
        if raw:
            target = Path(str(raw))
            project = find_project((target if target.is_absolute() else cwd / target).parent)
    return (project, cwd) if project else None


def matches(call: dict) -> list[tuple[str, str]]:
    """Every always-pause entry the call touches, as (rule id, reason). Empty outside a project."""
    from .fence_rules import RULES
    located = _locate(call)
    if located is None:
        return []
    project, cwd = located
    try:
        fence = load_fence(project)
    except Exception as exc:  # a fence that cannot be read fails closed
        return [("fence-unreadable", f"fence.yaml cannot be read ({exc}); the owner decides")]
    ctx = Ctx(str(call.get("tool_name") or ""), call.get("tool_input") or {}, cwd, project, fence,
              Path(__file__).resolve().parents[2])
    found = []
    for rule_id, _label, fn in RULES:
        reason = fn(ctx)
        if reason:
            found.append((rule_id, reason))
    changed = packcheck.tampered(fence)
    if changed and ctx.tool not in ("Read", "Glob", "Grep"):
        found.append(("fence-edit", changed))
    return found + packcheck.pack_hits(fence, ctx.tool, ctx.cmd)


def evaluate(call: dict) -> Decision:
    found = matches(call)
    if not found:
        return ALLOW
    rule_id, reason = found[0]
    return Decision("ask", rule_id, reason)
