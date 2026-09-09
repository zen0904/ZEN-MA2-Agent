import unittest

from zen_ma2_agent.knowledge import (
    AB_RESPONSES,
    EVIDENCE_SCHEMA,
    DesignDecisionScores,
    ab_review,
    case_context,
    evaluate_general_promotion,
    evaluate_user_promotion,
    general_principle_evidence,
    industry_reference,
    resolve_conflict,
    training_case_evidence,
    user_feedback,
    validate_evidence,
)


class LightingKnowledgeArchitectureTests(unittest.TestCase):
    def test_evidence_schema_and_layers_keep_provenance(self):
        record = industry_reference(evidence_id="industry-1", domain="KPOP", claim="reserve impact resources", context={"rig_scale": "LARGE"}, provenance="DOCUMENTED_DERIVED_OBSERVATION")
        self.assertEqual(record["schema"], EVIDENCE_SCHEMA)
        self.assertEqual(record["source_type"], "INDUSTRY_REFERENCE")
        self.assertEqual(record["scope"], "DOMAIN")
        self.assertEqual(validate_evidence(record)["evidence_id"], "industry-1")
        context = training_case_evidence(case_id="TRAINING_CASE_001", claim="strobe is an impact candidate", context={"style": "KPOP"})
        self.assertEqual(context["scope"], "CASE")

    def test_single_feedback_stays_case_local_and_unknown_is_formal(self):
        feedback = user_feedback(feedback_type="USER_DISLIKED", claim="effect too early", case_id="CASE_001", song_id="SONG_1", rig_id="RIG_1")
        self.assertEqual(feedback["scope"], "CASE")
        self.assertEqual(feedback["confidence"], "LOW")
        self.assertEqual(evaluate_user_promotion([feedback], "effect too early")["status"], "CASE_FEEDBACK_ONLY")
        scores = DesignDecisionScores(.8, .7, None, "MEDIUM")
        self.assertIsNone(scores.user_preference_score)

    def test_repeated_feedback_becomes_candidate_only_after_cross_case_and_rig_threshold(self):
        records = [user_feedback(feedback_type="USER_LIKED", claim="layer escalation", case_id=case_id, song_id=f"song-{index}", rig_id=rig_id) for index, (case_id, rig_id) in enumerate((("CASE_1", "RIG_1"), ("CASE_2", "RIG_2"), ("CASE_2", "RIG_2")), start=1)]
        result = evaluate_user_promotion(records, "layer escalation")
        self.assertTrue(result["promoted"])
        self.assertEqual(result["status"], "USER_PREFERENCE_CANDIDATE")
        self.assertEqual(result["candidate"]["scope"], "USER")
        self.assertEqual(evaluate_user_promotion(records[:2], "layer escalation")["status"], "CASE_FEEDBACK_ONLY")

    def test_industry_domain_isolation_and_general_promotion_requires_domains(self):
        first = industry_reference(evidence_id="industry-kpop", domain="KPOP", claim="reserve impact resources", context={}, provenance="REFERENCE_A")
        second = industry_reference(evidence_id="industry-band", domain="BAND", claim="reserve impact resources", context={}, provenance="REFERENCE_B")
        result = evaluate_general_promotion([first, second], "reserve impact resources")
        self.assertTrue(result["promoted"])
        isolated = evaluate_general_promotion([first], "reserve impact resources")
        self.assertFalse(isolated["promoted"])
        self.assertEqual(isolated["status"], "CANDIDATE_ONLY")

    def test_ab_feedback_is_normalized_without_style_promotion(self):
        record = ab_review(variant_a="A", variant_b="B", response="A_PREFERRED", context={"case_id": "CASE_1", "song_id": "SONG_1", "rig_id": "RIG_1"})
        self.assertEqual(record["claim"], "A_PREFERRED")
        self.assertEqual(record["scope"], "CASE")
        with self.assertRaises(ValueError):
            ab_review(variant_a="A", variant_b="B", response="A_IS_BEST", context={})
        self.assertIn("BOTH_ACCEPTABLE", AB_RESPONSES)

    def test_general_principle_provenance_and_case_not_global(self):
        principle = general_principle_evidence(principle="RESERVE_HEADROOM", claim="reserve headroom for later escalation")
        self.assertEqual(principle["source_type"], "GENERAL_PRINCIPLE")
        self.assertEqual(principle["provenance"], "CURRENT_INTERNAL_GENERAL_PRINCIPLE")
        case = case_context(case_id="TRAINING_CASE_001", domain="KPOP", claim="strobe is an impact candidate", context={})
        self.assertEqual(case["scope"], "CASE")
        self.assertEqual(case["domain"], "KPOP")

    def test_industry_user_conflict_preserves_both(self):
        result = resolve_conflict(industry_support=3, user_disliked=1, claim="effect too early")
        self.assertEqual(result["status"], "PROFESSIONALLY_VALID_USER_STYLE_DIVERGENCE")
        self.assertTrue(result["preserve_industry_knowledge"])
        self.assertTrue(result["create_user_variant"])

    def test_evidence_rejects_command_fields(self):
        with self.assertRaises(ValueError):
            industry_reference(evidence_id="bad", domain="GENERAL", claim="unsafe", context={"raw_command": "Store Cue 1"}, provenance="test")


if __name__ == "__main__":
    unittest.main()
