import json
import unittest
from pathlib import Path

from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.industry_review import (
    AI_RECOMMENDATION_SCHEMA,
    REVIEW_SCHEMA,
    active_knowledge_eligibility,
    ai_recommendation,
    antipattern_review_matrix,
    is_active_candidate,
    observation_priority_summary,
    principle_review_matrix,
    review_batch,
    review_observation,
    source_bias_metadata,
    validate_recommendation,
    validate_review,
)


FIXTURE = Path(__file__).parent / "fixtures" / "industry_reference_pack_001.json"


class IndustryHumanReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.pack = build_pack(raw["sources"], raw["observations"])
        cls.obs = cls.pack["observations"][0]

    def test_review_schema_and_observation_immutability(self):
        before = dict(self.obs)
        review = review_observation(self.obs, decision="ACCEPT", reason="Source and context are clear.", scope_confirmation="DOMAIN_ONLY", confidence="HIGH")
        self.assertEqual(review["schema"], REVIEW_SCHEMA)
        self.assertEqual(self.obs, before)
        self.assertTrue(is_active_candidate(review))

    def test_accept_with_limitation_is_active_but_scope_bound(self):
        review = review_observation(self.obs, decision="ACCEPT_WITH_LIMITATION", reason="Useful only for large touring rigs.", scope_confirmation="DOMAIN_ONLY")
        result = active_knowledge_eligibility(review)
        self.assertTrue(result["eligible"])
        self.assertEqual(result["scope"], "DOMAIN_ONLY")
        self.assertIn("cross-source", result["reason"])

    def test_pending_needs_context_reject_and_unsure_are_blocked(self):
        for decision in ("NEEDS_CONTEXT", "REJECT", "UNSURE", "DUPLICATE"):
            review = review_observation(self.obs, decision=decision, reason="Deferred for review.")
            self.assertFalse(is_active_candidate(review))
            self.assertEqual(active_knowledge_eligibility(review)["status"], "BLOCKED_PENDING_ACCEPTANCE")

    def test_ai_recommendation_is_separate_from_human_decision(self):
        recommendation = ai_recommendation(self.obs)
        self.assertEqual(recommendation["schema"], AI_RECOMMENDATION_SCHEMA)
        self.assertNotIn("decision", recommendation)
        self.assertIn("recommended_decision", recommendation)
        validate_recommendation(recommendation)
        visual = next(item for item in self.pack["observations"] if item["evidence_type"] == "VISUAL_INFERENCE")
        self.assertEqual(ai_recommendation(visual)["recommended_decision"], "NEEDS_CONTEXT")

    def test_batch_review_is_deterministic_and_skips_unlisted(self):
        observations = self.pack["observations"][:3]
        records = review_batch(observations, {"OBS001": {"decision": "ACCEPT", "reason": "clear"}, "OBS003": {"decision": "UNSURE", "reason": "defer"}}, reviewed_at="2026-01-01T00:00:00+00:00")
        self.assertEqual([item["evidence_id"] for item in records], ["OBS001", "OBS003"])
        self.assertTrue(all(validate_review(item)["schema"] == REVIEW_SCHEMA for item in records))

    def test_priority_visual_and_model_are_high(self):
        summary = observation_priority_summary(self.pack["observations"])
        self.assertIn("OBS016", summary["HIGH"])
        self.assertIn("OBS015", summary["HIGH"])
        self.assertTrue(summary["MEDIUM"])

    def test_manufacturer_bias_metadata_does_not_reject_sources(self):
        metadata = source_bias_metadata(self.pack["sources"])
        self.assertEqual(len(metadata), 6)
        self.assertTrue(all(item["selection_bias"] == "MANUFACTURER_CASE_STUDY_BIAS" for item in metadata))
        self.assertTrue(all(item["review_note"] for item in metadata))

    def test_principle_and_antipattern_matrices_start_pending(self):
        principles = principle_review_matrix(self.pack, ["FOCUS_HIERARCHY"])
        anti = antipattern_review_matrix(self.pack, ["EFFECT_TOO_EARLY"])
        self.assertEqual(principles[0]["current_status"], "PENDING_HUMAN_REVIEW")
        self.assertIn("OBS005", anti[0]["conflicting_observations"])

    def test_review_rejects_command_fields(self):
        with self.assertRaises(ValueError):
            review_observation({"observation_id": "x", "source_id": "s", "command": "Store Cue"}, decision="REJECT", reason="bad")


if __name__ == "__main__":
    unittest.main()
