import sys
import json
import re
import tempfile
from types import SimpleNamespace
from pathlib import Path
from shutil import copytree

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.desktop import ZenDesktop, run_desktop
from zen_ma2_agent.desktop_automation import automation_enabled, automation_port
from zen_ma2_agent.web_server import MobileServer
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class _PortableSmokeClient:
    """Read-only stand-in used only by the frozen UI routing smoke command."""

    export_directory: Path | None = None

    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries: list[str] = []
        self.commands: list[str] = []
        self.effect_label = ""
        self.timecode_offset = "0s"

    def connect(self, username: str, password: str = "") -> str:
        self.state, self.authenticated_user = ConnectionState.READY, username
        return f"Logged in as User '{username}'"

    def execute(self, command: str) -> str:
        self.commands.append(command)
        match = re.fullmatch(r'Export Layout (\d+) "(ZEN_AGENT_LAYOUT_\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if match:
            assert self.export_directory is not None
            layout_no, filename = match.groups()
            (self.export_directory / filename).write_text(
                f'<MA><Group index="{int(layout_no) - 1}" name=""><LayoutData><CObjects /></LayoutData></Group></MA>',
                encoding="utf-8",
            )
            return "exported"
        if command == "List Group":
            return 'Group 1 "HYBRID"\n'
        if command == "List Effect":
            return "Effect 1 Base\n"
        if command == "List Effect 2500":
            return f'Effect 2500 "{self.effect_label}"\n' if self.effect_label else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command == "List Timecode":
            return f"Timecode 9000 9000  ZEN Timecode Test Offset: {self.timecode_offset} (0)\n"
        if command.startswith("Label Effect 2500 "):
            self.effect_label = command.split('"', 2)[1]
        if command.startswith("Assign Timecode 9000/Offset = "):
            self.timecode_offset = command.rsplit("= ", 1)[1]
        if command in {"List Fixture", "List Layout", "List Preset All", "List Preset Position", "List Sequence", "List Page", "List Executor"}:
            return ""
        return "Executing : " + command

    def close(self) -> None:
        self.state = ConnectionState.DISCONNECTED


def _portable_smoke_core() -> tuple[AgentCore, tempfile.TemporaryDirectory[str]]:
    temporary = tempfile.TemporaryDirectory(prefix="zen-portable-ui-smoke-")
    root = Path(temporary.name)
    copytree(Path(sys.executable).resolve().parent / "skills", root / "skills")
    export_directory = root / "importexport"
    export_directory.mkdir()
    _PortableSmokeClient.export_directory = export_directory
    runtime = AgentRuntime(root, client_factory=_PortableSmokeClient)
    runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(export_directory)}
    core = AgentCore(runtime)
    core.connect("127.0.0.1", 30000, "SMOKE", "")
    return core, temporary


def main() -> int:
    core = AgentCore()
    if "--build-identity" in sys.argv:
        print(json.dumps(core.build_identity, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    smoke_mode = "--portable-routing-smoke" in sys.argv
    effect_approval_smoke = "--portable-effect-approval-smoke" in sys.argv
    timecode_approval_smoke = "--portable-timecode-approval-smoke" in sys.argv
    if "--ui-smoke-request" in sys.argv or smoke_mode or effect_approval_smoke or timecode_approval_smoke:
        option = "--portable-effect-approval-smoke" if effect_approval_smoke else "--portable-timecode-approval-smoke" if timecode_approval_smoke else "--portable-routing-smoke" if smoke_mode else "--ui-smoke-request"
        index = sys.argv.index(option)
        if index + 1 >= len(sys.argv):
            raise SystemExit(f"{option} requires text")
        smoke_temporary = None
        if smoke_mode or effect_approval_smoke or timecode_approval_smoke:
            core, smoke_temporary = _portable_smoke_core()
        app = QApplication.instance() or QApplication([])
        window = ZenDesktop(core, SimpleNamespace(port=8765))
        window.request.setText(sys.argv[index + 1])
        window.submit()
        print(window.chat.toPlainText(), flush=True)
        if smoke_mode:
            response = core.chat[-1]
            print(json.dumps({"routing": core.last_chat_routing, "response": response}, ensure_ascii=False), flush=True)
        if effect_approval_smoke:
            pending = next((item for item in core.actions.values() if item.status == "PENDING_APPROVAL"), None)
            if not pending:
                raise SystemExit("Portable effect approval smoke did not produce a pending ActionPlan.")
            before = list(core.runtime.client.commands)
            window.execute_action()
            print(json.dumps({"before": before, "action_status": pending.status, "result": pending.result, "commands": core.runtime.client.commands}, ensure_ascii=False), flush=True)
        if timecode_approval_smoke:
            pending = next((item for item in core.actions.values() if item.status == "PENDING_APPROVAL"), None)
            if not pending:
                raise SystemExit("Portable Timecode approval smoke did not produce a pending ActionPlan.")
            before = list(core.runtime.client.commands)
            window.execute_action()
            print(json.dumps({"before": before, "action_status": pending.status, "result": pending.result, "commands": core.runtime.client.commands}, ensure_ascii=False), flush=True)
        window.close()
        QTimer.singleShot(0, app.quit)
        app.exec()
        if smoke_temporary:
            smoke_temporary.cleanup()
        return 0
    mobile = core.runtime.preferences.get("mobile", {})
    server = MobileServer(core, int(mobile.get("port", 8765)))
    if mobile.get("enabled", True):
        server.start()
    try:
        return run_desktop(core, server, automation_port=automation_port() if automation_enabled(sys.argv) else None)
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
