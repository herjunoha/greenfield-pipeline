"""The test author's output for acme-csv: cli only, no network, results read from captured files. No step in any of
these suites is an HTTP call, which is the point of the fixture: the case model is not HTTP-shaped."""
from linkr_suites import check, step


def suites(python):
    def run(*args, capture=()):
        return {"cli": {"cmd": python, "args": ["csvsum.py", *args], "capture": list(capture)}}

    def write(name, text):
        return {"cli": {"cmd": python, "args": ["-c", f"open({name!r}, 'w', newline='').write({text!r})"]}}

    def case(name, steps, kind="positive", severity="critical"):
        return {"id": "TC-01", "name": name, "type": kind, "severity": severity, "steps": steps}

    def suite(ac, dimension, *cases):
        return {"ac": ac, "baseline_sha": "STAMP", "contract_sha": "STAMP", "surface": "csvsum-cli",
                "dimension": dimension, "cases": list(cases)}

    summary = "$.files['summary.json'].text"
    return {
        "AC-1": suite("AC-1", "functional", case("two numeric columns are summed", [
            step(write("in1.csv", "a,b\n1,2\n3,4\n")),
            step(run("summarize", "in1.csv", "--out", "summary.json", capture=["summary.json"]),
                 check("$.exit_code", "eq", 0, "contract:usage.md"),
                 check(summary, "contains", '"rows": 2', "example:EX-1"),
                 check(summary, "contains", '"a": 4', "example:EX-1"),
                 check(summary, "contains", '"b": 6', "example:EX-1"))])),
        "AC-2": suite("AC-2", "functional", case("a missing file exits 2 and writes nothing", [
            step(run("--version"), check("$.exit_code", "eq", 0, "contract:usage.md")),          # liveness: it runs
            step(run("summarize", "no-such-file.csv", "--out", "never.json", capture=["never.json"]),
                 check("$.exit_code", "eq", 2, "contract:usage.md"),
                 check("$.stderr", "contains", "not found", "canonical:AC-2"),
                 check("$.files['never.json'].exists", "eq", False, "canonical:AC-2"))], "negative")),
        "AC-3": suite("AC-3", "functional", case("a header-only file has zero rows", [
            step(write("in3.csv", "a,b\n")),
            step(run("summarize", "in3.csv", "--out", "summary3.json", capture=["summary3.json"]),
                 check("$.exit_code", "eq", 0, "contract:usage.md"),
                 check("$.files['summary3.json'].text", "contains", '"rows": 0', "canonical:AC-3"),
                 check("$.files['summary3.json'].text", "contains", '"a": 0', "canonical:AC-3"))], "edge")),
        "AC-4": suite("AC-4", "performance", case("5000 rows in under two seconds", [
            step({"cli": {"cmd": python, "args": ["-c", "open('big.csv','w').write('a,b\\n'+''.join(f'{i},{i}\\n' for i in range(5000)))"]}}),
            step(run("summarize", "big.csv", "--out", "big.json", capture=["big.json"]),
                 check("$.exit_code", "eq", 0, "contract:usage.md"),
                 check("$.elapsed_ms", "lt", 2000, "canonical:AC-4"))], severity="major")),
    }
