import tempfile
import threading
import time
import unittest
import re
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers import AdapterResponseError, AdapterUnsupported, ZenStateAdapter
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class MailboxStateClient:
    export_directory: Path | None = None

    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.executed: list[str] = []
        self.mailbox = ""

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.executed.append(command)
        match = re.fullmatch(r'Export Group (\d+) "(ZEN_AGENT_G\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if match:
            assert self.export_directory is not None
            group_no, filename = match.groups()
            (self.export_directory / filename).write_text(
                f'<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA"><Group index="{int(group_no) - 1}" name="HYBRID"><Subfixtures><Subfixture fix_id="1" /><Subfixture fix_id="101" /><Subfixture fix_id="1007" /></Subfixtures></Group></MA>',
                encoding="utf-8",
            )
            return "exported"
        match = re.fullmatch(r'Export Layout (\d+) "(ZEN_AGENT_LAYOUT_\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if match:
            assert self.export_directory is not None
            layout_no, filename = match.groups()
            (self.export_directory / filename).write_text(
                f'<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA"><Group index="{int(layout_no) - 1}" name="Empty"><LayoutData><CObjects /></LayoutData></Group></MA>',
                encoding="utf-8",
            )
            return "exported"
        if command.startswith('SetUserVar $ZEN_AGENT_REQUEST="'):
            self.mailbox = command.removeprefix('SetUserVar $ZEN_AGENT_REQUEST="').removesuffix('"')
            return ""
        if command == "Plugin 3":
            request_id, operation, argument = self.mailbox.split(" ", 2)
            if operation == "group_membership" and argument == "1":
                return (f"stale ZEN_STATE|stale01|BEGIN|group_membership|1\r\n"
                        f"ZEN_STATE|{request_id}|BEGIN|group_membership|1\r\n"
                        f"ZEN_STATE|{request_id}|MEMBER|1\r\nZEN_STATE|{request_id}|MEMBER|101\r\n"
                        f"ZEN_STATE|{request_id}|MEMBER|1007\r\nZEN_STATE|{request_id}|END|group_membership|1\r\n")
            return f"ZEN_STATE|{request_id}|ERROR|UNKNOWN_COMMAND\r\n"
        responses = {
            "List Group": 'Group 1 "HYBRID"\r\nGroup 8 "SPARSE"\r\n',
            "List Fixture": 'Fixture 1 "Spot" (Type A)\r\nFixture 101 "Wash" (Type B)\r\nFixture 1007 "Beam" (Type C)\r\n',
            "List Sequence": 'Sequence 5 "SONG 01"\r\nSequence 21 "Encore"\r\n',
        }
        return responses.get(command, "unrelated MA2 feedback")

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class ExtendedStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-extended-state-")
        self.root = Path(self.temp.name)
        self.source_root = Path(__file__).resolve().parents[1]
        copytree(self.source_root / "skills", self.root / "skills")
        self.export_directory = self.root / "ma2-importexport"
        self.export_directory.mkdir()
        MailboxStateClient.export_directory = self.export_directory
        self.core = AgentCore(AgentRuntime(self.root, client_factory=MailboxStateClient))
        self.core.runtime.preferences["state_adapter"] = {"plugin_slot": 3, "timeout_seconds": 1.0, "importexport_path": str(self.export_directory)}
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    def test_groups_fixtures_and_membership_use_export_provider(self):
        self.assertEqual([item["number"] for item in self.core.refresh_state("groups")["values"]], [1, 8])
        self.assertEqual([item["number"] for item in self.core.refresh_state("fixtures")["values"]], [1, 101, 1007])
        result = self.core.request_group_membership(1)
        self.assertEqual(result["group"]["fixtures"], [1, 101, 1007])
        self.assertEqual(result["group"]["members"], [
            {"fix_id": 1, "export_order": 0},
            {"fix_id": 101, "export_order": 1},
            {"fix_id": 1007, "export_order": 2},
        ])
        commands = self.core.runtime.client.executed
        export = next(command for command in commands if command.startswith("Export Group 1 "))
        self.assertRegex(export, r'^Export Group 1 "ZEN_AGENT_G1_[a-f0-9]{16}\.xml" /nc$')
        self.assertNotIn("Plugin 3", commands)
        self.assertEqual(self.core.state.get("group_membership").source, "ma2_export_xml")

    def test_request_id_filtering_and_fragmented_frames(self):
        adapter = ZenStateAdapter()
        request = adapter.request("group_membership", 1, request_id="abc123")
        self.assertEqual(request.wire, "abc123 group_membership 1")
        self.assertNotIn("|", request.wire)
        fragmented = "noise ZEN_STA" + "TE|old001|BEGIN|group_membership|1\r\n" + "ZEN_STATE|abc123|BEGIN|group_membership|1\r\nZEN_STATE|abc123|MEMBER|101\r\nZEN_STATE|abc123|END|group_membership|1"
        self.assertEqual(adapter.group_membership(fragmented, request)["fixtures"], [101])
        with self.assertRaises(AdapterResponseError):
            adapter.group_membership("ZEN_STATE|old001|BEGIN|group_membership|1", request)

    def test_malformed_unknown_and_duplicate_responses_are_rejected(self):
        adapter = ZenStateAdapter()
        request = adapter.request("group_membership", 1, request_id="abc123")
        with self.assertRaises(AdapterResponseError):
            adapter.group_membership("ZEN_STATE|abc123|BEGIN|group_membership|1\r\nZEN_STATE|abc123|END|group_membership|2", request)
        with self.assertRaises(AdapterUnsupported):
            adapter.group_membership("ZEN_STATE|abc123|ERROR|UNKNOWN_COMMAND", request)
        with self.assertRaises(AdapterUnsupported):
            adapter.group_membership("ZEN_STATE|abc123|BEGIN|group_membership|1\r\nZEN_STATE|abc123|END|group_membership|1", request)
        with self.assertRaises(AdapterUnsupported):
            adapter.group_membership("ZEN_STATE|abc123|ERROR|GROUP_NOT_FOUND", request)

    def test_chat_and_mobile_share_mailbox_state(self):
        membership = self.core.handle_request("HYBRID 裡有哪些燈？", source="desktop")
        self.assertEqual(membership["type"], "ANSWER")
        self.assertIn("1, 101, 1007", membership["message"])
        client = TestClient(create_app(self.core, self.source_root))
        token = client.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        response = client.post("/api/chat", json={"text": "有哪些 Fixture？"}, headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("1007: Beam", response.json()["message"])

    def test_quotes_escape_and_concurrent_requests_are_serialized(self):
        self.assertEqual(AgentRuntime.user_var_command('a"b\\c'), 'SetUserVar $ZEN_AGENT_REQUEST="a\\"b\\\\c"')
        client = self.core.runtime.client
        original_execute = client.execute

        def delayed(command):
            if command == "Plugin 3":
                time.sleep(0.03)
            return original_execute(command)

        client.execute = delayed
        errors: list[Exception] = []

        def run(request_id):
            try:
                self.core.runtime.read_adapter_state(plugin_slot=3, request=f"{request_id} group_membership 1", timeout_seconds=1)
            except Exception as exc:  # pragma: no cover - assertion below captures it
                errors.append(exc)

        first = threading.Thread(target=run, args=("thread01",))
        second = threading.Thread(target=run, args=("thread02",))
        first.start(); second.start(); first.join(); second.join()
        self.assertEqual(errors, [])
        commands = [command for command in client.executed if command.startswith("SetUserVar") or command == "Plugin 3"]
        self.assertEqual(len(commands), 4)
        self.assertTrue(commands[0].startswith("SetUserVar"))
        self.assertEqual(commands[1], "Plugin 3")
        self.assertTrue(commands[2].startswith("SetUserVar"))
        self.assertEqual(commands[3], "Plugin 3")

    def test_group_export_does_not_require_a_plugin_slot(self):
        self.core.runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(self.export_directory)}
        result = self.core.request_group_membership(1)
        self.assertEqual(result["status"], "available")
        self.assertFalse(any(command.startswith("Plugin") for command in self.core.runtime.client.executed))

    def test_empty_layout_chat_uses_export_provider_without_plugin_slot(self):
        self.core.runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(self.export_directory)}
        result = self.core.handle_request("Layout 1 裡有哪些燈？", source="mobile")
        self.assertEqual(result["type"], "ANSWER")
        self.assertIn("Fixture layout data is not available from the current MA2 Layout Export provider.", result["message"])
        self.assertIn("Visible CObjects: 0.", result["message"])
        self.assertNotIn("Fixtures: 0", result["message"])
        self.assertEqual(self.core.state.get("layout_items").source, "ma2_export_xml")
        self.assertFalse(any(command.startswith("Plugin") for command in self.core.runtime.client.executed))


if __name__ == "__main__":
    unittest.main()
