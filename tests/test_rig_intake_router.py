import json
import unittest
from pathlib import Path

from zen_ma2_agent.design_guidance import build_design_guidance_context, run_shadow_designer
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.rig_intake import (
    RIG_CONTEXT_SCHEMA,
    RIG_PROPOSAL_SCHEMA,
    SHOW_INTAKE_SCHEMA,
    route_show_intake,
    validate_rig_context,
    validate_show_intake,
)
from zen_ma2_agent.song_analysis import SongAnalysisAdapter
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent


class RigIntakeRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((ROOT / "fixtures" / "rig_intake_router_001.json").read_text(encoding="utf-8"))
        cls.intakes = fixture["intakes"]
        song_fixture = json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8"))
        cls.analysis = next(item["analysis"] for item in song_fixture["cases"] if item["case_id"] == "CASE_D_BUILDUP_DROP")
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        raw = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(raw["sources"], raw["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]
        cls.profile = {
            "groups": [{"group_id": 1, "name": "SAFE_TEST", "fixture_ids_in_selection_order": list(range(101, 109))}],
            "fixtures": [{"fixture_id": item, "fixture_type": "SAFE_TYPE"} for item in range(101, 109)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}],
            "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "UNINITIALIZED"},
        }

    def route(self, name):
        return route_show_intake(json.loads(json.dumps(self.intakes[name])))

    def test_user_confirmed_layout_bypasses_planner_and_preserves_placement(self):
        intake = validate_show_intake(self.intakes["user_confirmed"])
        result = self.route("user_confirmed")
        self.assertEqual(intake["schema"], SHOW_INTAKE_SCHEMA)
        self.assertEqual(result["route"], "USER_CONFIRMED_LAYOUT")
        self.assertEqual(result["planner_status"], "BYPASSED")
        self.assertIsNone(result["rig_proposal"])
        self.assertEqual(result["rig_context"]["schema"], RIG_CONTEXT_SCHEMA)
        self.assertEqual(result["rig_context"]["placement_semantics"], intake["user_confirmed_layout"])
        self.assertTrue(all(item["source"] == "USER_CONFIRMED" and item["certainty"] == "CONFIRMED" for item in result["rig_context"]["placement_semantics"]))

    def test_sparse_floor_only_input_produces_bounded_proposal_without_dimensions(self):
        result = self.route("sparse_floor_only")
        proposal = result["rig_proposal"]
        self.assertEqual(result["planner_status"], "PROPOSAL_READY")
        self.assertEqual(proposal["schema"], RIG_PROPOSAL_SCHEMA)
        self.assertTrue(all(item["mounting"] == "FLOOR" for item in proposal["placements"]))
        self.assertTrue(any(item["fact_id"] == "STAGE_WIDTH" and item["certainty"] == "UNKNOWN" for item in proposal["unknowns"]))
        self.assertEqual(proposal["fallback"]["status"], "SAFE_BOUNDED_FALLBACK")

    def test_visible_truss_never_becomes_hanging_permission(self):
        result = self.route("photo_truss_unknown")
        proposal = result["rig_proposal"]
        self.assertTrue(any(item["fact_id"] == "VISIBLE_TRUSS" and item["certainty"] == "INFERRED" for item in result["rig_context"]["facts"]))
        self.assertTrue(any(item["fact_id"] == "SAFE_TO_HANG_FIXTURES" and item["certainty"] == "UNKNOWN" for item in result["rig_context"]["unknowns"]))
        self.assertTrue(all(item["mounting"] != "FLOWN_APPROVED" for item in proposal["placements"]))

    def test_led_only_context_uses_only_declared_led_roles_in_shadow_guidance(self):
        context = self.route("led_only")["rig_context"]
        self.assertEqual({item["role"] for item in context["available_roles"]}, {"COLOR_FIELD", "DENSITY_LAYER", "TIMING_LAYER"})
        guidance = build_design_guidance_context(self.analysis, context, self.packs, self.evidence, self.reviews)
        designer_input = SongAnalysisAdapter().to_designer_input(self.analysis)
        baseline = FirstSongDesigner().design(designer_input, self.profile)
        shadow = run_shadow_designer(FirstSongDesigner(), designer_input, self.profile, guidance)
        resource = next(item for item in shadow["advisories"] if item["advisory_id"] == "advisory-resource-adaptation")
        selected = {role for choice in resource["resource_choices"] for key in ("KEEP", "REDUCE", "OMIT") for role in choice[key]}
        self.assertFalse(any(token in role for role in selected for token in ("MOVER", "BEAM", "GOBO", "AERIAL")))
        self.assertEqual(baseline, shadow["actual_show_plan"])

    def test_asymmetric_confirmed_layout_is_preserved_and_exposed(self):
        intake = json.loads(json.dumps(self.intakes["user_confirmed"]))
        intake["intake_id"] = "ASYMMETRIC_CONFIRMED"
        intake["facts"].append({"fact_id": "ASYMMETRIC_LAYOUT", "value": True, "certainty": "CONFIRMED", "source": "USER_CONFIRMED"})
        intake["user_confirmed_layout"][1]["count"] = 5
        intake["user_confirmed_layout"][2]["count"] = 3
        result = route_show_intake(intake)
        self.assertTrue(result["rig_context"]["asymmetry"]["detected"])
        self.assertEqual([item["count"] for item in result["rig_context"]["placement_semantics"] if item["fixture_family"] == "MOVING HEAD"], [5, 3])
        self.assertEqual(result["planner_status"], "BYPASSED")

    def test_missing_noncritical_information_proceeds_but_critical_no_fallback_asks_one_question(self):
        sparse = self.route("sparse_floor_only")
        self.assertEqual(sparse["clarification_requirements"], [])
        blocked = self.route("critical_unknown")
        self.assertEqual(blocked["planner_status"], "BLOCKED_TARGETED_CLARIFICATION")
        self.assertEqual(len(blocked["clarification_requirements"]), 1)
        self.assertEqual(blocked["clarification_requirements"][0]["question_id"], "CONFIRM_SAFE_FLOOR_ZONE")

    def test_existing_show_reuses_existing_context_without_redesign(self):
        result = self.route("existing_show")
        self.assertEqual(result["route"], "EXISTING_SHOW")
        self.assertEqual(result["planner_status"], "BYPASSED_EXISTING_SHOW")
        self.assertIsNone(result["rig_proposal"])
        self.assertEqual(result["rig_context"]["proposal_ref"], "data/ZEN_CURRENT_SHOW_PROFILE.json")
        self.assertEqual(result["rig_context"]["placement_semantics"][0]["zone"], "SCANNED_LAYOUT_UNKNOWN_SEMANTICS")

    def test_provenance_remains_distinct_and_commands_or_unsafe_flying_are_rejected(self):
        result = self.route("sparse_floor_only")
        context = validate_rig_context(result["rig_context"])
        self.assertTrue(any(item["certainty"] == "CONFIRMED" for item in context["facts"]))
        self.assertTrue(any(item["certainty"] == "INFERRED" for item in context["facts"]))
        self.assertTrue(any(item["certainty"] == "UNKNOWN" for item in context["unknowns"]))
        self.assertTrue(all(item["certainty"] == "INFERRED" for item in result["rig_proposal"]["placements"]))
        self.assertTrue(any(item["fact_id"] == "REAR_FLOOR_ZONE_USABLE" and item["certainty"] == "INFERRED" for item in context["facts"]))
        guidance = build_design_guidance_context(self.analysis, context, self.packs, self.evidence, self.reviews)
        self.assertEqual(guidance["case_context"]["provenance"]["source_mode"], "ASSISTED_RIG_PLANNING")
        self.assertTrue(any(item["certainty"] == "UNKNOWN" for item in guidance["case_context"]["provenance"]["unknowns"]))
        unsafe = json.loads(json.dumps(self.intakes["sparse_floor_only"]))
        unsafe["telnet"] = "Store Cue 1"
        with self.assertRaises(ValueError):
            validate_show_intake(unsafe)
        unconfirmed_fly = json.loads(json.dumps(self.intakes["user_confirmed"]))
        unconfirmed_fly["user_confirmed_layout"][0]["mounting"] = "FLOWN_APPROVED"
        safety = route_show_intake(unconfirmed_fly)
        self.assertEqual(safety["planner_status"], "BYPASSED_USER_LAYOUT_SAFETY_CLARIFICATION")
        self.assertEqual(safety["clarification_requirements"][0]["question_id"], "CONFIRM_HANGING_CAPABILITY")
        self.assertEqual(safety["rig_context"]["placement_semantics"][0]["mounting"], "FLOWN_APPROVED")


if __name__ == "__main__":
    unittest.main()
