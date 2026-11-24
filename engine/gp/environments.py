"""Environments and preflight (plan 6.1). An environment is where the software runs for a case. Production is never
listed. `up` starts it, waits for health and always stops it; `preflight` is the proof the driver can reach the
software, which red-first depends on. Credential values are never read: only that each name is set."""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

from . import fence
from .project import load_fence

KEYS = {"name", "kind", "runner", "start", "health", "base_url", "env_names", "reset", "doubles", "cwd", "timeout",
        "state_url", "state_cmd"}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
RUNTIMES = ("docker", "podman", "docker-compose", "podman-compose")
NAME_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class EnvError(ValueError):
    pass


def load_all(root: Path) -> tuple[list, list[str]]:
    path = root / "greenfield" / "environments.yaml"
    if not path.is_file():
        return [], []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [], [f"environments.yaml: not valid YAML ({exc})"]
    envs = data.get("environments") if isinstance(data, dict) else None
    if not isinstance(envs, list):
        return [], ["environments.yaml: needs an `environments:` list"]
    problems = []
    for i, env in enumerate(envs):
        problems += [f"environments.yaml [{i}]: {p}" for p in validate(env, root)]
    return envs, problems


def _production(root: Path, tool: str, key: str, text: str) -> bool:
    call = {"tool_name": tool, "cwd": str(root), "tool_input": {key: text}}
    return any(rule == "production" for rule, _ in fence.matches(call))


def _runtime() -> str | None:
    named = os.environ.get("GP_CONTAINER_RUNTIME")
    if named:
        return shutil.which(named)
    return shutil.which("docker") or shutil.which("podman")


def validate(env, root: Path) -> list[str]:
    if not isinstance(env, dict):
        return ["an environment must be a mapping"]
    out = []
    extra = sorted(set(env) - KEYS)
    if extra:
        out.append(f"unknown keys {extra}")
    name = env.get("name")
    if not isinstance(name, str) or not name.strip():
        out.append("name is required")
    where = f"{name}: "
    kind, runner = env.get("kind", "local"), env.get("runner", "container")
    if kind not in ("local", "remote"):
        out.append(f"{where}kind must be local or remote (production is never listed)")
    if runner not in ("container", "process"):
        out.append(f"{where}runner must be container or process")
    fenced = load_fence(root)
    health = env.get("health")
    if health is not None:
        if not isinstance(health, dict) or not isinstance(health.get("cmd"), str) or not health.get("expect"):
            out.append(f"{where}health needs cmd and expect")
        else:
            try:
                re.compile(health["expect"])
            except re.error:
                out.append(f"{where}health.expect is not a valid regex")
    for key in ("start", "reset", "state_cmd"):
        if env.get(key) is not None and not isinstance(env[key], (str, list)):
            out.append(f"{where}{key} must be a command")
    texts = [("Bash", "command", str(env.get(k))) for k in ("start", "reset") if env.get(k)]
    texts += [("Bash", "command", health["cmd"])] if isinstance(health, dict) and health.get("cmd") else []
    if env.get("base_url"):
        texts.append(("WebFetch", "url", str(env["base_url"])))
        host = (urlparse(str(env["base_url"])).hostname or "").lower()
        remote_ok = {str(h).lower() for h in fenced.get("remote_hosts") or []}
        if kind == "local" and host not in LOOPBACK:
            out.append(f"{where}a local environment is reached on loopback, not {host!r}")
        if kind == "remote" and host not in remote_ok:
            out.append(f"{where}remote host {host!r} is not in fence.yaml remote_hosts")
    if any(_production(root, tool, key, text) for tool, key, text in texts):
        out.append(f"{where}names something that looks like production; production is never an environment")
    names = env.get("env_names") or []
    if not isinstance(names, list) or [n for n in names if not (isinstance(n, str) and NAME_RE.match(n))]:
        out.append(f"{where}env_names must be a list of variable names (UPPER_CASE), never values")
    for double in env.get("doubles") or []:
        prov = root / "greenfield" / "doubles" / str(double) / "PROVENANCE.md"
        text = prov.read_text(encoding="utf-8") if prov.is_file() else ""
        missing = [h for h in ("Source:", "Date:", "Does not model:") if h not in text]
        if missing:
            out.append(f"{where}double {double!r} needs doubles/{double}/PROVENANCE.md with {', '.join(missing)}")
    if env.get("start") and runner == "process":
        repos = fenced.get("code_repos") or []
        if not repos or any(not isinstance(r, dict) or r.get("runner", "container") != "process" for r in repos):
            out.append(f"{where}runner: process needs every code_repos entry in fence.yaml to declare "
                       "runner: process (the owner's accepted diff)")
    return out


