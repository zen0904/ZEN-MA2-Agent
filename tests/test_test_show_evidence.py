import unittest

from zen_ma2_agent.test_show_evidence import (
    SHEESH_TEST_SEQUENCE,
    SHEESH_TEST_SEQUENCE_LABEL,
    SHEESH_TEST_GROUP_FIXTURES,
    bounded_test_show_color_rows,
    derive_sheesh_test_dimmer_bindings,
    derive_sheesh_test_preset_bindings,
    test_show_palette_manifest,
)


class TestShowEvidenceTests(unittest.TestCase):
    @staticmethod
    def group(group_id, members, *, exact=None):
        refs = exact if exact is not None else [str(value) for value in members]
        return {"group_id": group_id, "name": f"G{group_id}",
                "fixture_ids_in_selection_order": list(members),
                "fixture_refs_in_selection_order": list(refs),
                "membership": {"status": "SUPPORTED", "source": "ma2_export_xml"}}

    def setUp(self):
        self.profile = {
            "groups": [
                self.group(1, SHEESH_TEST_GROUP_FIXTURES[1]),
                self.group(2, SHEESH_TEST_GROUP_FIXTURES[2]),
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

    def test_dimmer_bindings_require_exact_current_group_membership_and_observed_set_dimmer(self):
        profile = {
            **self.profile,
            "groups": [
                self.group(group_id, members, exact=([f"{value}.2" for value in members] if group_id == 7 else None))
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
                self.group(group_id, list(reversed(members)), exact=([f"{value}.2" for value in reversed(members)] if group_id == 7 else None))
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
                self.group(group_id, (list(members[:-1]) + [9998] if group_id == 3 else list(members)),
                           exact=([f"{value}.2" for value in members] if group_id == 7 else None))
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

    def test_group7_dot1_cannot_recover_historical_color_or_dimmer_binding(self):
        profile = {
            **self.profile,
            "groups": [
                self.group(1, SHEESH_TEST_GROUP_FIXTURES[1]),
                self.group(7, SHEESH_TEST_GROUP_FIXTURES[7],
                           exact=[f"{value}.1" for value in SHEESH_TEST_GROUP_FIXTURES[7]]),
            ],
        }
        plan = {**self.plan, "cues": [{"cue_number": 6, "actions": [
            {"operation": "CALL_PRESET", "target": {"type": "group", "ref": 1}, "preset_ref": "4.101"},
            {"operation": "CALL_PRESET", "target": {"type": "group", "ref": 7}, "preset_ref": "4.112"},
            {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 30},
            {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 7}, "level": 30},
        ]}]}
        color = derive_sheesh_test_preset_bindings(profile, plan)
        self.assertEqual(color["status"], "PARTIAL")
        self.assertEqual({row["group_id"] for row in color["bindings"]}, {1})
        self.assertEqual(color["mismatched_groups"], [7])
        dimmer = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertNotIn(7, {row["group_id"] for row in dimmer["bindings"]})
        self.assertIn(7, dimmer["mismatched_groups"])

    def test_group7_exact_dot2_reordered_matches_functional_evidence(self):
        members = list(reversed(SHEESH_TEST_GROUP_FIXTURES[7]))
        profile = {**self.profile, "groups": [self.group(7, members, exact=[f"{value}.2" for value in members])]}
        plan = {**self.plan, "cues": [{"cue_number": 6, "actions": [
            {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 7}, "level": 30},
            {"operation": "CALL_PRESET", "target": {"type": "group", "ref": 7}, "preset_ref": "4.112"},
        ]}]}
        dimmer = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertIn(7, {row["group_id"] for row in dimmer["bindings"]})
        color = derive_sheesh_test_preset_bindings(profile, plan)
        self.assertEqual(len(color["bindings"]), 1)
        self.assertEqual(color["bindings"][0]["evidence"]["group_7_evidence_scope"],
                         "FUNCTIONAL_TEST_EVIDENCE_NOT_HISTORICAL_ORIGINAL_MEMBERSHIP")

    def test_single_instance_dot1_group_keeps_parent_compatible_recovery(self):
        members = SHEESH_TEST_GROUP_FIXTURES[1]
        profile = {
            **self.profile,
            "groups": [self.group(1, members, exact=[f"{value}.1" for value in members])],
            "fixtures": [
                {"fixture_id": value, "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}}
                for value in members
            ],
        }
        plan = {**self.plan, "cues": [{"cue_number": 1, "actions": [
            {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 30},
        ]}]}
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertIn(1, {row["group_id"] for row in result["bindings"]})
        profile["fixtures"][0]["stage_geometry"]["subfixtures"].append({"subfixture_id": 2})
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertNotIn(1, {row["group_id"] for row in result["bindings"]})

    def test_root_id_only_group7_profile_is_not_exact_evidence(self):
        profile = {**self.profile, "groups": [{"group_id": 7, "fixture_ids_in_selection_order": list(SHEESH_TEST_GROUP_FIXTURES[7])}]}
        plan = {**self.plan, "cues": [{"cue_number": 6, "actions": [
            {"operation": "SET_DIMMER", "target": {"type": "group", "ref": 7}, "level": 30},
        ]}]}
        result = derive_sheesh_test_dimmer_bindings(profile, plan)
        self.assertEqual(result["bindings"], [])
        self.assertIn(7, result["mismatched_groups"])

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
