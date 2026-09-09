import json
import unittest
from pathlib import Path

from zen_ma2_agent.industry_pack_002 import (
    PACK002_SCHEMA,
    PRIOR_SCHEMA,
    VISUAL_LANGUAGES,
    build_pack_002,
    build_prior,
    classify_visual_language,
    compare_packs,
    style_alignment,
    validate_observation_002,
    validate_source_002,
)
from zen_ma2_agent.industry_references import build_pack


ROOT = Path(__file__).parent
FIXTURE = ROOT / "fixtures" / "industry_reference_pack_002.json"
FIXTURE_001 = ROOT / "fixtures" / "industry_reference_pack_001.json"


class IndustryPack002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.pack = build_pack_002(cls.raw)

    def test_contemporary_prior_schema_and_window(self):
        prior = self.pack["contemporary_prior"]
        self.assertEqual(prior["schema"], PRIOR_SCHEMA)
        self.assertEqual(prior["time_window"], "2022-2025")
        self.assertGreaterEqual(prior["evidence_count"], 10)

    def test_time_window_is_required_and_bounded(self):
        bad = dict(self.raw["sources"][0])
        bad["time_window"] = "1990-1999"
        with self.assertRaises(ValueError):
            validate_source_002(bad)

    def test_visual_language_classification_is_explicit(self):
        self.assertEqual(classify_visual_language(["clean_minimal", "HYBRID", "HYBRID"]), ["CLEAN_MINIMAL", "HYBRID"])
        with self.assertRaises(ValueError):
            classify_visual_language(["NEON_MAGIC"])
        self.assertTrue(set(self.pack["sources"][0]["visual_language"]) <= VISUAL_LANGUAGES)

    def test_transient_and_impact_categories_are_present(self):
        categories = {item["category"] for item in self.pack["observations"]}
        self.assertIn("TRANSIENT_IMPACT", categories)
        self.assertIn("IMPACT_RESERVATION", categories)
        self.assertIn("POST_IMPACT_RESET", categories)

    def test_controlled_maximalism_and_clutter_are_separate(self):
        categories = {item["category"] for item in self.pack["observations"]}
        self.assertIn("CONTROLLED_MAXIMALISM", categories)
        self.assertIn("VISUAL_CLUTTER", categories)
        clutter = [o for o in self.pack["observations"] if o["category"] == "VISUAL_CLUTTER"]
        self.assertTrue(any(o["evidence_type"] == "DIRECT_SOURCE_STATEMENT" for o in clutter))

    def test_visual_first_fields_and_evidence_separation(self):
        self.assertTrue(all("visual_language" in o for o in self.pack["observations"]))
        kinds = {o["evidence_type"] for o in self.pack["observations"]}
        self.assertEqual(kinds, {"DIRECT_SOURCE_STATEMENT", "VISUAL_INFERENCE", "MODEL_INTERPRETATION"})

    def test_style_alignment_never_promotes_profile(self):
        result = style_alignment(self.pack, self.raw["style_candidate"])
        self.assertFalse(result["promoted"])
        self.assertTrue(result["review_required"])
        self.assertTrue(any(item["status"] in {"ALIGN", "PARTIALLY_ALIGN"} for item in result["alignments"]))

    def test_invalid_promoted_style_candidate_rejected(self):
        bad = dict(self.raw)
        bad["style_candidate"] = {"promoted": True}
        with self.assertRaises(ValueError):
            build_pack_002(bad)

    def test_source_bias_is_retained(self):
        self.assertTrue(all(item["selection_bias"] for item in self.pack["sources"]))
        self.assertIn("MANUFACTURER_CASE_STUDY_BIAS", {item["selection_bias"] for item in self.pack["sources"]})

    def test_pack_001_and_002_coexist(self):
        p1raw = json.loads(FIXTURE_001.read_text(encoding="utf-8"))
        p1 = build_pack(p1raw["sources"], p1raw["observations"])
        result = compare_packs(p1, self.pack)
        self.assertEqual(result["pack001_sources"], 6)
        self.assertEqual(result["pack002_sources"], 9)
        self.assertEqual(result["global_promotions"], [])

    def test_observation_rejects_command_fields(self):
        bad = dict(self.raw["observations"][0])
        bad["command"] = "Store Cue"
        with self.assertRaises(ValueError):
            validate_observation_002(bad)

    def test_prior_builder_uses_source_diversity(self):
        prior = build_prior(self.pack["sources"], self.pack["observations"])
        self.assertEqual(prior["schema"], PRIOR_SCHEMA)
        self.assertGreaterEqual(prior["source_diversity"], 4)
        self.assertEqual(self.pack["schema"], PACK002_SCHEMA)


if __name__ == "__main__":
    unittest.main()
