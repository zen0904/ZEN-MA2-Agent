from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import monotonic
from typing import Any

from .events import EventBus
from .config import save_preferences
from .network import internet_online, lan_ipv4_addresses
from .pairing import PairingManager
from .parser import ParseError
from .runtime import AgentRuntime
from .telnet_client import ConnectionState


@dataclass
class ActionRecord:
    id: str
    plan: dict[str, Any]
    status: str = "PENDING_APPROVAL"
    result: str | None = None


class AgentCore:
    """Single control boundary used by Desktop UI and mobile HTTP/WebSocket UI."""

    def __init__(self, runtime: AgentRuntime | None = None):
        self.runtime = runtime or AgentRuntime()
        self.events = EventBus()
        self.pairing = PairingManager()
        self.chat: list[dict[str, Any]] = []
        self.actions: dict[str, ActionRecord] = {}
        self.progress = "Idle"
        self._last_state = ""
        self._active_action_id: str | None = None
        self._internet_status = False
        self._internet_checked_at = 0.0

    def snapshot(self) -> dict[str, Any]:
        ma2 = self.runtime.preferences["ma2"]
        mode = self.runtime.preferences.get("internet_access", "AUTO")
        if mode == "OFFLINE":
            online = False
        elif mode == "ONLINE":
            online = True
        else:
            if monotonic() - self._internet_checked_at > 5:
                self._internet_status = internet_online()
                self._internet_checked_at = monotonic()
            online = self._internet_status
        return {
            "connection": {"state": self.runtime.state.value, "ready": self.runtime.ready, "status": self.runtime.status_text(), "host": ma2["host"], "port": ma2["port"], "user": self.runtime.client.authenticated_user if self.runtime.client else None},
            "internet": "ONLINE" if online else "OFFLINE",
            "phone_connected": self.pairing.connected_count,
            "progress": self.progress,
            "chat": list(self.chat[-40:]),
            "actions": [{"id": item.id, "status": item.status, "result": item.result, **item.plan} for item in self.actions.values()],
            "state_browser": {name: "Not available yet" for name in ("Groups", "Fixtures", "Presets", "Sequences", "Cues", "Executors", "Effects", "Layouts", "Timecode", "Programmer", "Selection")},
        }

    def tick(self) -> None:
        self.runtime.poll_connection()
        state = self.runtime.status_text()
        if state != self._last_state:
            self._last_state = state
            self.events.emit("connection", self.snapshot())

    def connect(self, host: str, port: object, username: str, password: str = "") -> str:
        response = self.runtime.connect(host, port, username, password)
        self.events.emit("connection", self.snapshot())
        return response

    def disconnect(self) -> None:
        self.runtime.disconnect()
        self.events.emit("connection", self.snapshot())

    def set_internet_access(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"AUTO", "OFFLINE", "ONLINE"}:
            raise ValueError("Internet access must be AUTO, OFFLINE, or ONLINE.")
        self.runtime.preferences["internet_access"] = mode
        save_preferences(self.runtime.preferences, self.runtime.root)
        self.events.emit("internet", self.snapshot())

    def submit_request(self, text: str, source: str = "desktop") -> dict[str, Any]:
        self.chat.append({"role": "user", "source": source, "text": text})
        self.progress = "Understanding request"
        self.events.emit("progress", {"stage": self.progress})
        try:
            plan = self.runtime.preview(text)
        except ParseError:
            response = "I can currently plan supported selection, dimmer, sequence, fixture-range, and configured Blackout actions. MA2 state and plugin reasoning are scaffolded for the next skills."
            self.chat.append({"role": "assistant", "kind": "explanation", "text": response})
            self.progress = "Idle"
            self.events.emit("chat", self.snapshot())
            return {"message": response, "action": None}
        action_id = uuid.uuid4().hex[:12]
        if self._active_action_id:
            previous = self.actions.get(self._active_action_id)
            if previous and previous.status == "PENDING_APPROVAL":
                previous.status = "CANCELLED"
        record = ActionRecord(action_id, plan.as_dict())
        self.actions[action_id] = record
        self._active_action_id = action_id
        response = "Action plan ready for review." if plan.executable else plan.preview_note
        self.chat.append({"role": "assistant", "kind": "plan", "text": response, "action_id": action_id})
        self.progress = "Waiting for approval"
        self.events.emit("plan", self.snapshot())
        return {"message": response, "action": {"id": action_id, "status": record.status, **record.plan}}

    def cancel_action(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            return False
        action.status = "CANCELLED"
        if self._active_action_id == action_id:
            self._active_action_id = None
        self.progress = "Idle"
        self.events.emit("plan", self.snapshot())
        return True

    def approve_action(self, action_id: str, *, danger_confirmed: bool = False) -> dict[str, Any]:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            raise ValueError("Action is not awaiting approval.")
        if action_id != self._active_action_id:
            raise ValueError("This preview is no longer the active action.")
        if not self.runtime.ready:
            raise PermissionError("MA2 must be READY before an approved action can execute.")
        if action.plan["safety"] == "DANGEROUS" and not danger_confirmed:
            raise PermissionError("Dangerous actions require a second confirmation.")
        action.status = "APPROVED"
        self.progress = "Executing"
        self.events.emit("progress", {"stage": self.progress})
        try:
            result = self.runtime.execute_current()
            action.status, action.result = "EXECUTED", result or "Command sent"
            self._active_action_id = None
            self.chat.append({"role": "assistant", "kind": "result", "text": action.result, "action_id": action_id})
            self.progress = "Verifying"
        except Exception as exc:
            action.status, action.result = "FAILED", str(exc)
            self._active_action_id = None
            self.progress = "Idle"
            self.events.emit("error", {"message": str(exc)})
            raise
        self.events.emit("execution", self.snapshot())
        return {"id": action.id, "status": action.status, "result": action.result}

    def phone_urls(self, port: int) -> list[str]:
        return [f"http://{address}:{port}/?nonce={self.pairing.nonce}" for address in lan_ipv4_addresses()]
