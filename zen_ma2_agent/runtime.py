from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .config import load_preferences, save_preferences, validate_ma2_settings
from .models import CommandPlan
from .parser import parse
from .portable import app_root, ensure_runtime_dirs
from .safety import build_plan
from .telnet_client import ConnectionState, MA2TelnetClient


class AgentRuntime:
    def __init__(self, root: Path | None = None, client_factory: Callable[..., MA2TelnetClient] = MA2TelnetClient):
        self.root = root or app_root()
        self.preferences = load_preferences(self.root)
        self.client_factory = client_factory
        self.client: MA2TelnetClient | None = None
        self.current_plan: CommandPlan | None = None
        self.reconnect_required = False
        self._audit_cursor = 0

    @property
    def state(self) -> ConnectionState:
        return self.client.state if self.client else ConnectionState.DISCONNECTED

    @property
    def ready(self) -> bool:
        return self.state is ConnectionState.READY and not self.reconnect_required

    def update_connection_settings(self, host: str, port: object, username: str) -> dict:
        ma2 = validate_ma2_settings(host, port, username)
        previous = self.preferences["ma2"]
        if self.state is not ConnectionState.DISCONNECTED and ma2 != previous:
            self.reconnect_required = True
        self.preferences = {**self.preferences, "ma2": ma2}
        save_preferences(self.preferences, self.root)
        return ma2

    def preview(self, text: str) -> CommandPlan:
        self.current_plan = build_plan(parse(text), self.preferences)
        self.log("preview", self.current_plan.as_dict())
        return self.current_plan

    def connect(self, host: str, port: object, username: str, password: str = "") -> str:
        if self.state is not ConnectionState.DISCONNECTED:
            raise ConnectionError("Already connected. Disconnect before connecting again.")
        ma2 = self.update_connection_settings(host, port, username)
        ma2 = validate_ma2_settings(**ma2, require_username=True)
        self.client = self.client_factory(ma2["host"], ma2["port"], float(self.preferences["read_timeout_seconds"]))
        try:
            response = self.client.connect(ma2["username"], password)
        except Exception:
            self.client = None
            raise
        self.reconnect_required = False
        self._audit_cursor = 0
        self._flush_audit()
        self.log("connect", {"host": ma2["host"], "port": ma2["port"], "requested_username": ma2["username"], "state": self.state.value})
        return response

    def poll_connection(self) -> ConnectionState:
        if self.client and self.state is ConnectionState.AUTHENTICATING:
            self.client.poll_authentication()
            self._flush_audit()
            if self.state is ConnectionState.AUTH_FAILED:
                self.log("auth_failed", {"requested_username": self.client.requested_username, "current_user": self.client.current_session_user})
        return self.state

    def disconnect(self) -> None:
        if self.client:
            self.client.close()
        self.client = None
        self.current_plan = None
        self.reconnect_required = False
        self._audit_cursor = 0
        self.log("disconnect", {})

    def execute_current(self) -> str:
        if not self.ready or not self.client:
            raise ConnectionError("Connect and reach MA2 READY before executing.")
        if not self.current_plan or not self.current_plan.executable or not self.current_plan.command:
            raise ValueError("No executable approved preview is available.")
        response = self.client.execute(self.current_plan.command)
        self.log("execute", {"plan": self.current_plan.as_dict(), "response": response})
        return response

    def read_state(self, command: str) -> str:
        """Core-owned read-only transport entrypoint for generic state providers."""
        if not self.ready or not self.client:
            raise ConnectionError("Connect and reach MA2 READY before reading show state.")
        if not re.fullmatch(r'(?:List (?:Group|Fixture|Layout|Sequence|Cue)(?: \d+)?|Plugin (?:"ZEN_AGENT"|\d+) "[a-z_]+(?: \d+)?")', command, re.I):
            raise PermissionError("State transport only accepts allow-listed read-only List commands or ZEN_AGENT adapter reads.")
        response = self.client.execute(command)
        self.log("state_read", {"command": command, "response": response})
        return response

    def execute_approved_commands(self, commands: tuple[str, ...]) -> list[str]:
        """Only AgentCore calls this after approval; Skills never receive the client."""
        if not self.ready or not self.client:
            raise ConnectionError("Connect and reach MA2 READY before executing.")
        if not commands:
            raise ValueError("Approved workflow has no MA2 commands.")
        responses: list[str] = []
        for command in commands:
            responses.append(self.client.execute(command))
        self.log("workflow_execute", {"commands": list(commands), "responses": responses})
        return responses

    def status_text(self) -> str:
        if self.reconnect_required:
            return "Settings changed — reconnect required"
        if self.state is ConnectionState.AUTHENTICATING and self.client:
            current = f"\nCurrent session: {self.client.current_session_user}" if self.client.current_session_user else ""
            return f"MA2: AUTHENTICATING{current}\nTarget user: {self.client.requested_username}"
        if self.state is ConnectionState.AUTH_FAILED and self.client:
            return f"MA2: AUTH FAILED\nRequested user: {self.client.requested_username}\nCurrent user: {self.client.current_session_user or 'unknown'}"
        if self.state is ConnectionState.READY and self.client:
            ma2 = self.preferences["ma2"]
            return f"MA2: READY — {self.client.authenticated_user}\nHost: {ma2['host']}:{ma2['port']}\nUser: {self.client.authenticated_user}"
        return f"MA2: {self.state.value}"

    def _flush_audit(self) -> None:
        if not self.client:
            return
        entries = getattr(self.client, "audit_entries", [])
        for entry in entries[self._audit_cursor:]:
            self.log("telnet_audit", {"message": entry})
        self._audit_cursor = len(entries)

    def log(self, event: str, data: dict) -> None:
        _, logs = ensure_runtime_dirs(self.root)
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "data": data}
        with (logs / "agent.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
