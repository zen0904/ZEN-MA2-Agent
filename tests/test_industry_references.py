import json
import unittest
from pathlib import Path

from zen_ma2_agent.industry_references import (
    OBSERVATION_CATEGORIES,
    OBSERVATION_SCHEMA,
    PACK_SCHEMA,
    SOURCE_SCHEMA,
    DerivedObservation,
    IndustryReferenceSource,
    build_pack,
    cross_analyze,
    validate_observation,
    validate_source,
)


FIXTURE = Path(__file__).parent / "fixtures" / "industry_reference_pack_001.json"


class IndustryReferencePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.pack = build_pack(cls.raw["sources"], cls.raw["observations"])

    def test_source_schema_reliability_and_copyright_policy(self):
        source = validate_source(self.raw["sources"][0])
        self.assertEqual(source["schema"], SOURCE_SCHEMA)
        self.assertIn(source["reliability"], {"HIGH", "MEDIUM", "LOW", "UNKNOWN"})
        self.assertEqual(source["copyright_policy"], "DERIVED_OBSERVATIONS_ONLY")

    def test_pack_has_three_domains_and_two_sources_each(self):
        counts = {}
        for source in self.pack["sources"]:
            counts[source["domain"]] = counts.get(source["domain"], 0) + 1
        self.assertEqual(self.pack["schema"], PACK_SCHEMA)
        self.assertGreaterEqual(len(counts), 3)
        self.assertTrue(all(count >= 2 for count in counts.values()))

    def test_observation_direct_inferred_and_unknown_are_distinct(self):
        kinds = {item["evidence_type"] for item in self.pack["observations"]}
        self.assertIn("DIRECT_SOURCE_STATEMENT", kinds)
        self.assertIn("VISUAL_INFERENCE", kinds)
        self.assertIn("MODEL_INTERPRETATION", kinds)
        self.assertIn("LOW", {item["confidence"] for item in self.pack["observations"]})
        self.assertEqual(self.pack["observations"][0]["schema"], OBSERVATION_SCHEMA)

    def test_human_review_is_default(self):
        record = DerivedObservation("x", "s", "GENERAL", "SECTION_CONTRAST", "short observation", "DIRECT_SOURCE_STATEMENT", "UNKNOWN", "DOMAIN", "test", "unknown")
        self.assertEqual(record.review_status, "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(validate_observation(record.to_dict())["review_status"], "HUMAN_REVIEW_REQUIRED")

    def test_unknown_category_and_invalid_domain_rejected(self):
        with self.assertRaises(ValueError):
            DerivedObservation("x", "s", "GENERAL", "NOT_A_CATEGORY", "short", "DIRECT_SOURCE_STATEMENT", "LOW", "DOMAIN", "test", "unknown")
        with self.assertRaises(ValueError):
            DerivedObservation("x", "s", "UNLISTED", "SECTION_CONTRAST", "short", "DIRECT_SOURCE_STATEMENT", "LOW", "DOMAIN", "test", "unknown")
        self.assertIn("SECTION_CONTRAST", OBSERVATION_CATEGORIES)

    def test_source_and_observation_references_are_traceable(self):
        source_ids = {item["source_id"] for item in self.pack["sources"]}
        self.assertTrue(all(item["source_id"] in source_ids for item in self.pack["observations"]))
        self.assertEqual(len(source_ids), len(self.pack["sources"]))

    def test_cross_domain_repeats_are_reported_without_global_promotion(self):
        result = cross_analyze(self.pack, ["FOCUS_HIERARCHY", "RESOURCE_AWARENESS"], ["EFFECT_FATIGUE"])
        categories = {item["category"] for item in result["repeated_cross_domain"]}
        self.assertIn("FOCUS_HIERARCHY", categories)
        self.assertEqual(result["global_promotions"], [])

    def test_conflicting_or_contextual_stances_are_preserved(self):
        result = cross_analyze(self.pack, ["EFFECT_FATIGUE_AVOIDANCE"], ["EFFECT_TOO_EARLY"])
        self.assertTrue(any(item["category"] == "MOVEMENT_USAGE" for item in result["conflicts"]))
        statuses = {item["status"] for item in result["principles"]}
        self.assertIn("PARTIALLY_SUPPORTED", statuses)
        anti = {item["name"]: item["status"] for item in result["anti_patterns"]}
        self.assertEqual(anti["EFFECT_TOO_EARLY"], "CONTEXT_DEPENDENT")

    def test_copyright_safe_records_reject_long_copied_text_and_forbidden_fields(self):
        with self.assertRaises(ValueError):
            DerivedObservation("x", "s", "GENERAL", "SECTION_CONTRAST", "a" * 601, "DIRECT_SOURCE_STATEMENT", "LOW", "DOMAIN", "test", "unknown")
        with self.assertRaises(ValueError):
            DerivedObservation("x", "s", "GENERAL", "SECTION_CONTRAST", "short", "DIRECT_SOURCE_STATEMENT", "LOW", "DOMAIN", "test", "unknown", context={"quote": "copied"})

    def test_pack_rejects_unknown_source_reference(self):
        bad = dict(self.raw["observations"][0])
        bad["source_id"] = "MISSING"
        with self.assertRaises(ValueError):
            build_pack(self.raw["sources"], [bad])


if __name__ == "__main__":
    unittest.main()
