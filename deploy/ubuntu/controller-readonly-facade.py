from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 18876
UPSTREAM = "http://127.0.0.1:8876"
ALLOWED_GETS = frozenset({"/healthz", "/zen/v0.1/status"})
ALLOWED_POSTS = frozenset({"/zen/v0.1/tools/zen.department.status"})
MAX_REQUEST_BODY = 8192
MAX_RESPONSE_BODY = 65536

log_dir = Path("/var/log/zen-agent")
log_dir.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("controller-readonly-facade")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    log_dir / "controller-readonly-facade.log",
    maxBytes=1_000_000,
    backupCount=2,
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
class Handler(BaseHTTPRequestHandler):
    server_version = "ZEN-Controller-ReadOnly-Facade/0.1"

    def log_message(self, fmt: str, *args) -> None:
        logger.info("%s %s", self.client_address[0], fmt % args)

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _proxy(self, method: str, body: bytes | None = None) -> None:
        headers = {"accept": "application/json"}
        if body is not None:
            headers["content-type"] = "application/json"
        req = Request(
            UPSTREAM + self.path,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urlopen(req, timeout=3.0) as response:
                raw = response.read(MAX_RESPONSE_BODY + 1)
                if len(raw) > MAX_RESPONSE_BODY:
                    raise ValueError("upstream body too large")
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("upstream payload must be object")
                status = int(response.status)
            self._json(status, payload)
        except Exception:
            logger.warning("upstream request failed method=%s path=%s", method, self.path)
            self._json(502, {"status": "UPSTREAM_UNAVAILABLE"})

    def do_GET(self) -> None:
        if self.path not in ALLOWED_GETS:
            self._json(404, {"status": "NOT_FOUND"})
            return
        self._proxy("GET")

    def do_POST(self) -> None:
        if self.path not in ALLOWED_POSTS:
            self._json(405, {"status": "READ_ONLY"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
        except ValueError:
            self._json(400, {"status": "INVALID_REQUEST"})
            return
        if length < 0 or length > MAX_REQUEST_BODY:
            self._json(413, {"status": "PAYLOAD_TOO_LARGE"})
            return
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
            if not isinstance(payload, dict):
                raise ValueError("body must be object")
        except Exception:
            self._json(400, {"status": "INVALID_JSON"})
            return
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self._proxy("POST", canonical)

    def _deny_mutation(self) -> None:
        self._json(405, {"status": "READ_ONLY"})

    do_PUT = _deny_mutation
    do_PATCH = _deny_mutation
    do_DELETE = _deny_mutation
def main() -> int:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    logger.info(
        "listening host=%s port=%s upstream=%s",
        LISTEN_HOST,
        LISTEN_PORT,
        UPSTREAM,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
