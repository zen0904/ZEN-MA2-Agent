import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.builder import FirstSongBuildError, ShowPlanBuilder
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import ShowPlanSchemaError, validate_show_plan
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


INPUT = json.loads((Path(__file__).resolve().parents[1] / "examples" / "FIRST_SONG_INPUT.json").read_text(encoding="utf-8"))


class FirstSongClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries, self.commands = [], []
        self.sequence_label = None
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
        if command == "List Effect": return "Effect 1000 DIM Low 1\n"
        if command == "List Sequence": return f'Sequence 201 "{self.sequence_label}"\n' if self.sequence_label else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command.startswith("List Cue ") and " Part 0 Sequence 201" in command:
            number = int(command.split()[2])
            label, fade = next((label, fade) for cue, label, fade in self.cues if cue == number)
            return f"Cue 0 {label}  0      {fade:g}     InDelay\n"
        if command.startswith("Label Sequence 201 "):
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
        self.assertIn("Target Sequence: 201", response["message"])
        self.assertIn("At Preset 6.2", response["message"])
        self.assertNotIn("Store Cue", self.runtime.client.commands)
        result = self.core.approve_action(response["action"]["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertIn("Verification: PARTIAL", result["result"])
        self.assertEqual(self.runtime.client.sequence_label, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST")
        self.assertEqual(len(self.runtime.client.cues), 7)
        self.assertEqual(self.runtime.client.commands.count("ClearAll"), 2)

    def test_unavailable_active_range_blocks_without_writes(self):
        bad = dict(INPUT); bad["active_sequence_range"] = [201, 200]
        with self.assertRaises(ValueError):
            self.core.preview_first_song(bad)

    def test_allocator_skips_scanned_used_slot_and_never_overwrites(self):
        profile = {
            "groups": [{"group_id": 1, "name": "HYBRID"}],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}],
            "sequences": [{"number": 201, "name": "USER_SEQUENCE"}],
        }
        plan = FirstSongDesigner().design(INPUT, profile)
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertEqual(workflow.task.intent.parameters["sequence"], 202)
        self.assertNotIn("Store Cue 1 Sequence 201", workflow.preview_note)

    def test_narrow_rollback_needs_exact_agent_ownership_proof(self):
        command = ShowPlanBuilder.narrow_rollback_command(201, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST", {"number": 201, "name": "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST"})
        self.assertEqual(command, "Delete Sequence 201 /nc")
        with self.assertRaises(FirstSongBuildError):
            ShowPlanBuilder.narrow_rollback_command(201, "ZEN_AI_TEST_ZEN_FIRST_SONG_TEST", {"number": 201, "name": "USER_SEQUENCE"})


if __name__ == "__main__":
    unittest.main()
