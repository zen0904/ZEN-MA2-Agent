import json
import unittest
from pathlib import Path

from zen_ma2_agent.current_show_visual_relationships import (
    VISUAL_RELATIONSHIP_SCHEMA,
    describe_shadow_use,
    human_confirm_group_fields,
    load_visual_relationship_intake,
    validate_visual_relationship_intake,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "current_show_visual_relationships_001.json"


class CurrentShowVisualRelationshipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.intake = load_visual_relationship_intake(FIXTURE)

    def test_exact_existing_show_groups_start_unknown_and_role_free(self):
        self.assertEqual(self.intake["schema"], VISUAL_RELATIONSHIP_SCHEMA)
        self.assertEqual([(item["group_id"], item["group_label"], item["fixture_count"]) for item in self.intake["groups"]], [
            (1, "HYBRID", 8), (2, "SPOT", 8), (3, "BEAM", 8), (4, "WASH", 8),
            (5, "B-EYE", 8), (6, "LED PAR", 8), (7, "STROBE", 8),
        ])
        for group in self.intake["groups"]:
            self.assertEqual(group["physical_presence"]["value"], ["UNKNOWN"])
            self.assertTrue(all(group[field]["confirmation_state"] == "UNKNOWN" for field in (
                "physical_presence", "coverage_scope", "visual_weight_relative", "symmetry", "primary_visual_domain",
            )))
        self.assertEqual(self.intake["relationships"], [])
        self.assertNotIn("9999", json.dumps(self.intake))

    def test_preexisting_geometry_and_semantic_limits_remain_separate(self):
        evidence = {item["evidence_id"]: item for item in self.intake["preexisting_evidence"]}
        self.assertEqual(evidence["CURRENT_SHOW_GEOMETRY"]["state"], "PREEXISTING_EVIDENCE")
        self.assertIn("GEOMETRY_UNINITIALIZED", evidence["CURRENT_SHOW_GEOMETRY"]["limitations"])
        self.assertIn("NONE", evidence["CURRENT_SHOW_SEMANTIC_POSITIONS"]["limitations"])

    def test_human_confirmation_requires_explicit_values_and_preserves_other_unknowns(self):
        confirmed = human_confirm_group_fields(self.intake, group_id=1, fields={"coverage_scope": "BROAD", "symmetry": "MIXED"}, reviewer="ZEN")
        group = confirmed["groups"][0]
        self.assertEqual(group["coverage_scope"]["value"], "BROAD")
        self.assertEqual(group["coverage_scope"]["confirmation_state"], "HUMAN_CONFIRMED")
        self.assertEqual(group["physical_presence"]["value"], ["UNKNOWN"])
        self.assertEqual(group["human_review"], "UNSET")

    def test_relationships_fail_closed_without_human_confirmation(self):
        bad = json.loads(json.dumps(self.raw))
        bad["relationships"] = [{
            "relationship_id": "g1_g2", "from_group_id": 1, "to_group_id": 2,
            "relationship_type": "VISUALLY_OVERLAPS_WITH", "confirmation_state": "UNKNOWN",
            "provenance": "INFERRED_FROM_LABEL",
        }]
        with self.assertRaises(ValueError):
            validate_visual_relationship_intake(bad)

    def test_intake_stays_unwired_even_when_used_for_conceptual_shadow_review(self):
        result = describe_shadow_use(self.intake)
        self.assertEqual(result["mode"], "CONCEPTUAL_ONLY_NOT_WIRED")
        self.assertEqual(result["confirmed_group_ids"], [])
        self.assertIn("change_ab002_actions", result["cannot_do"])


if __name__ == "__main__":
    unittest.main()
