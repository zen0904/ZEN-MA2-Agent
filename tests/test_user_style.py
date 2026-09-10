import json
import unittest
from pathlib import Path

from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.user_style import (
    CANDIDATE_SCHEMA,
    SCHEMA,
    compare_with_industry,
    REVIEW_SCHEMA,
    build_review_records,
    synthesize_candidates,
    validate_candidate,
    validate_evidence,
    validate_review,
)


ROOT = Path(__file__).parent


class UserStyleEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))
        cls.evidence = [validate_evidence(item) for item in raw["evidence"]]
        cls.pack = build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))
        cls.decisions = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.decisions.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])

    def test_schema_and_human_provenance(self):
        self.assertEqual(self.evidence[0]["schema"], SCHEMA)
        self.assertTrue(all(item["provenance"] == "HUMAN_VISUAL_REVIEW" for item in self.evidence))

    def test_raw_reaction_and_normalized_interpretation_are_separate(self):
        item = self.evidence[0]
        self.assertEqual(item["raw_user_reaction"], item["user_reaction"])
        self.assertIn("CONTROLLED_HIGH_IMPACT", item["normalized_traits"])

    def test_primary_positive_and_negative_case_local(self):
        self.assertEqual(self.evidence[0]["strength"], "STRONG_POSITIVE")
        negative = next(item for item in self.evidence if item["evidence_id"] == "USE006_BILLY")
        self.assertEqual(negative["scope"], "CASE_LOCAL")
        self.assertEqual(negative["strength"], "STRONG_NEGATIVE")

    def test_mixed_reference_preserved(self):
        mixed = next(item for item in self.evidence if item["evidence_id"] == "USE005_KAROLG")
        self.assertEqual(mixed["strength"], "NEUTRAL")
        self.assertIn("CONTROLLED_MAXIMALISM", mixed["contradictions"])

    def test_cross_domain_candidates(self):
        candidates = synthesize_candidates(self.evidence, ["CONTROLLED_MAXIMALISM", "PALETTE_COHERENCE", "MUSIC_STRUCTURE_ALIGNMENT"])
        self.assertTrue(any(item["status"] in {"SUPPORTED", "PARTIAL"} for item in candidates))
        self.assertEqual(validate_candidate({k: v for k, v in candidates[0].items() if k in {"schema", "candidate_id", "name", "meaning", "supporting_references", "contradicting_references", "evidence_strength", "confidence", "promotion_status", "promoted"}})["schema"], CANDIDATE_SCHEMA)

    def test_high_impact_always_rejected(self):
        item = synthesize_candidates(self.evidence, ["HIGH_IMPACT_ALWAYS"])[0]
        self.assertEqual(item["status"], "REJECTED_BY_EVIDENCE")
        self.assertFalse(item["promoted"])

    def test_maximalism_not_equal_clutter(self):
        max_item = next(item for item in self.evidence if "CONTROLLED_MAXIMALISM" in item["normalized_traits"] and item["strength"] == "STRONG_POSITIVE")
        self.assertNotEqual(max_item["evidence_id"], "USE006_BILLY")
        self.assertIn("VISUAL_CLUTTER_DISLIKE", next(item for item in self.evidence if item["evidence_id"] == "USE006_BILLY")["contradictions"])

    def test_multicolor_not_automatically_bad(self):
        self.assertNotIn("MULTICOLOR_BAD", {trait for item in self.evidence for trait in item["normalized_traits"]})
        self.assertIn("PALETTE_COHERENCE", next(item for item in self.evidence if item["evidence_id"] == "USE005_KAROLG")["normalized_traits"])

    def test_minimalism_can_be_positive(self):
        drake = next(item for item in self.evidence if item["evidence_id"] == "USE003_DRAKE")
        self.assertIn("INTENTIONAL_RESTRAINT", drake["normalized_traits"])
        self.assertIn("NEGATIVE_SPACE_ACCEPTANCE", drake["normalized_traits"])

    def test_abc_energy_preference(self):
        abc = next(item for item in self.evidence if item["evidence_id"] == "USE007_ABC_ENERGY")
        self.assertIn("MULTI_LEVEL_ENERGY_DESIGN", abc["normalized_traits"])
        self.assertIn("HIGH_IMPACT_ALWAYS", abc["contradictions"])

    def test_music_following_candidates(self):
        music = next(item for item in self.evidence if item["evidence_id"] == "USE008_MUSIC_FOLLOWING")
        self.assertEqual(set(music["normalized_traits"]), {"MUSIC_STRUCTURE_ALIGNMENT", "RHYTHMIC_ACCENT_SYNC", "DYNAMIC_CONTOUR_TRACKING"})

    def test_candidate_never_promoted(self):
        items = synthesize_candidates(self.evidence, ["CONTROLLED_HIGH_IMPACT", "HIGH_IMPACT_ALWAYS"])
        self.assertTrue(all(not item["promoted"] and item["promotion_status"] == "HUMAN_REVIEWED_CANDIDATE" for item in items))

    def test_yg_label_is_not_global_rule(self):
        self.assertEqual(self.evidence[0]["reference_domain"], "KPOP_YG_LEANING")
        self.assertEqual(next(item for item in self.evidence if item["evidence_id"] == "USE002_SUBTRONICS")["scope"], "CROSS_CASE_CANDIDATE")

    def test_industry_alignment_does_not_promote(self):
        candidates = synthesize_candidates(self.evidence, ["CONTROLLED_MAXIMALISM", "INTENTIONAL_RESTRAINT"])
        alignment = compare_with_industry(candidates, self.pack)
        self.assertTrue(all(item["status"] in {"ALIGN", "PARTIAL_ALIGN", "UNKNOWN"} and not item["promoted"] for item in alignment))

    def test_professional_validity_is_independent(self):
        self.assertTrue(any(item["reference_domain"] == "BAND_LIVE" for item in self.evidence))
        self.assertTrue(all(item["provenance"] == "HUMAN_VISUAL_REVIEW" for item in self.evidence))

    def test_command_fields_rejected(self):
        bad = dict(self.evidence[0])
        bad["command"] = "Store Cue"
        with self.assertRaises(ValueError):
            validate_evidence(bad)

    def test_review_schema_and_unset_human_decision(self):
        candidates = synthesize_candidates(self.evidence, ["CLEAN_VISUAL_HIERARCHY", "HIGH_IMPACT_ALWAYS"])
        records = build_review_records(candidates)
        self.assertEqual(records[0]["schema"], REVIEW_SCHEMA)
        self.assertTrue(all(record["decision"] == "UNSET" for record in records))
        self.assertTrue(all(record["ai_recommendation"] != "UNSET" for record in records))
        self.assertTrue(all(validate_review(record)["schema"] == REVIEW_SCHEMA for record in records))

    def test_review_acceptance_is_separate_from_promotion(self):
        candidate = synthesize_candidates(self.evidence, ["CLEAN_VISUAL_HIERARCHY"])[0]
        record = build_review_records([candidate])[0]
        accepted = dict(record, decision="ACCEPT", rationale="Human confirms this bounded preference.", reviewer="ZEN", reviewed_at="2026-09-10")
        normalized = validate_review(accepted)
        self.assertEqual(normalized["decision"], "ACCEPT")
        self.assertNotIn("promoted", normalized)
        self.assertEqual(candidate["promotion_status"], "HUMAN_REVIEWED_CANDIDATE")

    def test_review_rejects_invalid_decision(self):
        candidate = synthesize_candidates(self.evidence, ["CLEAN_VISUAL_HIERARCHY"])[0]
        record = dict(build_review_records([candidate])[0], decision="AUTO_ACCEPT")
        with self.assertRaises(ValueError):
            validate_review(record)

    def test_explicit_human_decisions_match_confirmation(self):
        by_candidate = {item["candidate_id"]: item for item in self.decisions}
        for name in ("CLEAN_VISUAL_HIERARCHY", "PALETTE_COHERENCE", "MUSIC_STRUCTURE_ALIGNMENT", "RHYTHMIC_ACCENT_SYNC", "DYNAMIC_CONTOUR_TRACKING", "MULTI_LEVEL_ENERGY_DESIGN", "INTENTIONAL_RESTRAINT"):
            self.assertEqual(by_candidate[f"candidate_{name}"]["decision"], "ACCEPT")
        self.assertEqual(by_candidate["candidate_CONTROLLED_HIGH_IMPACT"]["decision"], "ACCEPT_WITH_LIMITATION")
        self.assertEqual(by_candidate["candidate_CONTROLLED_MAXIMALISM"]["decision"], "ACCEPT_WITH_LIMITATION")

    def test_explicit_rejected_interpretations_remain_rejected(self):
        by_candidate = {item["candidate_id"]: item for item in self.decisions}
        for name in ("HIGH_IMPACT_ALWAYS", "MAXIMALISM_EQUALS_CLUTTER", "MULTICOLOR_EQUALS_BAD"):
            self.assertEqual(by_candidate[f"candidate_{name}"]["decision"], "REJECT")

    def test_uncovered_candidates_remain_unset(self):
        candidates = synthesize_candidates(self.evidence, ["DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "GEOMETRIC_COMPOSITION"])
        reviews = {item["candidate_id"]: item for item in build_review_records(candidates)}
        self.assertTrue(all(reviews[item["candidate_id"]]["decision"] == "UNSET" for item in candidates))

    def test_second_batch_context_decisions_are_explicit(self):
        by_candidate = {item["candidate_id"]: item for item in self.decisions}
        for name in ("DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "HIGH_SECTION_DELTA", "RESTRAINT_BETWEEN_PEAKS", "CONTROLLED_BUILDUP", "GEOMETRIC_COMPOSITION"):
            self.assertEqual(by_candidate[f"candidate_{name}"]["decision"], "NEEDS_MORE_EVIDENCE")
        self.assertEqual(by_candidate["candidate_PROGRESSIVE_ENERGY_ARC"]["decision"], "ACCEPT")
        self.assertEqual(by_candidate["candidate_EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK"]["decision"], "ACCEPT")

    def test_complete_energy_look_has_high_priority(self):
        item = next(item for item in self.decisions if item["candidate_id"] == "candidate_EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK")
        self.assertEqual(item["priority"], "HIGH")
        self.assertIn("not merely", item["limitations"])


if __name__ == "__main__":
    unittest.main()
