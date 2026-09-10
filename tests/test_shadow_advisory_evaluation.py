import json
import unittest
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.shadow_advisory_evaluation import (
    EVALUATION_SCHEMA,
    evaluate_fixture,
    evaluate_shadow_case,
    validate_evaluation_fixture,
)
from zen_ma2_agent.training_case import build_training_case_001
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent
PROJECT = ROOT.parent


class ShadowAdvisoryEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = validate_evaluation_fixture(json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8")))
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        raw_001 = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(raw_001["sources"], raw_001["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]
        cls.profile = {
            "groups": [{"group_id": 1, "name": "HYBRID", "fixture_ids_in_selection_order": list(range(101, 109))}, {"group_id": 2, "name": "BEAM", "fixture_ids_in_selection_order": list(range(201, 209))}],
            "fixtures": [{"fixture_id": item, "fixture_type": "HYBRID_TYPE"} for item in range(101, 109)] + [{"fixture_id": item, "fixture_type": "BEAM_TYPE"} for item in range(201, 209)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}], "effects": [], "semantic_presets": [],
            "geometry_analysis": {"status": "SUPPORTED"},
        }
        cls.case = build_training_case_001(cls.profile)

    def evaluate(self):
        return evaluate_fixture(self.fixture, designer=FirstSongDesigner(), profile=self.profile, training_case=self.case, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews)

    def test_five_explicitly_synthetic_structures_are_present(self):
        self.assertEqual(len(self.fixture["cases"]), 5)
        self.assertTrue(all(item["synthetic_label"] == "SYNTHETIC_EVALUATION_ONLY" for item in self.fixture["cases"]))
        self.assertEqual({item["case_id"] for item in self.fixture["cases"]}, {
            "CASE_A_HIGH_ENERGY_CONTEMPORARY_POP", "CASE_B_MEDIUM_VERSE_CHORUS", "CASE_C_RESTRAINED_MINIMAL", "CASE_D_BUILDUP_DROP", "CASE_E_IRREGULAR_NON_LINEAR",
        })

    def test_every_case_preserves_actual_deterministic_show_plan(self):
        result = self.evaluate()
        self.assertEqual(result["schema"], EVALUATION_SCHEMA)
        self.assertEqual(result["baseline_preservation"], "IDENTICAL")
        self.assertTrue(all(item["baseline_vs_shadow_plan"] == "IDENTICAL" for item in result["cases"]))

    def test_quality_rubric_is_non_aggregated_and_traceable(self):
        result = self.evaluate()
        for item in result["cases"]:
            self.assertEqual(item["rubric"]["MUSICAL_STRUCTURE_UNDERSTANDING"], "STRONG")
            self.assertEqual(item["rubric"]["COMPLETE_LOOK_REASONING"], "STRONG")
            self.assertEqual(item["rubric"]["EVIDENCE_TRACEABILITY"], "STRONG")
            self.assertEqual(item["rubric"]["ACTIONABLE_DESIGN_VALUE"], "ACCEPTABLE")
            self.assertNotIn("total", {key.casefold() for key in item["rubric"]})

    def test_negative_rules_and_context_dependent_candidates_do_not_reappear(self):
        result = self.evaluate()
        self.assertEqual(result["negative_failures"], [])
        for item in result["cases"]:
            self.assertIn("DOMINANT_THEME_COLOR", item["intentionally_unused_or_contextual_style"])
            self.assertIn("STRONG_TRANSIENT_IMPACT", item["intentionally_unused_or_contextual_style"])
            rejected = {entry["name"] for entry in item["guidance_context"]["rejected_interpretations"]}
            self.assertTrue({"HIGH_IMPACT_ALWAYS", "MAXIMALISM_EQUALS_CLUTTER", "MULTICOLOR_EQUALS_BAD", "MINIMALISM_EQUALS_LOW_PREFERENCE", "KPOP_YG_EQUALS_GLOBAL_STYLE_RULE"} <= rejected)

    def test_complete_look_reasoning_distinguishes_low_and_high_sections(self):
        result = self.evaluate()
        pop = next(item for item in result["cases"] if item["case_id"] == "CASE_A_HIGH_ENERGY_CONTEMPORARY_POP")
        advisory = next(item for item in pop["advisories"] if item["advisory_id"] == "advisory-complete-energy-states")
        self.assertIn("intro (INTRO)", advisory["recommendation"])
        self.assertIn("chorus_1 (CHORUS)", advisory["recommendation"])
        self.assertIn("not one look at different Dimmer levels", advisory["recommendation"])

    def test_irregular_case_is_non_monotonic_and_retains_non_formulaic_arc(self):
        result = self.evaluate()
        irregular = next(item for item in result["cases"] if item["case_id"] == "CASE_E_IRREGULAR_NON_LINEAR")
        energies = [item["energy"] for item in irregular["energy_map"]]
        self.assertFalse(all(left <= right for left, right in zip(energies, energies[1:])))
        self.assertEqual(irregular["rubric"]["NON_FORMULAIC_REASONING"], "STRONG")
        arc = next(item for item in irregular["advisories"] if item["advisory_id"] == "advisory-whole-song-arc")
        self.assertIn("not a prescribed energy curve", arc["unresolved_conditions"][0])

    def test_existing_realistic_fixture_is_reused_as_a_baseline_control(self):
        analysis = json.loads((PROJECT / "examples" / "REALISTIC_SONG_ANALYSIS.json").read_text(encoding="utf-8"))
        control = {"case_id": "EXISTING_REALISTIC_CONTROL", "name": "Existing realistic fixture control", "analysis": analysis}
        result = evaluate_shadow_case(control, designer=FirstSongDesigner(), profile=self.profile, training_case=self.case, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews)
        self.assertEqual(result["baseline_vs_shadow_plan"], "IDENTICAL")
        self.assertEqual(result["negative_failures"], [])


if __name__ == "__main__":
    unittest.main()
