from __future__ import annotations

import ipaddress
import socketserver
import threading
from collections import OrderedDict
from typing import Callable, Optional

from .protocol import (
    BridgeCommand,
    BridgeProtocolError,
    BridgeRequest,
    MAX_LINE_BYTES,
    PROTOCOL_VERSION,
    RequestDeduplicator,
    format_error,
    format_ready,
    parse_request_line,
)

DEFAULT_BRIDGE_HOST = "127.0.0.1"
DEFAULT_BRIDGE_PORT = 8877
DEFAULT_RESPONSE_CACHE_CAPACITY = 256

StatusPayloadProvider = Callable[[], str]


def _request_id_hint(line: str) -> str:
    tokens = line.split()
    if len(tokens) >= 3:
        candidate = tokens[2]
        if candidate and len(candidate) <= 64 and all(ch.isalnum() or ch in "._-" for ch in candidate):
            return candidate
    return "UNKNOWN"


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class BridgeDispatcher:
    """Deterministic no-write dispatcher for ZEN/1 Bridge requests."""

    def __init__(
        self,
        status_payload_provider: Optional[StatusPayloadProvider] = None,
        *,
        dedup_capacity: int = DEFAULT_RESPONSE_CACHE_CAPACITY,
    ):
        self._status_payload_provider = status_payload_provider or (
            lambda: "FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE=NO"
        )
        self._dedup = RequestDeduplicator(dedup_capacity)
        self._responses: OrderedDict[str, str] = OrderedDict()
        self._capacity = dedup_capacity
        self._lock = threading.Lock()

    def dispatch(self, request: BridgeRequest) -> str:
        with self._lock:
            dedup_state = self._dedup.check(request)
            if dedup_state == "DUPLICATE":
                cached = self._responses.get(request.request_id)
                if cached is not None:
                    self._responses.move_to_end(request.request_id)
                    return cached

            if request.command == BridgeCommand.PING:
                response = format_ready(request.request_id, "PONG")
            elif request.command == BridgeCommand.STATUS:
                payload = str(self._status_payload_provider()).strip()
                response = format_ready(request.request_id, payload)
            elif request.command == BridgeCommand.DIMMER:
                response = format_ready(request.request_id, "NOT_EXECUTED")
            elif request.command == BridgeCommand.DESIGN:
                response = format_ready(request.request_id, "NOT_IMPLEMENTED")
            else:  # pragma: no cover
                response = format_error(request.request_id, "NOT_IMPLEMENTED")

            self._responses[request.request_id] = response
            self._responses.move_to_end(request.request_id)
            while len(self._responses) > self._capacity:
                self._responses.popitem(last=False)
            return response

    def handle_line(self, line: str) -> str:
        request_id = _request_id_hint(line)
        try:
            request = parse_request_line(line)
            return self.dispatch(request)
        except BridgeProtocolError as exc:
            return format_error(request_id, exc.code)
        except Exception:
            return format_error(request_id, "INTERNAL_ERROR")


class _BridgeRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        self.request.settimeout(self.server.connection_timeout)  # type: ignore[attr-defined]
        while True:
            raw = self.rfile.readline(MAX_LINE_BYTES + 2)
            if not raw:
                return
            if len(raw) > MAX_LINE_BYTES + 1 or (len(raw) == MAX_LINE_BYTES + 1 and not raw.endswith(b"\n")):
                self.wfile.write(f"{PROTOCOL_VERSION} ERROR UNKNOWN LINE_TOO_LONG\n".encode("utf-8"))
                self.wfile.flush()
                return
            try:
                line = raw.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError:
                self.wfile.write(f"{PROTOCOL_VERSION} ERROR UNKNOWN INVALID_PROTOCOL\n".encode("utf-8"))
                self.wfile.flush()
                continue
            response = self.server.dispatcher.handle_line(line)  # type: ignore[attr-defined]
            self.wfile.write((response + "\n").encode("utf-8"))
            self.wfile.flush()


class _ThreadingBridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler, *, dispatcher: BridgeDispatcher, connection_timeout: float):
        self.dispatcher = dispatcher
        self.connection_timeout = connection_timeout
        super().__init__(server_address, handler)


class BridgeServer:
    """Small TCP line server. It has no MA transport or LLM authority."""

    def __init__(
        self,
        dispatcher: Optional[BridgeDispatcher] = None,
        *,
        host: str = DEFAULT_BRIDGE_HOST,
        port: int = DEFAULT_BRIDGE_PORT,
        connection_timeout: float = 5.0,
        allow_remote: bool = False,
    ):
        if not 1 <= int(port) <= 65535:
            raise ValueError("bridge port must be in range 1..65535")
        if connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        if not allow_remote and not _is_loopback_host(host):
            raise ValueError("non-loopback Bridge bind requires allow_remote=True and separate security review")
        self.host = host
        self.port = int(port)
        self.connection_timeout = float(connection_timeout)
        self.dispatcher = dispatcher or BridgeDispatcher()
        self._server: Optional[_ThreadingBridgeServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._server = _ThreadingBridgeServer(
            (self.host, self.port),
            _BridgeRequestHandler,
            dispatcher=self.dispatcher,
            connection_timeout=self.connection_timeout,
        )
        self.port = int(self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, name="zen-ma-bridge", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._server = None
        self._thread = None
