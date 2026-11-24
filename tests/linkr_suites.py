"""The test author's output for acme-linkr as data: one suite per AC, written against the contract, the canonical and
the confirmed examples, never against code. Used by the scratch run."""
KEY = {"X-Api-Key": "demo"}
CREATE = {"http": {"method": "POST", "path": "/links", "headers": KEY, "json": {"url": "https://example.com/a"}}}
REDIRECT = {"http": {"path": "/{{0.body.code}}", "follow": False}}


def check(path, op, value, source):
    return {"path": path, "op": op, "value": value, "from": source}


def step(do, *checks):
    return {"do": do, "expect": list(checks)}


def case(name, steps, kind="positive", severity="critical"):
    return {"id": "TC-01", "name": name, "type": kind, "severity": severity, "steps": steps}


def suite(ac, surface, dimension, *cases):
    return {"ac": ac, "baseline_sha": "STAMP", "contract_sha": "STAMP", "surface": surface,
            "dimension": dimension, "cases": list(cases)}


def suites(python):
    def cli(*args):
        return {"cli": {"cmd": python, "args": ["linkr.py", "--db", *args]}}

    api = "linkr-api"
    return {
        "AC-1": suite("AC-1", api, "functional", case("a caller with a key gets a six-character code", [
            step(CREATE, check("$.status", "eq", 201, "contract:links.yaml"),
                 check("$.body.code", "matches", "^[a-z0-9]{6}$", "contract:links.yaml"))])),
        "AC-2": suite("AC-2", api, "functional", case("a visitor is sent to the original address", [
            step(CREATE, check("$.status", "eq", 201, "contract:links.yaml")),
            step(REDIRECT, check("$.status", "eq", 302, "contract:links.yaml"),
                 check("$.headers.location", "eq", "https://example.com/a", "canonical:AC-2"))])),
        "AC-3": suite("AC-3", api, "functional", case("an unknown code answers not found", [
            step(CREATE, check("$.status", "eq", 201, "contract:links.yaml")),     # liveness control: it answers
            step({"http": {"path": "/zzzzzz"}}, check("$.status", "eq", 404, "contract:links.yaml"))], "negative")),
        "AC-4": suite("AC-4", api, "security", case("a javascript address is refused", [
            step({"http": {"method": "POST", "path": "/links", "headers": KEY, "json": {"url": "javascript:alert(1)"}}},
                 check("$.status", "eq", 400, "example:EX-1"))], "negative")),
        "AC-5": suite("AC-5", api, "security", case("creating without a key is refused", [
            step({"http": {"method": "POST", "path": "/links", "json": {"url": "https://example.com/a"}}},
                 check("$.status", "eq", 401, "contract:links.yaml"))], "negative")),
        "AC-6": suite("AC-6", api, "performance", case("a redirect answers within 200 ms", [
            step(CREATE, check("$.status", "eq", 201, "contract:links.yaml")),
            step(REDIRECT, check("$.elapsed_ms", "lt", 200, "canonical:AC-6"))], severity="major")),
        "AC-7": suite("AC-7", "linkr-cli", "functional", case("create prints the short code", [
            step(cli("tc7.db", "create", "https://example.com/a"), check("$.exit_code", "eq", 0, "canonical:AC-7"),
                 check("$.stdout", "matches", "^[a-z0-9]{6}\\s*$", "canonical:AC-7"))])),
        "AC-8": suite("AC-8", "linkr-cli", "functional", case("stats shows two visits after two opens", [
            step(cli("tc8.db", "create", "https://example.com/a")),
            step(cli("tc8.db", "open", "{{0.stdout}}")),
            step(cli("tc8.db", "open", "{{0.stdout}}")),
            step(cli("tc8.db", "stats", "{{0.stdout}}"), check("$.stdout", "matches", "^2\\s*$", "example:EX-2"))])),
    }
