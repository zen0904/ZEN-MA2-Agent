import unittest

from zen_ma2_agent.test_show_evidence import (
    SHEESH_TEST_SEQUENCE,
    SHEESH_TEST_SEQUENCE_LABEL,
    bounded_test_show_color_rows,
    derive_sheesh_test_preset_bindings,
    test_show_palette_manifest,
)


class TestShowEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "groups": [
                {"group_id": 1, "name": "G1"},
                {"group_id": 2, "name": "G2"},
            ],
            "fixtures": [
                {"fixture_id": 101, "fixture_type": "2 TYPE"},
            ],
            "presets": [
                {"reference": "4.101", "preset_type": "COLOR", "name": "ZEN_COLOR_01_RED"},
                {"reference": "4.112", "preset_type": "COLOR", "name": "ZEN_COLOR_12_WHITE"},
            ],
            "sequences": [
                {"number": SHEESH_TEST_SEQUENCE, "name": SHEESH_TEST_SEQUENCE_LABEL},
            ],
        }
        self.plan = {
            "schema": "zen.show_plan.v0.1",
            "sequence": SHEESH_TEST_SEQUENCE,
            "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
            "test_palette": [
                {"preset": 101, "label": "ZEN_COLOR_01_RED", "rgb": [100, 0, 0]},
                {"preset": 112, "label": "ZEN_COLOR_12_WHITE", "rgb": [100, 100, 100]},
            ],
            "cues": [
                {
                    "cue_number": 1,
                    "actions": [
                        {
                            "operation": "CALL_PRESET",
                            "target": {"type": "group", "ref": 1},
                            "preset_ref": "4.101",
                        }
                    ],
                },
                {
                    "cue_number": 2,
                    "actions": [
                        {
                            "operation": "CALL_PRESET",
                            "target": {"type": "group", "ref": 2},
                            "preset_ref": "4.112",
                        }
                    ],
                },
            ],
        }

    def test_exact_current_test_show_objects_recover_only_observed_pairs(self):
        result = derive_sheesh_test_preset_bindings(self.profile, self.plan)
        self.assertEqual(result["status"], "SHOW_BOUND_VERIFIED")
        pairs = {(row["group_id"], row["reference"]) for row in result["bindings"]}
        self.assertEqual(pairs, {(1, "4.101"), (2, "4.112")})
        self.assertTrue(all(row["status"] == "SHOW_BOUND_VERIFIED" for row in result["bindings"]))
        self.assertTrue(all(row["evidence"]["reuse_scope"] == "CURRENT_MATCHING_TEST_SHOW_ONLY" for row in result["bindings"]))


    def test_bounded_color_inventory_recovers_only_exact_known_labels(self):
        manifest = test_show_palette_manifest(self.plan)
        self.assertEqual(manifest["4.101"], "ZEN_COLOR_01_RED")
        rows = bounded_test_show_color_rows(
            self.plan,
            {
                "4.101": 'Color 4.101 4.101 ZEN_COLOR_01_RED Normal',
                "4.112": 'Color 4.112 4.112 WRONG Normal',
            },
        )
        self.assertEqual(
            rows,
            [{
                "preset_type": "COLOR",
                "number": 101,
                "reference": "4.101",
                "name": "ZEN_COLOR_01_RED",
                "source": "FRESH_LIST_PRESET_REFERENCE_TEST_SHOW",
            }],
        )

    def test_bounded_color_inventory_ignores_missing_objects(self):
        rows = bounded_test_show_color_rows(
            self.plan,
            {
                "4.101": "Error #14: OBJECT DOES NOT EXIST",
                "4.112": "WARNING, NO OBJECTS FOUND FOR LIST",
            },
        )
        self.assertEqual(rows, [])

    def test_sequence_identity_mismatch_blocks_recovery(self):
        profile = dict(self.profile)
        profile["sequences"] = [{"number": 901, "name": "OTHER"}]
        result = derive_sheesh_test_preset_bindings(profile, self.plan)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["bindings"], [])
        self.assertEqual(result["reason"], "CURRENT_TEST_SEQUENCE_IDENTITY_NOT_PRESENT")

    def test_current_preset_label_or_type_mismatch_blocks_recovery(self):
        profile = dict(self.profile)
        profile["presets"] = [
            {"reference": "4.101", "preset_type": "FOCUS", "name": "ZEN_COLOR_01_RED"},
            {"reference": "4.112", "preset_type": "COLOR", "name": "ZEN_COLOR_12_WHITE"},
        ]
        result = derive_sheesh_test_preset_bindings(profile, self.plan)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("TYPE_MISMATCH", result["reason"])

        profile = dict(self.profile)
        profile["presets"] = [
            {"reference": "4.101", "preset_type": "COLOR", "name": "CHANGED"},
            {"reference": "4.112", "preset_type": "COLOR", "name": "ZEN_COLOR_12_WHITE"},
        ]
        result = derive_sheesh_test_preset_bindings(profile, self.plan)
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("LABEL_MISMATCH", result["reason"])

    def test_plan_does_not_expand_observed_applicability(self):
        result = derive_sheesh_test_preset_bindings(self.profile, self.plan)
        pairs = {(row["group_id"], row["reference"]) for row in result["bindings"]}
        self.assertNotIn((2, "4.101"), pairs)
        self.assertNotIn((1, "4.112"), pairs)


if __name__ == "__main__":
    unittest.main()
