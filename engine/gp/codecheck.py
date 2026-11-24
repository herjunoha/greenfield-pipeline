"""Code rules of `gp check` (plan 4.4, 4.6): no dirty build, a lockfile, no secret in a committed file, every
dependency a row in deps.tsv from a declared registry under the pack's license policy, and a trunk merge only on
a commit that has a passing verdict. Findings name the file and rule, never the secret's value."""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import builds, items, packs
from .project import load_fence

LOCKS = {"package.json": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "npm-shrinkwrap.json"),
         "pyproject.toml": ("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock", "requirements.lock"),
         "Cargo.toml": ("Cargo.lock",), "Gemfile": ("Gemfile.lock",), "composer.json": ("composer.lock",)}
UNPARSED = ("go.mod", "Cargo.toml", "Gemfile", "composer.json", "pom.xml", "build.gradle")
SECRETS = (("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
           ("an AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
           ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
           ("a Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
           ("an API key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
           ("a hard-coded credential", re.compile(
               r"""(?i)\b(?:password|passwd|secret|api_?key|token)\w*\s*[:=]\s*['"]([^'"\s]{8,})['"]""")))
PLACEHOLDER = re.compile(r"(?i)example|changeme|placeholder|dummy|<.*>|\$\{|x{4,}|\*{3,}|your[_-]|test")


def tracked(repo: Path) -> list[Path]:
    return [repo / p for p in builds.git(repo, "ls-files").splitlines() if p]


def dirty_build(root: Path) -> list[str]:
    out, recorded = [], builds.read(root)
    for repo in builds.repos(root):
        name = repo["component"]
        if not (repo["path"] / ".git").exists():
            out.append(f"{name}: {repo['path'].name} is not a git repo (gp product init)")
            continue
        if builds.dirty(repo["path"]):
            out.append(f"{name}: uncommitted changes; a dirty tree is never a build")
        entry = recorded.get(name)
        if entry and entry.get("dirty"):
            out.append(f"{name}: builds.yaml records a dirty build")
        elif entry and entry.get("commit") != builds.head(repo["path"]):
            out.append(f"{name}: builds.yaml records {str(entry.get('commit'))[:8]} but HEAD has moved; "
                       "a verdict covers one build, so record a new one (gp build)")
    return out


def lockfile(repo: Path) -> list[str]:
    out = []
    for manifest, locks in LOCKS.items():
        if (repo / manifest).is_file() and not any((repo / lock).is_file() for lock in locks) \
                and not (manifest == "pyproject.toml" and (repo / "requirements.txt").is_file()):
            out.append(f"{repo.name}: {manifest} has no lockfile ({', '.join(locks[:2])}...)")
    req = repo / "requirements.txt"
    if req.is_file():
        for n, line in enumerate(req.read_text(encoding="utf-8").splitlines(), 1):
            text = line.split("#")[0].strip()
            if text and not text.startswith("-") and "==" not in text:
                out.append(f"{repo.name}: requirements.txt line {n} is not pinned with ==")
    return out


def secrets(repo: Path) -> list[str]:
    out = []
    for path in tracked(repo):
        rel = path.relative_to(repo).as_posix()
        if re.match(r"^\.env(\..+)?$", path.name) and path.name != ".env.example":
            out.append(f"{repo.name}/{rel}: an env file is committed")
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for label, pattern in SECRETS:
                found = pattern.search(line)
                if found and not PLACEHOLDER.search(found.group(1) if found.groups() else found.group(0)):
                    out.append(f"{repo.name}/{rel}:{n}: looks like {label}")
                    break
    return out


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def declared(repo: Path) -> tuple[set[str], list[str]]:
    names, notes = set(), []
    pkg = repo / "package.json"
    if pkg.is_file():
        data = json.loads(pkg.read_text(encoding="utf-8"))
        names |= {_norm(n) for k in ("dependencies", "devDependencies") for n in (data.get(k) or {})}
    req = repo / "requirements.txt"
    if req.is_file():
        for line in req.read_text(encoding="utf-8").splitlines():
            found = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line.split("#")[0])
            if found and not line.strip().startswith("-"):
                names.add(_norm(found.group(1)))
    toml = repo / "pyproject.toml"
    if toml.is_file():
        try:
            import tomllib
            deps = (tomllib.loads(toml.read_text(encoding="utf-8")).get("project") or {}).get("dependencies") or []
            names |= {_norm(re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", d).group(0)) for d in deps}
        except ImportError:
            notes.append(f"{repo.name}: pyproject.toml dependencies are not read on this Python; use requirements.txt")
    notes += [f"{repo.name}: {m} dependencies are not parsed; record them in deps.tsv by hand" for m in UNPARSED
              if (repo / m).is_file()]
    return names, notes


def dependencies(root: Path, repo: Path) -> tuple[list[str], list[str]]:
    names, notes = declared(repo)
    rows, out = {}, []
    lines = (root / "greenfield" / "deps.tsv").read_text(encoding="utf-8").splitlines()[1:]
    for line in lines:
        cols = (line.split("\t") + [""] * 5)[:5]
        if cols[0].strip():
            rows[_norm(cols[0])] = cols
    fence = load_fence(root)
    hosts = {str(r.get("host", "")).lower() for r in fence.get("registries") or [] if isinstance(r, dict)}
    pack_dir = Path(fence["pack_path"]) if fence.get("pack_path") else packs.bundled()[packs.GENERIC]
    allowed = packs.show(pack_dir, "policy.licenses") if (pack_dir / "pack.yaml").is_file() else []
    all_items = items.load_all(root / "greenfield" / "items")
    for name in sorted(names - set(rows)):
        out.append(f"{repo.name}: dependency {name} has no row in deps.tsv")
    for key in sorted(names & set(rows)):
        _, _version, lic, registry, item = (c.strip() for c in rows[key])
        if not (lic and registry and item):
            out.append(f"deps.tsv: {key} needs license, registry and item")
        elif registry.lower() not in hosts:
            out.append(f"deps.tsv: {key} came from {registry}, which fence.yaml does not declare as a registry")
        elif allowed and lic not in allowed:
            accepted = all_items.get(item)
            if not (accepted and accepted.state == "closed" and accepted.reason == "done"):
                out.append(f"deps.tsv: {key} has license {lic}, outside the pack's policy; "
                           f"item {item} must be closed by the owner first")
    return out, notes


def run(root: Path) -> tuple[list[str], list[str]]:
    problems, notes = dirty_build(root), []
    for repo in builds.repos(root):
        if (repo["path"] / ".git").exists():
            problems += lockfile(repo["path"]) + secrets(repo["path"])
            more, note = dependencies(root, repo["path"])
            problems, notes = problems + more, notes + note
    return problems, notes


def merge(root: Path, ref: str, component: str | None = None) -> list[str]:
    """A merge to trunk needs a passing verdict on the exact commit being merged."""
    found = [r for r in builds.repos(root) if component in (None, r["component"])]
    if len(found) != 1:
        return ["name one declared component"]
    repo = found[0]
    commit = builds.head(repo["path"], ref)
    if builds.has_verdict(root, repo["component"], commit):
        return []
    return [f"{repo['component']}: {ref} is {commit[:8]}, and no full run on exactly that commit passed every AC; "
            f"it does not merge to {repo['trunk']}"]
