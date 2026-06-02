#!/usr/bin/env python3
"""Minimal stdlib HTTP stub for the Reactive-Resume v5 API.

Routes served:
  GET /api/rpc/resumes           -> list of resume metadata
  GET /api/rpc/resumes/r1        -> contents of tests/fixtures/rr_sample.json
  GET /api/rpc/resumes/auth-fail -> 401
  GET /api/rpc/resumes/unavailable -> 503

Run:  python tests/stubs/rr_stub.py
Port: 9911
Auto-shuts after 60 s or on SIGINT.
"""
import json
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 9911
FIXTURE = Path(__file__).parent.parent / "fixtures" / "rr_sample.json"

LIST_RESPONSE = json.dumps(
    [{"id": "r1", "name": "My CV", "updatedAt": "2026-01-01T00:00:00Z"}]
).encode()


class RRHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # noqa: ANN001
        print(f"[rr_stub] {self.address_string()} - {fmt % args}", file=sys.stderr)

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]

        if path == "/api/rpc/resumes":
            self._send(200, LIST_RESPONSE, "application/json")

        elif path == "/api/rpc/resumes/r1":
            body = FIXTURE.read_bytes()
            self._send(200, body, "application/json")

        elif path == "/api/rpc/resumes/auth-fail":
            self._send(401, b'{"error":"unauthorized"}', "application/json")

        elif path == "/api/rpc/resumes/unavailable":
            self._send(503, b'{"error":"service unavailable"}', "application/json")

        else:
            self._send(404, b'{"error":"not found"}', "application/json")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = HTTPServer(("127.0.0.1", PORT), RRHandler)
    print(f"[rr_stub] listening on http://127.0.0.1:{PORT}", file=sys.stderr)

    def _shutdown(signum, frame):  # noqa: ANN001
        print("[rr_stub] shutting down", file=sys.stderr)
        threading.Thread(target=server.shutdown).start()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    timer = threading.Timer(60, lambda: _shutdown(None, None))
    timer.daemon = True
    timer.start()

    server.serve_forever()


if __name__ == "__main__":
    main()
