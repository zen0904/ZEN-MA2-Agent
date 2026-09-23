import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_real_ma2_test_show_sheesh.py"
SPEC = importlib.util.spec_from_file_location("sheesh_resource_restore_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class _Client:
    def __init__(self, detail_outputs=None, preset_outputs=None):
        self.commands = []
        self.detail_outputs = dict(detail_outputs or {})
        self.preset_outputs = dict(preset_outputs or {})

    def execute(self, command):
        self.commands.append(command)
        if command.startswith("List Preset 4."):
            return self.preset_outputs.get(command, "Error #14: OBJECT DOES NOT EXIST")
        if command.startswith("List Effect 1."):
            return self.detail_outputs.get(command, "")
        return ""


class _Runtime:
    def __init__(self, outputs, detail_outputs=None, preset_outputs=None):
        self.outputs = outputs
        self.client = _Client(detail_outputs, preset_outputs)

    def read_state(self, command):
        return self.outputs[command]


class _Core:
    def __init__(self, outputs, detail_outputs=None, preset_outputs=None):
        self.runtime = _Runtime(outputs, detail_outputs, preset_outputs)


def _outputs():
    groups = "\n".join(
        f'Group {number} "{label}"'
        for number, label in MODULE.EXPECTED_GROUPS.items()
    )
    fixtures = "\n".join(
        [
            'Fixture 101 "A"',
            'Fixture 201 "B"',
            'Fixture 301 "C"',
            'Fixture 401 "D"',
            'Fixture 501 "E"',
            'Fixture 601 "F"',
            'Fixture 701 "G"',
            'Fixture 9999 "PROTECTED"',
        ]
    )
    return {
        "List Group": groups,
        "List Fixture": fixtures,
        "List Sequence": 'Sequ 2 "LEAN"\nSequ 901 "ZEN_SHEESH_TEST"\n',
        "List Executor": 'Executor 2.002 Sequence=Seq 2 "ZEN_SHEESH_LEAN"\n',
    }


class SheeshResourceRestoreScriptTests(unittest.TestCase):
    def test_resources_only_preflight_does_not_require_legacy_executor_assignment(self):
        core = _Core(_outputs())
        reads = {}
        MODULE._assert_preflight(
            core,
            reads,
            resume_existing_build=True,
            require_owned_executor=False,
        )
        self.assertIn("List Executor", reads)

    def test_resume_path_still_requires_exact_legacy_executor_assignment(self):
        core = _Core(_outputs())
        with self.assertRaisesRegex(RuntimeError, "not the exact owned SHEESH assignment"):
            MODULE._assert_preflight(
                core,
                {},
                resume_existing_build=True,
                require_owned_executor=True,
            )


    def test_fresh_build_allocates_sequence_executor_and_palette_from_front(self):
        outputs = _outputs()
        outputs["List Sequence"] = 'Sequence 1 "A"\nSequence 2 "B"\n'
        outputs["List Executor"] = (
            'Executor 1.001 Sequence=Seq 1 "A"\n'
            'Executor 1.002 Sequence=Seq 2 "B"\n'
        )
        core = _Core(outputs)
        reads = {}
        plan = MODULE._load_plan(MODULE.PLAN_PATH)
        MODULE._assert_test_show_identity(core, reads)
        remapped, sequence, label, executor_display, executor_address = MODULE._allocate_fresh_build(
            core,
            plan,
            reads,
        )
        self.assertEqual(sequence, 3)
        self.assertEqual(executor_display, "1.003")
        self.assertEqual(executor_address, "1.3")
        self.assertEqual(label, "ZEN_SHEESH_TEST")
        self.assertEqual(
            [entry["preset"] for entry in remapped["test_palette"]],
            list(range(1, 14)),
        )
        self.assertTrue(
            all(
                action.get("preset_ref", "").split(".", 1)[1].isdigit()
                for cue in remapped["cues"]
                for action in cue["actions"]
                if action.get("operation") == "CALL_PRESET"
            )
        )

    def test_fresh_cue_commands_never_fall_back_to_legacy_901_or_executor_201(self):
        plan = MODULE._load_plan(MODULE.PLAN_PATH)
        commands = [
            command
            for command, _ in MODULE._cue_commands(
                plan,
                sequence=3,
                sequence_label="ZEN_SHEESH_TEST_SEQ3",
                executor_address="1.3",
            )
        ]
        self.assertTrue(any("Sequence 3" in command for command in commands))
        self.assertIn('Assign Sequence 3 At Executor 1.3 /nc', commands)
        self.assertNotIn('Assign Sequence 901 At Executor 201 /nc', commands)

    def test_effect_rows_upgrade_exact_reserved_label_only_from_qty_none(self):
        outputs = _outputs()
        outputs["List Effect"] = (
            'Effect 2500 "FX_DIM_CHASE_SLOW"\n'
            'Effect 2501 "UNRELATED"\n'
        )
        core = _Core(
            outputs,
            {"List Effect 1.2500.*": "Effect 1.2500.1\nQTY=None\n"},
        )
        rows = MODULE._effect_rows(core, {})
        slow = next(row for row in rows if row["number"] == 2500)
        unrelated = next(row for row in rows if row["number"] == 2501)
        self.assertEqual(slow["kind"], "TEMPLATE")
        self.assertEqual(slow["template_detail"]["reason"], "ALL_EFFECT_LINES_QTY_NONE")
        self.assertIsNone(unrelated["kind"])
        self.assertNotIn("List Effect 1.2501.*", core.runtime.client.commands)

    def test_effect_rows_marks_reserved_selective_and_does_not_promote_it(self):
        outputs = _outputs()
        outputs["List Effect"] = 'Effect 2500 "FX_DIM_CHASE_SLOW"\n'
        core = _Core(
            outputs,
            {"List Effect 1.2500.*": "Effect 1.2500.1\nQTY=8\n"},
        )
        rows = MODULE._effect_rows(core, {})
        self.assertEqual(rows[0]["kind"], "SELECTIVE")

    def test_fresh_build_uses_first_free_sequence_executor_and_color_slots(self):
        outputs = _outputs()
        outputs["List Sequence"] = (
            'Sequ 1 1 FIRST On 0 0\n'
            'Sequ 2 2 SECOND On 0 0\n'
        )
        outputs["List Executor"] = (
            'Executor 1.001 Sequence=Seq 1 "FIRST"\n'
            'Executor 1.002 Sequence=Seq 2 "SECOND"\n'
        )
        core = _Core(
            outputs,
            preset_outputs={
                "List Preset 4.1": 'Color 4.1 4.1 FOREIGN Normal\n',
            },
        )
        plan = MODULE._load_plan(MODULE.PLAN_PATH)

        remapped, sequence, label, executor_display, executor_address = MODULE._allocate_fresh_build(
            core,
            plan,
            {},
        )

        self.assertEqual(sequence, 3)
        self.assertEqual(executor_display, "1.003")
        self.assertEqual(executor_address, "1.3")
        self.assertEqual(label, "ZEN_SHEESH_TEST")
        self.assertEqual(
            [entry["preset"] for entry in remapped["test_palette"]],
            list(range(2, 15)),
        )
        refs = {
            action["preset_ref"]
            for cue in remapped["cues"]
            for action in cue["actions"]
            if action.get("operation") == "CALL_PRESET"
        }
        self.assertNotIn("4.101", refs)
        self.assertTrue(refs <= {f"4.{number}" for number in range(2, 15)})

    def test_fresh_palette_reuses_exact_owned_semantic_resource_before_creating_duplicate(self):
        core = _Core(
            _outputs(),
            preset_outputs={
                "List Preset 4.101": 'Color 4.101 4.101 ZEN_COLOR_01_RED Normal\n',
            },
        )
        plan = MODULE._load_plan(MODULE.PLAN_PATH)

        remapped = MODULE._allocate_fresh_palette(core, plan, {})

        self.assertEqual(remapped["test_palette"][0]["preset"], 101)
        self.assertEqual(remapped["test_palette"][1]["preset"], 1)
        self.assertEqual(
            remapped["cues"][2]["actions"][0]["preset_ref"],
            "4.101",
        )

    def test_runtime_cue_commands_use_allocated_ids_not_legacy_tail_ids(self):
        plan = MODULE._load_plan(MODULE.PLAN_PATH)
        commands = [
            command
            for command, _step in MODULE._cue_commands(
                plan,
                sequence=3,
                sequence_label="ZEN_SHEESH_TEST_SEQ3",
                executor_address="1.3",
            )
        ]
        self.assertTrue(any("Sequence 3" in command for command in commands))
        self.assertIn('Assign Sequence 3 At Executor 1.3 /nc', commands)
        self.assertIn('Label Executor 1.3 "ZEN_SHEESH_TEST_SEQ3" /nc', commands)
        self.assertFalse(any("Sequence 901" in command for command in commands))
        self.assertFalse(any("Executor 201" in command for command in commands))

    def test_noop_or_failed_read_only_path_is_guarded_from_final_clear(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("if core.runtime.ready and audit:", source)
        self.assertNotIn("write_started = False", source)


if __name__ == "__main__":
    unittest.main()
