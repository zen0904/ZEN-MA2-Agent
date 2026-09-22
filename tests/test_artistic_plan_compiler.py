import unittest

from zen_ma2_agent.designer.artistic_plan import (
    ArtisticPlanCompileError,
    compile_artistic_cue_plan,
)


class ArtisticPlanCompilerTests(unittest.TestCase):
    def setUp(self):
        self.groups = {1, 2, 3}
        self.presets = {"4.1", "6.2"}

    def compile(self, provider_plan, *, cue_labels=None):
        return compile_artistic_cue_plan(
            provider_plan,
            song="SHEESH",
            target_executor="2.001",
            active_sequence_range=[301, 400],
            verified_group_ids=self.groups,
            verified_preset_refs=self.presets,
            cue_labels=cue_labels,
        )

    def test_compiler_is_not_hardcoded_to_six_cues(self):
        provider_plan = {
            "cues": [
                {"fade": 1.5, "actions": [{"group": 1, "dimmer": 20}]},
                {"fade": 1, "actions": [{"group": 2, "preset": "6.2"}]},
                {"fade": 0.5, "actions": [{"group": 3, "dimmer": 45}]},
            ]
        }
        plan, audit = self.compile(provider_plan)

        self.assertEqual(plan["schema"], "zen.show_plan.v0.1")
        self.assertEqual(plan["song"], "SHEESH")
        self.assertEqual(plan["target_executor"], "2.001")
        self.assertEqual(plan["active_sequence_range"], [301, 400])
        self.assertEqual([cue["cue_number"] for cue in plan["cues"]], [1, 2, 3])
        self.assertEqual([cue["label"] for cue in plan["cues"]], ["CUE_001", "CUE_002", "CUE_003"])
        self.assertEqual(audit["cue_labels_source"], "PROVIDER_OR_GENERIC")
        self.assertFalse(audit["artistic_values_changed"])

    def test_caller_owns_experiment_specific_labels(self):
        provider_plan = {
            "cues": [
                {"fade": 1, "actions": [{"group": 1, "dimmer": 20}]}
                for _ in range(6)
            ]
        }
        labels = ["INTRO", "BUILD", "VERSE", "PRE_DROP", "SHEESH_IMPACT", "AFTER_IMPACT"]
        plan, audit = self.compile(provider_plan, cue_labels=labels)

        self.assertEqual([cue["label"] for cue in plan["cues"]], labels)
        self.assertEqual(audit["cue_labels_source"], "CALLER")

        with self.assertRaisesRegex(ArtisticPlanCompileError, "must match"):
            self.compile(provider_plan, cue_labels=labels[:-1])

    def test_provider_label_is_used_when_caller_does_not_supply_one(self):
        plan, _ = self.compile({
            "cues": [
                {"label": "OPEN", "fade": 1, "actions": [{"group": 1, "dimmer": 20}]},
                {"label": "HIT", "fade": 0, "actions": [{"group": 2, "dimmer": 100}]},
            ]
        })
        self.assertEqual([cue["label"] for cue in plan["cues"]], ["OPEN", "HIT"])

    def test_legacy_strict_provider_shape_is_accepted_without_trusting_metadata(self):
        provider_plan = {
            "schema": "whatever-the-provider-wrote",
            "song": "WRONG",
            "target_executor": 2.001,
            "active_sequence_range": ["999", "1000"],
            "cues": [
                {
                    "cue_number": "99",
                    "label": "ignored",
                    "fade": "1.5",
                    "actions": [
                        {
                            "operation": "SET_DIMMER",
                            "target": {"type": "group", "ref": "1"},
                            "level": "30",
                        }
                    ],
                }
                for _ in range(2)
            ],
        }
        plan, _ = self.compile(provider_plan, cue_labels=["A", "B"])

        self.assertEqual(plan["song"], "SHEESH")
        self.assertEqual(plan["target_executor"], "2.001")
        self.assertEqual(plan["active_sequence_range"], [301, 400])
        self.assertEqual(plan["cues"][0]["cue_number"], 1)
        self.assertEqual(plan["cues"][0]["label"], "A")
        self.assertEqual(plan["cues"][0]["actions"][0]["level"], 30)
        self.assertEqual(plan["cues"][0]["actions"][0]["target"]["ref"], 1)

    def test_unverified_group_and_preset_fail_closed(self):
        bad_group = {
            "cues": [{"fade": 1, "actions": [{"group": 99, "dimmer": 20}]}]
        }
        with self.assertRaisesRegex(ArtisticPlanCompileError, "not in the verified Group"):
            self.compile(bad_group)

        bad_preset = {
            "cues": [{"fade": 1, "actions": [{"group": 1, "preset": "9.9"}]}]
        }
        with self.assertRaisesRegex(ArtisticPlanCompileError, "not in the verified Preset"):
            self.compile(bad_preset)

    def test_semantic_substitution_is_not_performed(self):
        provider_plan = {
            "cues": [
                {
                    "fade": 1,
                    "actions": [
                        {"operation": "SET_COLOR", "target": {"type": "group", "ref": 1}}
                    ],
                }
            ]
        }
        with self.assertRaisesRegex(ArtisticPlanCompileError, "Unsupported artistic operation"):
            self.compile(provider_plan)

    def test_transport_fields_are_rejected(self):
        provider_plan = {
            "cues": [
                {
                    "fade": 1,
                    "actions": [{"group": 1, "dimmer": 20}],
                    "command": "Store Cue 1",
                }
            ]
        }
        with self.assertRaisesRegex(ArtisticPlanCompileError, "forbidden transport"):
            self.compile(provider_plan)


if __name__ == "__main__":
    unittest.main()
