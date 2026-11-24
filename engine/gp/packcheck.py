"""Pack integrity and grammar (plan 8). A pack supplies values and small adapters; it can only ADD to safety. The fence
takes the union of core's list and the pack's pause.yaml, and an entry that loosens a core one is ignored and fails
`gp pack check`. The pack's hash lives in fence.yaml; a mismatch asks until the owner accepts it."""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import yaml

from . import packs

REQUIRED = ("name", "company", "language", "roles", "own_terms", "redact", "brand", "stack", "policy", "documents")
RULE_KEYS = {"id", "match", "tool", "unless_listed", "action", "reason"}
CONNECTOR_KEYS = {"notify", "feeds", "numbering"}
CAPPED = ("lessons.md", "standards.md")        # retro keeps these small (plan 10)
CAP_LINES = 30


def _yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None


def pause_rules(pack_dir: Path) -> tuple[list[dict], list[str]]:
    """(the rules the fence will use, problems). A rule that loosens, or cannot be read, is dropped."""
    data, problems, good = _yaml(pack_dir / "pause.yaml"), [], []
    if data is None:
        return [], []
    rules = data.get("rules") if isinstance(data, dict) else data
    if not isinstance(rules, list):
        return [], ["pause.yaml: needs a list of rules"]
    for i, rule in enumerate(rules):
        where = f"pause.yaml rule {i}"
        if not isinstance(rule, dict) or set(rule) - RULE_KEYS:
            problems.append(f"{where}: keys are {', '.join(sorted(RULE_KEYS))}")
            continue
        if rule.get("action", "ask") not in ("ask", "deny"):
            problems.append(f"{where}: action {rule.get('action')!r} loosens the core list; a pack can only ask or deny")
            continue
        if not (rule.get("match") or rule.get("tool")):
            problems.append(f"{where}: needs match (a command regex) or tool (a tool glob)")
            continue
        try:
            re.compile(rule.get("match") or "")
        except re.error:
            problems.append(f"{where}: match is not a valid regex")
            continue
        good.append(rule)
    return good, problems


def check(pack_dir: Path) -> list[str]:
    problems = []
    try:
        data = packs.load(pack_dir)
    except Exception as exc:
        return [str(exc)]
    problems += [f"pack.yaml: missing {key}" for key in REQUIRED if key not in data]
    for pattern in data.get("redact") or []:
        try:
            re.compile(pattern)
        except re.error:
            problems.append(f"pack.yaml: redact pattern {pattern!r} is not a valid regex")
    if not isinstance((data.get("policy") or {}).get("licenses"), list):
        problems.append("pack.yaml: policy.licenses must be a list")
    problems += pause_rules(pack_dir)[1]
    connectors = _yaml(pack_dir / "connectors.yaml") or {}
    if not isinstance(connectors, dict) or set(connectors) - CONNECTOR_KEYS:
        problems.append(f"connectors.yaml: keys are {', '.join(sorted(CONNECTOR_KEYS))}")
    offerings = pack_dir / "offerings.md"
    if offerings.is_file():
        for pattern in data.get("redact") or []:
            try:
                if re.search(pattern, offerings.read_text(encoding="utf-8")):
                    problems.append(f"offerings.md matches the redact pattern {pattern!r}")
            except re.error:
                pass
    for name in CAPPED:
        path = pack_dir / name
        if path.is_file() and len(path.read_text(encoding="utf-8").splitlines()) > CAP_LINES:
            problems.append(f"{name} is longer than {CAP_LINES} lines; retro keeps it small")
    return problems


def pack_dir_of(fence: dict) -> Path | None:
    return Path(str(fence["pack_path"])) if fence.get("pack_path") else None


def tampered(fence: dict) -> str | None:
    """The pack changed since the owner accepted it, or is gone."""
    path = pack_dir_of(fence)
    if path is None or not fence.get("pack_sha256"):
        return None
    if not path.is_dir():
        return "the pack folder named in fence.yaml is missing"
    if packs.sha256(path) != fence["pack_sha256"]:
        return "a pack file changed since the owner accepted it (gp pack accept records the new hash)"
    return None


def pack_hits(fence: dict, tool: str, command: str) -> list[tuple[str, str]]:
    """The pack's added pause rules that a call touches, as (id, reason)."""
    path = pack_dir_of(fence)
    if path is None or not path.is_dir():
        return []
    hits = []
    for n, rule in enumerate(pause_rules(path)[0]):
        by_tool = rule.get("tool") and fnmatch.fnmatch(tool.lower(), str(rule["tool"]).lower())
        by_cmd = rule.get("match") and command and re.search(rule["match"], command)
        listed = rule.get("unless_listed") and any(
            isinstance(v, dict) and re.search(str(v.get("match", "")), command) for v in fence.get(rule["unless_listed"]) or [])
        if (by_tool or by_cmd) and not listed:
            hits.append((f"pack-{rule.get('id') or n}", str(rule.get("reason") or "the pack adds this pause")))
    return hits
