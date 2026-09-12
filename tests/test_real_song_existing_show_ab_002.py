import json
import unittest
from copy import deepcopy
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.real_song_existing_show_ab_002 import (
    APPROVAL_SOURCE,
    CASE_ID,
    evaluate_real_song_existing_show_ab_002,
)
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent
PROJECT = ROOT.parent


class RealSongExistingShowAB002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = json.loads((ROOT / "fixtures" / "real_song_existing_show_ab_001.json").read_text(encoding="utf-8"))
        cls.approval = json.loads((ROOT / "fixtures" / "real_song_existing_show_ab_002.json").read_text(encoding="utf-8"))
        cls.analysis = json.loads((PROJECT / "examples" / "REALISTIC_SONG_ANALYSIS.json").read_text(encoding="utf-8"))
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        pack_001 = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [
            build_pack(pack_001["sources"], pack_001["observations"]),
            build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8"))),
        ]

    def evaluate(self):
        return evaluate_real_song_existing_show_ab_002(
            self.base, self.approval, self.analysis, industry_packs=self.packs,
            user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner(),
        )

    def test_approval_is_exact_case_scoped_and_reuses_only_scanned_groups(self):
        result = self.evaluate()
        self.assertEqual(result["case_id"], CASE_ID)
        self.assertEqual(result["human_approval"]["approval_scope"], "CASE_SPECIFIC_ELIGIBILITY_ONLY")
        self.assertEqual(result["human_approval"]["approved_density_group_ids"], list(range(1, 8)))
        self.assertEqual(result["existing_show_route"], {"route": "EXISTING_SHOW", "planner_status": "BYPASSED_EXISTING_SHOW"})
        self.assertEqual(result["resource_binding_policy"], "CASE_SPECIFIC_DENSITY_LAYER_ONLY")

    def test_invalid_or_non_case_approval_fails_closed(self):
        invalid = deepcopy(self.approval)
        invalid["approved_density_group_ids"] = [1, 2, 3, 4, 5, 6, 9999]
        with self.assertRaises(ValueError):
            evaluate_real_song_existing_show_ab_002(self.base, invalid, self.analysis, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())
        invalid = deepcopy(self.approval)
        invalid["approval_scope"] = "GLOBAL"
        with self.assertRaises(ValueError):
            evaluate_real_song_existing_show_ab_002(self.base, invalid, self.analysis, industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())

    def test_production_baseline_is_unchanged_and_experimental_plan_is_typed(self):
        result = self.evaluate()
        self.assertTrue(result["production_default_unchanged"])
        self.assertEqual(validate_show_plan(result["baseline_plan"]), result["baseline_plan"])
        self.assertEqual(validate_show_plan(result["experimental_plan"]), result["experimental_plan"])
        self.assertEqual(result["experimental_plan"]["designer"]["mode"], "GUIDANCE_ASSISTED_AB_ONLY")
        self.assertFalse(result["experimental_plan"]["designer"]["production_designer_modified"])

    def test_every_b_cue_has_unambiguous_identity_and_complete_density_accounting(self):
        result = self.evaluate()
        cards = result["cue_cards"]
        self.assertEqual(len(cards), 11)
        for card in cards:
            self.assertTrue(card["cue_id"])
            self.assertTrue(card["section_instance_id"])
            self.assertIsInstance(card["cue_occurrence_index"], int)
            self.assertEqual(set(card["selected_groups"]) | set(card["intentionally_unused_groups"]), set(range(1, 8)))
            self.assertFalse(set(card["selected_groups"]) & set(card["intentionally_unused_groups"]))
            self.assertEqual([item["group_id"] for item in card["dimmer_actions"]], card["selected_groups"])
            self.assertEqual(card["approval_provenance"], APPROVAL_SOURCE)
            self.assertEqual(card["human_review"], "UNSET")

    def test_resource_state_detail_extends_the_canonical_role_state_without_ambiguity(self):
        result = self.evaluate()
        chorus = next(cue for cue in result["experimental_plan"]["cues"] if cue["source_section_id"] == "chorus_1" and cue["cue_occurrence_index"] == 0)
        design = chorus["experimental_design"]
        self.assertEqual(design["role_states"], [{"schema": "zen.role_state.v0.1", "role": "DENSITY_LAYER", "state": "REDUCE"}])
        selection = design["density_resource_selection"]
        resource_states = {item["target"]["ref"]: item["state"] for item in selection["resource_role_states"]}
        self.assertEqual(resource_states, {1: "REDUCE", 2: "REDUCE", 3: "REDUCE", 4: "OMIT", 5: "OMIT", 6: "OMIT", 7: "OMIT"})

    def test_experimental_actions_use_only_approved_density_dimmer_targets(self):
        result = self.evaluate()
        for cue in result["experimental_plan"]["cues"]:
            actions = cue["actions"]
            self.assertTrue(actions)
            self.assertTrue(all(action["operation"] == "SET_DIMMER" for action in actions))
            self.assertTrue(all(action["target"] == {"type": "group", "ref": action["target"]["ref"]} for action in actions))
            self.assertTrue(all(action["target"]["ref"] in range(1, 8) for action in actions))

    def test_density_is_not_a_monotonic_energy_group_count_ladder_and_omissions_exist(self):
        result = self.evaluate()
        bases = [card for card in result["cue_cards"] if card["cue_occurrence_index"] == 0]
        counts = [len(card["selected_groups"]) for card in bases]
        self.assertNotEqual(counts, sorted(counts))
        self.assertTrue(any(card["intentionally_unused_groups"] for card in result["cue_cards"]))
        chorus_1 = next(card for card in bases if card["section_id"] == "chorus_1")
        self.assertEqual(chorus_1["density_strategy"].split("; ")[0], "REDUCE_FOR_KNOWN_HEADROOM")
        self.assertEqual(chorus_1["dimmer_actions"][0]["level"], 38)

    def test_repeated_sections_only_redistribute_when_b3_has_a_recorded_basis(self):
        result = self.evaluate()
        verse_2 = next(card for card in result["cue_cards"] if card["section_id"] == "verse_2")
        self.assertEqual(verse_2["previous_look_comparison"]["status"], "MUSICALLY_JUSTIFIED_DELTA")
        self.assertEqual(verse_2["desired_vs_realized_delta"]["status"], "REALIZED")
        self.assertEqual(verse_2["actual_action_delta"], "CHANGED")
        self.assertEqual(verse_2["actual_plan_delta_vs_baseline"], "CHANGED")
        self.assertIn("REDISTRIBUTE_FOR_JUSTIFIED_REPEAT_DELTA", verse_2["density_strategy"])

    def test_known_quality_limits_are_reported_not_hidden(self):
        result = self.evaluate()
        self.assertEqual(result["recommendation"], "NEEDS_REVISION")
        self.assertIn("FINAL_COHORT_SATURATION_RISK", result["quality_flags"])
        self.assertIn("GROUP_LEVEL_HOMOGENEITY_UNRESOLVED", result["quality_flags"])
        self.assertNotIn("UNAPPROVED_ACTION_TYPE_PRESENT", result["quality_flags"])
        self.assertEqual(result["ma2_write_audit"], "ZERO_WRITES_BY_DESIGN")

    def test_experiment_is_deterministic(self):
        first, second = self.evaluate(), self.evaluate()
        self.assertEqual(first["experimental_plan"], second["experimental_plan"])
        self.assertEqual(first["cue_cards"], second["cue_cards"])


if __name__ == "__main__":
    unittest.main()
