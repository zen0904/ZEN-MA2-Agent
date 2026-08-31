import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class InspectClient:
    """A ready MA2 transport that records every attempted MA command."""

    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.executed = []

    def connect(self, username, password=""):
        self.state = ConnectionState.READY
        self.authenticated_user = username
        return f"Logged in as User '{username}'"

    def execute(self, command):
        self.executed.append(command)
        return "unexpected inspect transport call: " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class ProgrammerInspectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zen-programmer-inspect-")
        self.root = Path(self.temporary.name)
        self.source_root = Path(__file__).resolve().parents[1]
        copytree(self.source_root / "skills", self.root / "skills")
        self.core = AgentCore(AgentRuntime(self.root, client_factory=InspectClient))
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temporary.cleanup()

    def test_supported_chat_phrases_are_safe_explicit_unsupported_answers(self):
        cases = {
            "現在 Programmer 裡有什麼？": ("state_programmer", "UNSUPPORTED programmer"),
            "Programmer 有沒有東西？": ("state_programmer", "UNSUPPORTED programmer"),
            "哪些燈有 active value？": ("state_programmer", "UNSUPPORTED programmer"),
            "現在有什麼 Attribute 在 Programmer？": ("state_programmer", "UNSUPPORTED programmer"),
            "目前選了哪些燈？": ("state_selection", "UNSUPPORTED selection"),
            "Selection 裡有哪些 Fixture？": ("state_selection", "UNSUPPORTED selection"),
        }
        for query, (intent, expected) in cases.items():
            with self.subTest(query=query):
                response = self.core.handle_request(query)
                self.assertEqual(response["type"], "ANSWER")
                self.assertIn(expected, response["message"])
                self.assertNotIn("I understand this needs an MA2 workflow", response["message"])
                self.assertEqual(self.core.last_chat_routing["ROUTER_INTENT"], intent)
                self.assertEqual(self.core.last_chat_routing["PROVIDER"], "ProgrammerInspectCapability" if intent == "state_programmer" else "SelectionInspectCapability")
                self.assertIsNone(response["action"])
        self.assertEqual(self.core.runtime.client.executed, [])

    def test_unsupported_empty_results_have_precise_capabilities_and_stale_metadata(self):
        selection = self.core.get_selection()
        programmer = self.core.get_programmer_summary()
        self.assertEqual((selection["status"], selection["count"], selection["values"]), ("UNSUPPORTED", 0, []))
        self.assertEqual((programmer["status"], programmer["count"], programmer["values"]), ("UNSUPPORTED", 0, []))
        self.assertEqual(selection["capability"]["selection_members"], "unsupported")
        self.assertEqual(programmer["capability"]["programmer_values"], "unsupported")

        # A future provider may expose only presence.  An error must retain the
        # typed partial capability and stale metadata instead of crashing Chat.
        self.core.state.put(
            "programmer", [{"has_active_values": False, "fixtures": [], "attributes": []}],
            source="verified_partial_test",
            capability={"programmer_presence": "supported", "programmer_members": "unsupported", "programmer_values": "unsupported"},
        )
        snapshot = self.core.state.record_error("programmer", "temporary provider failure", source="verified_partial_test")
        self.assertTrue(snapshot.stale)
        self.assertEqual(snapshot.values[0]["fixtures"], [])
        self.assertEqual(snapshot.capability["programmer_presence"], "supported")
        self.assertEqual(snapshot.capability["programmer_members"], "unsupported")
        partial_text = self.core._format_state_answer(
            Intent("state_programmer", {}, "test"),
            {"resource": "programmer", "count": 1, "values": snapshot.values},
        )
        self.assertEqual(partial_text, "Programmer: empty")

        self.core.state.record_error("selection", "temporary provider failure", source="verified_partial_test")
        response = self.core.handle_request("目前選了哪些燈？")
        self.assertEqual(response["type"], "ANSWER")
        self.assertIn("UNSUPPORTED selection", response["message"])

    def test_disabled_safe_skill_never_requires_approval_or_generates_commands(self):
        skill = self.core.skills.get("programmer.inspect")
        self.assertEqual((skill.safety, skill.enabled), ("SAFE", False))
        response = self.core.handle_request("Programmer 有沒有東西？")
        self.assertEqual(response["type"], "ANSWER")
        self.assertFalse(self.core.actions)
        self.assertEqual(self.core.runtime.client.executed, [])


if __name__ == "__main__":
    unittest.main()
