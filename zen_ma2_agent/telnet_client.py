from __future__ import annotations

import re
import socket
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LOGIN_USER_RE = re.compile(r"logged\s+in\s+as\s+user\s+['\"]?([^'\"\r\n]+)", re.I)
LOGIN_ECHO_RE = re.compile(r"\b(login\s+\S+\s+)(\S+)", re.I)


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    TCP_CONNECTED = "TCP_CONNECTED"
    NEGOTIATING = "NEGOTIATING"
    AUTHENTICATING = "AUTHENTICATING"
    AUTH_FAILED = "AUTH_FAILED"
    READY = "READY"


class MA2ConnectionError(ConnectionError):
    pass


class MA2AuthenticationError(MA2ConnectionError):
    pass


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def login_command(username: str, password: str) -> str:
    return f"Login {username} {password}" if password else f"Login {username}"


def redact_login_echo(text: str) -> str:
    """Keep audit useful while never retaining a password echoed by Telnet."""
    return LOGIN_ECHO_RE.sub(lambda match: match.group(1) + "[REDACTED]", text)


@dataclass
class MA2TelnetClient:
    host: str
    port: int
    read_timeout_seconds: float = 0.35
    auth_timeout_seconds: float = 3.0
    socket_factory: Callable[..., socket.socket] = socket.create_connection
    socket: socket.socket | None = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    authenticated_user: str | None = None
    requested_username: str | None = None
    current_session_user: str | None = None
    auth_failure_reason: str | None = None
    audit_entries: list[str] = field(default_factory=list)
    _auth_started_at: float | None = field(default=None, init=False, repr=False)
    _receiver: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop_receiver: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _received: list[str] = field(default_factory=list, init=False, repr=False)
    _received_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _pending_password: str = field(default="", init=False, repr=False)
    _login_retry_sent: bool = field(default=False, init=False, repr=False)

    @property
    def connected(self) -> bool:
        return self.state is not ConnectionState.DISCONNECTED

    def connect(self, username: str, password: str = "") -> str:
        """Open TCP and start asynchronous authentication for exactly username."""
        if self.connected:
            raise MA2ConnectionError("Already connected. Disconnect before connecting again.")
        if not username:
            raise MA2AuthenticationError("USERNAME REQUIRED")
        try:
            self.socket = self.socket_factory((self.host, self.port), timeout=3)
            self.socket.settimeout(0.1)
        except OSError as exc:
            self.socket = None
            raise MA2ConnectionError(f"Cannot connect to grandMA2 at {self.host}:{self.port}: {exc}") from exc
        self.state = ConnectionState.TCP_CONNECTED
        self._start_receiver()
        self.state = ConnectionState.NEGOTIATING
        self.requested_username = username
        self.authenticated_user = None
        self.current_session_user = None
        self.auth_failure_reason = None
        # Retained only during this in-memory handshake so MA2's initial guest
        # banner can request one bounded retry. It is cleared on every terminal
        # auth path and is never emitted to audit/configuration.
        self._pending_password = password
        self._login_retry_sent = False
        self.state = ConnectionState.AUTHENTICATING
        self._auth_started_at = time.monotonic()
        self._send_login(username, password)
        # Password is never retained or written to audit output.
        return self.poll_authentication()

    def poll_authentication(self) -> str:
        """Consume received output and transition only on requested-user proof."""
        if self.state is not ConnectionState.AUTHENTICATING:
            return ""
        received = self._drain_received()
        if received:
            clean = strip_ansi(received)
            for line in clean.splitlines():
                line = line.strip()
                if line:
                    self.audit_entries.append(f"RX: {redact_login_echo(line)}")
            if re.search(r"\b(login\s+failed|invalid\s+(?:user|password)|denied)\b", clean, re.I):
                self.auth_failure_reason = clean.strip() or "MA2 rejected login."
                self.state = ConnectionState.AUTH_FAILED
                self._pending_password = ""
                return clean
            users = [match.group(1).strip() for match in LOGIN_USER_RE.finditer(clean)]
            if users:
                self.current_session_user = users[-1]
                if self.current_session_user == self.requested_username:
                    self.authenticated_user = self.current_session_user
                    self.state = ConnectionState.READY
                    self._pending_password = ""
                    return clean
            # grandMA2 3.9 may first report a default guest session while its
            # banner is still negotiating. A Login sent before that banner can
            # be discarded. Retry the exact requested identity once only after
            # MA2 explicitly asks to log in; never substitute a user or loop.
            if (
                self.requested_username
                and self.current_session_user != self.requested_username
                and re.search(r"please\s+login", clean, re.I)
                and not self._login_retry_sent
            ):
                self._login_retry_sent = True
                self._send_login(self.requested_username, self._pending_password)
        if self._auth_started_at is not None and time.monotonic() - self._auth_started_at >= self.auth_timeout_seconds:
            current = self.current_session_user or "unknown"
            self.auth_failure_reason = f"Requested user: {self.requested_username}; Current user: {current}"
            self.state = ConnectionState.AUTH_FAILED
            self._pending_password = ""
        return received

    def execute(self, command: str) -> str:
        if self.state is not ConnectionState.READY:
            raise MA2ConnectionError("MA2 is not READY.")
        return self._send_command(command)

    def _send_login(self, username: str, password: str) -> None:
        self.audit_entries.append(f"TX: Login {username}")
        self._send_line(login_command(username, password))

    def _send_command(self, command: str) -> str:
        self._send_line(command)
        time.sleep(max(0, self.read_timeout_seconds))
        received = strip_ansi(self._drain_received())
        for line in received.splitlines():
            if line.strip():
                self.audit_entries.append(f"RX: {redact_login_echo(line.strip())}")
        return received

    def _send_line(self, command: str) -> None:
        if not self.socket:
            raise MA2ConnectionError("Not connected to grandMA2.")
        try:
            self.socket.sendall((command.rstrip("\r\n") + "\r\n").encode("utf-8"))
        except OSError as exc:
            self.close()
            raise MA2ConnectionError(f"Telnet command failed: {exc}") from exc

    def _start_receiver(self) -> None:
        self._stop_receiver.clear()
        self._receiver = threading.Thread(target=self._receive_loop, name="zen-ma2-telnet-recv", daemon=True)
        self._receiver.start()

    def _receive_loop(self) -> None:
        while not self._stop_receiver.is_set() and self.socket:
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    return
                with self._received_lock:
                    self._received.append(chunk.decode("utf-8", errors="replace"))
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                return

    def _drain_received(self) -> str:
        with self._received_lock:
            result = "".join(self._received)
            self._received.clear()
        return result

    def close(self) -> None:
        self._stop_receiver.set()
        sock, self.socket = self.socket, None
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        if self._receiver and self._receiver.is_alive() and self._receiver is not threading.current_thread():
            self._receiver.join(timeout=0.3)
        self._receiver = None
        self.authenticated_user = None
        self.requested_username = None
        self.current_session_user = None
        self._auth_started_at = None
        self._pending_password = ""
        self._login_retry_sent = False
        self.state = ConnectionState.DISCONNECTED
