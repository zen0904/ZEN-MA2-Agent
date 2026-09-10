import json
import unittest
from copy import deepcopy
from pathlib import Path

from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.guidance_assisted_ab_003_evaluation import (
    QUALITY_CRITERIA,
    cue_design_intent_trace,
    evaluate_ab003_case,
)
from zen_ma2_agent.guidance_assisted_designer import (
    PROHIBITED_FORMULAIC_INTERPRETATIONS,
    REASONING_VERSION_B2,
    REASONING_VERSION_B3,
)
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.rig_intake import route_show_intake, validate_rig_context
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent


class GuidanceAssistedDesignerAB003Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        songs = json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8"))["cases"]
        cls.seed = deepcopy(next(item for item in songs if item["case_id"] == "CASE_D_BUILDUP_DROP"))["analysis"]
        cls.intakes = json.loads((ROOT / "fixtures" / "rig_intake_router_001.json").read_text(encoding="utf-8"))["intakes"]
        cls.evidence = [validate_evidence(item) for item in json.loads((ROOT / "fixtures" / "user_style_evidence_001.json").read_text(encoding="utf-8"))["evidence"]]
        cls.reviews = []
        for filename in ("user_style_review_decisions_001.json", "user_style_review_decisions_002.json"):
            cls.reviews.extend(validate_review(item) for item in json.loads((ROOT / "fixtures" / filename).read_text(encoding="utf-8"))["decisions"])
        pack_001 = json.loads((ROOT / "fixtures" / "industry_reference_pack_001.json").read_text(encoding="utf-8"))
        cls.packs = [build_pack(pack_001["sources"], pack_001["observations"]), build_pack_002(json.loads((ROOT / "fixtures" / "industry_reference_pack_002.json").read_text(encoding="utf-8")))]
        cls.profile = {
            "groups": [{"group_id": 1, "name": "FOCUS"}, {"group_id": 2, "name": "COLOR"}, {"group_id": 3, "name": "TEXTURE"}, {"group_id": 4, "name": "DENSITY"}, {"group_id": 5, "name": "TIMING"}],
            "fixtures": [{"fixture_id": item, "fixture_type": "SYNTHETIC"} for item in range(101, 141)],
            "presets": [{"reference": "6.2", "preset_type": "FOCUS", "name": "normal"}, {"reference": "4.1", "preset_type": "COLOR", "name": "cool palette"}],
            "effects": [], "semantic_presets": [], "geometry_analysis": {"status": "UNINITIALIZED"},
        }

    @staticmethod
    def _section(analysis, section_id):
        return next(item for item in analysis["sections"] if item["id"] == section_id)

    def _rig(self, bindings, *, intake_name="user_confirmed"):
        context = route_show_intake(deepcopy(self.intakes[intake_name]))["rig_context"]
        context["role_bindings"] = [{"role": role, "target": {"type": "group", "ref": ref}, "certainty": "CONFIRMED", "source": "SYNTHETIC_AB003_BINDING"} for role, ref in bindings.items()]
        return validate_rig_context(context)

    def _evaluate(self, analysis, *, led_only=False):
        bindings = {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5} if led_only else {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}
        return evaluate_ab003_case(analysis, profile=self.profile, rig_context=self._rig(bindings, intake_name="led_only" if led_only else "user_confirmed"), industry_packs=self.packs, user_evidence=self.evidence, user_reviews=self.reviews, baseline_designer=FirstSongDesigner())

    @staticmethod
    def _cue(result, section_id):
        return next(item for item in result["b3_plan"]["cues"] if item["source_section_id"] == section_id)

    def test_case_a_repeated_drop_can_develop_from_new_rhythmic_evidence(self):
        analysis = deepcopy(self.seed)
        analysis["events"].append({"time": 150, "type": "ACCENT", "strength": 0.9, "section_id": "drop_2"})
        result = self._evaluate(analysis)
        drop_2 = self._cue(result, "drop_2")["experimental_design"]
        self.assertEqual(drop_2["development"]["status"], "MUSICALLY_JUSTIFIED_DELTA")
        self.assertIn("MORE_EXPLICIT_RHYTHMIC_EVENTS", drop_2["development"]["basis"])

    def test_case_b_matching_repeated_drop_can_choose_intentional_similarity(self):
        analysis = deepcopy(self.seed)
        self._section(analysis, "drop_2").update({"energy": 0.94, "density": 0.9, "accent_level": 1.0})
        result = self._evaluate(analysis)
        drop_2 = self._cue(result, "drop_2")["experimental_design"]
        self.assertEqual(drop_2["development"]["status"], "INTENTIONAL_SIMILARITY")
        self.assertIn("continuity", drop_2["development"]["rationale"].casefold())

    def test_case_c_same_energy_repeat_can_develop_from_available_context_change(self):
        analysis = deepcopy(self.seed)
        self._section(analysis, "drop_2").update({"energy": 0.94, "density": 0.9, "accent_level": 1.0, "notes": ["Sustained textural opening"]})
        result = self._evaluate(analysis)
        drop_2 = self._cue(result, "drop_2")["experimental_design"]
        self.assertEqual(drop_2["development"]["status"], "MUSICALLY_JUSTIFIED_DELTA")
        self.assertIn("SECTION_NOTES_CONTEXT_CHANGED", drop_2["development"]["basis"])
        self.assertIn("MOVER_TEXTURE_LAYER", drop_2["selected_roles"])

    def test_case_d_quiet_section_can_use_texture_without_accent(self):
        analysis = deepcopy(self.seed)
        intro = self._section(analysis, "intro")
        intro.update({"energy": 0.22, "density": 0.15, "accent_level": 0.0, "notes": ["Sustained atmospheric texture"]})
        analysis["events"] = [item for item in analysis["events"] if item["section_id"] != "intro"]
        result = self._evaluate(analysis)
        intro_design = self._cue(result, "intro")["experimental_design"]
        self.assertIn("MOVER_TEXTURE_LAYER", intro_design["selected_roles"])
        self.assertEqual(intro_design["selection_basis"]["known_song_context"]["rhythmic_event_count"], 0)

    def test_case_e_high_energy_can_intentionally_omit_texture(self):
        analysis = deepcopy(self.seed)
        drop = self._section(analysis, "drop_1")
        drop.update({"accent_level": 0.05, "notes": []})
        analysis["events"] = [item for item in analysis["events"] if item["section_id"] != "drop_1"]
        result = self._evaluate(analysis)
        drop_design = self._cue(result, "drop_1")["experimental_design"]
        self.assertNotIn("MOVER_TEXTURE_LAYER", drop_design["selected_roles"])
        self.assertIn("MOVER_TEXTURE_LAYER", drop_design["omitted_roles"])

    def test_case_f_low_energy_rhythm_can_keep_timing(self):
        analysis = deepcopy(self.seed)
        analysis["events"].append({"time": 5, "type": "ACCENT", "strength": 0.8, "section_id": "intro"})
        result = self._evaluate(analysis, led_only=True)
        self.assertIn("TIMING_LAYER", self._cue(result, "intro")["experimental_design"]["selected_roles"])

    def test_case_g_high_sustained_section_can_omit_timing(self):
        analysis = deepcopy(self.seed)
        analysis["events"] = [item for item in analysis["events"] if item["section_id"] != "drop_1"]
        result = self._evaluate(analysis, led_only=True)
        self.assertNotIn("TIMING_LAYER", self._cue(result, "drop_1")["experimental_design"]["selected_roles"])

    def test_case_h_earlier_high_section_can_preserve_headroom_for_later_peak(self):
        analysis = deepcopy(self.seed)
        self._section(analysis, "drop_1").update({"energy": 0.80, "density": 0.85})
        self._section(analysis, "drop_2").update({"energy": 0.98, "density": 0.98})
        result = self._evaluate(analysis)
        drop = self._cue(result, "drop_1")["experimental_design"]
        self.assertTrue(drop["selection_basis"]["headroom_preserved"])
        self.assertIn("DENSITY_LAYER", drop["reduced_roles"])

    def test_b2_b3_trace_is_reviewable_and_production_remains_unchanged(self):
        result = self._evaluate(deepcopy(self.seed))
        self.assertTrue(result["production_default_unchanged"])
        self.assertEqual(result["b2_plan"]["designer"]["reasoning_version"], REASONING_VERSION_B2)
        self.assertEqual(result["b3_plan"]["designer"]["reasoning_version"], REASONING_VERSION_B3)
        trace = cue_design_intent_trace(result["b3_plan"])
        self.assertTrue(trace)
        required = {"SECTION", "KNOWN_SONG_CONTEXT", "PREVIOUS_VISUAL_STATE", "UPCOMING_CONTEXT", "DESIGN_INTENT", "KEEP", "CHANGE", "OMIT", "SUBSTITUTE", "INTENTIONALLY_UNCHANGED", "WHY", "UNKNOWN_UNAVAILABLE_INFORMATION", "TYPED_ACTION_DELTA", "HUMAN_REVIEW"}
        self.assertTrue(all(required <= set(item) and item["HUMAN_REVIEW"] == "UNSET" for item in trace))
        self.assertEqual(set(result["quality"]), set(QUALITY_CRITERIA))

    def test_unknowns_and_formulaic_interpretations_are_explicitly_guarded(self):
        result = self._evaluate(deepcopy(self.seed))
        records = [cue["experimental_design"] for cue in result["b3_plan"]["cues"]]
        self.assertTrue(all("INSTRUMENTATION_CHANGE:NOT_AVAILABLE" in item["design_intent"]["unknown_context"] for item in records))
        self.assertEqual(set(result["b3_plan"]["designer"]["formulaic_interpretations_rejected"]), PROHIBITED_FORMULAIC_INTERPRETATIONS)
        self.assertTrue(all(item["selection_basis"]["energy_is_not_a_layer_count"] for item in records))


if __name__ == "__main__":
    unittest.main()
