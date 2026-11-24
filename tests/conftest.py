import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

GF = [sys.executable, str(ROOT / "bin" / "gp")]
HOOK = [sys.executable, str(ROOT / "hooks" / "fence_hook.py")]


def run_gf(cwd, *args, env=None):
    import os
    return subprocess.run([*GF, *args], cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


@pytest.fixture
def project(tmp_path):
    """An initialised project (generic pack) with a product repo declared."""
    result = run_gf(tmp_path, "init", env={"GP_PACKS_DIR": str(tmp_path / "no-packs")})
    assert result.returncode == 0, result.stderr
    return tmp_path


@pytest.fixture
def bare(tmp_path_factory):
    """A folder with no greenfield/fence.yaml: the fence must stay silent here."""
    return tmp_path_factory.mktemp("bare")


import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CANONICAL = {
    "project": {
        "name": "links", "status": "draft", "objectives": ["shorten links"], "data_classes": ["none"],
        "surfaces": [{"name": "links-api", "kind": "http", "interface": None},
                     {"name": "tool", "kind": "cli", "interface": None}],
    },
    "requirements": [{"id": "AC-1", "statement": "s", "acceptance": "a", "dimension": "functional",
                      "surface": "links-api", "source": "brief.md"},
                     {"id": "AC-2", "statement": "s2", "acceptance": "a2", "dimension": "functional",
                      "surface": "links-api", "source": "brief.md"}],
    "examples": [
        {"id": "EX-1", "rule": "r", "given": {}, "expect": {}, "source": "sponsor-confirmed",
         "confirmed_by": "sponsor", "confirmed_on": "2026-11-13"},
        {"id": "EX-2", "rule": "r", "given": {}, "expect": {}, "source": "agent"},
        {"id": "EX-3", "rule": "r", "given": {}, "expect": {}, "source": "sponsor-confirmed"},
    ],
}

BASE_SUITE = {
    "ac": "AC-1", "baseline_sha": "STAMP", "contract_sha": "STAMP", "surface": "links-api",
    "dimension": "functional", "cases": [{
        "id": "TC-01", "name": "a visitor is redirected", "type": "positive", "severity": "critical",
        "steps": [
            {"do": {"http": {"method": "POST", "path": "/links", "json": {"url": "https://example.com/a"}}},
             "expect": [{"path": "$.status", "op": "eq", "value": 201, "from": "structural"},
                        {"path": "$.body.code", "op": "matches", "value": "^[a-z0-9]{6}$", "from": "canonical:AC-1"}]},
            {"do": {"http": {"method": "GET", "path": "/abc123", "follow": False}},
             "expect": [{"path": "$.status", "op": "eq", "value": 302, "from": "structural"}]},
        ],
        "final_check": [{"path": "$.state.links", "op": "eq", "value": 1, "from": "example:EX-1"}],
    }],
}


def suite_dict(**changes):
    data = copy.deepcopy(BASE_SUITE)
    data.update(changes)
    return data


def write_canonical(project, data=None):
    import yaml
    path = project / "greenfield" / "requirements" / "links.canonical.yaml"
    path.write_text(yaml.safe_dump(data or CANONICAL), encoding="utf-8")
    (project / "greenfield" / "sources" / "brief.md").write_text("# brief\nlinks\n", encoding="utf-8")


def write_suite(project, data=None, name="AC-1"):
    """Write a suite; a STAMP sha is replaced by what `gp acs` would print for that AC, as gus copies it."""
    import yaml
    from gp import audit
    data = data or suite_dict()
    canon, _ = audit.load(project)
    req = next((r for r in (canon or {}).get("requirements", []) if r["id"] == data["ac"]), None)
    if req:
        if data.get("baseline_sha") == "STAMP":
            data["baseline_sha"] = audit.ac_sha(req)
        if data.get("contract_sha") == "STAMP":
            data["contract_sha"] = audit.contract_sha(project, canon, req["surface"])
    path = project / "greenfield" / "suites" / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        self._send(201, {"code": "abc123"})

    def do_GET(self):
        if self.path == "/abc123":
            self._send(302, {}, {"Location": "https://example.com/a"})
        elif self.path == "/state":
            self._send(200, {"links": 1})
        else:
            self._send(404, {"error": "nope"})


@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture
def linkr(project):
    """The acme-linkr fixture (a fictional company's link shortener) laid over a fresh project."""
    import shutil
    shutil.copytree(FIXTURES / "acme-linkr" / "greenfield", project / "greenfield", dirs_exist_ok=True)
    return project


def edit_canonical(project, change):
    import yaml
    path = next((project / "greenfield" / "requirements").glob("*.canonical.yaml"))
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def leak_words():
    """The private denylist of company and personal words lives OUTSIDE the plugin; GP_LEAK_DENYLIST names its file.
    None when it is not set, and the leak checks then skip (they cannot run without it)."""
    import os
    path = os.environ.get("GP_LEAK_DENYLIST")
    if not path or not Path(path).is_file():
        return None
    return [w.strip().lower() for w in Path(path).read_text(encoding="utf-8").splitlines() if w.strip()]
