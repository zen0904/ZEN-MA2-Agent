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

    def test_shutdown_is_fixed_action(self):
        # Dispatch is queued to the GUI thread and returns before close executes.
        result = self.bridge_request({"action": "shutdown"})
        self.assertEqual(result, {"ok": True, "shutdown": True})


if __name__ == "__main__":
    unittest.main()
