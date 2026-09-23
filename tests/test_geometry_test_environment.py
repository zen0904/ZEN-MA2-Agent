import os
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.parser import ParseError, parse
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class TestEnvironmentClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands = []

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group":
            return ""
        if command == "List Fixture":
            return 'Fixture 1 "Test source"\nFixture 2 "Test destination"\n'
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class GeometryTestEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-geometry-test-environment-")
        self.root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", self.root / "skills")
        self.runtime = AgentRuntime(self.root, client_factory=TestEnvironmentClient)
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    @property
    def client(self):
        return self.runtime.client

    def test_test_requests_are_unreachable_without_explicit_mode(self):
        with self.assertRaises(ParseError):
            parse("ZEN TEST load geometry show")
        with self.assertRaises(ParseError):
            parse("ZEN TEST setup geometry groups 1 2")

    def test_load_is_previewed_then_approved_through_agent_core(self):
        with patch.dict(os.environ, {"ZEN_MA2_GEOMETRY_TEST_MODE": "1"}, clear=False):
            response = self.core.handle_request("ZEN TEST load geometry show")
            self.assertEqual(response["type"], "ACTION_PLAN")
            self.assertIn('Load isolated Show: "MA2_EFFECT_PROBE_WORK"', response["message"])
            self.assertEqual(self.client.commands, [])
            result = self.core.approve_action(response["action"]["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(self.client.commands, ['LoadShow "MA2_EFFECT_PROBE_WORK" /nc'])
        self.assertTrue(self.core._isolated_geometry_test_loaded)

    def test_group_setup_allocates_first_free_groups_and_uses_only_fixture_ids(self):
        with patch.dict(os.environ, {"ZEN_MA2_GEOMETRY_TEST_MODE": "1"}, clear=False):
            self.core._isolated_geometry_test_loaded = True
            response = self.core.handle_request("ZEN TEST setup geometry groups 1 2")
        self.assertEqual(response["type"], "ACTION_PLAN")
        commands = [step["command"] for step in response["action"]["steps"]]
        self.assertEqual(commands, [
            "Fixture 1", "Store Group 1 /nc", 'Label Group 1 "ZEN Clone Src TEST"',
            "Fixture 2", "Store Group 2 /nc", 'Label Group 2 "ZEN Clone Dst TEST"', "ClearAll",
        ])

    def test_group_setup_skips_occupied_front_slots(self):
        self.client.execute = lambda command: (
            'Group 1 "Existing"\nGroup 2 "Existing"\n'
            if command == "List Group"
            else 'Fixture 1 "Test source"\nFixture 2 "Test destination"\n'
            if command == "List Fixture"
            else "Executing : " + command
        )
        with patch.dict(os.environ, {"ZEN_MA2_GEOMETRY_TEST_MODE": "1"}, clear=False):
            self.core._isolated_geometry_test_loaded = True
            response = self.core.handle_request("ZEN TEST setup geometry groups 1 2")
        commands = [step["command"] for step in response["action"]["steps"]]
        self.assertIn("Store Group 3 /nc", commands)
        self.assertIn("Store Group 4 /nc", commands)

    def test_restore_cannot_be_requested_until_this_process_loaded_the_test_show(self):
        with patch.dict(os.environ, {"ZEN_MA2_GEOMETRY_TEST_MODE": "1"}, clear=False):
            response = self.core.handle_request("ZEN TEST restore production show")
        self.assertEqual(response["type"], "ERROR")
        self.assertIn("only after", response["message"])


if __name__ == "__main__":
    unittest.main()
