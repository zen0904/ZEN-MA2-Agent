from __future__ import annotations

import select
import socket
from dataclasses import dataclass


class MA2ConnectionError(ConnectionError):
    pass


@dataclass
class MA2TelnetClient:
    host: str
    port: int
    read_timeout_seconds: float = 0.35
    socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self.socket is not None

    def connect(self, login_command: str = "") -> str:
        self.close()
        try:
            self.socket = socket.create_connection((self.host, self.port), timeout=3)
            self.socket.setblocking(False)
        except OSError as exc:
            self.socket = None
            raise MA2ConnectionError(f"Cannot connect to grandMA2 at {self.host}:{self.port}: {exc}") from exc
        banner = self._read_available()
        if login_command.strip():
            self.execute(login_command)
        return banner

    def execute(self, command: str) -> str:
        if not self.socket:
            raise MA2ConnectionError("Not connected to grandMA2.")
        try:
            self.socket.sendall((command.rstrip("\r\n") + "\n").encode("utf-8"))
            return self._read_available()
        except OSError as exc:
            self.close()
            raise MA2ConnectionError(f"Telnet command failed: {exc}") from exc

    def _read_available(self) -> str:
        if not self.socket:
            return ""
        chunks: list[bytes] = []
        while True:
            readable, _, _ = select.select([self.socket], [], [], self.read_timeout_seconds if not chunks else 0)
            if not readable:
                break
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    def close(self) -> None:
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None
