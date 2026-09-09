import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.cue_effect_application import (
    CueEffectApplicationCapability,
    CueEffectApplicationError,
    CueEffectApplicationSkill,
    CueEffectApplicationSpec,
    allocate_sequence,
    ma2_response_has_error,
    resolve_spec,
)
from zen_ma2_agent.builder import ShowPlanBuilder
from zen_ma2_agent.models import Intent
from zen_ma2_agent.skill_system import SkillManifest


def catalog_entry():
    return {
        "effect_id": 3520,
        "label": "ZEN_FX_DIM_CHASE_SLOW_GROUP1",
        "ownership": "ZEN_AGENT",
        "requirement": {"target_type": "group", "target_ref": 1},
    }


def bound_spec():
    return resolve_spec(
        effect={"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}, catalog_entry=catalog_entry(),
        group={"number": 1, "name": "HYBRID"}, membership={"group_no": 1, "fixtures": [101, 102]},
        sequences=[{"number": 201}, {"number": 203}],
    )


class CueEffectApplicationTests(unittest.TestCase):
    def manifest(self):
        return SkillManifest("effects.cue_application_poc", "Cue Effect Application POC", "0.1", "test", ("verify_cue_effect_application",), ("groups", "group_membership", "effects", "sequences"), "MODIFY", "builtin")

    def test_fresh_allocation_skips_existing_sequences(self):
        self.assertEqual(allocate_sequence([{"number": 201}, {"number": 202}, {"number": 204}]), 203)
        with self.assertRaises(CueEffectApplicationError):
            allocate_sequence([{"number": number} for number in range(201, 301)])

    def test_stale_effect_and_missing_target_are_blocked(self):
        with self.assertRaisesRegex(CueEffectApplicationError, "STALE_EFFECT_RESOURCE"):
            resolve_spec(effect=None, catalog_entry=catalog_entry(), group={"number": 1}, membership={"group_no": 1, "fixtures": [101]}, sequences=[])
        with self.assertRaisesRegex(CueEffectApplicationError, "MISSING_TARGET_GROUP"):
            resolve_spec(effect={"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}, catalog_entry=catalog_entry(), group=None, membership={"group_no": 1, "fixtures": [101]}, sequences=[])

    def test_nonempty_membership_and_exact_catalog_label_are_required(self):
        with self.assertRaisesRegex(CueEffectApplicationError, "MISSING_TARGET_GROUP"):
            resolve_spec(effect={"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}, catalog_entry=catalog_entry(), group={"number": 1}, membership={"group_no": 1, "fixtures": []}, sequences=[])
        bad = {**catalog_entry(), "label": "CHANGED"}
        with self.assertRaisesRegex(CueEffectApplicationError, "STALE_EFFECT_RESOURCE"):
            resolve_spec(effect={"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}, catalog_entry=bad, group={"number": 1}, membership={"group_no": 1, "fixtures": [101]}, sequences=[])

    def test_plan_is_typed_allow_list_and_requires_approval(self):
        spec = bound_spec()
        skill = CueEffectApplicationSkill(self.manifest())
        intent = Intent("verify_cue_effect_application", {"cue_effect_spec": spec.summary()}, "test")
        workflow = skill.plan(skill.create_task(intent), None, {})
        skill.validate(workflow, None)
        self.assertEqual(workflow.safety, "MODIFY")
        self.assertEqual(workflow.approval_gates, ("PREVIEW",))
        self.assertEqual(workflow.commands, ("ClearAll", "Group 1", "Effect 3520", 'Store Cue 1 Sequence 202 "FX_CALL_TEST" Fade 0 /nc', 'Label Sequence 202 "ZEN_AI_EFFECT_CALL_TEST_202" /nc', "ClearAll"))
        self.assertFalse(any("At Effect" in command or "raw" in command.lower() for command in workflow.commands))

    def test_error_classifier_blocks_store_boundary(self):
        self.assertTrue(ma2_response_has_error("Error: illegal command"))
        self.assertTrue(ma2_response_has_error("Login incorrect"))
        self.assertFalse(ma2_response_has_error("Executing : Effect 3520"))

    def test_capability_enables_only_after_recorded_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            capability = CueEffectApplicationCapability(Path(directory))
            self.assertIsNone(capability.load_verified())
            recorded = capability.record(bound_spec())
            self.assertEqual(recorded["status"], "REAL_MACHINE_VERIFIED")
            self.assertEqual(capability.load_verified()["grammar"], "EFFECT_POOL_CALL")

    def test_builder_keeps_call_effect_blocked_without_verified_capability(self):
        plan = {"schema": "zen.show_plan.v0.1", "song": "FX", "active_sequence_range": [201, 300], "cues": [{"id": "c1", "cue_number": 1, "label": "FX", "fade": 0, "actions": [{"operation": "CALL_EFFECT", "target": {"type": "group", "ref": 1}, "effect_ref": {"id": 3520}}]}]}
        profile = {"groups": [{"group_id": 1, "name": "HYBRID"}], "presets": [], "effects": [{"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}], "sequences": []}
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertFalse(workflow.executable)
        self.assertEqual(workflow.task.intent.parameters["effect_application"], "EFFECT_APPLICATION_UNVERIFIED")
        self.assertNotIn("Effect 3520", workflow.commands)

    def test_builder_enables_only_explicit_real_machine_capability(self):
        plan = {"schema": "zen.show_plan.v0.1", "song": "FX", "active_sequence_range": [201, 300], "effect_application_capability": {"status": "REAL_MACHINE_VERIFIED", "grammar": "EFFECT_POOL_CALL", "ma2_version_family": "grandMA2_3.9"}, "cues": [{"id": "c1", "cue_number": 1, "label": "FX", "fade": 0, "actions": [{"operation": "CALL_EFFECT", "target": {"type": "group", "ref": 1}, "effect_ref": {"id": 3520}}]}]}
        profile = {"groups": [{"group_id": 1, "name": "HYBRID"}], "presets": [], "effects": [{"effect_id": 3520, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}], "sequences": []}
        workflow = ShowPlanBuilder().build_first_song(plan, profile)
        self.assertTrue(workflow.executable)
        self.assertEqual(workflow.task.intent.parameters["effect_application"], "REAL_MACHINE_VERIFIED")
        self.assertIn("Effect 3520", workflow.commands)


if __name__ == "__main__":
    unittest.main()
