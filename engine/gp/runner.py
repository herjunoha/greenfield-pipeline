"""Run suites through the drivers and score a run (plan sections 5.2 and 5.3). eve's job in code form: run it and
record what came back. This module never judges. Before a driver runs, the fence looks at what a case would do:
a case that trips an always-pause entry is not run, it is recorded as an error for the owner to run by hand."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from . import environments, fence, scorer, suite as suites_mod
from .suite import Case, Suite, SuiteError

DRIVERS = Path(__file__).resolve().parents[2] / "drivers"
DEFAULT_TIMEOUT = 30


class RunError(ValueError):
    pass


def environment(project: Path, name: str | None = None) -> dict:
    path = project / "greenfield" / "environments.yaml"
    if not path.is_file():
        return {"name": "default", "cwd": str(project)}
    envs = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("environments") or []
    for env in envs:
        if isinstance(env, dict) and (name is None or env.get("name") == name):
            problems = environments.validate(env, project)
            if problems:
                raise RunError("environment refused: " + "; ".join(problems))
            return env
    raise RunError(f"environment {name or '(first)'!r} not found in environments.yaml")


def driver_command(name: str) -> list[str]:
    script = DRIVERS / f"drv_{name}.py"
    if not script.is_file():
        raise RunError(f"no driver {name!r}; core ships http, cli and manual")
    return [sys.executable, str(script)]


def fenced(project: Path, case: Case, env: dict) -> str | None:
    for step in case.steps:
        do = step["do"]
        if "cli" in do:
            spec = do["cli"]
            call = {"tool_name": "Bash", "cwd": str(project),
                    "tool_input": {"command": " ".join([str(spec.get("cmd", "")), *map(str, spec.get("args") or [])])}}
        elif "http" in do:
            call = {"tool_name": "WebFetch", "cwd": str(project),
                    "tool_input": {"url": str(env.get("base_url", "")) + str(do["http"].get("path", ""))}}
        else:
            continue
        hit = fence.matches(call)
        if hit:
            return f"fence [{hit[0][0]}] {hit[0][1]}; the owner runs this case by hand"
    return None


def _reset(project: Path, env: dict, timeout: int) -> str | None:
    """The environment's `reset` command returns it to a known state between cases. It passes the fence first,
    and a reset that fails is an error for the case, never a fail."""
    cmd = env.get("reset")
    if not cmd:
        return None
    hit = fence.matches({"tool_name": "Bash", "cwd": str(project), "tool_input": {"command": str(cmd)}})
    if hit:
        return f"reset not run: fence [{hit[0][0]}] {hit[0][1]}; the owner runs it by hand"
    try:
        done = subprocess.run(str(cmd), shell=True, cwd=env.get("cwd") or str(project), capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"reset timed out after {timeout}s"
    return None if done.returncode == 0 else f"reset failed (exit {done.returncode}): {done.stderr.strip()[-200:]}"


def run_case(project: Path, suite: Suite, case: Case, env: dict) -> dict:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    base = {"ac": suite.ac, "case": case.id, "driver": case.driver, "started": started}
    blocked = fenced(project, case, env)
    if blocked:
        return {**base, "session_id": None, "steps": [], "final_state": {}, "error": blocked, "fenced": True}
    timeout = env.get("timeout", DEFAULT_TIMEOUT)
    why = _reset(project, env, timeout)
    if why:
        return {**base, "session_id": None, "steps": [], "final_state": {}, "error": why}
    request = {"environment": env, "setup": case.setup, "steps": [{"do": s["do"]} for s in case.steps],
               "timeout": timeout}
    try:
        done = subprocess.run(driver_command(case.driver), input=json.dumps(request), capture_output=True,
                              text=True, encoding="utf-8", timeout=timeout * (len(case.steps) + 1) + 10)
        output = json.loads(done.stdout)
    except Exception as exc:   # a driver that dies leaves an error and no invented observation
        output = {"session_id": None, "steps": [], "final_state": {}, "error": f"driver failed: {type(exc).__name__}: {exc}"}
    return {**base, "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"), **output}


def _new_run_dir(project: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root, n = project / "greenfield" / "runs", 1
    path = root / stamp
    while path.exists():
        n += 1
        path = root / f"{stamp}-{n}"
    return path


def run(project: Path, selected: list[Suite], env: dict, into: Path | None = None,
        rerun_reason: str | None = None, preflight: dict | None = None) -> Path:
    every = {s.ac for s in suites_mod.load_all(project)}
    run_dir = into or _new_run_dir(project)
    (run_dir / "cases" / "attempts").mkdir(parents=True, exist_ok=True)
    for s in selected:
        for case in s.cases:
            target = run_dir / "cases" / f"{s.ac}__{case.id}.json"
            if target.exists():
                if not rerun_reason:
                    raise RunError(f"{target.name} already ran in this run; a rerun needs --rerun-reason")
                n = len(list((run_dir / "cases" / "attempts").glob(f"{target.stem}.*.json"))) + 1
                target.replace(run_dir / "cases" / "attempts" / f"{target.stem}.{n}.json")
            record = run_case(project, s, case, env)
            if rerun_reason:
                record["rerun_reason"] = rerun_reason
            target.write_text(json.dumps(record, indent=2), encoding="utf-8")
    builds = project / "greenfield" / "builds.yaml"
    meta = {"full": {s.ac for s in selected} >= every, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "environment": env.get("name"), "preflight": preflight, "build_ids": (yaml.safe_load(builds.read_text(encoding="utf-8")) or {})
            if builds.is_file() else {}, "suites": {s.ac: s.sha for s in selected}}
    (run_dir / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return run_dir


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def score_run(project: Path, run_dir: Path) -> dict:
    """Refuses a run whose suites no longer verify or have changed since the run; otherwise writes scores/ and
    verdicts.json. Judgments come from judgments/<AC>__<TC>.json, written by tim, never from the builder."""
    meta = _read(run_dir / "run.json")
    if meta is None:
        raise RunError(f"{run_dir} has no run.json")
    problems, loaded = [], []
    for ac, sha in meta["suites"].items():
        path = project / "greenfield" / "suites" / f"{ac}.yaml"
        if not path.is_file():
            problems.append(f"{ac}: suite file is gone")
            continue
        s = suites_mod.load(path)
        if s.sha != sha:
            problems.append(f"{ac}: the suite changed after this run; run it again")
        problems += suites_mod.verify(s, project)
        loaded.append(s)
    if problems:
        raise SuiteError(problems)
    (run_dir / "scores").mkdir(exist_ok=True)
    acs = {}
    for s in loaded:
        results = []
        for case in s.cases:
            key = f"{s.ac}__{case.id}"
            result = scorer.score_case(case, _read(run_dir / "cases" / f"{key}.json"),
                                       _read(run_dir / "judgments" / f"{key}.json"))
            (run_dir / "scores" / f"{key}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
            results.append(result)
        acs[s.ac] = {"verdict": scorer.ac_verdict(results), "cases": {r["case"]: r["status"] for r in results}}
    verdicts = {"run": run_dir.name, "full": meta["full"], "build_ids": meta["build_ids"], "acs": acs}
    (run_dir / "verdicts.json").write_text(json.dumps(verdicts, indent=2), encoding="utf-8")
    return verdicts
