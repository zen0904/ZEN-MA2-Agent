import unittest

from scripts.run_sheesh_programming_test import (
    _attach_effect_identity_labels,
    _augment_canonical_referenced_resources,
    _recover_prior_postwrite_build,
    _resume_saved_canonical_artifact,
)


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

    def test_canonical_retry_refreshes_exact_referenced_preset_and_effect_without_artistic_recompile(self):
        class Client:
            def execute(self, command):
                if command == "List Preset 4.110":
                    return "Color 4.110 4.110 ZEN_COLOR_10_MAGENTA Normal"
                if command == "List Effect 2500":
                    return 'Effect 2500 "FX_DIM_CHASE_SLOW"'
                raise AssertionError(command)

        class Runtime:
            client = Client()

        class Core:
            runtime = Runtime()

        profile = {"presets": [], "effects": []}
        plan = {
            "cues": [{
                "actions": [
                    {"operation": "CALL_PRESET", "preset_ref": "4.110"},
                    {"operation": "CALL_EFFECT", "effect_ref": {"id": 2500}},
                ],
            }],
        }
        refreshed = _augment_canonical_referenced_resources(Core(), profile, plan)
        self.assertEqual(refreshed, {"presets": ["4.110"], "effects": [2500]})
        self.assertEqual(profile["presets"][0]["reference"], "4.110")
        self.assertEqual(profile["effects"][0]["effect_id"], 2500)

    def test_canonical_retry_fails_only_when_a_referenced_resource_is_actually_missing(self):
        class Client:
            def execute(self, command):
                return "Error #14: OBJECT DOES NOT EXIST"

        class Runtime:
            client = Client()

        class Core:
            runtime = Runtime()

        with self.assertRaisesRegex(RuntimeError, "SAVED_CANONICAL_PRESET_NOT_PRESENT"):
            _augment_canonical_referenced_resources(
                Core(),
                {"presets": [], "effects": []},
                {"cues": [{"actions": [{"operation": "CALL_PRESET", "preset_ref": "4.110"}]}]},
            )

    def test_compile_boundary_attaches_exact_verified_effect_label(self):
        plan = {
            "schema": "zen.show_plan.v0.1",
            "song": "SHEESH",
            "target_executor": "2.001",
            "active_sequence_range": [3, 3],
            "cues": [{
                "id": "cue_001",
                "cue_number": 1,
                "label": "HIT",
                "fade": 0,
                "actions": [{
                    "operation": "CALL_EFFECT",
                    "target": {"type": "group", "ref": 1},
                    "effect_ref": {"id": 2500},
                }],
            }],
        }
        resource_map = {
            "groups": [{
                "group_id": 1,
                "effect_resources": [{
                    "effect_id": 2500,
                    "name": "FX_DIM_CHASE_SLOW",
                    "application_status": "REAL_MACHINE_CONTENT_VERIFIED",
                }],
            }],
        }

        normalized = _attach_effect_identity_labels(plan, resource_map)

        self.assertEqual(
            normalized["cues"][0]["actions"][0]["effect_ref"],
            {"id": 2500, "label": "FX_DIM_CHASE_SLOW"},
        )
        self.assertEqual(plan["cues"][0]["actions"][0]["effect_ref"], {"id": 2500})

    def test_old_id_only_canonical_retry_hydrates_effect_label_from_saved_verified_map(self):
        saved = {
            "provider_plan_compile": {"provider_contract": "ARTISTIC_CUES_V0_2"},
            "artistic_resource_map": {
                "groups": [{
                    "group_id": 1,
                    "effect_resources": [{
                        "effect_id": 2500,
                        "name": "FX_DIM_CHASE_SLOW",
                    "application_status": "REAL_MACHINE_CONTENT_VERIFIED",
                }],
                }],
            },
            "canonical_artifact": {
                "schema": "zen.show_plan.v0.1",
                "song": "SHEESH",
                "target_executor": "2.002",
                "active_sequence_range": [2, 2],
                "cues": [{
                    "id": "cue_001",
                    "cue_number": 1,
                    "label": "HIT",
                    "fade": 0,
                    "actions": [{
                        "operation": "CALL_EFFECT",
                        "target": {"type": "group", "ref": 1},
                        "effect_ref": {"id": 2500},
                    }],
                }],
            },
        }

        resumed = _resume_saved_canonical_artifact(
            saved,
            sequence=3,
            target_executor="2.003",
        )

        self.assertEqual(
            resumed["cues"][0]["actions"][0]["effect_ref"],
            {"id": 2500, "label": "FX_DIM_CHASE_SLOW"},
        )
        self.assertEqual(saved["canonical_artifact"]["cues"][0]["actions"][0]["effect_ref"], {"id": 2500})

    def test_canonical_retry_rejects_current_effect_label_drift_before_writes(self):
        class Client:
            def execute(self, command):
                if command == "List Effect 2500":
                    return 'Effect 2500 "WRONG_EFFECT"'
                raise AssertionError(command)

        class Runtime:
            client = Client()

        class Core:
            runtime = Runtime()

        plan = {
            "cues": [{
                "actions": [{
                    "operation": "CALL_EFFECT",
                    "effect_ref": {"id": 2500, "label": "FX_DIM_CHASE_SLOW"},
                }],
            }],
        }
        with self.assertRaisesRegex(RuntimeError, "SAVED_CANONICAL_EFFECT_IDENTITY_MISMATCH:2500"):
            _augment_canonical_referenced_resources(
                Core(),
                {"presets": [], "effects": []},
                plan,
            )

    def test_postwrite_verification_failure_recovers_existing_build_without_writes(self):
        class Runtime:
            def read_state(self, command):
                if command == "List Executor":
                    return 'Executor 2.3 Sequence=Seq 3 "ZEN_AI_TEST_SHEESH_SEQ3"'
                raise AssertionError(command)

        class Core:
            runtime = Runtime()

            def verify_first_song_metadata(self, sequence, label, cues, cue_labels):
                self.metadata = (sequence, label, cues, cue_labels)
                return "Verification: PARTIAL"

            def _fresh_verify_effect_references(self, show_plan):
                return ["2500 — FX_DIM_CHASE_SLOW"]

            def _fresh_verify_preset_references(self, references):
                return [f"{reference} — COLOR" for reference in sorted(references)]

        saved = {
            "status": "FAILED",
            "error": "FirstSongBuildError: Verification failed: referenced Preset is no longer present: 4.101",
            "preview": {
                "action": {
                    "task": {
                        "intent": {
                            "parameters": {
                                "sequence": 3,
                                "sequence_label": "ZEN_AI_TEST_SHEESH_SEQ3",
                                "target_executor": "2.003",
                                "cue_labels": ["INTRO"],
                                "cues": [{
                                    "cue_number": 1,
                                    "label": "INTRO",
                                    "fade": 1,
                                    "actions": [{
                                        "operation": "CALL_EFFECT",
                                        "target": {"type": "group", "ref": 1},
                                        "effect_ref": {"id": 2500, "label": "FX_DIM_CHASE_SLOW"},
                                    }],
                                }],
                                "referenced_presets": ["4.101"],
                            },
                        },
                    },
                },
            },
        }

        recovered = _recover_prior_postwrite_build(Core(), saved)

        self.assertEqual(recovered["sequence"], 3)
        self.assertEqual(recovered["sequence_label"], "ZEN_AI_TEST_SHEESH_SEQ3")
        self.assertEqual(recovered["target_executor"], "2.003")
        self.assertEqual(recovered["cue_count"], 1)
        self.assertTrue(recovered["executor_verified"])
        self.assertEqual(recovered["preset_lines"], ["4.101 — COLOR"])

    def test_runner_checks_postwrite_recovery_before_new_allocation_or_broad_refresh(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "scripts" / "run_sheesh_programming_test.py").read_text(encoding="utf-8")
        run_source = source[source.index("def run("):]
        recovery = run_source.index("recovered = _recover_prior_postwrite_build(core, saved)")
        broad_refresh = run_source.index('for resource, kwargs in (')
        sequence_allocation = run_source.index("selected_sequence = _lowest_safe_sequence_id(context)")
        executor_allocation = run_source.index("target_executor = first_free_executor(executor_before, page=target_page)")
        self.assertLess(recovery, broad_refresh)
        self.assertLess(recovery, sequence_allocation)
        self.assertLess(recovery, executor_allocation)

    def test_non_postwrite_failure_does_not_trigger_existing_build_recovery(self):
        class Core:
            pass

        self.assertIsNone(
            _recover_prior_postwrite_build(
                Core(),
                {"status": "FAILED", "error": "ArtisticPlanCompileError: nope"},
            )
        )

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

    def test_runner_guards_cleanup_until_build_execution_is_attempted(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "scripts" / "run_sheesh_programming_test.py").read_text(encoding="utf-8")
        self.assertIn("build_execution_attempted = False", source)
        self.assertIn("if core.runtime.ready and build_execution_attempted:", source)

    def test_preview_only_stops_before_approval_and_write_cleanup(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "run_sheesh_programming_test.py"
        ).read_text(encoding="utf-8")
        run_source = source[source.index("def run("):source.index("def main()")]
        preview_branch = run_source.index("if preview_only:")
        approve = run_source.index("execution = core.approve_action(action_id)")
        write_guard = run_source.index("build_execution_attempted = True")
        self.assertLess(preview_branch, write_guard)
        self.assertLess(preview_branch, approve)
        self.assertIn('result["status"] = "PREVIEW_ONLY"', run_source)
        self.assertIn('result["ma2_writes"] = 0', run_source)
        self.assertIn('"commands": list(workflow.commands)', run_source)

    def test_preview_only_cli_flag_is_explicit(self):
        from pathlib import Path
        source = (
            Path(__file__).resolve().parents[1]
            / "scripts"
            / "run_sheesh_programming_test.py"
        ).read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--preview-only", action="store_true"', source)
        self.assertIn("preview_only=args.preview_only", source)

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
