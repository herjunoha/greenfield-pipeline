import json
import socket
import subprocess
import sys
from pathlib import Path

DRIVERS = Path(__file__).resolve().parents[1] / "drivers"


def drive(name, steps, env=None, timeout=10):
    request = {"environment": env or {}, "setup": {}, "steps": [{"do": s} for s in steps], "timeout": timeout}
    done = subprocess.run([sys.executable, str(DRIVERS / f"drv_{name}.py")], input=json.dumps(request),
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def http(path, **kw):
    return {"http": {"path": path, **kw}}


def test_http_observes_status_headers_body_and_final_state(server):
    out = drive("http", [http("/links", method="POST", json={"url": "u"}), http("/abc123", follow=False)],
                {"base_url": server, "state_url": "/state"})
    assert out["error"] is None and len(out["steps"]) == 2
    first, second = (s["observed"] for s in out["steps"])
    assert first["status"] == 201 and first["body"] == {"code": "abc123"} and "elapsed_ms" in first
    assert second["status"] == 302 and second["headers"]["location"] == "https://example.com/a"
    assert out["final_state"] == {"links": 1}


def test_http_error_statuses_are_observations_not_errors(server):
    out = drive("http", [http("/nothing")], {"base_url": server})
    assert out["error"] is None and out["steps"][0]["observed"]["status"] == 404
    assert out["steps"][0]["observed"]["body"] == {"error": "nope"}


def test_http_connection_failure_is_an_error_with_no_invented_observation():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    out = drive("http", [http("/x")], {"base_url": f"http://127.0.0.1:{port}"})
    assert out["error"] and out["steps"] == [] and out["final_state"] == {}


def test_http_refuses_absolute_urls_and_a_missing_base_url(server):
    assert "absolute" in drive("http", [http("http://elsewhere.example/x")], {"base_url": server})["error"]
    assert "base_url" in drive("http", [http("/x")], {})["error"]


def test_http_without_state_url_leaves_final_state_empty(server):
    assert drive("http", [http("/abc123")], {"base_url": server})["final_state"] == {}


def test_cli_observes_exit_code_streams_and_files(tmp_path):
    code = ("import sys;print('hello');sys.stderr.write('warn');"
            "open('out.txt','w').write('summary');sys.exit(3)")
    out = drive("cli", [{"cli": {"cmd": sys.executable, "args": ["-c", code], "capture": ["out.txt", "none.txt"]}}],
                {"cwd": str(tmp_path)})
    obs = out["steps"][0]["observed"]
    assert out["error"] is None and obs["exit_code"] == 3
    assert obs["stdout"].strip() == "hello" and obs["stderr"] == "warn"
    assert obs["files"]["out.txt"] == {"exists": True, "size": 7, "text": "summary"}
    assert obs["files"]["none.txt"]["exists"] is False


def test_cli_stdin_and_final_state(tmp_path):
    echo = "import sys;print(sys.stdin.read().upper())"
    state = [sys.executable, "-c", "import json;print(json.dumps({'n': 2}))"]
    out = drive("cli", [{"cli": {"cmd": sys.executable, "args": ["-c", echo], "stdin": "abc"}}],
                {"cwd": str(tmp_path), "state_cmd": state})
    assert out["steps"][0]["observed"]["stdout"].strip() == "ABC" and out["final_state"] == {"n": 2}


def test_cli_missing_command_and_timeout_are_errors(tmp_path):
    out = drive("cli", [{"cli": {"cmd": "no-such-binary-xyz"}}], {"cwd": str(tmp_path)})
    assert out["error"] and out["steps"] == []
    slow = drive("cli", [{"cli": {"cmd": sys.executable, "args": ["-c", "import time;time.sleep(5)"]}}],
                 {"cwd": str(tmp_path)}, timeout=1)
    assert "Timeout" in slow["error"] and slow["steps"] == []


def test_manual_hands_the_instruction_to_the_owner():
    out = drive("manual", [{"manual": {"instruction": "open the page on a phone"}}])
    assert out["manual"] is True and out["error"] == "manual step, needs the owner"
    assert out["instructions"] == ["open the page on a phone"] and out["steps"] == []


def test_a_step_can_use_what_an_earlier_step_observed(server):
    out = drive("http", [http("/links", method="POST", json={"url": "u"}), http("/{{0.body.code}}", follow=False)],
                {"base_url": server})
    assert out["error"] is None and out["steps"][1]["observed"]["status"] == 302


def test_a_template_with_nothing_to_fill_is_an_error_not_a_guess(server):
    out = drive("http", [http("/nothing"), http("/{{0.body.code}}")], {"base_url": server})
    assert "template value is not there" in out["error"] and len(out["steps"]) == 1
    assert "did not run" in drive("http", [http("/{{3.status}}")], {"base_url": server})["error"]


def test_the_cli_driver_fills_templates_too(tmp_path):
    echo = "import sys;print('code-' + sys.argv[1])"
    out = drive("cli", [{"cli": {"cmd": sys.executable, "args": ["-c", "print('abc')"]}},
                        {"cli": {"cmd": sys.executable, "args": ["-c", echo, "{{0.stdout}}"]}}], {"cwd": str(tmp_path)})
    assert out["error"] is None and out["steps"][1]["observed"]["stdout"].strip() == "code-abc"
