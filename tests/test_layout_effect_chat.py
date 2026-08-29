import json
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
<LayoutCObject center_x="5" center_y="6"><CObject name="Red 4.2"><Token>17</Token><Token>1</Token><Token>4</Token><Token>2</Token></CObject></LayoutCObject>
<LayoutCObject center_x="-4.85" center_y="-5.35"><CObject name="HYBRID 1"><Token>22</Token><Token>1</Token><Token>1</Token></CObject></LayoutCObject>
<LayoutCObject center_x="7" center_y="8"><CObject><Token>99</Token><Token>1</Token></CObject></LayoutCObject>
</CObjects></LayoutData></Group></MA>'''

GROUP_ONLY_LAYOUT_XML = '''<MA><Group index="0" name="Main Control"><LayoutData><CObjects>
<LayoutCObject center_x="-4.85" center_y="-5.35"><CObject name="HYBRID 1"><Token>22</Token><Token>1</Token><Token>1</Token></CObject></LayoutCObject>
</CObjects></LayoutData></Group></MA>'''


class LayoutEffectClient:
    export_directory: Path | None = None
    layout_xml = LAYOUT_XML

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
            (self.export_directory / filename).write_text(self.layout_xml, encoding="utf-8")
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
        directory = root / "importexport"; directory.mkdir(); LayoutEffectClient.export_directory = directory; LayoutEffectClient.layout_xml = LAYOUT_XML
        self.runtime = AgentRuntime(root, client_factory=LayoutEffectClient)
        self.runtime.preferences["state_adapter"] = {"plugin_slot": None, "timeout_seconds": 1.0, "importexport_path": str(directory)}
        self.core = AgentCore(self.runtime); self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    def test_validated_preset_group_and_unknown_tokens_resolve_safely(self):
        layout = LayoutExportProvider.parse(LAYOUT_XML, 1)
        self.assertEqual(layout["items"][0]["type"], "fixture")
        self.assertEqual(layout["items"][1]["type"], "macro")
        preset = layout["items"][2]
        self.assertEqual((preset["type"], preset["reference"], preset["ma2_class"], preset["provenance"]), ("preset", "4.2", "CMD_PRESET", "validated_real_ma2_3_9_probe"))
        group = layout["items"][3]
        self.assertEqual((group["type"], group["reference"], group["ma2_class"], group["provenance"]), ("group", 1, "CMD_GROUP", "validated_real_ma2_3_9_probe"))
        unknown = layout["items"][4]
        self.assertEqual(unknown["type"], "unknown")
        self.assertEqual(unknown["reference_tokens"], ["99", "1"])
        self.assertIsNone(unknown["validated_token_class"])
        self.assertEqual(set(VALIDATED_FIRST_TOKEN_CLASSES), {"17", "22"})
        self.assertIn("LayoutCObject", unknown["parent_path"])
        self.assertEqual([item["reference"] for item in LayoutObjectResolver.lighting_items(layout)], [101])
        conflicting = LayoutExportProvider.parse('''<MA><Group index="0"><LayoutData><CObjects>
<LayoutCObject><CObject><Token>17</Token><Token>1</Token><Token>1</Token></CObject></LayoutCObject>
</CObjects></LayoutData></Group></MA>''', 1)["items"][0]
        self.assertEqual((conflicting["type"], conflicting["resolved"]), ("unknown", False))

    def test_fixture_only_all_objects_and_group_layout_intersection(self):
        fixtures = self.core.handle_request("Layout 1 裡有哪些燈？")
        self.assertIn("Fixtures: 1", fixtures["message"])
        self.assertIn("Other objects: 4", fixtures["message"])
        self.assertNotIn("unknown", fixtures["message"])
        all_objects = self.core.handle_request("Layout 1 裡有哪些物件？")
        self.assertIn('Fixture 101 "Key"', all_objects["message"])
        self.assertIn('Macro 7 "Look"', all_objects["message"])
        self.assertIn('Preset 4.2 "Red"', all_objects["message"])
        self.assertIn('Group 1 "HYBRID"', all_objects["message"])
        self.assertIn("Unknown unresolved ['99', '1']", all_objects["message"])
        records = [json.loads(line) for line in (self.runtime.root / "logs" / "agent.jsonl").read_text(encoding="utf-8").splitlines()]
        diagnostics = [record["data"] for record in records if record["event"] == "layout_object_diagnostic"]
        self.assertGreaterEqual(len(diagnostics), 5)
        self.assertTrue(all({"raw_xml_tag", "raw_attributes", "parent_path", "reference_tokens", "name", "x", "y"} <= set(item) for item in diagnostics[-5:]))
        hybrid = self.core.handle_request("HYBRID 在 Layout 1 怎麼排？")
        self.assertEqual(hybrid["type"], "ANSWER")
        self.assertIn('Fixture 101 "Key"', hybrid["message"])

    def test_hybrid_group_button_is_not_a_fixture_and_reports_its_position(self):
        LayoutEffectClient.layout_xml = GROUP_ONLY_LAYOUT_XML
        fixtures = self.core.handle_request("Layout 1 裡有哪些燈？")
        self.assertIn("Fixtures: 0", fixtures["message"])
        self.assertIn("Other objects: 1", fixtures["message"])
        hybrid = self.core.handle_request("HYBRID 在 Layout 1 怎麼排？")
        self.assertEqual(hybrid["message"], 'Group 1 "HYBRID" is in Layout 1 at x=-4.85, y=-5.35.\nNo individual HYBRID fixture items are present.')

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
