"""cli driver, stdlib only. do.cli: {cmd, args, stdin, cwd, capture: [paths]}. observed: exit_code, stdout, stderr,
elapsed_ms, files per captured path {exists, size, text up to 64 KB}. No shell: cmd and args are an argv list."""
import json
import os
import subprocess
import sys
import time
import uuid

import drvlib

LIMIT = 64 * 1024


def _file(path: str) -> dict:
    if not os.path.isfile(path):
        return {"exists": False, "size": 0, "text": None}
    with open(path, "rb") as f:
        raw = f.read(LIMIT + 1)
    return {"exists": True, "size": os.path.getsize(path), "text": raw[:LIMIT].decode("utf-8", errors="replace")}


def _run(spec: dict, base_cwd: str, timeout: int) -> dict:
    cwd = os.path.join(base_cwd, spec["cwd"]) if spec.get("cwd") else base_cwd
    argv = [str(spec["cmd"]), *[str(a) for a in spec.get("args") or []]]
    started = time.monotonic()
    done = subprocess.run(argv, input=spec.get("stdin"), cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "files": {p: _file(os.path.join(cwd, p)) for p in spec.get("capture") or []}}


def main() -> None:
    req = json.load(sys.stdin)
    env, timeout = req.get("environment") or {}, req.get("timeout", 30)
    base = os.path.abspath(env.get("cwd") or ".")
    out = {"session_id": uuid.uuid4().hex, "steps": [], "final_state": {}, "error": None}
    try:
        for step in req.get("steps") or []:
            out["steps"].append({"observed": _run(drvlib.fill(step["do"]["cli"], out["steps"]), base, timeout)})
        if env.get("state_cmd"):
            done = subprocess.run([str(a) for a in env["state_cmd"]], cwd=base, capture_output=True, text=True,
                                  timeout=timeout)
            out["final_state"] = json.loads(done.stdout)
    except Exception as exc:  # missing command, timeout, bad spec: an error, not an observation
        out["error"] = f"step {len(out['steps'])}: {type(exc).__name__}: {exc}"
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
