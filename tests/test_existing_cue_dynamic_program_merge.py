import copy
import unittest
from pathlib import Path

from zen_ma2_agent.existing_cue_dynamic_program_merge import (
    ExistingCueDynamicProgramMergeError,
    build_existing_cue_dynamic_program_preview,
    commands_from_preview,
    verify_existing_cue_dynamic_program_merge,
)
from zen_ma2_agent.skill_system import SkillRegistry


REFS = [f"{fixture}.1" for fixture in range(101, 109)]
EFFECTS = {
    "DIMMER_CHASE_SLOW": 2500,
    "DIMMER_CHASE_MED": 2501,
    "DIMMER_CHASE_FAST": 2502,
    "ALTERNATE": 2501,
    "PULSE": 2502,
    "HIT": 2502,
    "BUILD": 2500,
}
INTENTS = [
    "STATIC_LOOK", "DIMMER_CHASE_SLOW", "DIMMER_CHASE_MED",
    "DIMMER_CHASE_FAST", "ALTERNATE", "PULSE", "HIT", "BUILD",
    "RELEASE", "BLACKOUT", "RESET",
]
PATTERNS = [
    "CENTER", "LEFT", "RIGHT", "FRONT", "UPSTAGE", "NARROW_FAN",
    "WIDE_FAN", "CROSS", "ALTERNATE", "EXPLODE", "COLLAPSE",
]


def profile(refs=REFS):
    return {
        "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "1" * 64},
        "fixtures": [
            {
                "fixture_id": int(ref.split(".")[0]),
                "fixture_type": "HYBRID_MOVING",
                "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]},
            }
            for ref in refs
            if ref.split(".")[0] != "9999"
        ],
        "fixture_type_profiles": [{
            "status": "SHOW_BOUND_VERIFIED",
            "fixture_type": {"list_label": "HYBRID_MOVING"},
            "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}},
            "channels": [
                {"attribute": "PAN", "functions": [{"from": "-315", "to": "315"}]},
                {"attribute": "TILT", "functions": [{"from": "-135", "to": "135"}]},
            ],
        }],
        "groups": [{
            "group_id": 1,
            "name": "HYBRID",
            "fixture_refs_in_selection_order": list(refs),
            "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"},
        }],
        "sequences": [{"number": 302, "name": "ZEN_SEQ302"}],
        "effects": [
            {"effect_id": 2500, "name": "FX_DIM_CHASE_SLOW", "kind": "TEMPLATE"},
            {"effect_id": 2501, "name": "FX_DIM_CHASE_MED", "kind": "TEMPLATE"},
            {"effect_id": 2502, "name": "FX_DIM_CHASE_FAST", "kind": "TEMPLATE"},
        ],
    }


def row(fixture, attribute, value, *, effect=None, preset=None):
    result = {
        "channel": {
            "fixture_id": str(fixture),
            "subfixture_id": "1",
            "attribute_name": attribute,
        },
        "raw_values": {"Value": str(value)},
        "preset": None,
        "effect": None,
    }
    if effect is not None:
        result["effect"] = {"no_components": ["1", str(effect)]}
    if preset is not None:
        result["preset"] = {"no_components": ["1", "2", str(preset)]}
    return result


def cue(number, label, rows):
    return {
        "number": {"number": str(number), "sub_number": "0"},
        "parts": [{"index": "0", "name": label, "cue_data": rows}],
    }


def target_discovery():
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": 302,
        "xml_discovery": {"sha256": "c" * 64},
        "cues": [
            cue(number, f"SHEESH_{number:02d}", [
                *[row(fixture, "DIM", 100) for fixture in range(101, 109)],
                *[row(fixture, "COLORRGB1", 50, preset=101) for fixture in range(101, 109)],
            ])
            for number in range(1, 30)
        ],
    }


def calibration_discovery():
    raw = [row(fixture, attr, value) for fixture in range(101, 109) for attr, value in (("PAN", 20), ("TILT", 30))]
    linked = [row(fixture, attr, 1, preset=13) for fixture in range(101, 109) for attr in ("PAN", "TILT")]
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": 12,
        "xml_discovery": {"sha256": "b" * 64},
        "cues": [cue(1, "RAW_POSITION", raw), cue(2, "PRESET_POSITION", linked)],
    }


