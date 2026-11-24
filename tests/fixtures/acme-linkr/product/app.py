"""acme-linkr walking skeleton: a run command and a health endpoint, nothing else."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

VERSION = "0.0.1"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        ok = self.path == "/health"
        body = json.dumps({"status": "ok", "version": VERSION} if ok else {"error": "not found"}).encode()
        self.send_response(200 if ok else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv):
    if "--version" in argv:
        print(VERSION)
        return 0
    port = int(argv[argv.index("--port") + 1]) if "--port" in argv else 8080
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
