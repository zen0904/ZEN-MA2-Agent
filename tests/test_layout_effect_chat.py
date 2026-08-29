import re
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.layouts import LayoutExportProvider, LayoutObjectResolver
from zen_ma2_agent.state.providers.layout_cobject_registry import VALIDATED_FIRST_TOKEN_CLASSES
from zen_ma2_agent.state.providers.show_pools import EffectProvider
from zen_ma2_agent.telnet_client import ConnectionState


LAYOUT_XML = '''<MA><Group index="0" name="Main Control"><LayoutData><CObjects>
<LayoutCObject center_x="1" center_y="2" fix_id="101"><CObject name="Key" /></LayoutCObject>
<LayoutCObject center_x="3" center_y="4" macro_no="7"><CObject name="Look" /></LayoutCObject>
<LayoutCObject center_x="5" center_y="6"><CObject><Token>17</Token><Token>1</Token><Token>1</Token><Token>1</Token></CObject></LayoutCObject>
</CObjects></LayoutData></Group></MA>'''


class LayoutEffectClient:
    export_directory: Path | None = None

    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        group = re.fullmatch(r'Export Group (\d+) "(ZEN_AGENT_G\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if group:
            assert self.export_directory is not None
            number, filename = group.groups()
            (self.export_directory / filename).write_text(f'<MA><Group index="{int(number)-1}" name="HYBRID"><Subfixtures><Subfixture fix_id="101" /></Subfixtures></Group></MA>', encoding="utf-8")
            return "exported"
        layout = re.fullmatch(r'Export Layout (\d+) "(ZEN_AGENT_LAYOUT_\d+_[A-Za-z0-9_-]+\.xml)" /nc', command)
        if layout:
            assert self.export_directory is not None
            _, filename = layout.groups()
            (self.export_directory / filename).write_text(LAYOUT_XML, encoding="utf-8")
            return "exported"
        if command == "List Group":
            return 'Group 1 "HYBRID"\n'
        raise AssertionError(command)

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class LayoutEffectChatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-layout-chat-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        directory = root / "importexport"; directory.mkdir(); LayoutEffectClient.export_directory = directory
        self.runtime = AgentRuntime(root, client_factory=LayoutEffectClient)
        self.runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(directory)}
        self.core = AgentCore(self.runtime); self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    def test_unknown_and_non_fixture_layout_items_are_not_fixtures(self):
        layout = LayoutExportProvider.parse(LAYOUT_XML, 1)
        self.assertEqual(layout["items"][0]["type"], "fixture")
        self.assertEqual(layout["items"][1]["type"], "macro")
        unknown = layout["items"][2]
        self.assertEqual(unknown["type"], "unknown")
        self.assertEqual(unknown["reference_tokens"], ["17", "1", "1", "1"])
        self.assertIsNone(unknown["validated_token_class"])
        self.assertEqual(VALIDATED_FIRST_TOKEN_CLASSES, {})
        self.assertIn("LayoutCObject", unknown["parent_path"])
        self.assertEqual([item["reference"] for item in LayoutObjectResolver.lighting_items(layout)], [101])

    def test_fixture_only_all_objects_and_group_layout_intersection(self):
        fixtures = self.core.handle_request("Layout 1 裡有哪些燈？")
        self.assertIn("Fixtures: 1", fixtures["message"])
        self.assertIn("Other objects: 2", fixtures["message"])
        self.assertNotIn("unknown", fixtures["message"])
        all_objects = self.core.handle_request("Layout 1 裡有哪些物件？")
        self.assertIn("fixture 101 Key", all_objects["message"])
        self.assertIn("macro 7 Look", all_objects["message"])
        self.assertIn("unknown unresolved ['17', '1', '1', '1']", all_objects["message"])
        hybrid = self.core.handle_request("HYBRID 在 Layout 1 怎麼排？")
        self.assertEqual(hybrid["type"], "ANSWER")
        self.assertIn("fixture 101 Key", hybrid["message"])

    def test_effect_pagination_formatting_diagnostics_and_generic_row_limit(self):
        effects = [{"number": number, "name": "DIM Chase" if number == 1005 else str(number)} for number in range(1000, 2780)]
        result = {"resource": "effects", "count": len(effects), "values": effects, "status": "available"}
        message = self.core._format_state_answer(Intent("effect_list", {}, "Effects"), result)
        self.assertTrue(message.startswith("Effects (1780)\nShowing first 30\n1000 (unlabeled)"))
        self.assertIn("1005: DIM Chase", message)
        self.assertNotIn("1030", message)
        self.assertIn("Next page: 下一頁", message)
        self.core.state.put("effects", effects, source="test")
        second = self.core.handle_request("下一頁")
        self.assertIn("Showing 31-60", second["message"])
        self.assertIn("1030 (unlabeled)", second["message"])
        self.assertEqual(EffectProvider.diagnostics(effects), {"parsed_count": 1780, "min_effect_number": 1000, "max_effect_number": 2779, "labeled_count": 1, "unlabeled_count": 1779})
        empty = self.core._format_state_answer(Intent("effect_list", {}, "Effects"), {"resource": "effects", "count": 0, "values": [], "status": "available"})
        self.assertEqual(empty, "Effects (0)\nNo entries returned.")
        fixtures = [{"number": number, "name": f"Fixture {number}"} for number in range(1, 32)]
        limited = self.core._format_state_answer(Intent("state_fixtures", {}, "Fixtures"), {"resource": "fixtures", "count": 31, "values": fixtures, "status": "available"})
        self.assertIn("Showing first 30", limited)
        self.assertNotIn("31: Fixture 31", limited)


if __name__ == "__main__":
    unittest.main()
