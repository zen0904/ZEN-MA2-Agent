from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 18877
UPSTREAM = "http://127.0.0.1:8876"
ALLOWED_PATHS = frozenset({"/healthz", "/zen/v0.1/status"})
MAX_BODY = 65536

log_dir = Path.home() / "AppData" / "Local" / "ZEN-MA2-Agent" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("lighting-readonly-facade")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    log_dir / "lighting-readonly-facade.log",
    maxBytes=1_000_000,
    backupCount=2,
    encoding="utf-8",
)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
class Handler(BaseHTTPRequestHandler):
    server_version = "ZEN-ReadOnly-Facade/0.1"

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

    def do_GET(self) -> None:
        if self.path not in ALLOWED_PATHS:
            self._json(404, {"status": "NOT_FOUND"})
            return
        try:
            req = Request(
                UPSTREAM + self.path,
                method="GET",
                headers={"accept": "application/json"},
            )
            with urlopen(req, timeout=2.0) as response:
                body = response.read(MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    raise ValueError("upstream body too large")
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("upstream payload must be object")
                status = int(response.status)
            self._json(status, payload)
        except Exception:
            logger.warning("upstream read failed path=%s", self.path)
            self._json(502, {"status": "UPSTREAM_UNAVAILABLE"})

    def _deny_mutation(self) -> None:
        self._json(405, {"status": "READ_ONLY"})

    do_POST = _deny_mutation
    do_PUT = _deny_mutation
    do_PATCH = _deny_mutation
    do_DELETE = _deny_mutation
def main() -> int:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    logger.info(
        "listening host=%s port=%s upstream=%s allowed=%s",
        LISTEN_HOST,
        LISTEN_PORT,
        UPSTREAM,
        sorted(ALLOWED_PATHS),
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
