import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from fastapi.testclient import TestClient

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers import AdapterResponseError, AdapterUnsupported, CueProvider, LayoutInventoryProvider, SequenceProvider, ZenStateAdapter
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.web_server import create_app


class ExtendedStateClient:
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
        responses = {
            "List Group": 'Group 1 "HYBRID"\r\nGroup 8 "SPARSE"\r\n',
            "List Fixture": 'Fixture 1 "Spot" (Type A)\r\nFixture 101 "Wash" (Type B)\r\nFixture 1007 "Beam" (Type C)\r\n',
            "List Layout": 'Layout 1 "Main Stage"\r\nLayout 7 "Empty"\r\n',
            "List Sequence": 'Sequence 5 "SONG 01"\r\nSequence 21 "Encore"\r\n',
            "List Cue 5": 'Cue 1 "Intro" Trigger Go Fade 2.5 Delay 0.5\r\nCue 2.5 "Verse" Trigger Time Fade 1\r\n',
            "List Cue 21": 'Cue 1 "Encore Intro" Trigger Go\r\n',
            'Plugin "ZEN_AGENT" "group_membership 1"': 'unrelated feedback\r\nZEN_STATE|group_membership|{"group_no":1,"name":"HYBRID","fixtures":[1,101,1007]}\r\n',
            'Plugin "ZEN_AGENT" "layouts 1"': 'ZEN_STATE|layouts|{"layout":1,"name":"Main Stage","items":[{"type":"fixture","fixture":101,"x":-2.4,"y":1.1,"width":0.5,"height":1.25,"rotation":-90},{"type":"group","group":1,"x":0,"y":-3.75}]}\r\n',
            'Plugin "ZEN_AGENT" "selection"': 'ZEN_STATE|selection|{"fixtures":[1,1007]}\r\n',
            'Plugin "ZEN_AGENT" "programmer"': 'ZEN_STATE|programmer|{"has_active_values":true,"active_attributes":["Dimmer","Pan"]}\r\n',
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
        self.core = AgentCore(AgentRuntime(self.root, client_factory=ExtendedStateClient))
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    def test_group_membership_parses_sparse_fixture_ids_and_fragmented_feedback(self):
        adapter = ZenStateAdapter()
        fragmented = 'noise ZEN_STA' + 'TE|group_membership|{"group_no":1,"name":"HYBRID","fixtures":[1,101,1007]}'
        self.assertEqual(adapter.group_membership(fragmented, 1)["fixtures"], [1, 101, 1007])
        result = self.core.request_group_membership(1)
        self.assertEqual(result["group"], {"group_no": 1, "name": "HYBRID", "fixtures": [1, 101, 1007]})
        self.assertEqual(self.core.snapshot()["state_browser"]["group_membership"]["source"], "ma2_lua_adapter")

    def test_layout_inventory_xy_negative_coordinates_and_empty_layout(self):
        self.assertEqual(LayoutInventoryProvider().parse('Layout 1 "Main"\nLayout 7 Empty'), [{"layout": 1, "name": "Main", "items": []}, {"layout": 7, "name": "Empty", "items": []}])
        result = self.core.refresh_state("layouts", layout_no=1)
        item = result["values"][0]["items"][0]
        self.assertEqual((item["fixture"], item["x"], item["y"], item["rotation"]), (101, -2.4, 1.1, -90.0))
        empty = ZenStateAdapter().layout('ZEN_STATE|layouts|{"layout":7,"name":"Empty","items":[]}', 7)
        self.assertEqual(empty["items"], [])
        response = self.core.handle_request("有哪些 Layout？")
        self.assertIn("1: Main Stage", response["message"])

    def test_selection_and_programmer_snapshots(self):
        self.assertEqual(self.core.get_selection()["selection"], {"fixtures": [1, 1007]})
        self.assertEqual(self.core.get_programmer_summary()["programmer"]["active_attributes"], ["Dimmer", "Pan"])
        self.assertEqual(ZenStateAdapter().selection('ZEN_STATE|selection|{"fixtures":[]}'), {"fixtures": []})

    def test_sequence_and_cue_inventory_metadata(self):
        sequences = self.core.refresh_state("sequences")
        cues = self.core.refresh_state("cues", sequence=5)
        self.assertEqual(sequences["values"], [{"number": 5, "name": "SONG 01"}, {"number": 21, "name": "Encore"}])
        self.assertEqual((cues["values"][0]["number"], cues["values"][0]["trigger"], cues["values"][0]["fade"], cues["values"][0]["delay"]), (1, "Go", 2.5, 0.5))
        self.assertEqual(CueProvider().parse("unrelated feedback", 5), [])
        self.assertEqual(SequenceProvider().parse("unrelated feedback"), [])
        self.core.refresh_state("cues", sequence=21)
        cached = self.core.snapshot()["state_browser"]["cues"]["values"]
        self.assertEqual(sorted(item["sequence"] for item in cached), [5, 5, 21])

    def test_malformed_or_unrelated_adapter_feedback_is_never_invented(self):
        adapter = ZenStateAdapter()
        with self.assertRaises(AdapterResponseError):
            adapter.layout('ZEN_STATE|layouts|{"layout":1,"items":[{"type":"fixture","fixture":101,"x":"bad","y":1}]}', 1)
        with self.assertRaises(AdapterUnsupported):
            adapter.selection("Logged in as User 'MM'")

    def test_cache_stale_and_refresh_metadata(self):
        self.core.refresh_state("sequences")
        initial = self.core.snapshot()["state_browser"]["sequences"]
        self.assertFalse(initial["stale"])
        self.assertEqual(initial["source"], "ma2_telnet_list")
        self.core.disconnect()
        self.assertTrue(self.core.snapshot()["state_browser"]["sequences"]["stale"])
        self.core.connect("127.0.0.1", 30000, "MM", "")
        self.core.refresh_state("sequences")
        self.assertFalse(self.core.snapshot()["state_browser"]["sequences"]["stale"])

    def test_chat_auto_refreshes_dependencies_and_mobile_shares_state(self):
        membership = self.core.handle_request("HYBRID 裡有哪些燈？", source="desktop")
        self.assertEqual(membership["type"], "ANSWER")
        self.assertIn("1, 101, 1007", membership["message"])
        self.assertEqual(self.core.runtime.client.executed[:2], ["List Group", 'Plugin "ZEN_AGENT" "group_membership 1"'])
        client = TestClient(create_app(self.core, self.source_root))
        token = client.post("/api/pair", json={"code": self.core.pairing.code, "nonce": self.core.pairing.nonce}).json()["token"]
        response = client.post("/api/chat", json={"text": "Sequence 5 有哪些 Cue？"}, headers={"Authorization": "Bearer " + token})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Intro", response.json()["message"])
        self.assertEqual(self.core.snapshot()["state_browser"]["cues"]["count"], 2)

    def test_unsupported_adapter_state_is_cached_without_unsafe_fallback(self):
        self.core.runtime.client.execute = lambda command: self.core.runtime.client.executed.append(command) or "Plugin not found"
        result = self.core.get_selection()
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertTrue(result["error"].startswith("UNSUPPORTED"))
        self.assertEqual(self.core.runtime.client.executed[-1], 'Plugin "ZEN_AGENT" "selection"')


if __name__ == "__main__":
    unittest.main()
