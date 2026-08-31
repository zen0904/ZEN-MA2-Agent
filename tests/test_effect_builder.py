import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.parser import parse
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class EffectBuilderClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands: list[str] = []
        self.groups = 'Group 1 "HYBRID"\nGroup 2 "WASH"\n'
        self.effects = "Effect 1 Base\n"
        self.created_name = ""

    def connect(self, username, password=""):
        self.state = ConnectionState.READY
        self.authenticated_user = username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group":
            return self.groups
        if command == "List Fixture":
            return 'Fixture 101 "Hybrid 1" (Hybrid)\n'
        if command == "List Effect":
            return self.effects
        if command == "List Effect 2500":
            return f'Effect 2500 "{self.created_name}"\n' if self.created_name else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command.startswith("Label Effect 2500 "):
            self.created_name = command.split('"', 2)[1]
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class EffectBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-effect-builder-")
        self.root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", self.root / "skills")
        self.runtime = AgentRuntime(self.root, client_factory=EffectBuilderClient)
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    @property
    def client(self):
        return self.runtime.client

    def test_natural_language_parses_defaults_speed_number_and_target_forms(self):
        cases = {
            "幫 HYBRID 做一個 Dimmer Chase": {"target_type": "group_name", "target": "HYBRID"},
            "幫 Group 1 做左右跑的 Dimmer Effect": {"target_type": "group_number", "target": 1},
            "做 Effect 2500 給 HYBRID": {"effect_number": 2500, "target": "HYBRID"},
            "建立一個 60 BPM 的 Dimmer Chase 給 HYBRID": {"speed_bpm": 60},
            "幫 Fixture 101 做 Dimmer Chase": {"target_type": "fixture_number", "target": 101},
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                intent = parse(text)
                self.assertEqual(intent.kind, "build_dimmer_chase")
                self.assertTrue(expected.items() <= intent.parameters.items())

    def test_preview_resolves_group_allocates_slot_and_never_executes_write(self):
        response = self.core.handle_request("幫 HYBRID 做一個 Dimmer Chase")
        self.assertEqual(response["type"], "ACTION_PLAN")
        action = response["action"]
        spec = action["intent"]["parameters"]["effect_spec"]
        self.assertEqual((spec["effect_number"], spec["target_type"], spec["target_number"], spec["speed_bpm"]), (2500, "group", 1, 60))
        self.assertIn('Effect: 2500 "HYBRID Dimmer Chase"', response["message"])
        self.assertIn("Safety: MODIFY", response["message"])
        self.assertIn("Approval required.", response["message"])
        self.assertEqual(self.client.commands, ["List Group", "List Effect"])
        self.assertEqual(action["rollback_strategy"], "Suggested rollback: Delete Effect 2500 (never automatic).")
        self.assertTrue(any(step["command"] == 'Assign Form "PWM" At Effect 1.2500.1' for step in action["steps"]))

    def test_existing_effect_is_protected_and_duplicate_group_needs_clarification(self):
        self.client.effects = 'Effect 2500 "Already Here"\n'
        exists = self.core.handle_request("做 Effect 2500 給 HYBRID")
        self.assertEqual(exists["type"], "ERROR")
        self.assertIn("already exists", exists["message"])
        self.assertFalse(self.core.actions)
        self.client.groups = 'Group 1 "HYBRID"\nGroup 2 "HYBRID"\n'
        self.core.state.mark_stale("groups")
        duplicate = self.core.handle_request("幫 HYBRID 做 Dimmer Chase")
        self.assertEqual(duplicate["type"], "NEEDS_CLARIFICATION")
        self.assertIn("Multiple Groups", duplicate["message"])

    def test_missing_target_and_unverified_reverse_do_not_create_action(self):
        missing = self.core.handle_request("幫 UNKNOWN 做 Dimmer Chase")
        self.assertEqual(missing["type"], "ERROR")
        self.assertIn("not found", missing["message"])
        reverse = self.core.handle_request("做一個反方向 Dimmer Chase 給 HYBRID")
        self.assertEqual(reverse["type"], "ERROR")
        self.assertIn("not yet command-verified", reverse["message"])
        self.assertFalse(self.core.actions)

    def test_modify_approval_gate_executes_only_the_structured_action_and_partially_verifies(self):
        action = self.core.handle_request("做 Effect 2500 給 HYBRID")["action"]
        writes_before = list(self.client.commands)
        self.assertEqual(writes_before, ["List Group", "List Effect"])
        result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        expected = [
            "Store Effect 2500 /nc", "Store Effect 1.2500.1 /nc", 'Assign Attribute "Dim" At Effect 1.2500.1',
            'Assign Form "PWM" At Effect 1.2500.1', "Assign Effect 2500 /lowvalue=0 /highvalue=100 /speed=60 /phase=0..360 /groups=1",
            "Group 1", "Store Effect 1.2500.* /nc", 'Label Effect 2500 "HYBRID Dimmer Chase" /nc', "List Effect 2500",
        ]
        self.assertEqual(self.client.commands[2:], expected)
        self.assertIn("Verification: PARTIAL", result["result"])
        self.assertIn("label matches", result["result"])

    def test_effect_query_remains_read_only_and_skill_is_enabled_modify(self):
        skill = self.core.skills.get("effects.builder")
        self.assertEqual((skill.enabled, skill.safety), (True, "MODIFY"))
        response = self.core.handle_request("Effect 2500 是什麼？")
        self.assertEqual(response["type"], "ANSWER")
        self.assertFalse(self.core.actions)
        self.assertEqual(self.client.commands, ["List Effect"])


if __name__ == "__main__":
    unittest.main()
