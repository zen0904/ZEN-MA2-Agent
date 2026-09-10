import json
import unittest
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.real_song_existing_show_ab import evaluate_real_song_existing_show_ab
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent
PROJECT = ROOT.parent


class RealSongExistingShowAB001Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / "fixtures" / "real_song_existing_show_ab_001.json").read_text(encoding="utf-8"))
        cls.analysis = json.loads((PROJECT / "examples" / "REALISTIC_SONG_ANALYSIS.json").read_text(encoding="utf-8"))
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        pack_001 = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(pack_001["sources"], pack_001["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]

    def evaluate(self):
        return evaluate_real_song_existing_show_ab(self.fixture, self.analysis, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())

    def test_real_song_and_existing_show_snapshot_are_exact_and_read_only(self):
        profile = self.fixture["show_snapshot"]["profile"]
        self.assertEqual(self.fixture["song_analysis_ref"], "examples/REALISTIC_SONG_ANALYSIS.json")
        self.assertEqual([item["name"] for item in profile["groups"]], ["HYBRID", "SPOT", "BEAM", "WASH", "B-EYE", "LED PAR", "STROBE"])
        self.assertEqual([item["reference"] for item in profile["presets"]], ["6.1", "6.2", "6.3", "6.4", "6.5"])
        self.assertEqual(profile["geometry_analysis"]["status"], "GEOMETRY_UNINITIALIZED")
        self.assertEqual(profile["semantic_presets"], [])

    def test_existing_show_route_preserves_resources_and_bypasses_planner(self):
        result = self.evaluate()
        self.assertEqual(result["existing_show_route"]["route"], "EXISTING_SHOW")
        self.assertEqual(result["existing_show_route"]["planner_status"], "BYPASSED_EXISTING_SHOW")
        self.assertEqual(result["resource_binding_policy"]["status"], "NO_CONFIRMED_ROLE_BINDINGS")
        self.assertEqual(result["ma2_write_audit"], "ZERO_WRITES_BY_DESIGN")

    def test_a_is_unchanged_and_b_exposes_existing_b3_intent_without_fabricated_binding(self):
        result = self.evaluate()
        self.assertTrue(result["production_default_unchanged"])
        self.assertEqual(validate_show_plan(result["baseline_plan"]), result["baseline_plan"])
        self.assertEqual(validate_show_plan(result["experimental_plan"]), result["experimental_plan"])
        for baseline, experimental in zip(result["baseline_plan"]["cues"], result["experimental_plan"]["cues"]):
            self.assertEqual(baseline["actions"], experimental["actions"])
            design = experimental["experimental_design"]
            self.assertEqual(design["intent_realizability"]["status"], "NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES")
            self.assertEqual(design["role_states"], [])
            self.assertEqual(design["human_review"], "UNSET")

    def test_review_uses_exact_occurrences_and_keeps_human_decisions_unset(self):
        result = self.evaluate()
        cards = result["review"]["cards"]
        self.assertEqual(len(cards), len(result["experimental_plan"]["cues"]))
        self.assertTrue(all(card["CUE_ID"] for card in cards))
        self.assertTrue(all(card["SECTION_INSTANCE_ID"] for card in cards))
        self.assertTrue(all(card["HUMAN_REVIEW"] == "UNSET" for card in cards))
        self.assertTrue(all(item["status"] == "NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES" for item in result["unrealized_intents"]))


if __name__ == "__main__":
    unittest.main()
