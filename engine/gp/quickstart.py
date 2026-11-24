"""The quickstart case (plan 4.4): the README's commands, run in a fresh checkout of the recorded build, must bring
the software up and pass its health check. The README block under `## Quickstart` lists the commands; every line but
the last sets up, the last starts the software, and `$PORT` (also `%PORT%`, `{port}`) is the environment's port."""
from __future__ import annotations

import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from . import builds, environments


class QuickstartError(ValueError):
    pass


def commands(readme: Path) -> list[str]:
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    section = re.search(r"(?ims)^##\s+quickstart\s*$(.*?)(?=^##\s|\Z)", text)
    block = re.search(r"```[a-z]*\n(.*?)```", section.group(1), re.S) if section else None
    lines = [re.sub(r"^\$\s*", "", line.strip()) for line in (block.group(1).splitlines() if block else [])]
    found = [line for line in lines if line and not line.startswith("#")]
    if not found:
        raise QuickstartError("the product README has no `## Quickstart` section with a code block of commands")
    return found


def _rmtree(path: Path) -> None:
    def retry(func, target, _info):
        Path(target).chmod(stat.S_IWRITE)
        func(target)
    shutil.rmtree(path, onerror=retry)


def run(root: Path, env: dict) -> dict:
    repo = next((r for r in builds.repos(root)), None)
    if repo is None:
        raise QuickstartError("no product repo is declared in fence.yaml code_repos")
    commit = (builds.read(root).get(repo["component"]) or {}).get("commit") or builds.head(repo["path"])
    port = urlparse(str(env.get("base_url") or "")).port
    if port is None:
        raise QuickstartError("the environment needs a base_url with a port so $PORT can be filled in")
    fill = lambda cmd: cmd.replace("$PORT", str(port)).replace("%PORT%", str(port)).replace("{port}", str(port))  # noqa: E731
    work = Path(tempfile.mkdtemp(prefix="gp-qs-"))
    try:
        clone = work / "clone"
        builds.git(work, "clone", "--quiet", str(repo["path"]), str(clone))
        builds.git(clone, "checkout", "--quiet", commit)
        steps = [fill(c) for c in commands(clone / "README.md")]
        for cmd in steps[:-1]:
            done = subprocess.run(cmd, shell=True, cwd=clone, capture_output=True, text=True, timeout=600)
            if done.returncode != 0:
                return {"ok": False, "reason": f"setup command failed (exit {done.returncode}): {cmd}: "
                                               f"{(done.stderr or done.stdout).strip()[-200:]}"}
        try:
            with environments.up(root, {**env, "start": steps[-1], "cwd": str(clone), "name": f"{env.get('name')}-quickstart"}):
                return {"ok": True, "commit": commit, "steps": steps}
        except environments.EnvError as exc:
            return {"ok": False, "reason": str(exc)}
    finally:
        _rmtree(work)
