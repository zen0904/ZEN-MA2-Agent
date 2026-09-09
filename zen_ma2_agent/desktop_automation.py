"""Test-only localhost bridge for exercising the running packaged Desktop.

This is intentionally a tiny fixed-action protocol.  It is inactive unless a
test flag is supplied, never exposes preferences/passwords, and marshals every
widget action back to the Qt GUI thread.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import threading
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer


# A real Show Diagnostics run can legitimately need longer than a conventional
# UI request (for example, while MA2 returns a large inventory).  This affects
# only the explicit test bridge; normal Desktop traffic never uses this value.
AUTOMATION_ACTION_TIMEOUT_SECONDS = 180


def automation_enabled(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> bool:
    argv = argv or []
    environ = environ or os.environ
    return "--automation-test" in argv or environ.get("ZEN_MA2_AUTOMATION") == "1"


def automation_port(environ: dict[str, str] | None = None) -> int:
    value = (environ or os.environ).get("ZEN_MA2_AUTOMATION_PORT", "8766")
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("ZEN_MA2_AUTOMATION_PORT must be a localhost TCP port.") from exc
    if not 0 <= port <= 65535:
        raise ValueError("ZEN_MA2_AUTOMATION_PORT must be from 0 to 65535.")
    return port


@dataclass
class _BridgeRequest:
    payload: dict[str, Any]
    reply: queue.Queue[dict[str, Any]]


_DISPATCH_EVENT = QEvent.Type(QEvent.registerEventType())


class _DispatchEvent(QEvent):
    def __init__(self, request: _BridgeRequest) -> None:
        super().__init__(_DISPATCH_EVENT)
        self.request = request


class DesktopAutomationBridge(QObject):
    """A Qt-owned dispatcher plus a localhost-only socket worker."""

    def __init__(self, desktop: Any, *, port: int) -> None:
        super().__init__(desktop)
        self.desktop = desktop
        self.port = port
        self._server: _BridgeServer | None = None
        self._last_dispatch_thread_id: int | None = None

    def start(self) -> int:
        self._server = _BridgeServer(self, self.port)
        self._server.start()
        if not self._server.ready.wait(timeout=3):
            raise RuntimeError("Desktop automation bridge did not start.")
        if self._server.error:
            raise self._server.error
        self.port = self._server.port
        self.desktop.core.runtime.log("automation_bridge", {"status": "enabled", "bind": "127.0.0.1", "port": self.port})
        return self.port

    def stop(self) -> None:
        if self._server:
            self._server.stop()
            self._server.join(timeout=2)
            self._server = None

    def _dispatch(self, request: _BridgeRequest) -> None:
        """Runs in the GUI thread through the queued Qt signal."""
        self._last_dispatch_thread_id = threading.get_ident()
        try:
            action = request.payload.get("action")
            if action == "status":
                result = {
                    "ok": True,
                    "build_head": self.desktop.core.build_identity.get("head"),
                    "desktop_alive": True,
                    "automation": True,
                    "connection_state": self.desktop.core.runtime.state.value,
                }
            elif action == "connect":
                # Do not construct a transport here: this deliberately calls the
                # same handler a user invokes from Settings.
                self.desktop.connect()
                result = {"ok": True, "connection_state": self.desktop.core.runtime.state.value, "handler": "ZenDesktop.connect"}
            elif action == "submit":
                text = request.payload.get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > 1000:
                    raise ValueError("submit requires non-empty text up to 1000 characters.")
                self.desktop.request.setText(text)
                # The real Desktop handler owns Chat, AgentCore, and routing.
                self.desktop.submit()
                result = {"ok": True, "handler": "ZenDesktop.submit", "connection_state": self.desktop.core.runtime.state.value}
            elif action == "preview_real_song":
                # A fixed bundled analysis fixture only. The bridge accepts no
                # payload or command string, and this still enters through the
                # shared Desktop → AgentCore preview lifecycle.
                self.desktop.preview_real_song_test()
                result = {"ok": True, "handler": "ZenDesktop.preview_real_song_test", "connection_state": self.desktop.core.runtime.state.value}
            elif action == "chat_text":
                result = {"ok": True, "chat_text": self.desktop.chat.toPlainText()}
            elif action == "state_snapshot":
                snapshot = self.desktop.core.snapshot()
                result = {"ok": True, "state_browser": snapshot["state_browser"], "actions": snapshot["actions"]}
            elif action == "execute_pending":
                # Deliberately use the actual Desktop Execute handler.  The
                # bridge cannot supply an action id or arbitrary MA command.
                self.desktop.execute_action()
                pending = next((item for item in self.desktop.core.actions.values() if item.status == "PENDING_APPROVAL"), None)
                result = {"ok": True, "handler": "ZenDesktop.execute_action", "pending": bool(pending)}
            elif action == "connection_state":
                result = {"ok": True, "connection_state": self.desktop.core.runtime.state.value, "status": self.desktop.core.runtime.status_text()}
            elif action == "shutdown":
                result = {"ok": True, "shutdown": True}
                QTimer.singleShot(25, self.desktop.close)
            else:
                raise ValueError("Unsupported automation action.")
        except Exception as exc:
            result = {"ok": False, "error": str(exc) or exc.__class__.__name__}
        request.reply.put(result)

    def event(self, event: QEvent) -> bool:
        if event.type() == _DISPATCH_EVENT:
            self._dispatch(event.request)
            return True
        return super().event(event)


class _BridgeServer(threading.Thread):
    def __init__(self, bridge: DesktopAutomationBridge, port: int) -> None:
        super().__init__(name="zen-desktop-automation", daemon=True)
        self.bridge, self.port = bridge, port
        self.ready = threading.Event()
        self.error: Exception | None = None
        self._stop_event = threading.Event()
        self._socket: socket.socket | None = None

    def run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(("127.0.0.1", self.port))
                listener.listen(4)
                listener.settimeout(0.2)
                self._socket = listener
                self.port = listener.getsockname()[1]
                self.ready.set()
                while not self._stop_event.is_set():
                    try:
                        client, address = listener.accept()
                    except TimeoutError:
                        continue
                    if address[0] != "127.0.0.1":
                        client.close()
                        continue
                    with client:
                        client.settimeout(3)
                        raw = client.recv(4096)
                        response = self._handle(raw)
                        client.sendall((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))
        except Exception as exc:
            self.error = exc
            self.ready.set()

    def _handle(self, raw: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) - {"action", "text"}:
                raise ValueError("Invalid automation request.")
            if payload.get("action") != "submit" and "text" in payload:
                raise ValueError("Only submit accepts text through the automation bridge.")
            reply: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
            QCoreApplication.postEvent(self.bridge, _DispatchEvent(_BridgeRequest(payload, reply)))
            return reply.get(timeout=AUTOMATION_ACTION_TIMEOUT_SECONDS)
        except Exception as exc:
            return {"ok": False, "error": str(exc) or exc.__class__.__name__}

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
