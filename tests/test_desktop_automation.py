import json
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from shutil import copytree
from types import SimpleNamespace

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.desktop import ZenDesktop
from zen_ma2_agent.desktop_automation import DesktopAutomationBridge, automation_enabled, automation_port
from zen_ma2_agent.effect_resources import EffectRequirement, show_identity
from zen_ma2_agent.cue_effect_application import CueEffectApplicationCapability, CueEffectApplicationSpec
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class AutomationClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands = []

    def connect(self, username, password=""):
        self.state = ConnectionState.READY
        self.authenticated_user = username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group":
            return 'Group 1 "HYBRID"\n'
        if command == "List Effect":
            return 'Effect 1 Base\nEffect 3520 "ZEN_FX_DIM_CHASE_SLOW_GROUP1"\n'
        if command == "List Effect 3520":
            return 'Effect 3520 "ZEN_FX_DIM_CHASE_SLOW_GROUP1"\n'
        if command == "List Fixture":
            return 'Fixture 101 "Hybrid 1" (Hybrid)\n'
        if command == "List Preset All":
            return "Focus 6.2 6.2  normal     Normal\n"
        if command == "List Sequence":
            return "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command == "List Timecode":
            return "Timecode 9000 9000 ZEN Test Offset: 0s (0)\n"
        return ""

    def close(self):
        self.state = ConnectionState.DISCONNECTED


def request(port, payload):
    with socket.create_connection(("127.0.0.1", port), timeout=25) as connection:
        connection.sendall(json.dumps(payload).encode("utf-8"))
        return json.loads(connection.recv(65536).decode("utf-8"))


class DesktopAutomationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-desktop-automation-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        copytree(Path(__file__).resolve().parents[1] / "examples", root / "examples")
        self.runtime = AgentRuntime(root, client_factory=AutomationClient)
        self.core = AgentCore(self.runtime)
        self.window = ZenDesktop(self.core, SimpleNamespace(port=8765))
        self.window.host.setText("127.0.0.1")
        self.window.port.setText("30000")
        self.window.user.setText("MM")
        self.bridge = DesktopAutomationBridge(self.window, port=0)
        self.port = self.bridge.start()

    def tearDown(self):
        self.bridge.stop()
        self.window.close()
        self.temp.cleanup()

    def bridge_request(self, payload):
        result = []
        worker = threading.Thread(target=lambda: result.append(request(self.port, payload)), daemon=True)
        worker.start()
        timer = QTimer()
        deadline = time.monotonic() + 10
        def finish_when_ready():
            if not worker.is_alive() or time.monotonic() >= deadline:
                timer.stop()
                self.app.quit()
        timer.timeout.connect(finish_when_ready)
        timer.start(5)
        self.app.exec()
        worker.join(timeout=1)
        self.assertTrue(result, "automation response was not delivered")
        return result[0]

    def test_disabled_by_default_and_localhost_only(self):
        self.assertFalse(automation_enabled([], {}))
        self.assertTrue(automation_enabled(["--automation-test"], {}))
        self.assertTrue(automation_enabled([], {"ZEN_MA2_AUTOMATION": "1"}))
        self.assertEqual(automation_port({"ZEN_MA2_AUTOMATION_PORT": "0"}), 0)
        self.assertEqual(self.bridge._server._socket.getsockname()[0], "127.0.0.1")

    def test_fixed_actions_hide_password_and_reject_raw_send(self):
        status = self.bridge_request({"action": "status"})
        self.assertTrue(status["ok"])
        self.assertNotIn("password", json.dumps(status).casefold())
        rejected = self.bridge_request({"action": "raw_send", "text": "Store Group 1"})
        self.assertFalse(rejected["ok"])

    def test_connect_and_submit_use_real_desktop_handlers(self):
        gui_thread_id = threading.get_ident()
        connected = self.bridge_request({"action": "connect"})
        self.assertEqual((connected["ok"], connected["handler"], connected["connection_state"]), (True, "ZenDesktop.connect", "READY"))
        self.assertEqual(self.bridge._last_dispatch_thread_id, gui_thread_id)
        submitted = self.bridge_request({"action": "submit", "text": "檢查 Show"})
        self.assertEqual((submitted["ok"], submitted["handler"]), (True, "ZenDesktop.submit"))
        self.assertEqual(self.bridge._last_dispatch_thread_id, gui_thread_id)
        transcript = self.bridge_request({"action": "chat_text"})["chat_text"]
        self.assertIn("Show Diagnostics", transcript)
        self.assertEqual(self.core.last_chat_routing["ROUTER_INTENT"], "diagnose_show")

    def test_execute_pending_is_fixed_desktop_handler_not_raw_transport(self):
        self.bridge_request({"action": "connect"})
        self.bridge_request({"action": "submit", "text": "Beam 亮 30%"})
        executed = self.bridge_request({"action": "execute_pending"})
        self.assertEqual((executed["ok"], executed["handler"], executed["pending"]), (True, "ZenDesktop.execute_action", False))
        self.assertEqual(self.runtime.client.commands, ['Group "BEAM"; At 30'])

    def test_fixed_real_song_preview_uses_desktop_core_and_accepts_no_raw_payload(self):
        self.bridge_request({"action": "connect"})
        for resource, kwargs in (("groups", {}), ("fixtures", {}), ("presets", {"sequence": "ALL"}), ("effects", {}), ("sequences", {})):
            self.core.refresh_state(resource, **kwargs)
        profile = self.core.scan_show_profile()
        requirement = EffectRequirement.from_dict({
            "feature": "DIMMER", "family": "CHASE", "waveform": "PWM", "low": 0, "high": 100,
            "speed_class": "SLOW", "speed_bpm": 30, "phase": "0..360", "direction": "forward", "groups": 1,
            "target_type": "group", "target_ref": 1, "target_name": "HYBRID",
        })
        self.core.effect_catalog.record(requirement=requirement, effect_id=3520, label="ZEN_FX_DIM_CHASE_SLOW_GROUP1", identity=show_identity(profile), verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"})
        CueEffectApplicationCapability(self.runtime.root).record(CueEffectApplicationSpec(3520, "ZEN_FX_DIM_CHASE_SLOW_GROUP1", 1, "HYBRID", 299, "ZEN_AI_EFFECT_CALL_TEST_299"))
        preview = self.bridge_request({"action": "preview_real_song"})
        self.assertTrue(preview["ok"], preview)
        self.assertEqual((preview["ok"], preview["handler"]), (True, "ZenDesktop.preview_real_song_test"))
        rejected = self.bridge_request({"action": "preview_real_song", "text": "Store Cue 1"})
        self.assertFalse(rejected["ok"])
        transcript = self.bridge_request({"action": "chat_text"})["chat_text"]
        self.assertIn("ZEN AI REAL SONG BUILD PREVIEW", transcript)
        self.assertNotIn("Store Cue", self.runtime.client.commands)

    def test_packaged_desktop_path_previews_effect_builder_before_any_modify(self):
        self.bridge_request({"action": "connect"})
        self.bridge_request({"action": "submit", "text": "幫 HYBRID 做 Dimmer Chase"})
        transcript = self.bridge_request({"action": "chat_text"})["chat_text"]
        self.assertIn("Effect Builder Preview", transcript)
        self.assertIn("Approval required.", transcript)
        self.assertEqual(self.runtime.client.commands, ["List Group", "List Effect"])

    def test_packaged_desktop_path_previews_timecode_offset_before_any_modify(self):
        self.bridge_request({"action": "connect"})
        self.bridge_request({"action": "submit", "text": "Timecode 9000 往後 500ms"})
        transcript = self.bridge_request({"action": "chat_text"})["chat_text"]
        self.assertIn("Timecode Offset Preview", transcript)
        self.assertIn("Approval required.", transcript)
        self.assertEqual(self.runtime.client.commands, ["List Timecode"])

    def test_shutdown_is_fixed_action(self):
        # Dispatch is queued to the GUI thread and returns before close executes.
        result = self.bridge_request({"action": "shutdown"})
        self.assertEqual(result, {"ok": True, "shutdown": True})


if __name__ == "__main__":
    unittest.main()
