from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import load_preferences
from .models import CommandPlan
from .parser import parse
from .portable import app_root, ensure_runtime_dirs
from .safety import build_plan
from .telnet_client import MA2TelnetClient


class AgentRuntime:
    def __init__(self, root: Path | None = None):
        self.root = root or app_root()
        self.preferences = load_preferences(self.root)
        self.client = MA2TelnetClient(self.preferences["host"], int(self.preferences["port"]), float(self.preferences["read_timeout_seconds"]))
        self.current_plan: CommandPlan | None = None

    def preview(self, text: str) -> CommandPlan:
        self.current_plan = build_plan(parse(text), self.preferences)
        self.log("preview", self.current_plan.as_dict())
        return self.current_plan

    def connect(self) -> str:
        banner = self.client.connect(str(self.preferences.get("login_command") or ""))
        self.log("connect", {"host": self.client.host, "port": self.client.port, "banner": banner})
        return banner

    def execute_current(self) -> str:
        if not self.current_plan or not self.current_plan.executable or not self.current_plan.command:
            raise ValueError("No executable approved preview is available.")
        response = self.client.execute(self.current_plan.command)
        self.log("execute", {"plan": self.current_plan.as_dict(), "response": response})
        return response

    def log(self, event: str, data: dict) -> None:
        _, logs = ensure_runtime_dirs(self.root)
        record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "data": data}
        with (logs / "agent.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
