import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.skill_system import SkillError, SkillRegistry
from zen_ma2_agent.state.models import Group
from zen_ma2_agent.state.providers import FixtureProvider, FixtureTypeExportError, GroupProvider
from zen_ma2_agent.state.store import StateStore
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class StateClient:
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
            return 'Group 1 "BEAM"\r\n2 WASH\r\n'
        if command == "List Fixture":
            return 'Fixture 101 "Spot A" (Sharpy)\r\n102 Wash B\r\n'
        return "sent: " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class StateAndSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-state-skill-")
        self.root = Path(self.temp.name)
        self.source_root = Path(__file__).resolve().parents[1]
        copytree(self.source_root / "skills", self.root / "skills")
        self.runtime = AgentRuntime(self.root, client_factory=StateClient)
        self.core = AgentCore(self.runtime)

    def tearDown(self):
        self.temp.cleanup()

    def ready(self):
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def test_group_and_fixture_protocol_and_shared_state_cache(self):
        self.ready()
        groups = self.core.refresh_state("groups")
        fixtures = self.core.refresh_state("fixtures")
        self.assertEqual(groups["values"], [{"number": 1, "name": "BEAM"}, {"number": 2, "name": "WASH"}])
        self.assertEqual(fixtures["values"][0], {"number": 101, "name": "Spot A", "fixture_type": "Sharpy"})
        snapshot = self.core.snapshot()["state_browser"]
        self.assertEqual(snapshot["groups"]["count"], 2)
        self.assertEqual(snapshot["fixtures"]["count"], 2)
        self.assertEqual(self.runtime.client.executed[:2], ["List Group", "List Fixture"])

    def test_provider_parsers_only_accept_inventory_rows(self):
        self.assertEqual(GroupProvider().parse("List Group\nGroup 3 'HYBRID'\n"), [Group(3, "HYBRID")])
        self.assertEqual(GroupProvider().parse("No. Name\nGroup  1 1    HYBRID\nGroup 10 10   Clone To\n"), [Group(1, "HYBRID"), Group(10, "Clone To")])
        fixture = FixtureProvider().parse('Fixture 4 "Key" (VL3000)')[0]
        self.assertEqual((fixture.number, fixture.name, fixture.fixture_type), (4, "Key", "VL3000"))

    def test_fixture_type_refresh_preserves_each_type_result_when_one_export_fails(self):
        class PerTypeProvider:
            source = "ma2_export_fixture_type_xml"

            def __init__(self):
                self.labels = []

            def export_and_bind(self, _runtime, label, _settings):
                self.labels.append(label)
                if label == "3 Broken Type":
                    raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_LABEL_MISMATCH", diagnostic={"observed": {"fixture_type_index": 0}})
                return {
                    "schema": "zen.fixture_type_channel_profile.v0.1",
                    "status": "SHOW_BOUND_VERIFIED",
                    "fixture_type": {"fixture_type_id": 2, "list_label": label},
                    "channels": [{"attribute": "DIM"}],
                }

            def capabilities(self, _runtime, _settings):
                return {"backend": "native_export_fixture_type_file"}

        provider = PerTypeProvider()
        self.core.fixture_type_export_provider = provider
        self.core.state.put("fixtures", [
            {"number": 101, "fixture_type": "2 Verified Type"},
            {"number": 102, "fixture_type": "3 Broken Type"},
        ], source="ma2_telnet_list")
        result = self.core.refresh_state("fixture_type_profiles")
        self.assertEqual(provider.labels, ["2 Verified Type", "3 Broken Type"])
        self.assertEqual([item["status"] for item in result["values"]], ["SHOW_BOUND_VERIFIED", "PARTIAL"])
        self.assertEqual(result["values"][1]["failure_reason"], "EXPORT_FIXTURE_TYPE_LABEL_MISMATCH")
        self.assertEqual(result["values"][1]["export_diagnostic"]["observed"]["fixture_type_index"], 0)
        self.assertEqual(self.core.state.get("fixture_type_profiles").capability["binding_status"], "PARTIAL")
        self.assertEqual(self.core.scan_show_profile()["known_limits"]["fixture_type_structure"], "PARTIAL")

    def test_skill_discovery_invalid_duplicate_and_enable_disable(self):
        registry = SkillRegistry(self.root)
        registry.discover()
        self.assertIn("group.select", [item["id"] for item in registry.list()])
        self.assertFalse(registry.set_enabled("group.select", False).enabled)
        self.assertTrue(registry.set_enabled("group.select", True).enabled)
        duplicate = self.root / "skills" / "installed" / "duplicate"; duplicate.mkdir(parents=True)
        (duplicate / "manifest.json").write_text(json.dumps({"id":"group.select","name":"Duplicate","version":"1","description":"x","intents":[],"required_state":[],"safety":"SAFE"}), encoding="utf-8")
        with self.assertRaisesRegex(SkillError, "Duplicate"):
            registry.discover()
        (duplicate / "manifest.json").unlink()
        (duplicate / "manifest.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(SkillError, "Invalid"):
            registry.discover()

    def test_required_state_dependency_and_untrusted_skill_code_not_imported(self):
        folder = self.root / "skills" / "builtin" / "needs.state"; folder.mkdir()
        (folder / "manifest.json").write_text(json.dumps({"id":"needs.state","name":"Needs State","version":"1","description":"x","intents":["needs_state"],"required_state":["groups"],"safety":"SAFE"}), encoding="utf-8")
        (folder / "skill.py").write_text("raise RuntimeError('must never import installed code')", encoding="utf-8")
        registry = SkillRegistry(self.root); registry.discover()
        with self.assertRaisesRegex(SkillError, "Required MA2 state unavailable"):
            registry.resolve(Intent("needs_state", {}, "test"), StateStore())
        store = StateStore(); store.put_groups([])
        self.assertEqual(registry.resolve(Intent("needs_state", {}, "test"), store).manifest.id, "needs.state")

    def test_builtin_workflow_regression_and_unapproved_commands_are_blocked(self):
        self.ready()
        action = self.core.submit_request("Go Sequence 5")["action"]
        self.assertEqual(action["task"]["skill_id"], "sequence.go")
        self.assertEqual(action["subtasks"][0]["phase"], "Planning")
        self.assertEqual(action["steps"][0]["command"], "Go Sequence 5")
        self.assertEqual(self.runtime.client.executed, [])
        self.core.approve_action(action["id"])
        self.assertEqual(self.runtime.client.executed, ["Go Sequence 5"])

    def test_skill_graph_can_compose_a_child_workflow_before_approval(self):
        parent = self.core.skills.plan_intent(Intent("go_sequence", {"sequence": 5}, "Go Sequence 5"), self.core.state, self.runtime.preferences)
        combined = self.core.skills.plan_subskill(parent, Intent("select_group", {"group": "BEAM"}, "Select Group BEAM"), self.core.state, self.runtime.preferences)
        self.assertEqual(len(combined.skill_graph), 2)
        self.assertEqual(combined.commands, ("Go Sequence 5", 'Group "BEAM"'))

    def test_user_installed_proposal_is_approval_gated_and_mobile_shares_registry(self):
        proposal = self.core.propose_skill("Cue Time Adjust", "adjust_cue_time", ["sequences", "cues"], "MODIFY")
        self.assertEqual(proposal["status"], "PENDING_APPROVAL")
        installed = self.core.install_skill_proposal(proposal["id"])
        self.assertEqual(installed["status"], "INSTALLED")
        skills = self.core.snapshot()["skills"]
        self.assertIn("adjust.cue.time", [item["id"] for item in skills])
        self.assertFalse(next(item for item in skills if item["id"] == "adjust.cue.time")["executable"])
        client = TestClient(create_app(self.core, self.source_root))
        token = client.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        response = client.get("/api/skills", headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("adjust.cue.time", [item["id"] for item in response.json()])


if __name__ == "__main__":
    unittest.main()
