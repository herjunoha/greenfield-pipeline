"""acme-linkr reference implementation: what a correct build of the eight ACs looks like. Stdlib only."""
import json
import random
import string
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "0.1.0"
LINKS = {}
VISITS = {}


def valid_scheme(url):
    return url.startswith(("http://", "https://"))


def new_code():
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(size) or b"{}")
        if self.path != "/links":
            return self._send(404, {"error": "not found"})
        if not self.headers.get("X-Api-Key"):   # keys are issued out of band; the toy takes any non-empty one
            return self._send(401, {"error": "missing API key"})
        url = str(body.get("url") or "")
        if not valid_scheme(url):
            return self._send(400, {"error": "only http and https addresses"})
        code = new_code()
        LINKS[code] = url
        VISITS[code] = 0
        self._send(201, {"code": code})

    def do_GET(self):
        code = self.path.lstrip("/")
        if code == "health":
            return self._send(200, {"status": "ok", "version": VERSION})
        if code == "state":
            return self._send(200, {"links": len(LINKS)})
        if code in LINKS:
            VISITS[code] += 1
            return self._send(302, {}, {"Location": LINKS[code]})
        self._send(404, {"error": "not found"})


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8080
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
