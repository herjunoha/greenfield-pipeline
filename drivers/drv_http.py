"""http driver, stdlib only. stdin: {"environment", "steps": [{"do": {"http": {...}}}], "timeout"};
stdout: {"session_id", "steps": [{"observed": {...}}], "final_state", "error"}. On failure it writes `error` and
stops; it never invents an observation. Paths are relative to environment.base_url; an absolute URL is refused."""
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

import drvlib


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _decode(raw: bytes, ctype: str):
    text = raw.decode("utf-8", errors="replace")
    if "json" in ctype or text[:1] in "{[":
        try:
            return json.loads(text)
        except ValueError:
            pass
    return text


def _send(opener, url, spec, timeout):
    data, headers = None, {k: str(v) for k, v in (spec.get("headers") or {}).items()}
    if "json" in spec:
        data = json.dumps(spec["json"]).encode()
        headers.setdefault("Content-Type", "application/json")
    elif "body" in spec:
        data = str(spec["body"]).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=str(spec.get("method", "GET")).upper())
    started = time.monotonic()
    try:
        response = opener.open(request, timeout=timeout)
    except urllib.error.HTTPError as err:   # 3xx without follow, 4xx and 5xx are observations, not errors
        response = err
    raw = response.read()
    heads = {k.lower(): v for k, v in response.headers.items()}
    return {"status": response.status if hasattr(response, "status") else response.code, "headers": heads,
            "body": _decode(raw, heads.get("content-type", "")), "elapsed_ms": int((time.monotonic() - started) * 1000)}


def main() -> None:
    req = json.load(sys.stdin)
    env, timeout = req.get("environment") or {}, req.get("timeout", 30)
    base = str(env.get("base_url") or "").rstrip("/")
    out = {"session_id": uuid.uuid4().hex, "steps": [], "final_state": {}, "error": None}
    jar = http.cookiejar.CookieJar()
    follow = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    stay = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), _NoRedirect)
    try:
        if not base:
            raise ValueError("environment.base_url is not set")
        for n, step in enumerate(req.get("steps") or []):
            spec = drvlib.fill(step["do"]["http"], out["steps"])
            path = str(spec.get("path", ""))
            if "://" in path:
                raise ValueError(f"step {n}: absolute URLs are refused, use a path under base_url")
            opener = follow if spec.get("follow", True) else stay
            out["steps"].append({"observed": _send(opener, base + path, spec, timeout)})
        if env.get("state_url"):
            out["final_state"] = _send(follow, base + str(env["state_url"]), {}, timeout)["body"]
    except Exception as exc:  # connection refused, timeout, bad spec: an error, not an observation
        out["error"] = f"step {len(out['steps'])}: {type(exc).__name__}: {exc}"
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    main()
