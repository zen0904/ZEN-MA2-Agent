import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.builder import FirstSongBuildError, ShowPlanBuilder
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import ShowPlanSchemaError, validate_show_plan
from zen_ma2_agent.effect_resources import EffectRequirement, show_identity
from zen_ma2_agent.cue_effect_application import CueEffectApplicationCapability, CueEffectApplicationSpec
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.song_analysis import SongAnalysisAdapter, SongAnalysisError, ScriptSongParser, validate_song_analysis
from zen_ma2_agent.telnet_client import ConnectionState


INPUT = json.loads((Path(__file__).resolve().parents[1] / "examples" / "FIRST_SONG_INPUT.json").read_text(encoding="utf-8"))
ANALYSIS = json.loads((Path(__file__).resolve().parents[1] / "examples" / "REALISTIC_SONG_ANALYSIS.json").read_text(encoding="utf-8"))
REAL_ANALYSIS = json.loads((Path(__file__).resolve().parents[1] / "examples" / "ZEN_REAL_LIGHTING_DESIGN_TEST.json").read_text(encoding="utf-8"))


class FirstSongClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries, self.commands = [], []
        self.sequence_label = None
        self.sequence_number = None
        self.cues = []

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group": return 'Group 1 "HYBRID"\n'
        if command == "List Fixture": return 'Fixture 101 "Hybrid 1" (Hybrid)\n'
        if command.startswith("List Fixture "): return "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command == "List Preset All": return "Focus 6.1 6.1  narrow     Normal\nFocus 6.2 6.2  normal     Normal\n"
        if command == "List Preset 6.2": return "Focus 6.2 6.2  normal     Normal\n"
        if command == "List Preset 4.101": return "Color 4.101 4.101  ZEN_COLOR_01_RED     Normal\n"
        if command == "List Effect": return 'Effect 1000 DIM Low 1\nEffect 3520 "ZEN_FX_DIM_CHASE_SLOW_GROUP1"\n'
        if command == "List Effect 3520": return 'Effect 3520 "ZEN_FX_DIM_CHASE_SLOW_GROUP1"\n'
        if command == "List Sequence": return f'Sequence {self.sequence_number} "{self.sequence_label}"\n' if self.sequence_label else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command.startswith("List Cue ") and self.sequence_number is not None and f" Part 0 Sequence {self.sequence_number}" in command:
            number = int(command.split()[2])
            label, fade = next((label, fade) for cue, label, fade in self.cues if cue == number)
            return f"Cue 0 {label}  0      {fade:g}     InDelay\n"
        if command.startswith("Label Sequence "):
            self.sequence_number = int(command.split()[2])
            self.sequence_label = command.split('"', 2)[1]
        if command.startswith("Store Cue "):
            bits = command.split('"')
            number = int(command.split()[2]); label = bits[1]; fade = float(command.split(" Fade ", 1)[1].split()[0])
            self.cues.append((number, label, fade))
        return "Executing : " + command

    def close(self): self.state = ConnectionState.DISCONNECTED


class FirstSongBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-first-song-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.runtime = AgentRuntime(root, client_factory=FirstSongClient)
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self): self.temp.cleanup()

    def test_schema_rejects_raw_commands_and_missing_typed_action(self):
        with self.assertRaises(ShowPlanSchemaError):
            validate_show_plan({"schema": "zen.show_plan.v0.1", "cues": [{"id": "x", "actions": [{"command": "Store Cue 1"}]}]})
        with self.assertRaises(ShowPlanSchemaError):
            validate_show_plan({"schema": "zen.show_plan.v0.1", "cues": [{"id": "x", "cue_number": 1, "fade": 1, "actions": [{"operation": "RAW", "target": {}}]}]})

    def test_schema_rejects_any_existing_resource_modification_operation(self):
        with self.assertRaises(ShowPlanSchemaError):
            validate_show_plan({"schema": "zen.show_plan.v0.1", "cues": [{"id": "x", "cue_number": 1, "fade": 1, "actions": [{"operation": "MODIFY_PRESET", "target": {"type": "preset", "ref": "6.2"}}]}]})

    def test_designer_uses_scanned_focus_reference_and_records_missing_semantic_position(self):
        profile = {"groups": [{"group_id": 1, "name": "HYBRID"}], "presets": [{"preset_type": "FOCUS", "reference": "6.2", "name": "normal"}], "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "SUPPORTED"}}
        plan = FirstSongDesigner().design(INPUT, profile)
        self.assertEqual(plan["cues"][0]["actions"][0]["preset_ref"], "6.2")
        self.assertIn("No exact POS_STAGE_*", plan["warnings"][0])

    def test_preview_is_dynamic_approved_and_verifies_owned_sequence_and_cues(self):
        response = self.core.preview_first_song(INPUT)
        self.assertEqual(response["type"], "ACTION_PLAN")
        self.assertIn("Target Sequence: 1", response["message"])
        self.assertIn("At Preset 6.2", response["message"])
        self.assertNotIn("Store Cue", self.runtime.client.commands)
        result = self.core.approve_action(response["action"]["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertIn("Verification: PARTIAL", result["result"])
        self.assertEqual(self.runtime.client.sequence_label, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST")
        self.assertEqual(len(self.runtime.client.cues), 7)
        self.assertEqual(self.runtime.client.commands.count("ClearAll"), 2)

    def test_runtime_allows_exact_preset_ref_and_still_rejects_arbitrary_preset_text(self):
        self.assertIn(
            "ZEN_COLOR_01_RED",
            self.runtime.read_state("List Preset 4.101"),
        )
        with self.assertRaises(PermissionError):
            self.runtime.read_state('List Preset 4.101 /nc')

    def test_post_build_verification_uses_exact_preset_lookup_when_all_inventory_omits_it(self):
        lines = self.core._fresh_verify_preset_references({"4.101"})
        self.assertEqual(lines, ["4.101 — ZEN_COLOR_01_RED"])
        self.assertIn("List Preset 4.101", self.runtime.client.commands)
        self.assertNotEqual(self.runtime.client.commands[-1], "List Preset All")

    def test_designer_defaults_missing_sequence_range_to_front_first_pool(self):
        data = dict(INPUT)
        data.pop("active_sequence_range", None)
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}],
            "effects": [],
        }
        plan = FirstSongDesigner().design(data, profile)
        self.assertEqual(plan["active_sequence_range"], [1, 9999])

    def test_unavailable_active_range_blocks_without_writes(self):
        bad = dict(INPUT); bad["active_sequence_range"] = [301, 300]
        with self.assertRaises(ValueError):
            self.core.preview_first_song(bad)

    def test_allocator_skips_scanned_used_slot_and_never_overwrites(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}],
            "sequences": [{"number": 1, "name": "USER_SEQUENCE"}],
        }
        plan = FirstSongDesigner().design(INPUT, profile)
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertEqual(workflow.task.intent.parameters["sequence"], 2)
        self.assertNotIn("Store Cue 1 Sequence 1", workflow.preview_note)

    def test_repeated_song_label_uses_sequence_scoped_operational_label(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [],
            "effects": [],
            "sequences": [
                {"number": 2, "name": "ZEN_AI_TEST_SHEESH"},
            ],
        }
        plan = {
            "schema": "zen.show_plan.v0.1",
            "song": "SHEESH",
            "target_executor": "2.003",
            "active_sequence_range": [3, 3],
            "cues": [{
                "id": "intro",
                "cue_number": 1,
                "label": "INTRO",
                "fade": 1.0,
                "actions": [
                    {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 20},
                ],
            }],
        }
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertEqual(workflow.task.intent.parameters["sequence"], 3)
        self.assertEqual(
            workflow.task.intent.parameters["sequence_label"],
            "ZEN_AI_TEST_SHEESH_SEQ3",
        )
        self.assertIn('Label Sequence 3 "ZEN_AI_TEST_SHEESH_SEQ3" /nc', workflow.commands)
        self.assertIn('Label Executor 2.1 "ZEN_AI_TEST_SHEESH_SEQ3" /nc', workflow.commands)

    def test_sequence_scoped_label_collision_advances_to_unique_suffix(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [],
            "effects": [],
            "sequences": [
                {"number": 1, "name": "ZEN_AI_TEST_SHEESH"},
                {"number": 2, "name": "ZEN_AI_TEST_SHEESH_SEQ3"},
            ],
        }
        plan = {
            "schema": "zen.show_plan.v0.1",
            "song": "SHEESH",
            "active_sequence_range": [3, 3],
            "cues": [{
                "id": "intro",
                "cue_number": 1,
                "label": "INTRO",
                "fade": 1.0,
                "actions": [
                    {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 20},
                ],
            }],
        }
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertEqual(workflow.task.intent.parameters["sequence_label"], "ZEN_AI_TEST_SHEESH_SEQ3_2")

    def test_optional_page_two_executor_assignment_is_allowlisted(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}],
            "effects": [],
            "sequences": [],
        }
        plan = {
            "schema": "zen.show_plan.v0.1",
            "song": "SHEESH",
            "target_executor": "2.001",
            "active_sequence_range": [301, 400],
            "cues": [{
                "id": "intro", "cue_number": 1, "label": "INTRO", "fade": 1.0,
                "actions": [{"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 20}],
            }],
        }
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        commands = workflow.commands
        self.assertIn("Assign Sequence 301 At Executor 2.1 /nc", commands)
        self.assertIn('Label Executor 2.1 "ZEN_AI_TEST_SHEESH" /nc', commands)
        self.assertEqual(workflow.task.intent.parameters["target_executor"], "2.001")

    def test_executor_allocator_skips_occupied_slots_from_the_front(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [],
            "effects": [],
            "sequences": [],
            "executors": [{"page": 2, "executor": 1}, {"page": 2, "executor": 2}],
        }
        plan = {
            "schema": "zen.show_plan.v0.1", "song": "SHEESH",
            "target_executor": "2.999", "active_sequence_range": [1, 1],
            "cues": [{"id": "intro", "cue_number": 1, "label": "INTRO", "fade": 1.0,
                      "actions": [{"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 20}]}],
        }
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertIn("Assign Sequence 1 At Executor 2.3 /nc", workflow.commands)

    def test_narrow_rollback_needs_exact_agent_ownership_proof(self):
        command = ShowPlanBuilder.narrow_rollback_command(201, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST", {"number": 201, "name": "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST"})
        self.assertEqual(command, "Delete Sequence 201 /nc")
        with self.assertRaises(FirstSongBuildError):
            ShowPlanBuilder.narrow_rollback_command(201, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST", {"number": 201, "name": "USER_SEQUENCE"})

    def test_script_parser_manual_override_and_role_vocabulary_are_explicit(self):
        analysis = ScriptSongParser().parse("00:00 Intro\n00:18 Verse\n00:46 Chorus\n01:15 Sax Solo", title="Script Test", active_sequence_range=[301, 400])
        self.assertEqual([item["role"] for item in analysis["sections"]], ["INTRO", "VERSE", "CHORUS", "SOLO"])
        self.assertEqual(analysis["sections"][0]["end"], 18.0)
        overridden = validate_song_analysis({**analysis, "manual_overrides": [{"section_id": "solo_4", "force_role": "SOLO", "force_energy": 0.75, "lighting_note": "Sax at stage left"}]})
        self.assertEqual(overridden["sections"][-1]["energy"], 0.75)
        self.assertIn("Sax at stage left", overridden["sections"][-1]["notes"])

    def test_song_analysis_rejects_overlap_out_of_range_energy_and_transport(self):
        overlap = json.loads(json.dumps(ANALYSIS)); overlap["sections"][1]["start"] = 1.0
        with self.assertRaises(SongAnalysisError): validate_song_analysis(overlap)
        unsafe = json.loads(json.dumps(ANALYSIS)); unsafe["sections"][0]["telnet"] = "Store Cue 1"
        with self.assertRaises(SongAnalysisError): validate_song_analysis(unsafe)
        invalid_energy = json.loads(json.dumps(ANALYSIS)); invalid_energy["sections"][0]["energy"] = 1.1
        with self.assertRaises(SongAnalysisError): validate_song_analysis(invalid_energy)

    def test_song_analysis_adapter_varies_repeated_choruses_and_bounds_accent_density(self):
        profile = {"groups": [{"group_id": 1, "name": "HYBRID"}], "presets": [{"preset_type": "FOCUS", "reference": "6.2", "name": "normal"}], "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "SUPPORTED"}}
        designer_input = SongAnalysisAdapter().to_designer_input(ANALYSIS)
        plan = FirstSongDesigner().design(designer_input, profile)
        choruses = [cue for cue in plan["cues"] if cue.get("role") == "CHORUS" and "ACCENT" not in cue["label"]]
        levels = [cue["actions"][1]["level"] for cue in choruses]
        self.assertGreater(levels[-1], levels[0])
        self.assertLessEqual(len([cue for cue in plan["cues"] if cue["source_section_id"] == "chorus_1"]), 2)
        self.assertGreaterEqual(len(plan["cues"]), 10)

    def test_song_analysis_uses_same_core_preview_and_approval_path(self):
        response = self.core.preview_song_analysis(ANALYSIS)
        self.assertEqual(response["type"], "ACTION_PLAN")
        self.assertIn("ZEN_REAL_SONG_ANALYSIS_TEST", response["message"])
        self.assertNotIn("Store Cue", self.runtime.client.commands)
        self.assertTrue((Path(self.runtime.root) / "data" / "ZEN_SONG_ANALYSIS.json").is_file())
        result = self.core.approve_action(response["action"]["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertGreaterEqual(len(self.runtime.client.cues), 10)

    def test_real_song_analysis_reuses_verified_effect_and_builds_multi_cue_plan(self):
        for resource, kwargs in (("groups", {}), ("fixtures", {}), ("presets", {"sequence": "ALL"}), ("effects", {}), ("sequences", {})):
            self.core.refresh_state(resource, **kwargs)
        profile = self.core.scan_show_profile()
        requirement = EffectRequirement.from_dict({
            "feature": "DIMMER", "family": "CHASE", "waveform": "PWM", "low": 0, "high": 100,
            "speed_class": "SLOW", "speed_bpm": 30, "phase": "0..360", "direction": "forward", "groups": 1,
            "target_type": "group", "target_ref": 1, "target_name": "HYBRID",
        })
        self.core.effect_catalog.record(requirement=requirement, effect_id=3520, label="ZEN_FX_DIM_CHASE_SLOW_GROUP1", identity=show_identity(profile), verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"})
        CueEffectApplicationCapability(self.runtime.root).record_content_verified(
            CueEffectApplicationSpec(3520, "ZEN_FX_DIM_CHASE_SLOW_GROUP1", 1, "HYBRID", 299, "ZEN_AI_EFFECT_CALL_TEST_299"),
            sequence_export_sha256="a" * 64,
        )
        preview = self.core.preview_song_analysis(REAL_ANALYSIS)
        self.assertIn("ZEN AI REAL SONG BUILD PREVIEW", preview["message"])
        self.assertIn("ZEN_FX_DIM_CHASE_SLOW_GROUP1", preview["message"])
        self.assertEqual(preview["action"]["task"]["intent"]["parameters"]["cue_count"], 10)
        cues = preview["action"]["task"]["intent"]["parameters"]["cues"]
        self.assertEqual(sum(action["operation"] == "CALL_EFFECT" for cue in cues for action in cue["actions"]), 5)
        self.assertFalse(any(command.startswith("Store Cue") for command in self.runtime.client.commands))
        result = self.core.approve_action(preview["action"]["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(len(self.runtime.client.cues), 10)
        self.assertEqual(self.runtime.client.commands.count("At Effect 3520"), 5)
        self.assertEqual(self.runtime.client.commands.count("ClearAll"), 2)
        report = Path(self.runtime.root) / "ZEN_REAL_SONG_DESIGN_REPORT.md"
        self.assertTrue(report.is_file())
        self.assertIn("Repeated-section variation", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