def _cwd(env: dict, root: Path) -> str:
    return str(env.get("cwd") or root)


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        import signal
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=10)


def _wait_healthy(env: dict, root: Path, proc, log: Path) -> str | None:
    """None when healthy, else why not."""
    health = env.get("health")
    if not health:
        return None
    limit = float(health.get("timeout", 60))
    deadline = time.monotonic() + limit
    seen = ""
    while True:
        if proc is not None and proc.poll() is not None:
            tail = log.read_text(encoding="utf-8", errors="replace")[-300:]
            return f"the start command exited with code {proc.returncode}: {tail.strip()}"
        try:
            done = subprocess.run(health["cmd"], shell=True, cwd=_cwd(env, root), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=max(5, min(30, limit)))
            seen = (done.stdout + done.stderr)[-200:]
            if re.search(health["expect"], done.stdout + done.stderr):
                return None
        except subprocess.TimeoutExpired:
            seen = "health command timed out"
        if time.monotonic() > deadline:
            return f"health did not match {health['expect']!r} within {limit:g}s; last output: {seen.strip()!r}"
        time.sleep(0.5)


def static_checks(env: dict, root: Path) -> list[tuple[str, bool, str]]:
    checks = [(f"environment {env.get('name')}", not (p := validate(env, root)), "; ".join(p) or "valid")]
    missing = [n for n in env.get("env_names") or [] if not os.environ.get(n)]
    checks.append(("credential names", not missing, f"not set: {', '.join(missing)}" if missing else "all set"))
    if env.get("start") and env.get("runner", "container") == "container":
        first = str(env["start"]).split()[0].lower() if str(env["start"]).split() else ""
        runtime = _runtime()
        checks.append(("container runtime", runtime is not None,
                       "found" if runtime else "none found; install docker or podman, or the owner accepts "
                       "runner: process in fence.yaml"))
        checks.append(("start is a container command", first in RUNTIMES,
                       "ok" if first in RUNTIMES else f"runner is container but start begins {first!r}"))
    return checks


@contextlib.contextmanager
def up(root: Path, env: dict):
    """Start the environment, wait for health, yield the preflight record, always stop. Raises EnvError."""
    checks = static_checks(env, root)
    failed = [f"{n}: {d}" for n, ok, d in checks if not ok]
    if failed:
        raise EnvError("preflight failed: " + " | ".join(failed))
    fd, name = tempfile.mkstemp(prefix="gp-env-", suffix=".log")
    os.close(fd)
    proc, log = None, Path(name)
    try:
        if env.get("start"):
            flags = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32"
                     else {"start_new_session": True})
            with log.open("wb") as sink:
                proc = subprocess.Popen(env["start"], shell=True, cwd=_cwd(env, root), stdout=sink,
                                        stderr=subprocess.STDOUT, **flags)
        why = _wait_healthy(env, root, proc, log)
        if why:
            raise EnvError(f"preflight failed: {why}")
        yield {"ok": True, "environment": env.get("name"), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "checks": [n for n, _, _ in checks] + (["health"] if env.get("health") else [])}
    finally:
        if proc is not None:
            _stop(proc)
        log.unlink(missing_ok=True)


def preflight(root: Path, env: dict) -> dict:
    record = {"environment": env.get("name"), "ok": False, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with up(root, env) as ok:
            record = ok
    except EnvError as exc:
        record["reason"] = str(exc)
    (root / "greenfield" / "preflight.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record
