import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.builder import ShowPlanBuilder
from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.designer import SHOW_PLAN_SCHEMA, validate_show_plan
from zen_ma2_agent.designer.schema import ShowPlanSchemaError
from zen_ma2_agent.fixture_profiler import FixtureProfiler
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.scanner import ShowScanner
from zen_ma2_agent.state.store import StateStore


class ScannerDesignerProfilerPocTests(unittest.TestCase):
    def setUp(self):
        self.state = StateStore()
        self.state.put("fixtures", [{"number": 101, "name": "Hybrid 1", "fixture_type": "Hybrid"}], source="ma2_telnet_list")
        self.state.put("groups", [{"number": 1, "name": "HYBRID"}], source="ma2_telnet_list")
        self.state.put("group_membership", [{"group_no": 1, "fixtures": [108, 101, 104], "source": "ma2_export_group_xml"}], source="ma2_export_group_xml")
        self.state.put("presets", [{"preset_type": "POSITION", "number": 1, "name": "POS_HOME"}], source="ma2_telnet_list")
        self.state.put("effects", [{"number": 18, "name": "MOVE", "kind": "SELECTIVE", "line_count": 1, "attributes": ["Pan"]}], source="ma2_telnet_list")

    def test_scanner_preserves_group_export_order_and_unknown_values(self):
        profile = ShowScanner().scan(self.state)
        self.assertTrue(profile["read_only"])
        self.assertEqual(profile["groups"][0]["fixture_ids_in_selection_order"], [108, 101, 104])
        self.assertEqual(profile["groups"][0]["fixture_refs_in_selection_order"], [])
        self.assertEqual(profile["fixtures"][0]["stage_position"]["status"], "UNAVAILABLE")
        self.assertEqual(profile["semantic_presets"][0]["semantic_role"], "HOME")
        self.assertEqual(profile["presets"][0]["stored_values"]["status"], "UNAVAILABLE")
        self.assertEqual(profile["effects"][0]["effect_lines"]["status"], "UNAVAILABLE")

    def test_scanner_preserves_exact_subfixture_refs_without_deduplication(self):
        self.state.put("group_membership", [{"group_no": 1, "fixtures": [701, 701, 702, 702], "fixture_refs": ["701.1", "701.2", "702.1", "702.2"], "source": "ma2_export_group_xml"}], source="ma2_export_group_xml")
        group = ShowScanner().scan(self.state)["groups"][0]
        self.assertEqual(group["fixture_ids_in_selection_order"], [701, 701, 702, 702])
        self.assertEqual(group["fixture_refs_in_selection_order"], ["701.1", "701.2", "702.1", "702.2"])

    def test_designer_rejects_embedded_transport_text_and_builder_is_non_executable(self):
        plan = {"schema": SHOW_PLAN_SCHEMA, "cues": [{"id": "cue-4", "intent": {"group_id": 1, "effect_id": 18, "semantic_position": "CENTER"}}]}
        profile = ShowScanner().scan(self.state)
        workflow = ShowPlanBuilder().draft(validate_show_plan(plan), profile)
        self.assertFalse(workflow.executable)
        self.assertEqual(workflow.commands, ())
        with self.assertRaises(ShowPlanSchemaError):
            validate_show_plan({"schema": SHOW_PLAN_SCHEMA, "cues": [{"id": "bad", "intent": {"command": "Store Cue 1"}}]})

    def test_fixture_profile_draft_keeps_observed_point_and_range_unknown(self):
        draft = FixtureProfiler().draft([{"fixture_id": 101, "fixture_type": "TEMP 18CH", "preset_id": 4, "preset_name": "COLOR_RED", "attribute": "COLOR1", "observed_dmx": 37, "evidence": "VERIFIED_PRESET"}])
        point = draft["observations"][0]
        self.assertEqual((point["observed_dmx"], point["range"], point["coarse_fine_relation"]), (37, "UNKNOWN", "UNVERIFIED_FINE_MAPPING"))
        self.assertEqual(draft["limits"]["automatic_preset_raw_capture"], "NOT_IMPLEMENTED")

    def test_scanner_json_artifact_is_local_only(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "ZEN_SHOW_PROFILE.json"
            ShowScanner().write(self.state, target)
            self.assertIn('"schema": "zen.show_profile.v0.1"', target.read_text(encoding="utf-8"))

    def test_agent_core_exposes_the_same_read_only_scanner_path(self):
        with tempfile.TemporaryDirectory() as folder:
            core = AgentCore(AgentRuntime(Path(folder)))
            core.state.put("fixtures", [{"number": 101, "name": "Hybrid 1"}], source="test")
            profile = core.scan_show_profile(Path(folder) / "ZEN_SHOW_PROFILE.json")
            self.assertTrue(profile["read_only"])
            self.assertEqual(profile["fixtures"][0]["fixture_id"], 101)


if __name__ == "__main__":
    unittest.main()
