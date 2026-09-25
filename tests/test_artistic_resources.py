import unittest

from zen_ma2_agent.artistic_resources import (
    ARTISTIC_RESOURCE_MAP_SCHEMA,
    build_artistic_resource_map,
    effect_applicability_from_map,
    model_resource_contract,
    preset_applicability_from_map,
)


class ArtisticResourceMapTests(unittest.TestCase):
    def setUp(self):
        self.identity = {
            "kind": "SCANNED_SHOW_PROFILE_FINGERPRINT",
            "value": "show-1",
            "confidence": "PARTIAL",
        }
        self.profile = {
            "show_identity": self.identity,
            "fixtures": [
                {"fixture_id": 101, "fixture_type": "2 HYBRID"},
                {"fixture_id": 201, "fixture_type": "2 HYBRID"},
            ],
            "groups": [
                {"group_id": 1, "name": "HYBRID", "fixture_ids_in_selection_order": [101]},
                {"group_id": 2, "name": "BEAM", "fixture_ids_in_selection_order": [201]},
            ],
            "presets": [
                {"reference": "4.101", "preset_type": "COLOR", "name": "RED"},
                {"reference": "6.1", "preset_type": "FOCUS", "name": "NARROW"},
            ],
            "effects": [
                {"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"},
                {"effect_id": 1000, "name": "Random Old Effect"},
            ],
            "fixture_type_profiles": [
                {
                    "status": "SHOW_BOUND_VERIFIED",
                    "fixture_type": {"list_label": "2 HYBRID"},
                    "capabilities": {
                        "DIMMER": {"status": "SHOW_BOUND_VERIFIED"},
                        "COLOR": {"status": "SHOW_BOUND_VERIFIED"},
                        "POSITION": {"status": "SHOW_BOUND_VERIFIED"},
                        "FOCUS": {"status": "SHOW_BOUND_VERIFIED"},
                        "GOBO": {"status": "SHOW_BOUND_VERIFIED"},
                        "PRISM": {"status": "SHOW_BOUND_VERIFIED"},
                        "ZOOM": {"status": "SHOW_BOUND_VERIFIED"},
                        "FROST": {"status": "NOT_PRESENT_IN_EXPORTED_PROFILE"},
                        "SHUTTER_STROBE": {"status": "SHOW_BOUND_VERIFIED"},
                    },
                }
            ],
        }
        self.preset_bindings = [
            {
                "status": "SHOW_BOUND_VERIFIED",
                "show_identity": self.identity,
                "group_id": 1,
                "reference": "4.101",
                "preset_type": "COLOR",
                "source": "REAL_MACHINE_APPLICATION_EVIDENCE",
            }
        ]
        self.catalog = [
            {
                "effect_id": 3520,
                "label": "ZEN_FX_DIM_CHASE_SLOW_GROUP1",
                "ownership": "ZEN_AGENT",
                "show_identity": self.identity,
                "source": "EFFECT_BUILDER_V1",
                "requirement": {
                    "kind": "DIMMER_CHASE",
                    "semantic_label": "ZEN_FX_DIM_CHASE_SLOW_GROUP1",
                    "target_type": "group",
                    "target_ref": 1,
                },
                "verification": {
                    "object": "VERIFIED",
                    "label": "VERIFIED",
                    "parameters": "PARTIAL",
                },
            }
        ]
        self.effect_application = {
            "schema": "zen.cue_effect_application.v0.2",
            "status": "REAL_MACHINE_CONTENT_VERIFIED",
            "grammar": "AT_EFFECT_POOL_CALL",
            "ma2_version_family": "grandMA2_3.9",
            "verification": {
                "application": "REAL_MACHINE_CONTENT_VERIFIED",
                "cue_content_readback": "VERIFIED",
            },
        }

    def build(self, **kwargs):
        values = {
            "preset_bindings": self.preset_bindings,
            "effect_catalog_entries": self.catalog,
            "effect_application_capability": self.effect_application,
        }
        values.update(kwargs)
        return build_artistic_resource_map(self.profile, **values)

    def test_map_separates_capability_from_group_resource_applicability(self):
        result = self.build()
        self.assertEqual(result["schema"], ARTISTIC_RESOURCE_MAP_SCHEMA)
        group1, group2 = result["groups"]

        self.assertEqual(group1["dimensions"]["COLOR"]["technical_capability"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(group2["dimensions"]["COLOR"]["technical_capability"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(group1["dimensions"]["COLOR"]["execution_status"], "VERIFIED_PRESET_RESOURCE")
        self.assertEqual(group2["dimensions"]["COLOR"]["execution_status"], "NO_VERIFIED_RESOURCE")
        self.assertEqual([item["reference"] for item in group1["preset_resources"]], ["4.101"])
        self.assertEqual(group2["preset_resources"], [])
        self.assertEqual(preset_applicability_from_map(result), {1: {"4.101"}, 2: set()})

    def test_effect_inventory_does_not_become_designer_resource_by_existence(self):
        result = self.build()
        group1 = result["groups"][0]
        self.assertEqual([item["effect_id"] for item in group1["effect_resources"]], [3520])
        self.assertNotIn(1000, {item["effect_id"] for item in group1["effect_resources"]})
        self.assertEqual(effect_applicability_from_map(result), {1: {3520}, 2: set()})
        self.assertEqual(result["effect_inventory_summary"]["unverified_effects_exposed_to_designer"], 0)

        contract = model_resource_contract(result)
        self.assertEqual([item["effect_id"] for item in contract[0]["effects"]], [3520])
        self.assertEqual(contract[1]["effects"], [])

    def test_effect_resource_is_not_executable_without_verified_application_grammar(self):
        result = self.build(effect_application_capability=None)
        group1 = result["groups"][0]
        self.assertEqual(group1["dimensions"]["EFFECT"]["execution_status"], "RESOURCE_VERIFIED_APPLICATION_UNVERIFIED")
        self.assertEqual(effect_applicability_from_map(result), {1: set(), 2: set()})
        self.assertEqual(model_resource_contract(result)[0]["effects"], [])

    def test_wrong_show_identity_never_binds_preset_or_effect(self):
        wrong = {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "other", "confidence": "PARTIAL"}
        preset_bindings = [{**self.preset_bindings[0], "show_identity": wrong}]
        catalog = [{**self.catalog[0], "show_identity": wrong}]
        result = self.build(preset_bindings=preset_bindings, effect_catalog_entries=catalog)
        self.assertEqual(result["groups"][0]["preset_resources"], [])
        self.assertEqual(result["groups"][0]["effect_resources"], [])

    def test_cached_sheesh_binding_cannot_survive_exact_subfixture_drift(self):
        profile = {
            **self.profile,
            "groups": [{
                "group_id": 1, "name": "ATOMIC", "fixture_ids_in_selection_order": [701],
                "fixture_refs_in_selection_order": ["701.1"],
                "membership": {"status": "SUPPORTED", "source": "ma2_export_xml"},
            }],
        }
        evidence = {"current_fixture_refs_in_selection_order": ["701.2"]}
        preset = {**self.preset_bindings[0], "source": "SHEESH_REAL_MA2_TEST_SHOW_BUILD_001", "evidence": evidence}
        dimmer = {"status": "SHOW_BOUND_VERIFIED", "show_identity": self.identity,
                  "group_id": 1, "capability": "DIMMER", "source": "SHEESH_REAL_MA2_TEST_SHOW_BUILD_001",
                  "evidence": evidence}
        result = build_artistic_resource_map(profile, preset_bindings=[preset], dimmer_bindings=[dimmer])
        group = result["groups"][0]
        self.assertEqual(group["preset_resources"], [])
        self.assertEqual(group["dimensions"]["DIMMER"]["execution_status"], "DIRECT_GROUP_LEVEL_UNVERIFIED_CAPABILITY")
        profile["groups"][0]["fixture_refs_in_selection_order"] = ["701.2"]
        result = build_artistic_resource_map(profile, preset_bindings=[preset], dimmer_bindings=[dimmer])
        group = result["groups"][0]
        self.assertEqual([row["reference"] for row in group["preset_resources"]], ["4.101"])
        self.assertEqual(group["dimensions"]["DIMMER"]["execution_status"], "SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL")

    def test_multi_instance_exact_selection_cannot_unlock_dimmer_effect_from_root_capability(self):
        identity = self.identity
        profile = {
            "show_identity": identity,
            "fixtures": [{
                "fixture_id": 701,
                "fixture_type": "7 Atomic 3000 LED Extended",
                "stage_geometry": {
                    "subfixtures": [{"subfixture_id": 1}, {"subfixture_id": 2}],
                },
            }],
            "groups": [{
                "group_id": 7,
                "name": "STROBE",
                "fixture_ids_in_selection_order": [701],
                "fixture_refs_in_selection_order": ["701.1"],
                "membership": {"status": "SUPPORTED", "source": "ma2_export_xml"},
            }],
            "presets": [],
            "effects": [
                {"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"},
                {"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP7"},
            ],
            "fixture_type_profiles": [{
                "status": "SHOW_BOUND_VERIFIED",
                "fixture_type": {"list_label": "7 Atomic 3000 LED Extended"},
                "capabilities": {"DIMMER": {"status": "SHOW_BOUND_VERIFIED"}},
            }],
        }
        catalog = [{
            "effect_id": 3520,
            "label": "ZEN_FX_DIM_CHASE_SLOW_GROUP7",
            "ownership": "ZEN_AGENT",
            "show_identity": identity,
            "source": "EFFECT_BUILDER_V1",
            "requirement": {
                "kind": "DIMMER_CHASE",
                "target_type": "group",
                "target_ref": 7,
            },
            "verification": {"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"},
        }]
        result = build_artistic_resource_map(
            profile,
            effect_catalog_entries=catalog,
            effect_application_capability=self.effect_application,
        )
        group = result["groups"][0]
        self.assertEqual(group["dimensions"]["DIMMER"]["technical_capability"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(group["dimensions"]["DIMMER"]["execution_status"], "DIRECT_GROUP_LEVEL_UNVERIFIED_CAPABILITY")
        self.assertEqual(group["effect_resources"], [])
        self.assertEqual(effect_applicability_from_map(result)[7], set())

    def test_group_name_never_creates_capability(self):
        profile = {**self.profile, "fixture_type_profiles": []}
        result = build_artistic_resource_map(profile)
        group2 = result["groups"][1]
        self.assertEqual(group2["name"], "BEAM")
        self.assertEqual(group2["dimensions"]["COLOR"]["technical_capability"]["status"], "UNKNOWN")
        self.assertEqual(group2["dimensions"]["POSITION"]["technical_capability"]["status"], "UNKNOWN")


    def test_strict_semantic_template_effect_can_recover_without_catalog(self):
        profile = {
            **self.profile,
            "effects": [
                {"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"},
                {"effect_id": 89, "name": "Almost Fast Chase"},
            ],
        }
        result = build_artistic_resource_map(
            profile,
            preset_bindings=self.preset_bindings,
            effect_catalog_entries=[],
            effect_application_capability=self.effect_application,
        )
        group1 = result["groups"][0]
        ids = {item["effect_id"] for item in group1["effect_resources"]}
        self.assertIn(88, ids)
        self.assertNotIn(89, ids)
        self.assertIn(88, effect_applicability_from_map(result)[1])
        self.assertEqual(result["effect_inventory_summary"]["unverified_effects_exposed_to_designer"], 0)

    def test_single_instance_exact_selection_can_use_root_dimmer_capability_for_effect(self):
        profile = {
            **self.profile,
            "fixtures": [{
                "fixture_id": 701,
                "fixture_type": "2 HYBRID",
                "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]},
            }],
            "groups": [{
                "group_id": 7,
                "name": "SINGLE_INSTANCE",
                "fixture_ids_in_selection_order": [701],
                "fixture_refs_in_selection_order": ["701.1"],
                "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"},
            }],
            "effects": [{"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"}],
        }
        result = build_artistic_resource_map(
            profile,
            effect_application_capability=self.effect_application,
        )
        group = result["groups"][0]
        self.assertEqual(
            group["dimensions"]["DIMMER"]["execution_status"],
            "SHOW_BOUND_VERIFIED_FIXTURE_TYPE_CAPABILITY",
        )
        self.assertEqual(
            group["dimensions"]["DIMMER"]["application_evidence"]["source"],
            "FIXTURE_TYPE_CAPABILITY_PLUS_EXACT_SELECTION",
        )
        self.assertEqual(effect_applicability_from_map(result)[7], {88})

    def test_strict_template_effect_needs_dimmer_capability_and_verified_application(self):
        no_capability = {
            **self.profile,
            "effects": [{"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"}],
            "fixture_type_profiles": [],
        }
        result = build_artistic_resource_map(
            no_capability,
            effect_application_capability=self.effect_application,
        )
        self.assertEqual(effect_applicability_from_map(result)[1], set())

        result = build_artistic_resource_map(
            {**self.profile, "effects": [{"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"}]},
            effect_application_capability=None,
        )
        self.assertEqual(effect_applicability_from_map(result)[1], set())

    def test_strict_template_effect_can_use_show_bound_group_dimmer_application_evidence(self):
        profile = {
            **self.profile,
            "effects": [
                {"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"},
            ],
            "fixture_type_profiles": [],
        }
        dimmer_binding = {
            "status": "SHOW_BOUND_VERIFIED",
            "show_identity": self.identity,
            "group_id": 1,
            "capability": "DIMMER",
            "implementation": "SET_DIMMER",
            "source": "REAL_MACHINE_TEST_BUILD",
            "evidence": {"fixture_ids_in_selection_order": [101]},
        }
        result = build_artistic_resource_map(
            profile,
            dimmer_bindings=[dimmer_binding],
            effect_application_capability=self.effect_application,
        )
        group1, group2 = result["groups"]
        self.assertEqual(
            group1["dimensions"]["DIMMER"]["technical_capability"]["status"],
            "UNKNOWN",
        )
        self.assertEqual(
            group1["dimensions"]["DIMMER"]["execution_status"],
            "SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL",
        )
        self.assertEqual(effect_applicability_from_map(result)[1], {88})
        self.assertEqual(effect_applicability_from_map(result)[2], set())
        self.assertEqual(
            group1["dimensions"]["EFFECT"]["execution_status"],
            "VERIFIED_EFFECT_RESOURCE",
        )

    def test_wrong_show_identity_dimmer_evidence_does_not_unlock_template_effect(self):
        profile = {
            **self.profile,
            "effects": [
                {"effect_id": 88, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"},
            ],
            "fixture_type_profiles": [],
        }
        wrong = {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "other", "confidence": "PARTIAL"}
        result = build_artistic_resource_map(
            profile,
            dimmer_bindings=[{
                "status": "SHOW_BOUND_VERIFIED",
                "show_identity": wrong,
                "group_id": 1,
                "capability": "DIMMER",
                "implementation": "SET_DIMMER",
            }],
            effect_application_capability=self.effect_application,
        )
        self.assertEqual(effect_applicability_from_map(result)[1], set())

    def test_unbound_presets_are_context_only_not_group_resources(self):
        result = self.build()
        refs = {item["reference"] for item in result["unbound_presets"]}
        self.assertIn("6.1", refs)
        self.assertNotIn("6.1", preset_applicability_from_map(result)[1])
        self.assertTrue(result["rules"]["preset_type_implies_group_applicability"] is False)


if __name__ == "__main__":
    unittest.main()
