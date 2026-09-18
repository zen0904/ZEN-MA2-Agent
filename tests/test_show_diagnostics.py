import re
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.diagnostics import ShowDiagnostics
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.store import StateStore
from zen_ma2_agent.telnet_client import ConnectionState


class DiagnosticsClient:
    export_directory: Path | None = None
    mode = "clean"

    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.executed: list[str] = []

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.executed.append(command)
        if self.mode == "provider_error" and command == "List Effect":
            raise ConnectionError("EFFECT_TIMEOUT")
        if command == "List Group":
            return 'Group 1 "BEAM"\nGroup 2 "BEAM"\n' if self.mode == "warning" else ""
        if command == "List Fixture":
            return 'Fixture 101 "Hybrid"\n' if self.mode != "warning" else 'Fixture 101 "Hybrid"\nFixture 102 ""\n'
        if command == "List Layout":
            return 'Layout 1 "Main"\n'
        if command == "List Preset All":
            return ""
        if command == "List Effect":
            return "\n".join(f"{number} {number}" for number in range(1000, 2780))
        if command == "List Sequence":
            return 'Sequence 12 "Empty"\n' if self.mode == "warning" else ""
        if command == "List Page" or command == "List Executor":
            return ""
        match = re.fullmatch(r'List Cue (\d+)', command)
        if match:
            return ""
        match = re.fullmatch(r'Export Group (\d+) "(ZEN_AGENT_G\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if match:
            number, filename = match.groups()
            fixtures = "" if number == "1" else '<Subfixture fix_id="101" />'
            assert self.export_directory is not None
            (self.export_directory / filename).write_text(f'<MA><Group index="{int(number)-1}" name="BEAM"><Subfixtures>{fixtures}</Subfixtures></Group></MA>', encoding="utf-8")
            return "exported"
        match = re.fullmatch(r'Export Layout (\d+) "(ZEN_AGENT_LAYOUT_\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if match:
            number, filename = match.groups()
            content = '<LayoutCObject center_x="0" center_y="0"><CObject><Token>99</Token><Token>1</Token></CObject></LayoutCObject>' if self.mode == "warning" else ""
            assert self.export_directory is not None
            (self.export_directory / filename).write_text(f'<MA><Group index="{int(number)-1}" name="Main"><LayoutData><CObjects>{content}</CObjects></LayoutData></Group></MA>', encoding="utf-8")
            return "exported"
        raise AssertionError(command)

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class ShowDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-diagnostics-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        export = root / "importexport"; export.mkdir()
        DiagnosticsClient.export_directory = export
        DiagnosticsClient.mode = "clean"
        self.runtime = AgentRuntime(root, client_factory=DiagnosticsClient)
        self.runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(export)}
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    def test_clean_show_is_ok_and_safe_skill_requires_no_approval(self):
        response = self.core.handle_request("檢查 Show")
        self.assertEqual(response["type"], "ANSWER")
        self.assertIn("Show Diagnostics\n\nStatus: OK", response["message"])
        self.assertIn("Layout fixture geometry: Unsupported", response["message"])
        self.assertFalse(self.core.actions)
        skill = self.core.skills.get("diagnostics.show")
        self.assertEqual((skill.enabled, skill.safety, skill.version), (True, "SAFE", "1.0"))
        forbidden = ("Store", "Assign", "Delete", "Move", "Go", "Off", "Fixture ")
        self.assertFalse(any(command.startswith(forbidden) for command in self.runtime.client.executed))

    def test_warning_findings_are_aggregated_and_details_filter(self):
        DiagnosticsClient.mode = "warning"
        summary = self.core.handle_request("幫我檢查目前 Show")
        self.assertIn("Status: WARNING", summary["message"])
        self.assertIn('Group 1 "BEAM" is empty.', summary["message"])
        self.assertIn("Layout 1 contains 1 unresolved CObjects.", summary["message"])
        self.assertIn("1780 Effects are unlabeled.", self.core.handle_request("顯示詳細診斷")["message"])
        warnings = self.core.handle_request("只看 Warning")
        self.assertIn("[WARNING]", warnings["message"])
        self.assertNotIn("[INFO]", warnings["message"])
        layout = self.core.handle_request("Layout 有什麼問題")
        self.assertIn("Layout 1 contains 1 unresolved CObjects.", layout["message"])

    def test_empty_preset_and_large_effect_pool_are_not_warnings(self):
        report = self.core.run_show_diagnostics()
        self.assertEqual(report.status, "OK")
        self.assertNotIn("preset.unlabeled", {item.id for item in report.findings})
        self.assertEqual(sum(item.id == "effect.unlabeled" for item in report.findings), 1)
        self.assertEqual(next(item.summary for item in report.findings if item.id == "effect.unlabeled"), "1780 Effects are unlabeled.")

    def test_provider_error_and_stale_state_do_not_crash(self):
        DiagnosticsClient.mode = "provider_error"
        report = self.core.run_show_diagnostics()
        self.assertEqual(report.status, "ERROR")
        self.assertIn("state.effects.error", {item.id for item in report.findings})
        state = StateStore(); state.put("groups", [], source="test"); state.mark_stale("groups", "test stale")
        stale = ShowDiagnostics().evaluate(state)
        self.assertIn("state.groups.stale", {item.id for item in stale.findings})

    def test_duplicate_group_and_fixture_rules(self):
        DiagnosticsClient.mode = "warning"
        report = self.core.run_show_diagnostics()
        ids = {item.id for item in report.findings}
        self.assertIn("group.duplicate_name", ids)
        self.assertIn("group.empty", ids)
        self.assertNotIn("fixture.duplicate_id", ids)


if __name__ == "__main__":
    unittest.main()
