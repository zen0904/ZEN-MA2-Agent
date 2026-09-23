import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.parser import ParseError, parse
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.timecodes import TimecodeProvider
from zen_ma2_agent.telnet_client import ConnectionState


class TimecodeClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands = []
        self.name = "ZEN Test"
        self.offset = "0s"
        self.present = True

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Timecode":
            offset = "0:15" if self.offset == "0.50s" else "0:00"
            return f"Timecode 9000 {self.name} Intern 0:00 {offset} Endless Repeat\n" if self.present else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command.startswith("Assign Timecode 9000/Offset = "):
            self.offset = command.rsplit("= ", 1)[1]
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class TimecodeOffsetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-timecode-offset-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.runtime = AgentRuntime(root, client_factory=TimecodeClient)
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    @property
    def client(self):
        return self.runtime.client

    def test_parser_uses_exact_integer_milliseconds_for_whole_and_range_requests(self):
        self.assertEqual(parse("Timecode 3 往後 2 秒").parameters, {"timecode_number": 3, "offset_ms": 2000})
        self.assertEqual(parse("Timecode 3 提前 0.5 秒").parameters, {"timecode_number": 3, "offset_ms": -500})
        ranged = parse("Timecode 3 的 10 秒到 30 秒往後 250ms").parameters
        self.assertEqual(ranged, {"timecode_number": 3, "offset_ms": 250, "range_start_ms": 10000, "range_end_ms": 30000})

    def test_timecode_provider_inventory_and_event_capability(self):
        rows = TimecodeProvider().parse("Timecode 9000 ZEN Test Intern 0:00 0:15 Endless Repeat\n")
        self.assertEqual(rows[0]["timecode_number"], 9000)
        self.assertEqual(rows[0]["name"], "ZEN Test")
        self.assertEqual((rows[0]["offset_raw"], rows[0]["offset_ms"]), ("0:15", 500))
        self.assertEqual(TimecodeProvider().parse("Timecode 9000 ZEN Test Intern 0:00 0:08 Endless Repeat\n")[0]["offset_ms"], 267)
        self.assertEqual(rows[0]["events"], [])
        self.assertEqual(rows[0]["event_capability"], "UNSUPPORTED")

    def test_positive_whole_offset_previews_without_execution(self):
        response = self.core.handle_request("Timecode 9000 往後 500ms")
        self.assertEqual(response["type"], "ACTION_PLAN")
        self.assertIn("Timecode Offset Preview", response["message"])
        self.assertIn("Offset: +0.500 s", response["message"])
        self.assertIn("Events affected: unavailable", response["message"])
        self.assertEqual(self.client.commands, ["List Timecode"])
        self.assertEqual(response["action"]["command"], "Assign Timecode 9000/Offset = 0.50s")
        self.assertIn("no automatic rollback", response["action"]["rollback_strategy"])

    def test_negative_and_range_requests_are_explicitly_unsupported_without_writes(self):
        earlier = self.core.handle_request("Timecode 9000 往前 500ms")
        self.assertEqual(earlier["type"], "ERROR")
        self.assertIn("UNSUPPORTED", earlier["message"])
        ranged = self.core.handle_request("Timecode 9000 的 10 秒到 30 秒往後 250ms")
        self.assertEqual(ranged["type"], "ERROR")
        self.assertIn("range-based", ranged["message"])
        self.assertEqual(self.client.commands, ["List Timecode", "List Timecode"])

    def test_non_frame_aligned_offset_is_rejected_without_writes(self):
        response = self.core.handle_request("Timecode 9000 往後 250ms")
        self.assertEqual(response["type"], "ERROR")
        self.assertIn("30 FPS", response["message"])
        self.assertEqual(self.client.commands, ["List Timecode"])

    def test_approval_refreshes_then_executes_and_reports_partial_readback(self):
        action = self.core.handle_request("Timecode 9000 往後 500ms")["action"]
        self.assertEqual(self.client.commands, ["List Timecode"])
        result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(self.client.commands, ["List Timecode", "List Timecode", "Assign Timecode 9000/Offset = 0.50s", "List Timecode"])
        self.assertIn("Verification: VERIFIED", result["result"])
        self.assertEqual(self.client.offset, "0.50s")

    def test_state_changed_since_preview_blocks_execution(self):
        action = self.core.handle_request("Timecode 9000 往後 500ms")["action"]
        self.client.name = "Changed outside ZEN"
        with self.assertRaisesRegex(ValueError, "STATE_CHANGED_SINCE_PREVIEW"):
            self.core.approve_action(action["id"])
        self.assertEqual(self.client.commands, ["List Timecode", "List Timecode"])

    def test_nonexistent_empty_and_safe_queries(self):
        self.client.present = False
        missing = self.core.handle_request("Timecode 9000 往後 500ms")
        self.assertEqual(missing["type"], "ERROR")
        self.assertIn("not found", missing["message"])
        listed = self.core.handle_request("有哪些 Timecode？")
        self.assertEqual((listed["type"], listed["message"]), ("ANSWER", "Timecodes (0)\nNo entries returned."))
        events = self.core.handle_request("Timecode 9000 有哪些事件？")
        self.assertEqual(events["type"], "ANSWER")
        self.assertIn("UNSUPPORTED", events["message"])

    def test_explicit_test_setup_is_environment_gated_and_allocates_first_free(self):
        with self.assertRaises(ParseError):
            parse("ZEN TEST create Timecode 9001")
        with patch.dict("os.environ", {"ZEN_MA2_TIMECODE_TEST_MODE": "1"}, clear=False):
            setup = self.core.handle_request("ZEN TEST create Timecode 9001")
        self.assertEqual(setup["type"], "ACTION_PLAN")
        self.assertIn("TEST-ONLY", setup["message"])
        self.assertEqual(self.client.commands, ["List Timecode"])
        self.assertIn("Create empty Timecode 1.", setup["message"])
        self.core.approve_action(setup["action"]["id"])
        self.assertEqual(self.client.commands[-1], "Store Timecode 1 /nc")


if __name__ == "__main__":
    unittest.main()
