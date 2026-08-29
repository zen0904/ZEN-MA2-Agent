from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
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
        self._state_adapter_lock = threading.Lock()
        self._export_state_lock = threading.Lock()

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
        if not re.fullmatch(r'List (?:Group|Fixture|Layout|Sequence|Cue)(?: \d+)?', command, re.I):
            raise PermissionError("State transport only accepts allow-listed read-only List commands.")
        response = self.client.execute(command)
        self.log("state_read", {"command": command, "response": response})
        return response

    def export_group_file(self, group_no: int, filename: str) -> str:
        """Run the one allow-listed, read-only-state filesystem export command."""
        if not self.ready or not self.client:
            raise ConnectionError("Connect and reach MA2 READY before exporting show state.")
        if isinstance(group_no, bool) or not isinstance(group_no, int) or group_no < 1:
            raise ValueError("Export Group requires a positive group number.")
        if not re.fullmatch(r"ZEN_AGENT_G[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml", filename):
            raise PermissionError("Export state only permits Agent-owned temporary XML filenames.")
        command = f'Export Group {group_no} "{filename}" /nc'
        with self._export_state_lock:
            response = self.client.execute(command)
        self.log("state_export", {"command": command, "group_no": group_no, "filename": filename})
        return response

    @staticmethod
    def user_var_command(value: str) -> str:
        """Build a single safe SetUserVar command without allowing a new MA line."""
        if "\r" in value or "\n" in value:
            raise ValueError("ZEN_AGENT request cannot contain a newline.")
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'SetUserVar $ZEN_AGENT_REQUEST="{escaped}"'

    def read_adapter_state(self, *, plugin_slot: int, request: str, timeout_seconds: float) -> str:
        """Serialize the two-command, read-only ZEN_AGENT UserVar mailbox."""
        if not self.ready or not self.client:
            raise ConnectionError("Connect and reach MA2 READY before reading show state.")
        if isinstance(plugin_slot, bool) or not isinstance(plugin_slot, int) or not 2 <= plugin_slot <= 9999:
            raise ValueError("ZEN_AGENT Plugin slot must be a configured number from 2 to 9999.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+ [a-z_]+(?: \d+)?", request):
            raise ValueError("Invalid ZEN_AGENT mailbox request.")
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("ZEN_AGENT timeout must be numeric.") from exc
        if timeout <= 0:
            raise ValueError("ZEN_AGENT timeout must be positive.")
        if not self._state_adapter_lock.acquire(timeout=timeout):
            raise TimeoutError("Timed out waiting for the ZEN_AGENT state mailbox.")
        request_id = request.split(" ", 1)[0]
        set_command = self.user_var_command(request)
        plugin_command = f"Plugin {plugin_slot}"
        started = monotonic()
        try:
            self.client.execute(set_command)
            response = self.client.execute(plugin_command)
            if monotonic() - started > timeout:
                raise TimeoutError(f"Timed out waiting for ZEN_AGENT request {request_id}.")
        except Exception:
            # If Plugin could not start, clear the mailbox before releasing the
            # serialization lock so a future request cannot consume stale data.
            try:
                self.client.execute(self.user_var_command(""))
            except Exception:
                pass
            raise
        finally:
            self._state_adapter_lock.release()
        self.log("state_adapter_read", {"request_id": request_id, "set_command": set_command, "plugin_command": plugin_command, "response": response})
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
