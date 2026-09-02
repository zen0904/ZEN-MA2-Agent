import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.parser import parse
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.group_membership import GroupMembershipProvider, GroupMembershipProviderError
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class CloneClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands = []
        self.fail_clone = False

    def connect(self, username, password=""):
        self.state = ConnectionState.READY
        self.authenticated_user = username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group":
            return 'Group 1 "HYBRID"\r\nGroup 2 "SPOT"\r\n'
        if command == "List Fixture":
            return 'Fixture 101 "Hybrid 1"\r\nFixture 102 "Hybrid 2"\r\nFixture 201 "Spot 1"\r\nFixture 202 "Spot 2"\r\n'
        if command.startswith("Clone Fixture") and self.fail_clone:
            return "Error: clone rejected"
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class MembershipProvider(GroupMembershipProvider):
    source = "test_export_xml"

    def __init__(self, memberships=None):
        self.memberships = memberships or {
            1: {"group_no": 1, "name": "HYBRID", "fixtures": [101, 102], "source": self.source},
            2: {"group_no": 2, "name": "SPOT", "fixtures": [201, 202], "source": self.source},
        }
        self.error = None

    def get_group_membership(self, runtime, group_no, settings):
        if self.error:
            raise GroupMembershipProviderError(self.error)
        result = dict(self.memberships[group_no])
        result.setdefault("members", [{"fix_id": fixture, "export_order": index} for index, fixture in enumerate(result["fixtures"])])
        return result


class GeometryCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-geometry-clone-")
        self.root = Path(self.temp.name)
        self.source_root = Path(__file__).resolve().parents[1]
        copytree(self.source_root / "skills", self.root / "skills")
        self.provider = MembershipProvider()
        self.runtime = AgentRuntime(self.root, client_factory=CloneClient)
        self.core = AgentCore(self.runtime, group_membership_provider=self.provider)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    @property
    def client(self):
        return self.runtime.client

    def _enable_skill(self):
        manifest_path = self.root / "skills" / "builtin" / "clone.geometry" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["enabled"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.core.skills.discover()

    def test_ordered_mapping_preview_is_real_state_only_and_disabled(self):
        response = self.core.handle_request("把 HYBRID Clone 到 SPOT")
        self.assertEqual(response["type"], "ACTION_PLAN")
        self.assertEqual(response["action"]["status"], "PREVIEW_ONLY")
        self.assertIsNone(response["action"]["id"])
        self.assertIn("101 → 201", response["message"])
        self.assertIn("102 → 202", response["message"])
        self.assertIn("Ordered 1:1", response["message"])
        self.assertIn("Approval required.", response["message"])
        self.assertIn("Disabled pending safe real-machine Clone write validation", response["message"])
        self.assertFalse(any(command.startswith("Clone ") for command in self.client.commands))
        self.assertFalse(self.core.actions)

    def test_natural_language_forms_bind_source_and_destination_without_commands(self):
        cases = {
            "把 HYBRID Clone 到 SPOT": ("HYBRID", "SPOT"),
            "Clone Group 1 到 Group 2": (1, 2),
            "用 Clone From 當來源，Clone To 當目標": ("Clone From", "Clone To"),
            "預覽 Group 1 → Group 2 Clone": (1, 2),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                intent = parse(text)
                self.assertIn(intent.kind, {"geometry_clone", "geometry_clone_mapping"})
                source = intent.parameters.get("source_group_number", intent.parameters.get("source_group_name"))
                destination = intent.parameters.get("destination_group_number", intent.parameters.get("destination_group_name"))
                self.assertEqual((source, destination), expected)

    def test_safe_mapping_query_uses_same_ordered_state(self):
        response = self.core.handle_request("HYBRID 跟 SPOT 的 Clone mapping 是什麼？")
        self.assertEqual(response["type"], "ANSWER")
        self.assertIn("Geometry Clone Mapping (SAFE)", response["message"])
        self.assertIn("101 → 201", response["message"])
        self.assertNotIn("Clone Fixture", response["message"])
        self.assertFalse(any(command.startswith("Clone ") for command in self.client.commands))

    def test_preview_limits_mapping_to_ten_pairs(self):
        self.provider.memberships[1]["fixtures"] = list(range(101, 113))
        self.provider.memberships[2]["fixtures"] = list(range(201, 213))
        response = self.core.handle_request("Clone Group 1 到 Group 2")
        self.assertIn("101 → 201", response["message"])
        self.assertIn("110 → 210", response["message"])
        self.assertNotIn("111 → 211", response["message"])
        self.assertIn("Showing first 10 of 12", response["message"])

    def test_count_mismatch_never_generates_commands(self):
        self.provider.memberships[2]["fixtures"] = [201]
        response = self.core.handle_request("Clone Group 1 到 Group 2")
        self.assertEqual(response["type"], "ACTION_PLAN")
        self.assertIn("Status: COUNT_MISMATCH", response["message"])
        self.assertIn("no MA2 Clone commands", response["message"])
        self.assertFalse(any(command.startswith("Clone ") for command in self.client.commands))

    def test_empty_group_duplicate_name_and_unavailable_membership_are_blocked(self):
        self.provider.memberships[1]["fixtures"] = []
        empty = self.core.handle_request("Clone Group 1 到 Group 2")
        self.assertEqual(empty["type"], "ERROR")
        self.assertIn("empty", empty["message"])
        self.provider.memberships[1]["fixtures"] = [101, 102]
        self.client.commands.clear()
        self.client.execute = lambda command: 'Group 1 "HYBRID"\r\nGroup 2 "HYBRID"\r\n' if command == "List Group" else "Executing"
        duplicate = self.core.handle_request("把 HYBRID Clone 到 SPOT")
        self.assertEqual(duplicate["type"], "NEEDS_CLARIFICATION")
        self.assertIn("Multiple Groups", duplicate["message"])
        self.client.execute = CloneClient.execute.__get__(self.client, CloneClient)
        self.provider.error = "EXPORT_FILE_TIMEOUT"
        unavailable = self.core.handle_request("Clone Group 1 到 Group 2")
        self.assertEqual(unavailable["type"], "ERROR")
        self.assertIn("Group Membership state is not fresh", unavailable["message"])

    def test_enabled_skill_requires_approval_and_fingerprint_blocks_state_change(self):
        self._enable_skill()
        action = self.core.handle_request("Clone Group 1 到 Group 2")["action"]
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual(self.client.commands, ["List Group"])
        self.provider.memberships[2]["fixtures"] = [202, 201]
        with self.assertRaisesRegex(ValueError, "STATE_CHANGED_SINCE_PREVIEW"):
            self.core.approve_action(action["id"])
        self.assertFalse(any(command.startswith("Clone ") for command in self.client.commands))

    def test_enabled_skill_executes_pairwise_and_reports_partial_verification(self):
        self._enable_skill()
        action = self.core.handle_request("Clone Group 1 到 Group 2")["action"]
        result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual([command for command in self.client.commands if command.startswith("Clone ")], [
            "Clone Fixture 101 At Fixture 201 /nc", "Clone Fixture 102 At Fixture 202 /nc",
        ])
        self.assertIn("Verification: PARTIAL", result["result"])
        self.assertIn("Internal cloned fixture data", result["result"])
        self.assertIn("Rollback: Not automatically available", action["rollback_strategy"])

    def test_desktop_and_mobile_route_to_the_same_preview_path(self):
        desktop = self.core.handle_request("Clone Group 1 to Group 2", source="desktop")
        app = TestClient(create_app(self.core, self.source_root))
        token = app.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        mobile = app.post("/api/chat", json={"text": "Clone Group 1 to Group 2"}, headers={"Authorization": "Bearer " + token}).json()
        self.assertEqual((desktop["type"], desktop["action"]["status"]), ("ACTION_PLAN", "PREVIEW_ONLY"))
        self.assertEqual((mobile["type"], mobile["action"]["status"]), ("ACTION_PLAN", "PREVIEW_ONLY"))

    def test_operator_cannot_enable_clone_before_safe_real_target_exists(self):
        with self.assertRaisesRegex(ValueError, "safe real-MA2 write target"):
            self.core.set_skill_enabled("clone.geometry", True)


if __name__ == "__main__":
    unittest.main()
