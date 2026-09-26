import copy
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.artistic_resources import (
    build_artistic_resource_map, model_resource_contract, preset_applicability_from_map,
)
from zen_ma2_agent.designer.artistic_plan import ArtisticPlanCompileError, compile_artistic_cue_plan
from zen_ma2_agent.position_application_evidence import (
    PositionApplicationBindingStore, PositionEvidenceError, build_position_poc_preview,
    derive_position_application_binding, position_binding_matches_profile,
)


class PositionApplicationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "a" * 64, "confidence": "PARTIAL"},
            "resources": {name: {"status": "SUPPORTED"} for name in (
                "groups", "group_membership", "fixtures", "fixture_geometry", "fixture_type_profiles", "presets", "sequences")},
            "fixtures": [
                {"fixture_id": 101, "fixture_type": "2 MOVING", "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}},
                {"fixture_id": 102, "fixture_type": "2 MOVING", "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}},
                {"fixture_id": 701, "fixture_type": "7 MULTI", "stage_geometry": {"subfixtures": [{"subfixture_id": 1}, {"subfixture_id": 2}]}},
            ],
            "fixture_type_profiles": [
                {"status": "SHOW_BOUND_VERIFIED", "fixture_type": {"list_label": "2 MOVING"},
                 "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}}},
                {"status": "SHOW_BOUND_VERIFIED", "fixture_type": {"list_label": "7 MULTI"},
                 "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}}},
            ],
            "groups": [
                {"group_id": 1, "name": "TEST_MOVING", "fixture_ids_in_selection_order": [101, 102],
                 "fixture_refs_in_selection_order": ["101", "102"],
                 "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"}},
                {"group_id": 2, "name": "OTHER", "fixture_ids_in_selection_order": [701],
                 "fixture_refs_in_selection_order": ["701.1"],
                 "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"}},
            ],
            "presets": [
                {"reference": "2.1", "preset_type": "POSITION", "name": "HOME"},
                {"reference": "2.2", "preset_type": "POSITION", "name": "CENTER"},
            ],
            "sequences": [{"number": 1, "name": "Foreign"}],
            "effects": [],
        }
        self.preview = build_position_poc_preview(self.profile, group_id=1, preset_ref="2.1")

    def discovery(self):
        rows = []
        for fixture in (101, 102):
            for attribute in ("PAN", "TILT"):
                rows.append({
                    "channel": {
                        "fixture_id": str(fixture),
                        "subfixture_id": "1",
                        "attribute_name": attribute,
                    },
                    "preset": {"no_components": ["2", "1"]},
                })
        return {"schema": "zen.sequence_export_discovery.v0.1", "status": "VERIFIED",
                "sequence_no": 2, "xml_discovery": {"sha256": "b" * 64},
                "cues": [{"number": {"number": "1", "sub_number": "0"},
                          "parts": [{"cue_data": rows}]}]}

    def binding(self):
        return derive_position_application_binding(self.profile, self.preview, self.discovery())

    def compile(self, resource_map, *, group=1, preset="2.1"):
        return compile_artistic_cue_plan(
            {"cues": [{"fade": 0, "actions": [{"group": group, "position_preset": preset}]}]},
            song="TEST", target_executor="2.001", active_sequence_range=[1, 999],
            verified_group_ids={1, 2}, verified_preset_refs={"2.1", "2.2"},
            verified_preset_types={"2.1": "POSITION", "2.2": "POSITION"},
            verified_preset_applicability=preset_applicability_from_map(resource_map),
        )

    def test_preview_is_typed_nonexecutable_and_creates_no_ma_write_path(self):
        self.assertFalse(self.preview["executable"])
        self.assertEqual(self.preview["ma2_writes"], 0)
        self.assertEqual(self.preview["sequence"]["id"], 2)
        self.assertEqual(self.preview["sequence"]["executor"], None)
        self.assertEqual(self.preview["typed_action"]["preset_type"], "POSITION")

    def test_technical_capability_and_preset_inventory_alone_do_not_unlock(self):
        resource_map = build_artistic_resource_map(self.profile)
        self.assertEqual(resource_map["groups"][0]["dimensions"]["POSITION"]["technical_capability"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(resource_map["groups"][0]["dimensions"]["POSITION"]["execution_status"], "NO_VERIFIED_RESOURCE")
        self.assertEqual(model_resource_contract(resource_map)[0]["presets"], [])
        with self.assertRaisesRegex(ArtisticPlanCompileError, "not verified applicable"):
            self.compile(resource_map)

    def test_exact_content_binding_unlocks_exact_group_preset_only(self):
        binding = self.binding()
        self.assertTrue(position_binding_matches_profile(self.profile, binding))
        resource_map = build_artistic_resource_map(self.profile, preset_bindings=[binding])
        self.assertEqual(model_resource_contract(resource_map)[0]["presets"][0]["reference"], "2.1")
        self.assertEqual(model_resource_contract(resource_map)[1]["presets"], [])
        compiled, _ = self.compile(resource_map)
        self.assertEqual(compiled["cues"][0]["actions"][0]["preset_type"], "POSITION")
        for group, preset in ((1, "2.2"), (2, "2.1")):
            with self.assertRaisesRegex(ArtisticPlanCompileError, "not verified applicable"):
                self.compile(resource_map, group=group, preset=preset)

    def test_wrong_show_identity_rejects_binding(self):
        profile = copy.deepcopy(self.profile)
        profile["show_identity"]["value"] = "c" * 64
        self.assertFalse(position_binding_matches_profile(profile, self.binding()))

    def test_exact_membership_drift_rejects_binding(self):
        profile = copy.deepcopy(self.profile)
        profile["groups"][0]["fixture_refs_in_selection_order"] = ["101", "701.1"]
        self.assertFalse(position_binding_matches_profile(profile, self.binding()))

    def test_preset_ref_type_or_label_drift_rejects_binding(self):
        binding = self.binding()
        for key, value in (("reference", "2.2"), ("preset_type", "COLOR"), ("preset_label", "FAKE")):
            changed = {**binding, key: value}
            self.assertFalse(position_binding_matches_profile(self.profile, changed))

    def test_multi_instance_parent_or_unproved_exact_channel_fails_closed(self):
        profile = copy.deepcopy(self.profile)
        profile["groups"][1]["fixture_refs_in_selection_order"] = ["701"]
        with self.assertRaisesRegex(PositionEvidenceError, "MULTI_INSTANCE_PARENT_SELECTION_AMBIGUOUS"):
            build_position_poc_preview(profile, group_id=2, preset_ref="2.1")
        profile["groups"][1]["fixture_refs_in_selection_order"] = ["701.2"]
        preview = build_position_poc_preview(profile, group_id=2, preset_ref="2.1")
        with self.assertRaisesRegex(PositionEvidenceError, "POSITION_PRESET_CUE_CONTENT_MISMATCH"):
            derive_position_application_binding(profile, preview, self.discovery())

    def test_real_ma2_multi_instance_parent_row_fails_closed(self):
        profile = copy.deepcopy(self.profile)
        profile["groups"][1]["fixture_refs_in_selection_order"] = ["701.2"]
        preview = build_position_poc_preview(
            profile, group_id=2, preset_ref="2.1"
        )
        rows = []
        for attribute in ("PAN", "TILT"):
            rows.append({
                "channel": {
                    "fixture_id": "701",
                    "attribute_name": attribute,
                },
                "preset": {"no_components": ["1", "2", "1"]},
            })
        discovery = {
            "schema": "zen.sequence_export_discovery.v0.1",
            "status": "VERIFIED",
            "sequence_no": preview["sequence"]["id"],
            "xml_discovery": {"sha256": "d" * 64},
            "cues": [{
                "number": {"number": "1", "sub_number": "0"},
                "parts": [{"cue_data": rows}],
            }],
        }
        with self.assertRaisesRegex(
            PositionEvidenceError, "MULTI_INSTANCE_PARENT_ROW_AMBIGUOUS"
        ):
            derive_position_application_binding(profile, preview, discovery)

    def test_sequence_content_must_prove_exact_position_channels(self):
        for change in ("WRONG_PRESET", "WRONG_ATTRIBUTE", "FOREIGN_REF", "PARTIAL"):
            discovery = self.discovery()
            rows = discovery["cues"][0]["parts"][0]["cue_data"]
            if change == "WRONG_PRESET":
                rows[0]["preset"]["no_components"] = ["2", "2"]
            elif change == "WRONG_ATTRIBUTE":
                rows[0]["channel"]["attribute_name"] = "DIM"
            elif change == "FOREIGN_REF":
                rows.append({"channel": {"fixture_id": "9999", "subfixture_id": "1", "attribute_name": "PAN"},
                             "preset": {"no_components": ["2", "1"]}})
            else:
                discovery["status"] = "PARTIAL"
            with self.assertRaises(PositionEvidenceError, msg=change):
                derive_position_application_binding(self.profile, self.preview, discovery)

    def test_preview_requires_fresh_inventory_and_never_targets_fixture_9999(self):
        profile = copy.deepcopy(self.profile)
        profile["groups"][0]["fixture_refs_in_selection_order"].append("9999")
        with self.assertRaises(PositionEvidenceError):
            build_position_poc_preview(profile, group_id=1, preset_ref="2.1")
        profile = copy.deepcopy(self.profile)
        profile["resources"]["presets"]["status"] = "STALE"
        with self.assertRaisesRegex(PositionEvidenceError, "FRESH_READ_ONLY_STATE_REQUIRED"):
            build_position_poc_preview(profile, group_id=1, preset_ref="2.1")

    def test_binding_store_records_only_after_exact_readback_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PositionApplicationBindingStore(Path(directory))
            self.assertEqual(store.load_verified(self.profile), [])
            invalid = self.discovery()
            invalid["cues"][0]["parts"][0]["cue_data"].pop()
            with self.assertRaises(PositionEvidenceError):
                store.record_after_readback(self.profile, self.preview, invalid)
            self.assertFalse(store.path.exists())
            stored = store.record_after_readback(self.profile, self.preview, self.discovery())
            self.assertTrue(store.has_candidates())
            self.assertEqual(store.load_verified(self.profile), [stored])
            changed = copy.deepcopy(self.profile)
            changed["presets"][0]["name"] = "RENAMED"
            self.assertEqual(store.load_verified(changed), [])


if __name__ == "__main__":
    unittest.main()
