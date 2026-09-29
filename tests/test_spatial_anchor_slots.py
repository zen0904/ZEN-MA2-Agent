import unittest

from zen_ma2_agent.spatial_anchor_slots import (
    HYDRATION_STATUS,
    SpatialAnchorSlotError,
    reserve_spatial_anchor_slots,
    spatial_anchor_catalog_matches_profile,
)


class SpatialAnchorSlotTests(unittest.TestCase):
    def profile(self):
        return {
            "show_identity": {"value": "a" * 64, "confidence": "REAL_MACHINE_VERIFIED"},
            "presets": [
                {"preset_type": "POSITION", "number": 1, "reference": "2.1", "name": "CENTER"},
                {"preset_type": "POSITION", "number": 2, "reference": "2.2", "name": "STAGE_LEFT"},
                {"preset_type": "COLOR", "number": 1, "reference": "4.1", "name": "RED"},
            ],
        }

    def requests(self):
        return [
            {"semantic_target": "MAIN_STAGE.CENTER", "preset_ref": "2.1", "expected_label": "CENTER"},
            {"semantic_target": "MAIN_STAGE.STAGE_LEFT", "preset_ref": "2.2", "expected_label": "STAGE_LEFT"},
        ]

    def test_reserves_exact_named_position_presets_without_claiming_empty_content(self):
        catalog = reserve_spatial_anchor_slots(self.profile(), self.requests())
        self.assertEqual(catalog["ma2_writes"], 0)
        self.assertEqual([row["preset_ref"] for row in catalog["slots"]], ["2.1", "2.2"])
        self.assertTrue(all(row["native_content_status"] == "UNVERIFIED" for row in catalog["slots"]))
        self.assertTrue(all(row["hydration_status"] == HYDRATION_STATUS for row in catalog["slots"]))
        self.assertTrue(all(row["hydration_allowed"] is False for row in catalog["slots"]))
        self.assertTrue(spatial_anchor_catalog_matches_profile(self.profile(), catalog))

    def test_label_drift_fails_closed(self):
        requests = self.requests()
        requests[0] = {**requests[0], "expected_label": "NOT_CENTER"}
        with self.assertRaisesRegex(SpatialAnchorSlotError, "LABEL_DRIFT"):
            reserve_spatial_anchor_slots(self.profile(), requests)

    def test_non_position_preset_cannot_be_reserved(self):
        request = [{"semantic_target": "MAIN_STAGE.CENTER", "preset_ref": "4.1", "expected_label": "RED"}]
        with self.assertRaisesRegex(SpatialAnchorSlotError, "PRESET_REF_INVALID"):
            reserve_spatial_anchor_slots(self.profile(), request)

    def test_duplicate_target_or_reference_fails_closed(self):
        duplicate_target = self.requests() + [
            {"semantic_target": "MAIN_STAGE.CENTER", "preset_ref": "2.3", "expected_label": "OTHER"}
        ]
        with self.assertRaisesRegex(SpatialAnchorSlotError, "TARGET_DUPLICATE"):
            reserve_spatial_anchor_slots(self.profile(), duplicate_target)
        duplicate_ref = self.requests() + [
            {"semantic_target": "MAIN_STAGE.STAGE_RIGHT", "preset_ref": "2.2", "expected_label": "STAGE_LEFT"}
        ]
        with self.assertRaisesRegex(SpatialAnchorSlotError, "PRESET_DUPLICATE"):
            reserve_spatial_anchor_slots(self.profile(), duplicate_ref)

    def test_verified_empty_evidence_and_grammar_make_slot_ready_for_preview(self):
        profile = self.profile()
        empty = {
            "schema": "zen.spatial_anchor_empty_evidence.v0.1",
            "status": "NATIVE_EMPTY_VERIFIED",
            "source": "PRESET_SELFIX_TO_ISOLATED_GROUP_NATIVE_EXPORT",
            "method_validation": "KNOWN_NONEMPTY_AND_KNOWN_EMPTY_AB_CONTROL_VERIFIED",
            "show_identity": profile["show_identity"],
            "slots": [
                {"reference": "2.1", "label": "CENTER", "preset_type": "POSITION", "native_content_status": "EMPTY", "selected_fixture_refs": [], "evidence": "PRESET_SELFIX_TO_ISOLATED_GROUP_NATIVE_EXPORT"},
                {"reference": "2.2", "label": "STAGE_LEFT", "preset_type": "POSITION", "native_content_status": "EMPTY", "selected_fixture_refs": [], "evidence": "PRESET_SELFIX_TO_ISOLATED_GROUP_NATIVE_EXPORT"},
            ],
        }
        capability = {
            "schema": "zen.spatial_anchor_hydration_capability.v0.1",
            "status": "REAL_MACHINE_CONTENT_VERIFIED",
            "grammar": "STORE_PRESET_MERGE_SELECTIVE",
            "ma2_version_family": "grandMA2_3.9",
            "evidence": {"sequence_export_sha256": "a" * 64},
            "verification": {
                "existing_empty_preset_identity": "VERIFIED",
                "merge_selective_application": "REAL_MACHINE_CONTENT_VERIFIED",
                "cue_content_readback": "VERIFIED",
            },
        }
        catalog = reserve_spatial_anchor_slots(
            profile, self.requests(), empty_evidence=empty, hydration_capability=capability
        )
        self.assertTrue(all(row["hydration_preconditions_verified"] for row in catalog["slots"]))
        self.assertTrue(all(row["hydration_status"] == "READY_FOR_PREVIEW" for row in catalog["slots"]))
        self.assertTrue(all(row["hydration_allowed"] is False for row in catalog["slots"]))
        self.assertEqual(catalog["constraints"], ["PREVIEW_AND_EXPLICIT_APPROVAL_REQUIRED_FOR_WRITE"])
        self.assertTrue(spatial_anchor_catalog_matches_profile(
            profile, catalog, empty_evidence=empty, hydration_capability=capability
        ))

    def test_show_or_preset_drift_invalidates_catalog(self):
        catalog = reserve_spatial_anchor_slots(self.profile(), self.requests())
        changed_show = self.profile()
        changed_show["show_identity"] = {"value": "b" * 64, "confidence": "REAL_MACHINE_VERIFIED"}
        self.assertFalse(spatial_anchor_catalog_matches_profile(changed_show, catalog))
        changed_label = self.profile()
        changed_label["presets"][0]["name"] = "CENTER_CHANGED"
        self.assertFalse(spatial_anchor_catalog_matches_profile(changed_label, catalog))


if __name__ == "__main__":
    unittest.main()
