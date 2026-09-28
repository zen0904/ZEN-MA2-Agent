from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 18878
DEFAULT_UPSTREAM = "http://127.0.0.1:8876"
MAX_REQUEST_BODY = 1024 * 1024
MAX_RESPONSE_BODY = 8 * 1024 * 1024

ALLOWED_GETS = frozenset({"/healthz", "/zen/v0.1/status"})
ALLOWED_TOOLS = frozenset({
    "zen.status",
    "zen.ma.status",
    "zen.ma.visual",
    "zen.ma.stage.visual",
    "zen.design.request",
    "zen.preview",
    "zen.position.preview",
    "zen.position.raw.preview",
    "zen.position.calibration.preview",
    "zen.position.semantic.bindings",
    "zen.position.semantic.bind",
    "zen.approve",
    "zen.worker.status",
    "zen.watchdog.status",
    "zen.host.status",
})
SLOW_TOOLS = frozenset({"zen.ma.visual", "zen.ma.stage.visual"})


def build_handler(upstream: str, allowed_clients: frozenset[str]):
    class Handler(BaseHTTPRequestHandler):
        server_version = "ZEN-Lighting-Operator-Facade/0.1"

        def log_message(self, fmt: str, *args) -> None:
            logger.info("%s %s", self.client_address[0], fmt % args)

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(body)))
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _client_allowed(self) -> bool:
            return self.client_address[0] in allowed_clients

        def _proxy(self, method: str, *, body: bytes | None = None, timeout: float = 15.0) -> None:
            req = Request(
                upstream + self.path,
                data=body,
                method=method,
                headers={
                    "accept": "application/json",
                    **({"content-type": "application/json"} if body is not None else {}),
                },
            )
            try:
                with urlopen(req, timeout=timeout) as response:
                    raw = response.read(MAX_RESPONSE_BODY + 1)
                    if len(raw) > MAX_RESPONSE_BODY:
                        raise ValueError("upstream body too large")
                    status = int(response.status)
            except HTTPError as exc:
                raw = exc.read(MAX_RESPONSE_BODY + 1)
                status = int(exc.code)
            except Exception as exc:
                logger.warning(
                    "upstream failure method=%s path=%s class=%s",
                    method,
                    self.path,
                    type(exc).__name__,
                )
                self._json(502, {"status": "UPSTREAM_UNAVAILABLE"})
                return

            if len(raw) > MAX_RESPONSE_BODY:
                self._json(502, {"status": "UPSTREAM_RESPONSE_TOO_LARGE"})
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                self._json(502, {"status": "UPSTREAM_INVALID_JSON"})
                return
            if not isinstance(payload, dict):
                self._json(502, {"status": "UPSTREAM_INVALID_PAYLOAD"})
                return
            self._json(status, payload)

        def do_GET(self) -> None:
            if not self._client_allowed():
                self._json(403, {"status": "CLIENT_NOT_ALLOWED"})
                return
            if self.path not in ALLOWED_GETS:
                self._json(404, {"status": "NOT_FOUND"})
                return
            self._proxy("GET")

        def do_POST(self) -> None:
            if not self._client_allowed():
                self._json(403, {"status": "CLIENT_NOT_ALLOWED"})
                return
            prefix = "/zen/v0.1/tools/"
            if not self.path.startswith(prefix):
                self._json(404, {"status": "NOT_FOUND"})
                return
            tool_name = self.path[len(prefix):]
            if tool_name not in ALLOWED_TOOLS:
                self._json(405, {"status": "TOOL_NOT_ALLOWED"})
                return
            try:
                length = int(self.headers.get("content-length", "0"))
            except ValueError:
                self._json(400, {"status": "INVALID_CONTENT_LENGTH"})
                return
            if length < 0 or length > MAX_REQUEST_BODY:
                self._json(413, {"status": "PAYLOAD_TOO_LARGE"})
                return
            body = self.rfile.read(length)
            try:
                parsed = json.loads(body.decode("utf-8") or "{}")
                if not isinstance(parsed, dict):
                    raise ValueError("body must be object")
            except Exception:
                self._json(400, {"status": "INVALID_JSON"})
                return
            canonical = json.dumps(parsed, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            timeout = 90.0 if tool_name in SLOW_TOOLS else 20.0
            self._proxy("POST", body=canonical, timeout=timeout)

        def _deny(self) -> None:
            self._json(405, {"status": "METHOD_NOT_ALLOWED"})

        do_PUT = _deny
        do_PATCH = _deny
        do_DELETE = _deny

    return Handler


def main() -> int:
    parser = argparse.ArgumentParser(description="ZEN Windows lighting typed operator facade")
    parser.add_argument("--listen-host", default=DEFAULT_LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN_PORT)
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM)
    parser.add_argument("--allow-client", action="append", required=True)
    args = parser.parse_args()

    allowed = frozenset(str(ipaddress.ip_address(value)) for value in args.allow_client)
    log_dir = Path.home() / "AppData" / "Local" / "ZEN-MA2-Agent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    global logger
    logger = logging.getLogger("lighting-operator-facade")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        log_dir / "lighting-operator-facade.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)

    server = ThreadingHTTPServer(
        (args.listen_host, args.listen_port),
        build_handler(args.upstream.rstrip("/"), allowed),
    )
    logger.info(
        "listening=%s:%s upstream=%s allowed_clients=%s",
        args.listen_host,
        args.listen_port,
        args.upstream,
        sorted(allowed),
    )
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
