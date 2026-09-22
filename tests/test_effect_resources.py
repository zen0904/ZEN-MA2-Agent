import tempfile
import unittest
import re
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.builder import ShowPlanBuilder
from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent.effect_resources import EffectCatalog, EffectRequirement, EffectRequirementError, EffectResourceResolver, apply_effect_references, show_identity
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


def profile(*, effects=None):
    return {
        "groups": [{"group_id": 1, "name": "HYBRID"}],
        "fixtures": [{"fixture_id": 101, "name": "Hybrid 1", "fixture_type": "Hybrid"}],
        "presets": [{"preset_type": "FOCUS", "reference": "6.2", "name": "normal"}],
        "effects": list(effects or [{"effect_id": 1, "name": "Base"}]),
        "sequences": [],
        "semantic_presets": [],
        "geometry_analysis": {"status": "SUPPORTED"},
    }


def requirement(speed="FAST"):
    return {
        "feature": "DIMMER", "family": "CHASE", "waveform": "PWM", "low": 0, "high": 100,
        "speed_class": speed, "speed_bpm": {"SLOW": 30, "MED": 60, "FAST": 120}[speed],
        "phase": "0..360", "direction": "forward", "groups": 1,
        "target_type": "group", "target_ref": 1, "target_name": "HYBRID",
    }


class EffectResourceClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries, self.commands = [], []
        self.created_names = {}

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Group":
            return 'Group 1 "HYBRID"\n'
        if command == "List Fixture":
            return 'Fixture 101 "Hybrid 1" (Hybrid)\n'
        if command.startswith("List Fixture "):
            return "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if command == "List Preset All":
            return "Focus 6.2 6.2  normal     Normal\n"
        if command == "List Effect":
            return "Effect 1 Base\n" + "".join(f'Effect {number} "{name}"\n' for number, name in sorted(self.created_names.items()))
        if match := re.fullmatch(r"List Effect (\d+)", command):
            number = int(match.group(1))
            return f'Effect {number} "{self.created_names[number]}"\n' if number in self.created_names else "WARNING, NO OBJECTS FOUND FOR LIST\n"
        if match := re.fullmatch(r'Label Effect (\d+) "([^"]+)" /nc', command):
            self.created_names[int(match.group(1))] = match.group(2)
        if command == "List Sequence":
            return "WARNING, NO OBJECTS FOUND FOR LIST\n"
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class EffectResourceResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-effect-resource-")
        self.root = Path(self.temp.name)
        self.catalog = EffectCatalog(self.root)
        self.resolver = EffectResourceResolver(self.catalog)

    def tearDown(self):
        self.temp.cleanup()

    def test_validation_rejects_unverified_families_and_parameter_expansion(self):
        with self.assertRaises(EffectRequirementError):
            EffectRequirement.from_dict({**requirement(), "feature": "PAN"})
        with self.assertRaises(EffectRequirementError):
            EffectRequirement.from_dict({**requirement(), "low": 10})
        with self.assertRaises(EffectRequirementError):
            EffectRequirement.from_dict({**requirement(), "speed_class": "FAST", "speed_bpm": 60})

    def test_verified_agent_owned_catalog_match_requires_current_identity_and_label(self):
        current = profile(effects=[{"effect_id": 2500, "name": "ZEN_FX_DIM_CHASE_FAST_GROUP1"}])
        item = EffectRequirement.from_dict(requirement())
        self.catalog.record(requirement=item, effect_id=2500, label="ZEN_FX_DIM_CHASE_FAST_GROUP1", identity=show_identity(current), verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"})
        found = self.resolver.resolve(item, profile=current)
        self.assertEqual((found.status, found.effect_ref["id"], found.effect_ref["match"]), ("EXISTING_MATCH", 2500, "VERIFIED_AGENT_CATALOG"))
        changed = profile(effects=[{"effect_id": 2500, "name": "RENAMED"}])
        stale = self.resolver.resolve(item, profile=changed)
        self.assertEqual(stale.status, "CREATE_REQUIRED")

    def test_strict_template_reuse_and_name_only_candidate_rejection(self):
        exact = self.resolver.resolve(requirement("MED"), profile=profile(effects=[{"effect_id": 37, "name": "FX_DIM_CHASE_MED", "kind": "TEMPLATE"}]))
        self.assertEqual((exact.status, exact.effect_ref["ownership"], exact.effect_ref["match"]), ("EXISTING_MATCH", "TEMPLATE", "STRICT_SEMANTIC_TEMPLATE"))
        candidate = self.resolver.resolve(requirement(), profile=profile(effects=[{"effect_id": 37, "name": "DIM PWM FAST CHASE"}]))
        self.assertEqual(candidate.status, "CREATE_REQUIRED")
        self.assertEqual(candidate.candidates[0]["id"], 37)
        selective_same_name = self.resolver.resolve(
            requirement("MED"),
            profile=profile(effects=[{"effect_id": 38, "name": "FX_DIM_CHASE_MED", "kind": "SELECTIVE"}]),
        )
        self.assertEqual(selective_same_name.status, "CREATE_REQUIRED")

    def test_create_required_converts_only_to_existing_effect_builder_spec_and_deduplicates_key(self):
        first = self.resolver.resolve(requirement(), profile=profile())
        second = self.resolver.resolve(requirement(), profile=profile())
        self.assertEqual(first.status, "CREATE_REQUIRED")
        self.assertEqual(first.effect_spec.name, "ZEN_FX_DIM_CHASE_FAST_GROUP1")
        self.assertEqual(first.effect_spec.effect_number, 2500)
        self.assertEqual(first.requirement.normalized_key, second.requirement.normalized_key)
        self.assertEqual(first.effect_spec.summary(), second.effect_spec.summary())

    def test_resolved_effect_reference_is_typed_and_schema_rejects_raw_command(self):
        plan = {"schema": "zen.show_plan.v0.1", "cues": [{"id": "cue-1", "cue_number": 1, "fade": 0.5, "actions": [{"operation": "CALL_EFFECT", "target": {"type": "group", "ref": 1}, "effect_requirement_id": "fast"}]}]}
        item = EffectRequirement.from_dict(requirement())
        resolved = self.resolver.resolve(item, profile=profile(effects=[{"effect_id": 2500, "name": "ZEN_FX_DIM_CHASE_FAST_GROUP1"}]))
        # Save evidence first; resolution is deliberately not name-only Agent ownership.
        self.catalog.record(requirement=item, effect_id=2500, label="ZEN_FX_DIM_CHASE_FAST_GROUP1", identity=show_identity(profile(effects=[{"effect_id": 2500, "name": "ZEN_FX_DIM_CHASE_FAST_GROUP1"}])), verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"})
        resolved = self.resolver.resolve(item, profile=profile(effects=[{"effect_id": 2500, "name": "ZEN_FX_DIM_CHASE_FAST_GROUP1"}]))
        output = apply_effect_references(plan, {"fast": resolved})
        self.assertEqual(output["cues"][0]["actions"][0]["effect_ref"]["id"], 2500)
        validate_show_plan(output)
        with self.assertRaises(Exception):
            validate_show_plan({"schema": "zen.show_plan.v0.1", "cues": [{"id": "x", "actions": [{"command": "At Effect 2500"}]}]})

    def test_first_song_effect_references_have_a_clear_cue_grammar_gate(self):
        song = {"song_name": "EFFECT_PLAN", "active_sequence_range": [301, 400], "effect_policy": "DIMMER_CHASE_V1", "sections": [{"name": name, "role": role, "energy": energy} for name, role, energy in (("INTRO", "INTRO", .2), ("VERSE", "VERSE", .4), ("PRE", "PRE_CHORUS", .6), ("CHORUS1", "CHORUS", .9), ("CHORUS2", "CHORUS", .95), ("OUTRO", "OUTRO", .2))]}
        designed = FirstSongDesigner().design(song, profile())
        self.assertIn("fx-dim-chase-med", designed["effect_requirements"])
        self.assertIn("fx-dim-chase-fast", designed["effect_requirements"])
        requirement_fast = EffectRequirement.from_dict(designed["effect_requirements"]["fx-dim-chase-fast"])
        effect_profile = profile(effects=[{"effect_id": 2500, "name": "ZEN_FX_DIM_CHASE_FAST_GROUP1"}, {"effect_id": 2501, "name": "ZEN_FX_DIM_CHASE_MED_GROUP1"}, {"effect_id": 2502, "name": "ZEN_FX_DIM_CHASE_SLOW_GROUP1"}])
        for effect_id, speed in ((2500, "FAST"), (2501, "MED"), (2502, "SLOW")):
            item = EffectRequirement.from_dict(designed["effect_requirements"][f"fx-dim-chase-{speed.lower()}"])
            self.catalog.record(requirement=item, effect_id=effect_id, label=f"ZEN_FX_DIM_CHASE_{speed}_GROUP1", identity=show_identity(effect_profile), verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"})
        resolutions = {key: self.resolver.resolve(value, profile=effect_profile) for key, value in designed["effect_requirements"].items()}
        resolved_plan = apply_effect_references(designed, resolutions)
        workflow = ShowPlanBuilder().build_first_song(resolved_plan, effect_profile)
        self.assertFalse(workflow.executable)
        self.assertEqual(workflow.task.intent.parameters["effect_application"], "EFFECT_APPLICATION_UNVERIFIED")
        self.assertNotIn("Effect 2500", workflow.commands)

    def test_core_uses_two_separate_approvals_for_effect_creation_and_song_build(self):
        copytree(Path(__file__).resolve().parents[1] / "skills", self.root / "skills")
        runtime = AgentRuntime(self.root, client_factory=EffectResourceClient)
        core = AgentCore(runtime)
        core.connect("127.0.0.1", 30000, "MM", "")
        song = {"song_name": "EFFECT_PHASES", "active_sequence_range": [301, 400], "effect_policy": "DIMMER_CHASE_V1", "sections": [{"name": name, "role": role, "energy": energy} for name, role, energy in (("INTRO", "INTRO", .2), ("VERSE", "VERSE", .4), ("PRE", "PRE_CHORUS", .6), ("CHORUS1", "CHORUS", .9), ("CHORUS2", "CHORUS", .95), ("OUTRO", "OUTRO", .2))]}
        phase_a = core.preview_first_song(song)
        self.assertEqual(phase_a["action"]["task"]["skill_id"], "effects.builder")
        self.assertIn("Effect Builder Preview", phase_a["message"])
        created = core.approve_action(phase_a["action"]["id"])
        self.assertEqual(created["status"], "EXECUTED")
        self.assertTrue((self.root / "data" / "ZEN_EFFECT_CATALOG.json").is_file())
        phase_b = core.preview_first_song(song)
        self.assertEqual(phase_b["action"]["task"]["skill_id"], "effects.builder")
        core.approve_action(phase_b["action"]["id"])
        phase_c = core.preview_first_song(song)
        self.assertEqual(phase_c["action"]["task"]["skill_id"], "effects.builder")
        core.approve_action(phase_c["action"]["id"])
        phase_d = core.preview_first_song(song)
        self.assertEqual(phase_d["action"]["status"], "PREVIEW_ONLY")
        self.assertIn("EFFECT_APPLICATION_UNVERIFIED", phase_d["message"])
        self.assertFalse(any(command.startswith("Store Cue") for command in runtime.client.commands))


if __name__ == "__main__":
    unittest.main()
