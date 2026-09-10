import json
import unittest
from copy import deepcopy
from pathlib import Path

from zen_ma2_agent.design_guidance import build_design_guidance_context
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.guidance_assisted_designer import (
    GUIDANCE_ASSISTED_MODE,
    PROHIBITED_FORMULAIC_INTERPRETATIONS,
    GuidanceAssistedExperimentalDesigner,
)
from zen_ma2_agent.guidance_ab_human_review import (
    GUIDANCE_AB_HUMAN_REVIEW_SCHEMA,
    validate_guidance_ab_human_review,
)
from zen_ma2_agent.industry_pack_002 import build_pack_002
from zen_ma2_agent.industry_references import build_pack
from zen_ma2_agent.rig_intake import route_show_intake, validate_rig_context
from zen_ma2_agent.song_analysis import SongAnalysisAdapter
from zen_ma2_agent.user_style import validate_evidence, validate_review


ROOT = Path(__file__).parent


class GuidanceAssistedDesignerAB002Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        songs = json.loads((ROOT / "fixtures" / "shadow_advisory_evaluation_001.json").read_text(encoding="utf-8"))["cases"]
        cls.build_drop = deepcopy(next(item for item in songs if item["case_id"] == "CASE_D_BUILDUP_DROP"))
        cls.minimal = deepcopy(next(item for item in songs if item["case_id"] == "CASE_C_RESTRAINED_MINIMAL"))
        intakes = json.loads((ROOT / "fixtures" / "rig_intake_router_001.json").read_text(encoding="utf-8"))["intakes"]
        cls.intakes = intakes
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

    def _rig(self, intake_name, bindings, *, asymmetry=False):
        context = route_show_intake(deepcopy(self.intakes[intake_name]))["rig_context"]
        context["role_bindings"] = [{"role": role, "target": {"type": "group", "ref": ref}, "certainty": "CONFIRMED", "source": "SYNTHETIC_EVALUATION_BINDING"} for role, ref in bindings.items()]
        if asymmetry:
            context["asymmetry"] = {"detected": True, "source": "USER_CONFIRMED"}
        return validate_rig_context(context)

    def _design(self, case, rig):
        analysis = case["analysis"]
        context = build_design_guidance_context(analysis, rig, self.packs, self.evidence, self.reviews)
        song = SongAnalysisAdapter().to_designer_input(analysis)
        baseline = FirstSongDesigner().design(song, self.profile)
        candidate = GuidanceAssistedExperimentalDesigner().design(song, self.profile, context)
        return baseline, candidate

    @staticmethod
    def _cue(candidate, section_id):
        return next(item for item in candidate["cues"] if item["source_section_id"] == section_id)

    def test_human_ab_review_records_are_separate_and_complete(self):
        raw = json.loads((ROOT / "fixtures" / "guidance_ab_human_review_001.json").read_text(encoding="utf-8"))
        records = [validate_guidance_ab_human_review(item) for item in raw["records"]]
        self.assertEqual({item["schema"] for item in records}, {GUIDANCE_AB_HUMAN_REVIEW_SCHEMA})
        self.assertEqual({item["human_decision"] for item in records}, {"DIRECTION_ACCEPTED_WITH_REQUIRED_IMPROVEMENT", "CONTEXT_DEPENDENT", "NEEDS_GUIDANCE_REWORK", "ACCEPT_WITH_CONTEXT_LIMITATION"})
        self.assertTrue(all(item["review_status"] == "RECORDED" for item in records))

    def test_second_drop_develops_only_when_song_evidence_becomes_richer(self):
        case = deepcopy(self.build_drop)
        case["analysis"]["events"].append({"time": 150, "type": "ACCENT", "strength": 0.9, "section_id": "drop_2"})
        _, candidate = self._design(case, self._rig("user_confirmed", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        first, second = self._cue(candidate, "drop_1"), self._cue(candidate, "drop_2")
        self.assertEqual(first["experimental_design"]["development"]["status"], "INTENTIONAL_SIMILARITY")
        self.assertEqual(second["experimental_design"]["development"]["status"], "MUSICALLY_JUSTIFIED_DELTA")
        self.assertIn("MORE_EXPLICIT_RHYTHMIC_EVENTS", second["experimental_design"]["development"]["basis"])
        self.assertNotEqual(first["actions"], second["actions"])

    def test_identical_repeated_section_can_remain_intentionally_similar(self):
        case = deepcopy(self.build_drop)
        second = next(item for item in case["analysis"]["sections"] if item["id"] == "drop_2")
        second.update({"energy": 0.94, "density": 0.9, "accent_level": 1.0})
        _, candidate = self._design(case, self._rig("user_confirmed", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "MOVER_TEXTURE_LAYER": 3, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        first, repeat = self._cue(candidate, "drop_1"), self._cue(candidate, "drop_2")
        self.assertEqual(repeat["experimental_design"]["development"]["status"], "INTENTIONAL_SIMILARITY")
        self.assertEqual(first["experimental_design"]["selected_roles"], repeat["experimental_design"]["selected_roles"])
        self.assertEqual(first["experimental_design"]["role_level_multipliers"], repeat["experimental_design"]["role_level_multipliers"])

    def test_led_low_can_use_timing_and_high_can_omit_it(self):
        case = deepcopy(self.build_drop)
        case["analysis"]["events"] = [{"time": 5, "type": "ACCENT", "strength": 0.8, "section_id": "intro"}]
        _, candidate = self._design(case, self._rig("led_only", {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        low, high = self._cue(candidate, "intro"), self._cue(candidate, "drop_1")
        self.assertIn("TIMING_LAYER", low["experimental_design"]["selected_roles"])
        self.assertNotIn("TIMING_LAYER", high["experimental_design"]["selected_roles"])
        self.assertTrue(low["experimental_design"]["selection_basis"]["energy_is_not_a_layer_count"])

    def test_led_medium_need_not_add_density_when_song_does_not_support_it(self):
        case = deepcopy(self.build_drop)
        build = next(item for item in case["analysis"]["sections"] if item["id"] == "build_1")
        build["density"] = 0.40
        case["analysis"]["events"].append({"time": 30, "type": "ACCENT", "strength": 0.7, "section_id": "build_1"})
        _, candidate = self._design(case, self._rig("led_only", {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        medium = self._cue(candidate, "build_1")["experimental_design"]
        self.assertNotIn("DENSITY_LAYER", medium["selected_roles"])
        self.assertIn("TIMING_LAYER", medium["selected_roles"])

    def test_complete_look_is_independent_of_energy_and_layer_count(self):
        case = deepcopy(self.build_drop)
        case["analysis"]["events"] = [{"time": 5, "type": "ACCENT", "strength": 0.8, "section_id": "intro"}]
        _, candidate = self._design(case, self._rig("led_only", {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        low = self._cue(candidate, "intro")["experimental_design"]
        high = self._cue(candidate, "drop_1")["experimental_design"]
        self.assertNotEqual(low["selected_roles"], high["selected_roles"])
        self.assertNotIn("TIMING_LAYER", high["selected_roles"])
        self.assertTrue(all(item["selection_basis"]["energy_is_not_a_layer_count"] for item in (low, high)))

    def test_restrained_and_asymmetric_treatment_remain_context_dependent(self):
        _, restrained = self._design(self.minimal, self._rig("sparse_floor_only", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        verse = self._cue(restrained, "verse_1")["experimental_design"]
        refrain = self._cue(restrained, "refrain_1")["experimental_design"]
        self.assertNotEqual(verse["selection_basis"]["section_structure"], refrain["selection_basis"]["section_structure"])
        _, asymmetric = self._design(self.build_drop, self._rig("user_confirmed", {"PRIMARY_FOCUS": 1, "COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}, asymmetry=True))
        self.assertTrue(all("MIRROR" not in str(cue.get("experimental_design", {})) for cue in asymmetric["cues"]))

    def test_prohibited_formulaic_interpretations_are_not_emitted_or_activated(self):
        _, candidate = self._design(self.build_drop, self._rig("led_only", {"COLOR_FIELD": 2, "DENSITY_LAYER": 4, "TIMING_LAYER": 5}))
        self.assertEqual(set(candidate["designer"]["formulaic_interpretations_rejected"]), PROHIBITED_FORMULAIC_INTERPRETATIONS)
        self.assertTrue(all(item["experimental_design"]["selection_basis"]["energy_is_not_a_layer_count"] for item in candidate["cues"]))
        self.assertTrue(all(item["experimental_design"]["human_review"] == "UNSET" for item in candidate["cues"]))
        self.assertEqual(candidate["designer"]["mode"], GUIDANCE_ASSISTED_MODE)


if __name__ == "__main__":
    unittest.main()