def position_binding(refs=REFS):
    return {
        "status": "REAL_MACHINE_CONTENT_VERIFIED",
        "show_identity": profile(refs)["show_identity"],
        "group_id": 1,
        "fixture_refs": sorted(refs),
        "reference": "2.13",
        "preset_label": "ZEN_POSITION_CAL_P13",
        "evidence": {"sequence": 12, "cue": 2, "sequence_export_sha256": "a" * 64},
    }


def effect_capability():
    return {
        "schema": "zen.cue_effect_application.v0.2",
        "status": "REAL_MACHINE_CONTENT_VERIFIED",
        "grammar": "AT_EFFECT_POOL_CALL",
        "ma2_version_family": "grandMA2_3.9",
        "verification": {
            "application": "REAL_MACHINE_CONTENT_VERIFIED",
            "cue_content_readback": "VERIFIED",
        },
    }


def effect_resources(*, fresh=True):
    return [
        {
            "effect_id": effect_id,
            "label": label,
            "group_id": 1,
            "ownership": "ZEN_AGENT",
            "show_identity": profile()["show_identity"],
            "fresh": fresh,
            "list_effect_sha256": str(effect_id)[0] * 64,
            "catalog_sha256": str(effect_id)[-1] * 64,
        }
        for effect_id, label in (
            (2500, "FX_DIM_CHASE_SLOW"),
            (2501, "FX_DIM_CHASE_MED"),
            (2502, "FX_DIM_CHASE_FAST"),
        )
    ]


def artistic_plan():
    result = []
    for number in range(1, 30):
        intent = INTENTS[(number - 1) % len(INTENTS)]
        result.append({
            "cue_number": number,
            "cue_label": f"SHEESH_{number:02d}",
            "effect_intent": intent,
            "effect_id": EFFECTS.get(intent),
            "position_pattern": PATTERNS[(number - 1) % len(PATTERNS)],
        })
    return result


def metadata():
    return [
        {"number": number, "name": f"SHEESH_{number:02d}", "fade": 0.5, "delay": 0.0}
        for number in range(1, 30)
    ]


def stage_evidence():
    return {
        "capture_readable": True,
        "stage_view_visible": True,
        "capture_sha256": "d" * 64,
        "operator_assessment": "PRIOR_VARIATION_TOO_SMALL",
        "recommended_scale": 1.5,
    }


def build(**overrides):
    profile_value = overrides.pop("profile", profile())
    args = {
        "target_discovery": target_discovery(),
        "calibration_discovery": calibration_discovery(),
        "position_binding": position_binding(),
        "effect_application_capability": effect_capability(),
        "effect_resources": effect_resources(),
        "artistic_cue_plan": artistic_plan(),
        "stage_view_evidence": stage_evidence(),
        "sequence_no": 302,
        "group_id": 1,
        "cue_start": 1,
        "cue_end": 29,
        "executor_assignments": [{"page": 2, "executor": 8, "location": "2.8", "label": "ZEN_SEQ302"}],
        "cue_metadata": metadata(),
    }
    args.update(overrides)
    return build_existing_cue_dynamic_program_preview(profile_value, **args)


def post_discovery(preview):
    result = target_discovery()
    by_number = {cue_row["number"]["number"]: cue_row for cue_row in result["cues"]}
    for update in preview["cue_updates"]:
        rows = by_number[str(update["cue_number"])]["parts"][0]["cue_data"]
        if update.get("effect_id") is not None:
            for fixture in range(101, 109):
                dim = next(item for item in rows if item["channel"]["fixture_id"] == str(fixture) and item["channel"]["attribute_name"] == "DIM")
                dim["effect"] = {"no_components": ["1", str(update["effect_id"])]}
        for fixture in update["fixtures"]:
            root = fixture["fixture_ref"].split(".")[0]
            rows.extend((row(root, "PAN", fixture["pan"]), row(root, "TILT", fixture["tilt"])))
    result["xml_discovery"]["sha256"] = "e" * 64
    return result


