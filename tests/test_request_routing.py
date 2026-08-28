import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class RoutingClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.executed = []

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.executed.append(command)
        if command == "List Group":
            return 'Group 1 "BEAM"\r\nGroup 2 "WASH"\r\n'
        return "sent: " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class RequestRoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-router-")
        self.root = Path(self.temp.name)
        self.source_root = Path(__file__).resolve().parents[1]
        copytree(self.source_root / "skills", self.root / "skills")
        self.core = AgentCore(AgentRuntime(self.root, client_factory=RoutingClient))

    def tearDown(self):
        self.temp.cleanup()

    def ready(self):
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def test_clone_phrases_normalize_to_one_not_implemented_capability(self):
        expected = {"group_clone", 1, 2, "group.clone"}
        for request in ("複製群組1變2", "複製 Group 1 到 2", "Clone Group 1 to Group 2"):
            response = self.core.handle_request(request)
            self.assertEqual(response["type"], "NOT_IMPLEMENTED")
            self.assertNotIn("Unsupported MVP", response["message"])
            self.assertEqual({response["intent"].kind, response["intent"].parameters["source_group"], response["intent"].parameters["destination_group"], response["capability"]}, expected)

    def test_group_query_automatically_reads_state(self):
        self.ready()
        response = self.core.handle_request("現在有哪些 Group")
        self.assertEqual(response["type"], "ANSWER")
        self.assertIn("1: BEAM", response["message"])
        self.assertEqual(self.core.runtime.client.executed, ["List Group"])

    def test_existing_operations_remain_action_plans(self):
        for request, skill_id in (("選 Group HYBRID", "group.select"), ("Beam 亮 30%", "dimmer.set"), ("Go Sequence 5", "sequence.go"), ("選 Fixture 1 到 10", "fixture.select")):
            response = self.core.handle_request(request)
            self.assertEqual(response["type"], "ACTION_PLAN")
            self.assertEqual(response["action"]["task"]["skill_id"], skill_id)

    def test_vague_request_needs_clarification_not_mvp_command_list(self):
        response = self.core.handle_request("幫我整理一下")
        self.assertEqual(response["type"], "NEEDS_CLARIFICATION")
        self.assertNotIn("Unsupported MVP", response["message"])

    def test_desktop_and_mobile_use_same_handle_request_path(self):
        desktop = self.core.handle_request("複製群組1變2", source="desktop")
        client = TestClient(create_app(self.core, self.source_root))
        token = client.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        mobile = client.post("/api/chat", json={"text": "複製群組1變2"}, headers={"Authorization": "Bearer " + token}).json()
        self.assertEqual((desktop["type"], desktop["intent"].kind), (mobile["type"], mobile["intent"]["kind"]))
        self.assertEqual([item["source"] for item in self.core.chat if item["role"] == "user"], ["desktop", "mobile"])


if __name__ == "__main__":
    unittest.main()
