import unittest

from scripts.run_sheesh_programming_test import _resume_saved_canonical_artifact


class SheeshSavedRetryTests(unittest.TestCase):
    def test_canonical_retry_keeps_artistic_actions_and_only_reallocates_runtime_metadata(self):
        saved = {
            "provider_plan_compile": {"provider_contract": "ARTISTIC_CUES_V0_2"},
            "canonical_artifact": {
                "schema": "zen.show_plan.v0.1",
                "song": "SHEESH",
                "target_executor": "2.002",
                "active_sequence_range": [2, 2],
                "cues": [{
                    "id": "cue_001", "cue_number": 1, "label": "INTRO", "fade": 1.0,
                    "actions": [{"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 25}],
                }],
            }
        }
        resumed = _resume_saved_canonical_artifact(saved, sequence=3, target_executor="2.003")
        self.assertEqual(resumed["active_sequence_range"], [3, 3])
        self.assertEqual(resumed["target_executor"], "2.003")
        self.assertEqual(resumed["cues"], saved["canonical_artifact"]["cues"])

    def test_invalid_saved_canonical_artifact_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "SAVED_CANONICAL_ARTIFACT_INVALID"):
            _resume_saved_canonical_artifact(
                {
                    "provider_plan_compile": {"provider_contract": "ARTISTIC_CUES_V0_2"},
                    "canonical_artifact": {"schema": "wrong"},
                },
                sequence=1,
                target_executor="2.001",
            )

    def test_canonical_without_compile_evidence_uses_legacy_saved_result_path(self):
        self.assertIsNone(
            _resume_saved_canonical_artifact(
                {"canonical_artifact": {"schema": "zen.show_plan.v0.1"}},
                sequence=1,
                target_executor="2.001",
            )
        )


if __name__ == "__main__":
    unittest.main()
