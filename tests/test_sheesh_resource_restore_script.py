import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_real_ma2_test_show_sheesh.py"
SPEC = importlib.util.spec_from_file_location("sheesh_resource_restore_script", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class _Client:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        if command.startswith("List Preset 4."):
            return "Error #14: OBJECT DOES NOT EXIST"
        return ""


class _Runtime:
    def __init__(self, outputs):
        self.outputs = outputs
        self.client = _Client()

    def read_state(self, command):
        return self.outputs[command]


class _Core:
    def __init__(self, outputs):
        self.runtime = _Runtime(outputs)


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

    def test_failed_preflight_path_is_guarded_from_final_clear(self):
        source = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("write_started = False", source)
        self.assertIn("if core.runtime.ready and write_started:", source)


if __name__ == "__main__":
    unittest.main()
