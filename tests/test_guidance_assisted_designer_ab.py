import json
import unittest
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent.guidance_assisted_ab_evaluation import evaluate_ab_case, validate_ab_fixture
from zen_ma2_agent.guidance_assisted_designer import GUIDANCE_ASSISTED_MODE, GuidanceAssistedExperimentalDesigner
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.rig_intake import route_show_intake, validate_rig_context
from zen_ma2_agent.song_analysis import SongAnalysisAdapter
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent


class GuidanceAssistedDesignerABTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ab_fixture = validate_ab_fixture(json.loads((ROOT / "fixtures" / "guidance_assisted_ab_001.json").read_text(encoding="utf-8")))
        songs = json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8"))["cases"]
        cls.songs = {item["case_id"]: item for item in songs}
        intakes = json.loads((ROOT / "fixtures" / "rig_intake_router_001.json").read_text(encoding="utf-8"))["intakes"]
        cls.intakes = intakes
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        raw = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(raw["sources"], raw["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]
        cls.profile = {
            "groups": [
                {"group_id": 1, "name": "FOCUS"}, {"group_id": 2, "name": "COLOR"}, {"group_id": 3, "name": "TEXTURE"},
                {"group_id": 4, "name": "DENSITY"}, {"group_id": 5, "name": "TIMING"},
            ],
            "fixtures": [{"fixture_id": item, "fixture_type": "SYNTHETIC"} for item in range(101, 141)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}, {"reference": "4.1", "preset_type": "COLOR", "name": "cool palette"}],
            "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "UNINITIALIZED"},
        }

    def rig(self, intake_name, bindings, *, asymmetry=False):
        context = route_show_intake(json.loads(json.dumps(self.intakes[intake_name])))["rig_context"]
        context["role_bindings"] = [{"role": role, "target": {"type": "group", "ref": group}, "certainty": "CONFIRMED", "source": "SYNTHETIC_EVALUATION_BINDING"} for role, group in bindings.items()]
        if asymmetry:
            context["asymmetry"] = {"detected": True, "source": "USER_CONFIRMED"}
        return validate_rig_context(context)

    def cases(self):
        return {
            "AB_CASE_1_BUILDUP_DROP": (self.songs["CASE_D_BUILDUP_DROP"], self.rig("user_confirmed", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5})),
            "AB_CASE_2_RESTRAINED_MINIMAL": (self.songs["CASE_C_RESTRAINED_MINIMAL"], self.rig("sparse_floor_only", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5})),
            "AB_CASE_3_LED_ONLY": (self.songs["CASE_D_BUILDUP_DROP"], self.rig("led_only", {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5})),
            "AB_CASE_4_ASYMMETRIC": (self.songs["CASE_D_BUILDUP_DROP"], self.rig("user_confirmed", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}, asymmetry=True)),
        }

    def evaluate(self, key):
        song, rig = self.cases()[key]
        return evaluate_ab_case(song, profile=self.profile, rig_context=rig, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())

    def test_fixture_has_four_required_synthetic_cases(self):
        self.assertEqual({item["case_id"] for item in self.ab_fixture["cases"]}, set(self.cases()))

    def test_production_default_is_unchanged_and_experiment_is_explicit(self):
        song, rig = self.cases()["AB_CASE_1_BUILDUP_DROP"]
        song_input = SongAnalysisAdapter().to_designer_input(song["analysis"])
        production = FirstSongDesigner()
        before = production.design(song_input, self.profile)
        result = self.evaluate("AB_CASE_1_BUILDUP_DROP")
        after = production.design(song_input, self.profile)
        self.assertEqual(before, after)
        self.assertEqual(result["experimental_mode"], GUIDANCE_ASSISTED_MODE)
        self.assertEqual(result["guidance_assisted_plan"]["designer"]["production_designer_modified"], False)
        self.assertTrue(result["production_default_unchanged"])

    def test_both_a_and_b_are_typed_plans_with_no_transport_text(self):
        result = self.evaluate("AB_CASE_1_BUILDUP_DROP")
        for plan in (result["baseline_plan"], result["guidance_assisted_plan"]):
            self.assertEqual(validate_show_plan(plan), plan)
            self.assertNotIn("telnet", str(plan).casefold())
            self.assertNotIn("command", str(plan).casefold())
        self.assertTrue(result["guidance_assisted_plan"]["designer"]["changed_typed_actions"])

    def test_buildup_drop_develops_complete_states_and_avoids_constant_maximum(self):
        result = self.evaluate("AB_CASE_1_BUILDUP_DROP")
        experimental = [item["experimental_design"] for item in result["guidance_assisted_plan"]["cues"] if item.get("experimental_design")]
        self.assertTrue(any(item["omitted_roles"] for item in experimental))
        self.assertTrue(any(item["selected_roles"] for item in experimental))
        self.assertEqual(result["assisted_rubric"]["COMPLETE_LOOK_QUALITY"], "STRONG")
        self.assertEqual(result["result"], "B_BETTER")

    def test_restrained_case_uses_intentional_omission_not_only_lower_dimmer(self):
        result = self.evaluate("AB_CASE_2_RESTRAINED_MINIMAL")
        low = next(cue["experimental_design"] for cue in result["guidance_assisted_plan"]["cues"] if cue.get("source_section_id") == "intro")
        medium = next(cue["experimental_design"] for cue in result["guidance_assisted_plan"]["cues"] if cue.get("source_section_id") == "refrain_1")
        self.assertTrue(low["omitted_roles"])
        self.assertNotEqual(low["selected_roles"], medium["selected_roles"])
        self.assertEqual(result["result"], "B_BETTER")

    def test_led_only_never_selects_mover_beam_gobo_or_position_language(self):
        result = self.evaluate("AB_CASE_3_LED_ONLY")
        selected = {role for cue in result["guidance_assisted_plan"]["cues"] for role in cue.get("experimental_design", {}).get("selected_roles", [])}
        self.assertFalse(any(token in role for role in selected for token in ("MOVER", "BEAM", "GOBO", "AERIAL", "POSITION")))
        self.assertIn("COLOR_FIELD", selected)
        self.assertEqual(result["result"], "B_BETTER")

    def test_asymmetric_rig_is_preserved_and_result_is_honestly_mixed(self):
        result = self.evaluate("AB_CASE_4_ASYMMETRIC")
        selected = {role for cue in result["guidance_assisted_plan"]["cues"] for role in cue.get("experimental_design", {}).get("selected_roles", [])}
        self.assertFalse(any("MIRROR" in role or "SYMMETRIC" in role for role in selected))
        self.assertEqual(result["result"], "MIXED")
        self.assertEqual(result["guidance_context"]["case_context"]["provenance"]["source_mode"], "USER_CONFIRMED_LAYOUT")

    def test_contextual_and_rejected_candidates_never_become_active(self):
        result = self.evaluate("AB_CASE_3_LED_ONLY")
        self.assertEqual(result["context_dependent_active"], [])
        self.assertEqual(result["rejected_active"], [])

    def test_existing_show_context_without_confirmed_binding_is_accepted_but_unchanged(self):
        rig = route_show_intake(json.loads(json.dumps(self.intakes["existing_show"]))) ["rig_context"]
        result = evaluate_ab_case(self.songs["CASE_D_BUILDUP_DROP"], profile=self.profile, rig_context=rig, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())
        self.assertFalse(result["guidance_assisted_plan"]["designer"]["changed_typed_actions"])
        self.assertEqual(result["result"], "NO_MEANINGFUL_DIFFERENCE")

    def test_undeclared_or_unscanned_role_binding_is_rejected(self):
        context = route_show_intake(json.loads(json.dumps(self.intakes["led_only"]))) ["rig_context"]
        context["role_bindings"] = [{"role": "MOVER_TEXTURE_LAYER", "target": {"type": "group", "ref": 99}, "certainty": "CONFIRMED", "source": "INVALID"}]
        with self.assertRaises(ValueError):
            validate_rig_context(context)


if __name__ == "__main__":
    unittest.main()
