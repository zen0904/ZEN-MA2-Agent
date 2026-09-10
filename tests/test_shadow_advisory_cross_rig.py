import json
import unittest
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.shadow_advisory_cross_rig import evaluate_cross_rig, validate_cross_rig_fixture
from zen_ma2_agent.shadow_rig_context import build_cross_rig_evaluation_contexts, validate_shadow_rig_context
from zen_ma2_agent.training_case import build_training_case_001
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent


class ShadowAdvisoryCrossRigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8"))
        cls.cross_fixture = validate_cross_rig_fixture(json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_002.json").read_text(encoding="utf-8")))
        by_id = {item["case_id"]: item for item in source["cases"]}
        cls.common_song, cls.restrained_song = by_id[cls.cross_fixture["common_song_case_id"]], by_id[cls.cross_fixture["restrained_song_case_id"]]
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        raw = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(raw["sources"], raw["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]
        group_names = [(1, "HYBRID"), (2, "SPOT"), (3, "BEAM"), (4, "WASH"), (5, "B-EYE"), (6, "LED PAR"), (7, "STROBE")]
        cls.profile = {
            "groups": [{"group_id": number, "name": name, "fixture_ids_in_selection_order": list(range(number * 100 + 1, number * 100 + 9))} for number, name in group_names],
            "fixtures": [{"fixture_id": item, "fixture_type": f"TYPE_{number}"} for number, _name in group_names for item in range(number * 100 + 1, number * 100 + 9)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}], "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "SUPPORTED"},
        }
        cls.rigs = build_cross_rig_evaluation_contexts(build_training_case_001(cls.profile))

    def evaluate(self):
        return evaluate_cross_rig(self.common_song, self.restrained_song, self.rigs, designer=FirstSongDesigner(), profile=self.profile, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews)

    def test_four_bounded_rigs_and_common_song_are_explicit(self):
        self.assertEqual(set(self.rigs), set(self.cross_fixture["rig_context_ids"]))
        self.assertTrue(all(item["label"] == "SHADOW_EVALUATION_ONLY" for item in self.rigs.values()))
        self.assertEqual(self.common_song["case_id"], "CASE_D_BUILDUP_DROP")

    def test_same_song_intent_is_preserved_but_resource_choices_differ(self):
        result = self.evaluate()
        self.assertTrue(result["same_song_intent_preserved"])
        self.assertTrue(result["cross_rig_differences"])
        self.assertEqual(len(set(result["cross_rig_choice_signatures"].values())), 4)
        self.assertEqual(result["baseline_preservation"], "IDENTICAL")
        self.assertEqual(result["failures"], [])

    def test_medium_rig_prioritizes_and_substitutes_with_explicit_reason(self):
        medium = next(item for item in self.evaluate()["common_song_results"] if item["guidance_context"]["case_context"]["case_id"] == "RIG_B_MEDIUM_LIVE")
        low = next(item for item in medium["resource_advisory"]["resource_choices"] if item["energy_state"] == "LOW")
        high = next(item for item in medium["resource_advisory"]["resource_choices"] if item["energy_state"] == "HIGH")
        self.assertIn("COMBINED_TEXTURE_IMPACT", low["OMIT"])
        self.assertTrue(high["SUBSTITUTE"])
        self.assertTrue(all(item["REASON"] for item in high["SUBSTITUTE"]))
        self.assertTrue(any("RHYTHMIC_ACCENT" in reason for reason in high["REASON"]))

    def test_led_only_redesigns_using_declared_led_capabilities(self):
        led = next(item for item in self.evaluate()["common_song_results"] if item["guidance_context"]["case_context"]["case_id"] == "RIG_C_LED_ONLY")
        high = next(item for item in led["resource_advisory"]["resource_choices"] if item["energy_state"] == "HIGH")
        selected = {role for choice in led["resource_advisory"]["resource_choices"] for key in ("KEEP", "REDUCE", "OMIT") for role in choice[key]}
        self.assertFalse(any("BEAM" in item or "AERIAL" in item or "GOBO" in item or "MOVER" in item for item in selected))
        self.assertIn("LEFT_RIGHT_TIMING_CONTRAST_PLUS_DENSITY_PUNCTUATION", {item["REPLACEMENT"] for item in high["SUBSTITUTE"]})
        self.assertEqual(led["cross_rig_rubric"]["SUBSTITUTION_REASONING"], "STRONG")

    def test_asymmetric_rig_keeps_hierarchy_without_forcing_a_mirror(self):
        imperfect = next(item for item in self.evaluate()["common_song_results"] if item["guidance_context"]["case_context"]["case_id"] == "RIG_D_IMPERFECT_ASYMMETRIC")
        high = next(item for item in imperfect["resource_advisory"]["resource_choices"] if item["energy_state"] == "HIGH")
        selected = {role for choice in imperfect["resource_advisory"]["resource_choices"] for key in ("KEEP", "REDUCE", "OMIT") for role in choice[key]}
        self.assertFalse(any(item in {"MIRROR_PAIR", "SYMMETRIC_TEXTURE", "SYMMETRIC_FULL_RIG"} for item in selected))
        self.assertIn("CENTER_FOCUS_PLUS_ASYMMETRIC_ACCENT", {item["REPLACEMENT"] for item in high["SUBSTITUTE"]})

    def test_restrained_song_has_complete_low_medium_high_looks_on_constrained_rigs(self):
        result = self.evaluate()
        for item in result["restrained_song_results"]:
            self.assertEqual(item["cross_rig_rubric"]["COMPLETE_LOOK_UNDER_CONSTRAINT"], "STRONG")
            low = next(choice for choice in item["resource_advisory"]["resource_choices"] if choice["energy_state"] == "LOW")
            self.assertTrue(low["OMIT"])
            self.assertTrue(low["REASON"])
        for item in result["common_song_results"]:
            self.assertEqual(item["cross_rig_rubric"]["COMPLETE_LOOK_UNDER_CONSTRAINT"], "STRONG")
            self.assertEqual({choice["energy_state"] for choice in item["resource_advisory"]["resource_choices"]}, {"LOW", "MEDIUM", "HIGH"})

    def test_resource_adaptation_follows_case_affordance_not_rig_name(self):
        changed = json.loads(json.dumps(self.rigs))
        changed["RIG_B_MEDIUM_LIVE"]["design_affordances"]["LOW"]["KEEP"] = ["BROAD_ENVIRONMENT"]
        altered = evaluate_cross_rig(self.common_song, self.restrained_song, changed, designer=FirstSongDesigner(), profile=self.profile, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews)
        medium = next(item for item in altered["common_song_results"] if item["guidance_context"]["case_context"]["case_id"] == "RIG_B_MEDIUM_LIVE")
        low = next(choice for choice in medium["resource_advisory"]["resource_choices"] if choice["energy_state"] == "LOW")
        self.assertEqual(low["KEEP"], ["BROAD_ENVIRONMENT"])

    def test_invalid_shadow_rig_cannot_select_undeclared_role(self):
        invalid = json.loads(json.dumps(self.rigs["RIG_C_LED_ONLY"]))
        invalid["design_affordances"]["HIGH"]["KEEP"].append("AERIAL")
        with self.assertRaises(ValueError):
            validate_shadow_rig_context(invalid)


if __name__ == "__main__":
    unittest.main()