class ExistingCueDynamicProgramMergeTests(unittest.TestCase):
    def test_builtin_skill_is_discoverable(self):
        registry = SkillRegistry(Path(__file__).resolve().parents[1])
        registry.discover()
        manifest = registry.get("existing_cue.dynamic_program_merge")
        self.assertIn("merge_existing_cue_dynamic_program", manifest.intents)

    def test_existing_seq302_path_never_allocates_new_sequence(self):
        preview = build()
        commands = commands_from_preview(preview)
        joined = "\n".join(commands)
        self.assertIn("Store Cue 29 Sequence 302 /merge /cueonly /nc", joined)
        self.assertNotIn("Sequence 303", joined)
        self.assertNotIn("Label Sequence", joined)
        self.assertNotIn("Assign Executor", joined)
        self.assertFalse(preview["write_scope"]["allocate_sequence"])

    def test_effect_is_attached_to_requested_existing_cue(self):
        preview = build()
        commands = commands_from_preview(preview)
        index = commands.index("At Effect 2500")
        self.assertEqual(commands[index - 1], "Group 1")
        self.assertEqual(commands[index + 1], "Store Cue 2 Sequence 302 /merge /cueonly /nc")

    def test_different_cues_use_different_effects(self):
        preview = build()
        chosen = {cue["effect_id"] for cue in preview["cue_updates"] if cue["effect_id"] is not None}
        self.assertEqual(chosen, {2500, 2501, 2502})

    def test_position_and_effect_coexist_in_same_cue_workflow(self):
        preview = build()
        cue2 = preview["cue_updates"][1]
        self.assertEqual(cue2["effect_id"], 2500)
        self.assertEqual(cue2["position_pattern"], "LEFT")
        self.assertGreater(max(abs(item["delta_pan"]) for item in cue2["fixtures"]), 5)
        commands = commands_from_preview(preview)
        self.assertIn('Attribute "Pan" At 29', commands)

    def test_unknown_unplanned_attribute_drift_fails_closed(self):
        preview = build()
        post = post_discovery(preview)
        post["cues"][0]["parts"][0]["cue_data"].append(row(101, "GOBO1", 7))
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, profile(), post)

    def test_unrelated_existing_effect_requires_explicit_replacement_plan(self):
        target = target_discovery()
        target["cues"][1]["parts"][0]["cue_data"][0]["effect"] = {
            "no_components": ["1", "2499"]
        }
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "UNRELATED_EFFECT_CONFLICT"):
            build(target_discovery=target)
        plan = artistic_plan()
        plan[1]["replace_effect_ids"] = [2499]
        preview = build(target_discovery=target, artistic_cue_plan=plan)
        self.assertEqual(preview["cue_updates"][1]["replace_effect_ids"], [2499])

    def test_fixture9999_is_rejected(self):
        changed = profile(["9999.1", *REFS[1:]])
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "FIXTURE_9999"):
            build(profile=changed, position_binding=position_binding(["9999.1", *REFS[1:]]))

    def test_stale_sequence_effect_or_group_evidence_blocks(self):
        changed = target_discovery()
        changed["status"] = "STALE"
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EXPORT_NOT_FRESH"):
            build(target_discovery=changed)
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EFFECT_EVIDENCE_STALE"):
            build(effect_resources=effect_resources(fresh=False))
        changed_profile = profile()
        changed_profile["groups"][0]["membership"]["status"] = "STALE"
        with self.assertRaises(Exception):
            build(profile=changed_profile)

    def test_effect_creation_without_cue_application_is_noncompliant(self):
        preview = build()
        preview["cue_updates"] = []
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "CUE_APPLICATIONS_MISSING"):
            commands_from_preview(preview)

    def test_position_requested_without_position_is_noncompliant(self):
        preview = build()
        preview["cue_updates"][0]["fixtures"] = []
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "POSITION_APPLICATION_MISSING"):
            commands_from_preview(preview)

    def test_native_postwrite_verification_separates_intended_and_protected(self):
        preview = build()
        result = verify_existing_cue_dynamic_program_merge(preview, profile(), post_discovery(preview))
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["cue_count"], 29)
        self.assertEqual(result["position_value_matches"], 29 * 8 * 2)
        self.assertGreater(result["effect_fixture_matches"], 0)
        self.assertEqual(result["protected_content"], "UNCHANGED")

    def test_operator_stage_evidence_scales_but_fixture_limits_still_bound(self):
        preview = build()
        self.assertEqual(preview["position_amplitude"]["scale"], 1.5)
        wide = next(item for item in preview["cue_updates"] if item["position_pattern"] == "WIDE_FAN")
        self.assertAlmostEqual(max(abs(row["delta_pan"]) for row in wide["fixtures"]), 18.0)
        bad = stage_evidence()
        bad["recommended_scale"] = 3.0
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "SCALE_INVALID"):
            build(stage_view_evidence=bad)


if __name__ == "__main__":
    unittest.main()
