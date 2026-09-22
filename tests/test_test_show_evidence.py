import unittest

from zen_ma2_agent.test_show_evidence import (
    SHEESH_TEST_SEQUENCE,
    SHEESH_TEST_SEQUENCE_LABEL,
    SHEESH_TEST_GROUP_FIXTURES,
    bounded_test_show_color_rows,
    derive_sheesh_test_dimmer_bindings,
    derive_sheesh_test_preset_bindings,
    derive_sheesh_test_rgb_palette_bindings,
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

    def test_rgb_palette_bindings_expand_only_for_exact_show_bound_rgb_groups(self):
        palette = [
            {"preset": number, "label": f"ZEN_COLOR_{number}", "rgb": [1, 2, 3]}
            for number in range(101, 114)
        ]
        profile = {
            "groups": [
                {
                    "group_id": group_id,
                    "name": f"G{group_id}",
                    "fixture_ids_in_selection_order": list(members),
                }
                for group_id, members in SHEESH_TEST_GROUP_FIXTURES.items()
            ],
            "fixtures": [
                {
                    "fixture_id": fixture_id,
                    "fixture_type": "2 RGB TYPE" if group_id == 6 else "3 OTHER TYPE",
                }
                for group_id, members in SHEESH_TEST_GROUP_FIXTURES.items()
                for fixture_id in members
            ],
            "presets": [
                {
                    "reference": f"4.{number}",
                    "preset_type": "COLOR",
                    "name": f"ZEN_COLOR_{number}",
                }
                for number in range(101, 114)
            ],
            "sequences": [
                {"number": SHEESH_TEST_SEQUENCE, "name": SHEESH_TEST_SEQUENCE_LABEL},
            ],
            "fixture_type_profiles": [
                {
                    "status": "SHOW_BOUND_VERIFIED",
                    "fixture_type": {"list_label": "2 RGB TYPE"},
                    "capabilities": {"RGB_COLOR": {"status": "SHOW_BOUND_VERIFIED"}},
                },
                {
                    "status": "SHOW_BOUND_VERIFIED",
                    "fixture_type": {"list_label": "3 OTHER TYPE"},
                    "capabilities": {"RGB_COLOR": {"status": "NOT_PRESENT_IN_EXPORTED_PROFILE"}},
                },
            ],
        }
        plan = {
            "schema": "zen.show_plan.v0.1",
            "sequence": SHEESH_TEST_SEQUENCE,
            "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
            "test_palette": palette,
            "cues": [],
        }
        result = derive_sheesh_test_rgb_palette_bindings(profile, plan)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(result["verified_groups"], [6])
        self.assertEqual(len(result["bindings"]), 13)
        self.assertTrue(all(row["group_id"] == 6 for row in result["bindings"]))
        self.assertIn("4.110", {row["reference"] for row in result["bindings"]})

    def test_rgb_palette_binding_rejects_generic_color_without_rgb_channels(self):
        palette = [
            {"preset": number, "label": f"ZEN_COLOR_{number}", "rgb": [1, 2, 3]}
            for number in range(101, 114)
        ]
        profile = {
            "groups": [{
                "group_id": 6,
                "name": "G6",
                "fixture_ids_in_selection_order": list(SHEESH_TEST_GROUP_FIXTURES[6]),
            }],
            "fixtures": [
                {"fixture_id": fixture_id, "fixture_type": "2 COLORWHEEL TYPE"}
                for fixture_id in SHEESH_TEST_GROUP_FIXTURES[6]
            ],
            "presets": [
                {"reference": f"4.{number}", "preset_type": "COLOR", "name": f"ZEN_COLOR_{number}"}
                for number in range(101, 114)
            ],
            "sequences": [{"number": SHEESH_TEST_SEQUENCE, "name": SHEESH_TEST_SEQUENCE_LABEL}],
            "fixture_type_profiles": [{
                "status": "SHOW_BOUND_VERIFIED",
                "fixture_type": {"list_label": "2 COLORWHEEL TYPE"},
                "capabilities": {
                    "COLOR": {"status": "SHOW_BOUND_VERIFIED"},
                    "RGB_COLOR": {"status": "NOT_PRESENT_IN_EXPORTED_PROFILE"},
                },
            }],
        }
        plan = {
            "schema": "zen.show_plan.v0.1",
            "sequence": SHEESH_TEST_SEQUENCE,
            "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
            "test_palette": palette,
            "cues": [],
        }
        result = derive_sheesh_test_rgb_palette_bindings(profile, plan)
        self.assertEqual(result["bindings"], [])
        self.assertEqual(result["verified_groups"], [])

    def test_dimmer_bindings_require_exact_current_group_membership_and_observed_set_dimmer(self):
        profile = {
            **self.profile,
            "groups": [
                {
                    "group_id": group_id,
                    "name": f"G{group_id}",
                    "fixture_ids_in_selection_order": list(members),
                }
                for group_id, members in SHEESH_TEST_GROUP_FIXTURES.items()
            ],
        }
        plan = {
            **self.plan,
            "cues": [
                {
                    "cue_number": 1,
                    "actions": [
                        {
                            "operation": "SET_DIMMER",
                            "target": {"type": "group", "ref": group_id},
                            "level": 50,
                        }
                        for group_id in sorted(SHEESH_TEST_GROUP_FIXTURES)
                    ],
                }
            ],
        }
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertEqual(result["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(
            {row["group_id"] for row in result["bindings"]},
            set(SHEESH_TEST_GROUP_FIXTURES),
        )
        self.assertTrue(all(row["capability"] == "DIMMER" for row in result["bindings"]))
        self.assertTrue(all(row["implementation"] == "SET_DIMMER" for row in result["bindings"]))

    def test_dimmer_binding_survives_selection_order_reordering_with_same_members(self):
        profile = {
            **self.profile,
            "groups": [
                {
                    "group_id": group_id,
                    "name": f"G{group_id}",
                    "fixture_ids_in_selection_order": list(reversed(members)),
                }
                for group_id, members in SHEESH_TEST_GROUP_FIXTURES.items()
            ],
        }
        plan = {
            **self.plan,
            "cues": [{
                "cue_number": 1,
                "actions": [
                    {
                        "operation": "SET_DIMMER",
                        "target": {"type": "group", "ref": group_id},
                        "level": 50,
                    }
                    for group_id in sorted(SHEESH_TEST_GROUP_FIXTURES)
                ],
            }],
        }
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertEqual(result["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(len(result["bindings"]), 7)
        first = next(row for row in result["bindings"] if row["group_id"] == 1)
        self.assertEqual(
            first["evidence"]["current_fixture_ids_in_selection_order"],
            list(reversed(SHEESH_TEST_GROUP_FIXTURES[1])),
        )

    def test_dimmer_binding_does_not_survive_group_membership_drift(self):
        profile = {
            **self.profile,
            "groups": [
                {
                    "group_id": group_id,
                    "name": f"G{group_id}",
                    "fixture_ids_in_selection_order": (
                        list(members[:-1]) + [9998]
                        if group_id == 3
                        else list(members)
                    ),
                }
                for group_id, members in SHEESH_TEST_GROUP_FIXTURES.items()
            ],
        }
        plan = {
            **self.plan,
            "cues": [
                {
                    "cue_number": 1,
                    "actions": [
                        {
                            "operation": "SET_DIMMER",
                            "target": {"type": "group", "ref": group_id},
                            "level": 25,
                        }
                        for group_id in sorted(SHEESH_TEST_GROUP_FIXTURES)
                    ],
                }
            ],
        }
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertEqual(result["status"], "PARTIAL")
        self.assertIn(3, result["mismatched_groups"])
        self.assertNotIn(3, {row["group_id"] for row in result["bindings"]})

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
