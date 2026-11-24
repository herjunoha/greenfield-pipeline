"""Product repos and build identity (plan 4.4, 6.2). A build is a clean commit of a declared repo; a verdict covers
one build. This module reads git and builds.yaml; it never pushes, merges or edits fence.yaml."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .project import load_fence


class BuildError(ValueError):
    pass


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise BuildError(f"git {' '.join(args)} failed in {repo.name}: {done.stderr.strip() or done.stdout.strip()}")
    return done.stdout.strip()


def repos(root: Path) -> list[dict]:
    """The `code_repos` entries of fence.yaml: path, component (default: the folder name), trunk (default main)."""
    out = []
    for entry in load_fence(root).get("code_repos") or []:
        if isinstance(entry, dict) and entry.get("path"):
            path = (root / str(entry["path"])).resolve()
            out.append({"path": path, "component": str(entry.get("component") or path.name),
                        "trunk": str(entry.get("trunk") or "main"), "runner": entry.get("runner", "container")})
    return out


def read(root: Path) -> dict:
    path = root / "greenfield" / "builds.yaml"
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.is_file() else {}


def dirty(repo: Path) -> bool:
    return bool(git(repo, "status", "--porcelain"))


def head(repo: Path, ref: str = "HEAD") -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")


def record(root: Path, component: str | None = None, image: str | None = None) -> dict:
    """Write the repo's HEAD into builds.yaml. A dirty tree is never a build."""
    found = [r for r in repos(root) if component in (None, r["component"])]
    if len(found) != 1:
        raise BuildError("name one declared component: " + (", ".join(r["component"] for r in repos(root))
                                                            or "no code_repos in fence.yaml"))
    repo = found[0]
    if not (repo["path"] / ".git").exists():
        raise BuildError(f"{repo['path'].name} is not a git repo (gp product init)")
    if dirty(repo["path"]):
        raise BuildError(f"{repo['component']} has uncommitted changes; a dirty tree is never a build")
    entry = {"commit": head(repo["path"]), "image": image, "dirty": False,
             "recorded": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    builds = read(root)
    builds[repo["component"]] = entry
    (root / "greenfield" / "builds.yaml").write_text(yaml.safe_dump(builds, sort_keys=True), encoding="utf-8")
    with (root / "greenfield" / "builds.tsv").open("a", encoding="utf-8", newline="\n") as f:   # the budget counts these
        f.write("\t".join([entry["recorded"], repo["component"], entry["commit"]]) + "\n")
    return entry


def has_verdict(root: Path, component: str, commit: str) -> bool:
    """A full run on exactly this commit whose every AC passed. Anything less is not a verdict (plan 7.4)."""
    for path in sorted((root / "greenfield" / "runs").glob("*/verdicts.json")):
        try:
            v = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        built = (v.get("build_ids") or {}).get(component) or {}
        if (built.get("commit") == commit and v.get("full") and v.get("acs")
                and all(a.get("verdict") == "pass" for a in v["acs"].values())):
            return True
    return False


def init_product(root: Path, path: str = "product", trunk: str = "main") -> list[str]:
    """Create an empty product repo with one commit (.gitignore). Returns the lines the OWNER adds to
    fence.yaml: the engine never writes the fence."""
    repo = root / path
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        git(repo, "init", "-b", trunk)
    ignore = repo / ".gitignore"
    if not ignore.exists():
        ignore.write_text(".env\n.env.*\n!.env.example\n__pycache__/\nnode_modules/\n", encoding="utf-8", newline="\n")
    try:
        head(repo)
    except BuildError:
        git(repo, "add", ".gitignore")
        git(repo, "-c", "user.name=greenfield-pipeline", "-c", "user.email=greenfield-pipeline@localhost", "commit", "-m",
            "chore: start the product repo")
    return [f"code_repos:", f"  - {{path: {path}, trunk: {trunk}, runner: container}}"]
