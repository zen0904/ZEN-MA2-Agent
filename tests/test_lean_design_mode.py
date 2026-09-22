import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.artistic_resources import build_artistic_resource_map
from zen_ma2_agent.designer.lean_design_mode import (
    DEFAULT_DELTA_REVISION_CALL_BUDGET,
    DEFAULT_PRIMARY_DESIGN_CALL_BUDGET,
    assemble_compact_design_context,
    build_delta_revision_context,
    load_or_build_compact_context,
    stable_context_hash,
)


class LeanDesignModeTests(unittest.TestCase):
    def setUp(self):
        self.song = {
            "song": "SHEESH",
            "artist": "BABYMONSTER",
            "performance_summary": "front-weighted performance",
            "irrelevant_full_show_dump": {"patch": [1, 2], "sequences": [301]},
        }
        self.spatial = {
            "show_fingerprint": "show-1",
            "stage_frame": "ZEN_STAGE_FRAME_V1",
            "coordinate_system": {"origin": "STAGE_CENTER", "x_positive": "STAGE_LEFT"},
            "spatial_strategy": "hero framing",
            "irrelevant_snapshot": {"fixture_inventory": list(range(1000))},
        }
        self.groups = [
            {"group_id": 2, "name": "RIGHT"},
            {"group_id": 1, "name": "CENTER"},
        ]
        self.presets = [
            {"reference": "6.2", "preset_type": "FOCUS", "name": "Impact"},
            {"reference": "4.1", "preset_type": "COLOR", "name": "Red"},
        ]
        self.effects = [
            {"effect_id": 3600, "name": "FX_HIT"},
            {"effect_id": 3520, "name": "FX_DIM_CHASE"},
        ]
        self.capabilities = [
            {
                "fixture_type_identity": "TYPE_A",
                "show_fingerprint": "show-1",
                "capabilities": ["Dimmer", "ColorRGB"],
                "observed_attributes": ["Dimmer"],
                "confidence": "VERIFIED",
                "source": "CURRENT_SHOW",
            }
        ]
        self.plan = {
            "cues": [
                {"cue_number": 1, "label": "INTRO", "fade": 1, "actions": [{"group": 1, "dimmer": 20}]},
                {"cue_number": 2, "label": "VERSE", "fade": 1, "actions": [{"group": 2, "preset": "4.1"}]},
                {"cue_number": 3, "label": "BUILD", "fade": 1, "actions": [{"group": 1, "dimmer": 30}]},
                {"cue_number": 4, "label": "PRE_DROP", "fade": 1, "actions": [{"group": 2, "preset": "6.2"}, {"group": 2, "effect": 3520}]},
                {"cue_number": 5, "label": "IMPACT", "fade": 1, "actions": [{"group": 1, "dimmer": 40}]},
            ]
        }

    def _build(self, **kwargs):
        values = {
            "song_context": self.song,
            "spatial_context": self.spatial,
            "groups": self.groups,
            "presets": self.presets,
            "effects": self.effects,
            "capability_profiles": self.capabilities,
            "prior_artistic_plan": self.plan,
            "owner_revision_text": "Cue 4 is too full before the drop.",
        }
        values.update(kwargs)
        return assemble_compact_design_context(**values)

    def test_compact_context_is_bounded_and_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first, second)
        self.assertEqual(first["context_hash"], stable_context_hash(first["context"]))
        self.assertEqual([row["group_id"] for row in first["context"]["verified_groups"]], [1, 2])
        self.assertEqual([row["effect_id"] for row in first["context"]["verified_effects"]], [3520, 3600])
        self.assertNotIn("irrelevant_full_show_dump", first["context"]["song"])
        self.assertNotIn("irrelevant_snapshot", first["context"]["spatial"])
        self.assertNotIn("patch", json.dumps(first["context"]))

    def test_context_hash_changes_when_authoritative_input_changes(self):
        changed = dict(self.song, performance_summary="different")
        self.assertNotEqual(self._build()["context_hash"], self._build(song_context=changed)["context_hash"])

    def test_cache_reuses_only_matching_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "context.json"
            first = load_or_build_compact_context(cache_path=path, **{
                "song_context": self.song,
                "spatial_context": self.spatial,
                "groups": self.groups,
                "effects": self.effects,
            })
            second = load_or_build_compact_context(cache_path=path, **{
                "song_context": self.song,
                "spatial_context": self.spatial,
                "groups": self.groups,
                "effects": self.effects,
            })
            changed = load_or_build_compact_context(cache_path=path, **{
                "song_context": dict(self.song, song="OTHER"),
                "spatial_context": self.spatial,
                "groups": self.groups,
                "effects": self.effects,
            })
            self.assertFalse(first["cache_reused"])
            self.assertTrue(second["cache_reused"])
            self.assertFalse(changed["cache_reused"])

    def test_delta_context_selects_affected_cue_neighborhood_and_resources(self):
        delta = build_delta_revision_context(
            accepted_artistic_plan=self.plan,
            owner_revision_text="Cue 4 is too full before the drop.",
            groups=self.groups,
            presets=self.presets,
            effects=self.effects,
            capability_profiles=self.capabilities,
            song_context=self.song,
            spatial_context=self.spatial,
        )
        context = delta["context"]
        self.assertEqual(context["affected_cue_numbers"], [4])
        self.assertEqual(context["cue_neighborhood"], [3, 4, 5])
        self.assertEqual(context["selection_mode"], "DETERMINISTIC_LOCAL")
        self.assertEqual([cue["cue_number"] for cue in context["accepted_artistic_plan"]["cues"]], [3, 4, 5])
        self.assertEqual({row["group_id"] for row in context["relevant_groups"]}, {1, 2})
        self.assertEqual({row["reference"] for row in context["relevant_presets"]}, {"6.2"})
        self.assertEqual({row["effect_id"] for row in context["relevant_effects"]}, {3520})
        self.assertEqual(delta["delta_revision_call_budget"], 1)

    def test_label_can_select_revision_region(self):
        delta = build_delta_revision_context(
            accepted_artistic_plan=self.plan,
            owner_revision_text="PRE_DROP is too busy",
            groups=self.groups,
            presets=self.presets,
            effects=self.effects,
        )
        self.assertEqual(delta["context"]["affected_cue_numbers"], [4])
        self.assertEqual(delta["context"]["cue_neighborhood"], [3, 4, 5])

    def test_unresolved_revision_never_guesses_cue_one(self):
        delta = build_delta_revision_context(
            accepted_artistic_plan=self.plan,
            owner_revision_text="make the transition less generic",
            groups=self.groups,
            presets=self.presets,
            effects=self.effects,
        )
        context = delta["context"]
        self.assertEqual(context["affected_cue_numbers"], [])
        self.assertEqual(context["selection_mode"], "UNRESOLVED_USE_FULL_BOUNDED_PLAN")
        self.assertEqual(context["cue_neighborhood"], [1, 2, 3, 4, 5])
        self.assertEqual([cue["cue_number"] for cue in context["accepted_artistic_plan"]["cues"]], [1, 2, 3, 4, 5])
        self.assertEqual({row["effect_id"] for row in context["relevant_effects"]}, {3520, 3600})

    def test_explicit_affected_cues_override_request_inference(self):
        delta = build_delta_revision_context(
            accepted_artistic_plan=self.plan,
            owner_revision_text="reduce density",
            affected_cue_numbers=[2],
        )
        self.assertEqual(delta["context"]["affected_cue_numbers"], [2])
        self.assertEqual(delta["context"]["cue_neighborhood"], [1, 2, 3])

    def test_budgets_keep_default_path_lean(self):
        context = self._build()
        self.assertLessEqual(context["primary_design_call_budget"], 1)
        self.assertLessEqual(context["delta_revision_call_budget"], 1)
        self.assertFalse(context["multi_agent_default"])
        self.assertEqual(DEFAULT_PRIMARY_DESIGN_CALL_BUDGET, 1)
        self.assertEqual(DEFAULT_DELTA_REVISION_CALL_BUDGET, 1)

    def test_default_programming_runner_does_not_invoke_legacy_role_chain(self):
        runner = Path(__file__).parents[1] / "scripts" / "run_sheesh_programming_test.py"
        source = runner.read_text(encoding="utf-8")
        self.assertNotIn("run_multi_agent_design", source)
        self.assertNotIn("run_spatial_revision_loop", source)


    def test_compact_and_delta_context_can_carry_authoritative_artistic_resource_map(self):
        identity = {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "show-1", "confidence": "PARTIAL"}
        profile = {
            "show_identity": identity,
            "fixtures": [
                {"fixture_id": 101, "fixture_type": "2 TYPE"},
                {"fixture_id": 201, "fixture_type": "2 TYPE"},
            ],
            "groups": [
                {"group_id": 1, "name": "CENTER", "fixture_ids_in_selection_order": [101]},
                {"group_id": 2, "name": "RIGHT", "fixture_ids_in_selection_order": [201]},
            ],
            "presets": [{"reference": "4.1", "preset_type": "COLOR", "name": "Red"}],
            "effects": [],
            "fixture_type_profiles": [],
        }
        resource_map = build_artistic_resource_map(profile)
        full = self._build(artistic_resource_map=resource_map)
        self.assertIn("artistic_resource_map", full["context"])
        self.assertEqual(
            [row["group_id"] for row in full["context"]["artistic_resource_map"]["groups"]],
            [1, 2],
        )

        delta = build_delta_revision_context(
            accepted_artistic_plan=self.plan,
            owner_revision_text="Cue 4 is too full before the drop.",
            groups=self.groups,
            presets=self.presets,
            effects=self.effects,
            artistic_resource_map=resource_map,
        )
        self.assertEqual(
            [row["group_id"] for row in delta["context"]["artistic_resource_map"]["groups"]],
            [1, 2],
        )

    def test_raw_transport_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "forbidden transport"):
            self._build(prior_artistic_plan={"cues": [{"actions": [], "command": "Store Cue 1"}]})
        with self.assertRaisesRegex(ValueError, "forbidden transport"):
            build_delta_revision_context(
                accepted_artistic_plan={"cues": [{"actions": [{"lua": "danger"}]}]},
                owner_revision_text="Cue 1",
            )


if __name__ == "__main__":
    unittest.main()
