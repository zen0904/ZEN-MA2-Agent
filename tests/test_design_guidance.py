import json
import unittest
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.design_guidance import (
    ADVISORY_SCHEMA,
    GUIDANCE_CONTEXT_SCHEMA,
    build_design_guidance_context,
    generate_shadow_advisories,
    run_shadow_designer,
)
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.song_analysis import SongAnalysisAdapter
from zen_ma2_agent.training_case import build_training_case_001
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent
PROJECT = ROOT.parent


class DesignGuidanceShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = json.loads((PROJECT / "examples" / "REALISTIC_SONG_ANALYSIS.json").read_text(encoding="utf-8"))
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        pack001_raw = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.pack001 = build_pack(pack001_raw["sources"], pack001_raw["observations"])
        cls.pack002 = build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))
        cls.profile = {
            "groups": [{"group_id": 1, "name": "HYBRID", "fixture_ids_in_selection_order": list(range(101, 109))}, {"group_id": 2, "name": "BEAM", "fixture_ids_in_selection_order": list(range(201, 209))}],
            "fixtures": [{"fixture_id": item, "fixture_type": "HYBRID_TYPE"} for item in range(101, 109)] + [{"fixture_id": item, "fixture_type": "BEAM_TYPE"} for item in range(201, 209)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}], "effects": [], "semantic_presets": [],
            "geometry_analysis": {"status": "SUPPORTED"},
        }
        cls.case = build_training_case_001(cls.profile)
        cls.context = build_design_guidance_context(cls.analysis, cls.case, [cls.pack001, cls.pack002], cls.evidence, cls.reviews)

    def test_schema_and_active_human_review_gate(self):
        self.assertEqual(self.context["schema"], GUIDANCE_CONTEXT_SCHEMA)
        active = {item["name"]: item for item in self.context["active_user_style"]}
        self.assertEqual(active["EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK"]["decision"], "ACCEPT")
        self.assertEqual(active["EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK"]["priority"], "HIGH")
        self.assertEqual(active["CONTROLLED_HIGH_IMPACT"]["decision"], "ACCEPT_WITH_LIMITATION")
        self.assertNotIn("DOMINANT_THEME_COLOR", active)

    def test_context_dependent_and_rejected_interpretations_remain_non_rules(self):
        contextual = {item["name"] for item in self.context["context_dependent_user_style"]}
        self.assertTrue({"DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "HIGH_SECTION_DELTA", "RESTRAINT_BETWEEN_PEAKS", "CONTROLLED_BUILDUP", "GEOMETRIC_COMPOSITION"} <= contextual)
        rejected = {item["name"] for item in self.context["rejected_interpretations"]}
        self.assertTrue({"HIGH_IMPACT_ALWAYS", "MAXIMALISM_EQUALS_CLUTTER", "MULTICOLOR_EQUALS_BAD", "MINIMALISM_EQUALS_LOW_PREFERENCE", "KPOP_YG_EQUALS_GLOBAL_STYLE_RULE"} <= rejected)
        self.assertFalse(any(item.get("active_in_shadow_guidance") for item in self.context["context_dependent_user_style"] + self.context["rejected_interpretations"]))

    def test_song_signal_categories_remain_granular(self):
        kinds = {item["kind"] for item in self.context["song_signals"]}
        self.assertTrue({"SECTION_STRUCTURE", "RHYTHMIC_ACCENT", "DYNAMIC_CONTOUR", "BUILDUP_RELEASE", "REPEATED_SECTION_DEVELOPMENT"} <= kinds)
        self.assertNotIn("MUSIC_SYNC", kinds)

    def test_industry_and_user_sources_stay_separate_and_traceable(self):
        self.assertTrue(self.context["industry_evidence"])
        self.assertTrue(all(item["pack_id"].startswith("INDUSTRY_REFERENCE_PACK") for item in self.context["industry_evidence"]))
        self.assertTrue(all("source_id" in item and "limitations" in item for item in self.context["industry_evidence"]))
        self.assertTrue(all(item["evidence_provenance"] == ["HUMAN_VISUAL_REVIEW"] * len(item["evidence_provenance"]) for item in self.context["active_user_style"] if item["evidence_provenance"]))

    def test_advisories_keep_conflict_and_scope_explicit(self):
        advisories = generate_shadow_advisories(self.context)
        self.assertTrue(all(item["schema"] == ADVISORY_SCHEMA for item in advisories))
        complete = next(item for item in advisories if item["advisory_id"] == "advisory-complete-energy-states")
        self.assertIn("USER_STYLE", complete["source_categories"])
        self.assertEqual(complete["confidence"], "HIGH")
        self.assertTrue(any(item["outcome"] == "PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE" for item in generate_shadow_advisories(self.context)[-1]["conflicts"]))
        self.assertIn("not a prescribed energy curve", next(item for item in advisories if item["advisory_id"] == "advisory-whole-song-arc")["unresolved_conditions"][0])

    def test_resource_limitation_is_explicit_not_a_weighted_sum(self):
        limited = json.loads(json.dumps(self.case))
        limited["resource_scale"] = "LIMITED"
        context = build_design_guidance_context(self.analysis, limited, [self.pack002], self.evidence, self.reviews)
        complete = next(item for item in generate_shadow_advisories(context) if item["advisory_id"] == "advisory-complete-energy-states")
        self.assertTrue(any(item["outcome"] == "RESOURCE_LIMITATION" for item in complete["conflicts"]))
        self.assertNotIn("weight", str(complete).lower())

    def test_baseline_and_shadow_use_existing_designer_with_identical_show_plan(self):
        designer_input = SongAnalysisAdapter().to_designer_input(self.analysis)
        baseline = FirstSongDesigner().design(designer_input, self.profile)
        shadow = run_shadow_designer(FirstSongDesigner(), designer_input, self.profile, self.context)
        self.assertEqual(shadow["runtime_mode"], "SHADOW_ONLY")
        self.assertEqual(shadow["designer_runtime_guidance_activation"], "NOT_RUN")
        self.assertEqual(baseline, shadow["actual_show_plan"])
        self.assertTrue(shadow["advisories"])

    def test_unsafe_song_or_guidance_commands_are_rejected(self):
        unsafe = json.loads(json.dumps(self.analysis))
        unsafe["telnet"] = "Store Cue 1"
        with self.assertRaises(ValueError):
            build_design_guidance_context(unsafe, self.case, [], self.evidence, self.reviews)
        unsafe_context = json.loads(json.dumps(self.context))
        unsafe_context["case_context"]["command"] = "Store Cue 1"
        with self.assertRaises(ValueError):
            generate_shadow_advisories(unsafe_context)

    def test_active_human_review_cannot_be_detached_from_original_evidence(self):
        detached = [dict(item) for item in self.reviews]
        index = next(index for index, item in enumerate(detached) if item["candidate_id"] == "candidate_CLEAN_VISUAL_HIERARCHY")
        detached[index]["evidence_ids"] = ["NOT_A_REAL_EVIDENCE_ID"]
        with self.assertRaises(ValueError):
            build_design_guidance_context(self.analysis, self.case, [], self.evidence, detached)


if __name__ == "__main__":
    unittest.main()
