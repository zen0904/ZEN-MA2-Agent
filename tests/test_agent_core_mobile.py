import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class ReadyClient:
    def __init__(self, host, port, timeout):
        self.host, self.port, self.timeout = host, port, timeout
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.executed = []

    def connect(self, username, password=""):
        self.authenticated_user = username
        self.state = ConnectionState.READY
        return f"Logged in as User '{username}'"

    def execute(self, command):
        self.executed.append(command)
        return f"sent: {command}"

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class AgentCoreMobileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-agent-core-")
        self.root = Path(self.temp.name)
        self.runtime = AgentRuntime(self.root, client_factory=ReadyClient)
        self.core = AgentCore(self.runtime)
        self.app_root = Path(__file__).resolve().parents[1]

    def tearDown(self):
        self.temp.cleanup()

    def ready(self):
        self.runtime.connect("127.0.0.1", 30000, "MM", "")

    def test_shared_state_event_and_approval_lifecycle(self):
        events = []
        unsubscribe = self.core.events.subscribe(events.append)
        self.ready()
        action = self.core.submit_request("Beam 亮 30%", source="desktop")["action"]
        self.assertEqual(action["safety"], "MODIFY")
        self.assertEqual(self.core.snapshot()["connection"]["state"], "READY")
        result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(self.runtime.client.executed, ['Group "BEAM"; At 30'])
        self.assertTrue(any(event["type"] == "plan" for event in events))
        unsubscribe()

    def test_disconnected_or_superseded_action_cannot_execute(self):
        first = self.core.submit_request("Beam 亮 30%")["action"]
        with self.assertRaises(PermissionError):
            self.core.approve_action(first["id"])
        self.ready()
        second = self.core.submit_request("Go Sequence 5")["action"]
        self.assertEqual(self.core.actions[first["id"]].status, "CANCELLED")
        with self.assertRaises(ValueError):
            self.core.approve_action(first["id"])
        self.core.approve_action(second["id"])

    def test_pairing_protects_api_ws_and_mobile_uses_core_approval(self):
        client = TestClient(create_app(self.core, self.app_root))
        self.assertEqual(client.get("/").status_code, 200)
        self.assertEqual(client.get("/api/state").status_code, 401)
        self.assertEqual(client.post("/api/pair", json={"code": "000000", "nonce": self.core.pairing.nonce}).status_code, 403)
        token = client.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(client.get("/api/state", headers=headers).status_code, 200)
        with client.websocket_connect(f"/ws?token={token}") as ws:
            self.assertEqual(ws.receive_json()["type"], "snapshot")
        self.ready()
        action = client.post("/api/chat", json={"text": "Beam 亮 30%"}, headers=headers).json()["action"]
        result = client.post(f"/api/actions/{action['id']}/approve", json={"danger_confirmed": False}, headers=headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["status"], "EXECUTED")

    def test_portable_web_pwa_assets_and_lan_qr_url(self):
        for name in ("index.html", "manifest.json", "sw.js", "app.js", "icon.svg"):
            self.assertTrue((self.app_root / "web" / name).is_file(), name)
        urls = self.core.phone_urls(8765)
        self.assertTrue(all("127.0.0.1" not in url for url in urls))
        self.assertTrue(all(f"nonce={self.core.pairing.nonce}" in url for url in urls))
        self.assertIn("onclose=()=>setTimeout(boot,1500)", (self.app_root / "web" / "app.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
