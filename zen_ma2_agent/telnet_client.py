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


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    TCP_CONNECTED = "TCP_CONNECTED"
    NEGOTIATING = "NEGOTIATING"
    AUTHENTICATING = "AUTHENTICATING"
    READY = "READY"


class MA2ConnectionError(ConnectionError):
    pass


class MA2AuthenticationError(MA2ConnectionError):
    pass


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def login_command(username: str, password: str) -> str:
    return f"Login {username} {password}" if password else f"Login {username}"


@dataclass
class MA2TelnetClient:
    host: str
    port: int
    read_timeout_seconds: float = 0.35
    socket_factory: Callable[..., socket.socket] = socket.create_connection
    socket: socket.socket | None = None
    state: ConnectionState = ConnectionState.DISCONNECTED
    authenticated_user: str | None = None
    _receiver: threading.Thread | None = field(default=None, init=False, repr=False)
    _stop_receiver: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _received: list[str] = field(default_factory=list, init=False, repr=False)
    _received_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def connected(self) -> bool:
        return self.state is not ConnectionState.DISCONNECTED

    def connect(self, username: str, password: str = "") -> str:
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
        banner = self._drain(wait_seconds=self.read_timeout_seconds)
        self.state = ConnectionState.AUTHENTICATING
        response = self._send_and_read(login_command(username, password))
        combined = strip_ansi((banner + response).strip())
        if re.search(r"\b(login\s+failed|invalid\s+(?:user|password)|denied)\b", combined, re.I):
            self.close()
            raise MA2AuthenticationError(combined or "MA2 rejected login.")
        match = LOGIN_USER_RE.search(combined)
        self.authenticated_user = match.group(1).strip() if match else username
        self.state = ConnectionState.READY
        return combined

    def execute(self, command: str) -> str:
        if self.state is not ConnectionState.READY:
            raise MA2ConnectionError("MA2 is not READY.")
        return self._send_and_read(command)

    def _send_and_read(self, command: str) -> str:
        if not self.socket:
            raise MA2ConnectionError("Not connected to grandMA2.")
        try:
            self.socket.sendall((command.rstrip("\r\n") + "\r\n").encode("utf-8"))
            return strip_ansi(self._drain(wait_seconds=self.read_timeout_seconds))
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

    def _drain(self, wait_seconds: float) -> str:
        deadline = time.monotonic() + max(0, wait_seconds)
        while time.monotonic() < deadline:
            time.sleep(0.01)
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
        self.state = ConnectionState.DISCONNECTED
