import copy
import json
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.existing_cue_dynamic_program_merge import (
    ExistingCueDynamicProgramMergeError,
    build_existing_cue_dynamic_program_preview,
    commands_from_dynamic_preview,
    effect_ids_by_cue_ref,
    protected_content_snapshot,
    verify_existing_cue_dynamic_program_merge,
)
from tests.test_position_existing_cue_merge import (
    LABELS,
    build as build_position,
    cue,
    cue_metadata,
    row,
    target_discovery,
    profile,
)


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


def effects():
    return {1: {
        2500: {"label": "ZEN_FX_DIM_CHASE_SLOW_GROUP1", "kind": "DIMMER_CHASE"},
        2501: {"label": "ZEN_FX_DIM_CHASE_MED_GROUP1", "kind": "DIMMER_CHASE"},
        2502: {"label": "ZEN_FX_DIM_CHASE_FAST_GROUP1", "kind": "DIMMER_CHASE"},
    }}


def capabilities():
    return {1: ["DIMMER", "COLOR", "POSITION", "GOBO", "PRISM", "EFFECT"]}


def presets():
    return {1: {
        "4.101": {
            "name": "ZEN_COLOR_RED",
            "dimension": "COLOR",
            "preset_type": "COLOR",
            "attribute_names": ["COLORRGB1"],
        },
        "3.201": {
            "name": "ZEN_GOBO_BREAKUP",
            "dimension": "GOBO",
            "preset_type": "GOBO",
            "attribute_names": ["GOBO1"],
        },
    }}


def artistic_plan():
    patterns = ["EXPLODE", "CROSS", "UPSTAGE", "WIDE_FAN"]
    effect_ids = [2500, None, 2501, 2502]
    cues = []
    for number, (label, pattern, effect_id) in enumerate(zip(LABELS, patterns, effect_ids), 1):
        actions = [] if effect_id is None else [{
            "operation": "CALL_EFFECT",
            "target": {"type": "group", "ref": 1},
            "effect_ref": {"id": effect_id},
        }]
        cues.append({
            "id": f"cue_{number:03d}",
            "cue_number": number,
            "label": label,
            "fade": 0.5,
            "position_pattern": pattern,
            "position_scale": 1.5 if number in {1, 4} else 1.0,
            "capability_intent": [{
                "group": 1,
                "dimension": "PRISM",
                "use": "OPTIONAL" if number == 1 else "AVOID",
                "reason": "impact option" if number == 1 else "keep beam clean",
                "technical_status": "SHOW_BOUND_VERIFIED",
                "execution_status": "NO_VERIFIED_RESOURCE",
                "execution_authorized": False,
            }],
            "actions": actions,
        })
    return {"schema": "zen.show_plan.v0.1", "cues": cues}


def effect_row(fixture, effect_id):
    return {
        "multipart_indexes": {"value": "0", "effect": "0"},
        "channel": {
            "fixture_id": str(fixture),
            "subfixture_id": "1",
            "attribute_name": "DIM",
        },
        "raw_values": {
            "EffectRate": "1",
            "EffectLow": "0",
            "EffectHigh": "100",
        },
        "preset": None,
        "effect": {"no_components": ["1", str(effect_id)]},
    }


def preset_row(fixture, attribute, reference):
    pool, number = reference.split(".")
    return {
        "multipart_indexes": {"value": "0", "preset": "0"},
        "channel": {
            "fixture_id": str(fixture),
            "subfixture_id": "1",
            "attribute_name": attribute,
        },
        "raw_values": {},
        "preset": {"no_components": ["1", pool, number]},
        "effect": None,
    }


def build_dynamic(*, pre=None, plan=None, pos=None, verified_effects=None, verified_presets=None, verified_capabilities=None, capability=None):
    pre = pre or target_discovery()
    pos = pos or build_position(target=pre)
    return build_existing_cue_dynamic_program_preview(
        position_preview=pos,
        pre_discovery=pre,
        artistic_plan=plan or artistic_plan(),
        verified_effects_by_group=effects() if verified_effects is None else verified_effects,
        effect_application_capability=effect_capability() if capability is None else capability,
        verified_presets_by_group={} if verified_presets is None else verified_presets,
        verified_capabilities_by_group=(
            capabilities() if verified_capabilities is None else verified_capabilities
        ),
    )


def post_from(pre, preview):
    post = copy.deepcopy(pre)
    post["xml_discovery"] = {"sha256": "d" * 64}
    cues = {
        int(item["number"]["number"]): item
        for item in post["cues"]
    }
    positioned = {
        int(item["cue_number"]): item
        for item in preview["position_preview"]["cue_updates"]
    }
    for number, update in positioned.items():
        rows = cues[number]["parts"][0]["cue_data"]
        for fixture in update["fixtures"]:
            root, _, sub = str(fixture["fixture_ref"]).partition(".")
            rows.extend([
                row(root, "PAN", fixture["pan"], subfixture=sub or None),
                row(root, "TILT", fixture["tilt"], subfixture=sub or None),
            ])
        effect = preview["cue_effects"][str(number)]
        replacements = set(
            next(item for item in preview["cue_updates"] if item["cue_number"] == number).get("replace_effect_ids") or []
        )
        if effect is not None and replacements:
            kept = []
            for existing in rows:
                raw_effect = existing.get("effect") if isinstance(existing, dict) else None
                parts = raw_effect.get("no_components") if isinstance(raw_effect, dict) else None
                effect_id = int(parts[-1]) if isinstance(parts, list) and parts and str(parts[-1]).isdigit() else None
                channel = existing.get("channel") if isinstance(existing, dict) else None
                fixture = str(channel.get("fixture_id")) if isinstance(channel, dict) else ""
                if effect_id in replacements and fixture in {"101", "102"}:
                    continue
                kept.append(existing)
            rows[:] = kept
        if effect is not None:
            rows.extend([effect_row(101, effect["id"]), effect_row(102, effect["id"])])
        for preset in preview["cue_presets"][str(number)]:
            for fixture in (101, 102):
                for attribute in preset["attribute_names"]:
                    rows.append(preset_row(fixture, attribute, preset["reference"]))
    return post


class ReadyClient:
    state = ConnectionState.READY
    authenticated_user = "MM"
    audit_entries = []

    def execute(self, command):
        raise AssertionError(f"unexpected direct transport: {command}")


class ExistingCueDynamicProgramMergeCoreTests(unittest.TestCase):
    request = (
        "Dynamic existing Sequence 302 Position Effect Group 1 Preset 2.13 "
        "Cues 1-4 Executor 2.8"
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-existing-dynamic-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.core = AgentCore(AgentRuntime(root))
        self.core.runtime.client = ReadyClient()
        for resource in (
            "groups", "group_membership", "fixtures", "fixture_geometry",
            "fixture_type_profiles", "presets", "effects", "sequences", "executors",
        ):
            self.core.state.put(resource, [], source="test")
        self.preview = build_dynamic()

    def tearDown(self):
        self.temp.cleanup()

    def child(self):
        return self.core.skills.plan_intent(
            Intent(
                "merge_existing_cue_dynamic_program",
                {"dynamic_merge_preview": self.preview},
                self.request,
            ),
            self.core.state,
            self.core.runtime.preferences,
        )

    def test_root_routes_dynamic_existing_merge_before_generic_builder(self):
        with patch.object(
            self.core, "_plan_existing_dynamic_merge_child", return_value=self.child(),
        ), patch.object(
            self.core, "_plan_lean_design_child",
            side_effect=AssertionError("generic provider path must not run"),
        ):
            action = self.core.program_show_request(self.request)["action"]
        self.assertEqual(action["task"]["skill_id"], "show.program")
        self.assertEqual(
            action["skill_graph"][-1]["skill_id"],
            "existing_cue.dynamic_program_merge",
        )
        child = action["continuation_context"]["child_execution"]
        self.assertEqual(child["intent_kind"], "merge_existing_cue_dynamic_program")
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertIn("Position=EXPLODE", action["preview_note"] )
        self.assertIn("Effect=2500", action["preview_note"] )
        self.assertNotIn("Sequence 303", action["preview_note"] )

    def test_core_filters_dynamic_presets_without_exact_attribute_evidence(self):
        resource_map = {"groups": [{
            "group_id": 1,
            "preset_resources": [
                {"reference": "4.101", "name": "RED", "dimension": "COLOR", "attribute_names": ["COLORRGB1"]},
                {"reference": "3.201", "name": "GOBO", "dimension": "GOBO", "attribute_names": []},
                {"reference": "5.301", "name": "PRISM", "dimension": "PRISM", "attribute_names": ["PRISM1"]},
            ],
        }]}
        result = AgentCore._verified_dynamic_presets(resource_map, 1)
        self.assertEqual(set(result), {"4.101"})


class ExistingCueDynamicIdentityNormalizationTests(unittest.TestCase):
    def test_show_identity_is_compared_after_artistic_evidence_normalization(self):
        core = object.__new__(AgentCore)
        raw_profile = {"show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "before"}}
        position_profile = {"show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "after"}}

        def normalize(profile):
            profile["show_identity"] = dict(position_profile["show_identity"])
            return {"groups": []}, {"status": "REAL_MACHINE_CONTENT_VERIFIED"}

        with patch.object(core, "_build_current_artistic_resource_map", side_effect=normalize) as builder:
            resource_map, capability = core._normalize_dynamic_artistic_profile(
                raw_profile, position_profile
            )
        builder.assert_called_once_with(raw_profile)
        self.assertEqual(resource_map, {"groups": []})
        self.assertEqual(capability["status"], "REAL_MACHINE_CONTENT_VERIFIED")

    def test_real_identity_drift_still_fails_after_normalization(self):
        core = object.__new__(AgentCore)
        profile = {"show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "one"}}
        position = {"show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "two"}}
        with patch.object(
            core, "_build_current_artistic_resource_map",
            return_value=({"groups": []}, {"status": "REAL_MACHINE_CONTENT_VERIFIED"}),
        ):
            with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "SHOW_IDENTITY_DRIFT"):
                core._normalize_dynamic_artistic_profile(profile, position)


class ExistingCueDynamicProgramMergeRoutingTests(unittest.TestCase):
    def test_ascii_existing_dynamic_request_is_parsed_before_generic_design(self):
        parsed = AgentCore._parse_existing_dynamic_merge_request(
            "Dynamic existing Sequence 302 Position Effect Group 1 Preset 2.13 Cues 1-29 Executor 2.8"
        )
        self.assertEqual(parsed, {
            "sequence_no": 302, "group_id": 1, "preset_ref": "2.13",
            "cue_start": 1, "cue_end": 29, "expected_executor": "2.8",
        })
        self.assertIsNone(AgentCore._parse_existing_position_merge_request(
            "Dynamic existing Sequence 302 Position Effect Group 1 Preset 2.13 Cues 1-29 Executor 2.8"
        ))

    def test_dynamic_parser_requires_explicit_existing_target_and_effect_semantics(self):
        self.assertIsNone(AgentCore._parse_existing_dynamic_merge_request(
            "Program Sequence 302 Position Group 1 Preset 2.13 Cues 1-29"
        ))
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "REQUIRES_EXISTING_SEQUENCE"):
            AgentCore._parse_existing_dynamic_merge_request(
                "Dynamic existing Sequence 302 Position Effect"
            )


class ExistingCueDynamicSpatialContextTests(unittest.TestCase):
    def test_fresh_spatial_context_is_target_group_bounded_and_preserves_limitations(self):
        current_profile = profile()
        preview = build_position(profile=current_profile)
        spatial = AgentCore._current_dynamic_spatial_context(current_profile, preview)
        self.assertEqual(spatial["show_fingerprint"], "1" * 64)
        self.assertEqual(
            spatial["spatial_bootstrap_mode"],
            "CURRENT_SHOW_STRUCTURED_POSITION_EVIDENCE",
        )
        self.assertEqual(
            spatial["coordinate_system"]["pan_negative"], "STAGE_RIGHT"
        )
        self.assertFalse(spatial["coordinate_system"]["xyz_sign_mapping_claimed"])
        self.assertFalse(
            spatial["position_summary"]["pattern_semantics"]["physical_targeting_claimed"]
        )
        self.assertEqual(
            {str(row["fixture_id"]) for row in spatial["geometry_summary"]},
            {"101", "102"},
        )
        self.assertEqual(
            spatial["stage_frame"]["stage_view_pixels_authority"],
            "SUPPLEMENTAL_ONLY_NOT_STRUCTURED_GEOMETRY_AUTHORITY",
        )
        payload = json.dumps(spatial, sort_keys=True)
        self.assertNotIn("9999", payload)
        self.assertNotIn("physical_targeting_claimed\": true", payload.lower())

    def test_spatial_context_rejects_protected_fixture_9999(self):
        current_profile = profile()
        current_profile["fixtures"].append({
            "fixture_id": 9999,
            "fixture_type": "PROTECTED",
            "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]},
        })
        preview = build_position(profile=current_profile)
        preview["group"]["exact_refs"].append("9999.1")
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_FIXTURE_9999"):
            AgentCore._current_dynamic_spatial_context(current_profile, preview)


class ExistingCueDynamicProgramMergeTests(unittest.TestCase):
    def test_preview_targets_existing_sequence_and_combines_position_effects(self):
        preview = build_dynamic()
        self.assertEqual(preview["target_sequence"]["id"], 302)
        self.assertEqual(preview["cue_updates"][0]["position_pattern"], "EXPLODE")
        self.assertEqual(preview["cue_updates"][0]["position_scale"], 1.5)
        self.assertEqual(preview["cue_updates"][0]["effect"]["id"], 2500)
        self.assertIsNone(preview["cue_updates"][1]["effect"])
        self.assertFalse(preview["cue_updates"][0]["capability_intent"][0]["execution_authorized"])
        self.assertIn("PRISM", preview["cue_updates"][0]["optional_capabilities"])
        self.assertIn("COLOR", preview["cue_updates"][0]["intentionally_unused_capabilities"])
        self.assertGreater(preview["cue_updates"][0]["expected_pan_range"][1] - preview["cue_updates"][0]["expected_pan_range"][0], 20)
        self.assertEqual(preview["ma2_writes"], 0)

    def test_unavailable_requested_capability_remains_visible_without_compiling(self):
        plan = artistic_plan()
        plan["cues"][0]["capability_intent"].append({
            "group": 1,
            "dimension": "IRIS",
            "use": "USE",
            "reason": "requested artistic option but no verified implementation",
            "technical_status": "NOT_PRESENT_IN_GROUP_FIXTURE_TYPES",
            "execution_status": "NO_VERIFIED_RESOURCE",
            "execution_authorized": False,
        })
        preview = build_dynamic(plan=plan, verified_capabilities={1: ["POSITION", "PRISM", "COLOR"]})
        cue = preview["cue_updates"][0]
        self.assertIn("IRIS", cue["requested_but_unexecutable_capabilities"])
        self.assertNotIn("IRIS", cue["used_capability_families"])
        self.assertNotIn("Iris", "\n".join(commands_from_dynamic_preview(preview)))

    def test_executable_requested_capability_without_action_fails_closed(self):
        plan = artistic_plan()
        plan["cues"][0]["capability_intent"].append({
            "group": 1,
            "dimension": "GOBO",
            "use": "USE",
            "reason": "must be implemented",
            "technical_status": "SHOW_BOUND_VERIFIED",
            "execution_status": "VERIFIED_PRESET_RESOURCE",
            "execution_authorized": True,
        })
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EXECUTABLE_CAPABILITY_USE_NOT_IMPLEMENTED"):
            build_dynamic(plan=plan, verified_capabilities={1: ["POSITION", "PRISM", "COLOR", "GOBO"]})

    def test_command_plan_never_allocates_or_creates_resources(self):
        commands = commands_from_dynamic_preview(build_dynamic())
        joined = "\n".join(commands)
        self.assertIn("At Effect 2500", joined)
        self.assertIn("At Effect 2501", joined)
        self.assertIn("Store Cue 1 Sequence 302 /merge /cueonly /nc", joined)
        self.assertNotIn("Store Effect", joined)
        self.assertNotIn("Label ", joined)
        self.assertNotIn("Assign ", joined)
        self.assertNotIn("Sequence 303", joined)
        self.assertNotIn("Prism", joined)
        self.assertNotIn("Zoom", joined)
        self.assertNotIn("Frost", joined)
        cue1_stores = [i for i, command in enumerate(commands) if command == "Store Cue 1 Sequence 302 /merge /cueonly /nc"]
        self.assertEqual(len(cue1_stores), 2)
        between = commands[cue1_stores[0] + 1:cue1_stores[1]]
        self.assertIn("ClearAll", between)
        self.assertTrue(any(command.startswith("Fixture ") for command in between))

    def test_verified_existing_presets_join_the_same_existing_cue_preview(self):
        plan = artistic_plan()
        plan["cues"][0]["actions"].insert(0, {
            "operation": "CALL_PRESET",
            "target": {"type": "group", "ref": 1},
            "preset_ref": "4.101",
            "preset_type": "COLOR",
        })
        plan["cues"][2]["actions"].insert(0, {
            "operation": "CALL_PRESET",
            "target": {"type": "group", "ref": 1},
            "preset_ref": "3.201",
            "preset_type": "GOBO",
        })
        preview = build_dynamic(plan=plan, verified_presets=presets())
        cue1 = preview["cue_updates"][0]
        cue3 = preview["cue_updates"][2]
        self.assertEqual(cue1["selected_presets"][0]["reuse"], "EXISTING_VERIFIED_PRESET")
        self.assertIn("COLOR", cue1["used_capability_families"])
        self.assertEqual(cue3["beam_gobo_focus_changes"][0]["dimension"], "GOBO")
        commands = commands_from_dynamic_preview(preview)
        self.assertIn("At Preset 4.101", commands)
        self.assertIn("At Preset 3.201", commands)
        self.assertFalse(any(command.startswith("Store Preset") for command in commands))

    def test_requested_preset_without_exact_resource_or_attribute_evidence_fails_closed(self):
        plan = artistic_plan()
        plan["cues"][0]["actions"].insert(0, {
            "operation": "CALL_PRESET",
            "target": {"type": "group", "ref": 1},
            "preset_ref": "4.101",
            "preset_type": "COLOR",
        })
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PRESET_NOT_VERIFIED"):
            build_dynamic(plan=plan)
        incomplete = presets()
        incomplete[1]["4.101"]["attribute_names"] = []
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PRESET_NOT_VERIFIED"):
            build_dynamic(plan=plan, verified_presets=incomplete)

    def test_native_postwrite_verifies_selected_preset_and_protected_content(self):
        pre = target_discovery()
        plan = artistic_plan()
        plan["cues"][0]["actions"].insert(0, {
            "operation": "CALL_PRESET",
            "target": {"type": "group", "ref": 1},
            "preset_ref": "4.101",
            "preset_type": "COLOR",
        })
        preview = build_dynamic(pre=pre, plan=plan, verified_presets=presets())
        report = verify_existing_cue_dynamic_program_merge(preview, post_from(pre, preview))
        self.assertEqual(report["preset_fixture_matches"], 2)
        drift = post_from(pre, preview)
        drift["cues"][0]["parts"][0]["cue_data"].append(row("101", "GOBO1", 7))
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, drift)

    def test_preview_helper_requires_exact_schema(self):
        preview = build_dynamic()
        preview.pop("schema")
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PREVIEW_SCHEMA_INVALID"):
            commands_from_dynamic_preview(preview)

    def test_artistic_cue_order_and_uniqueness_are_fail_closed(self):
        plan = artistic_plan()
        plan["cues"][0], plan["cues"][1] = plan["cues"][1], plan["cues"][0]
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "CUE_ORDER_MISMATCH"):
            build_dynamic(plan=plan)
        plan = artistic_plan()
        plan["cues"].append(copy.deepcopy(plan["cues"][0]))
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "DUPLICATE_ARTISTIC_CUE_NUMBER"):
            build_dynamic(plan=plan)

    def test_one_effect_plus_no_new_effect_is_valid_variation(self):
        plan = artistic_plan()
        for cue_item in plan["cues"]:
            cue_item["actions"] = []
        plan["cues"][0]["actions"] = [{
            "operation": "CALL_EFFECT",
            "target": {"type": "group", "ref": 1},
            "effect_ref": {"id": 2500},
        }]
        preview = build_dynamic(plan=plan)
        self.assertEqual(preview["cue_effects"]["1"]["id"], 2500)
        self.assertIsNone(preview["cue_effects"]["2"])

    def test_effect_on_wrong_attribute_family_is_rejected(self):
        pre = target_discovery()
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        for item in post["cues"][0]["parts"][0]["cue_data"]:
            effect = item.get("effect") or {}
            parts = effect.get("no_components") if isinstance(effect, dict) else None
            if isinstance(parts, list) and parts and str(parts[-1]) == "2500":
                item["channel"]["attribute_name"] = "COLORRGB1"
                break
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, post)

    def test_sibling_subfixture_effect_change_is_protected(self):
        pre = target_discovery()
        sibling = effect_row(101, 2502)
        sibling["channel"]["subfixture_id"] = "2"
        pre["cues"][0]["parts"][0]["cue_data"].append(sibling)
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        for item in post["cues"][0]["parts"][0]["cue_data"]:
            channel = item.get("channel") or {}
            if channel.get("fixture_id") == "101" and channel.get("subfixture_id") == "2":
                item["effect"] = {"no_components": ["1", "2501"]}
                break
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, post)

    def test_unrelated_fixture_position_drift_is_protected(self):
        pre = target_discovery()
        pre["cues"][0]["parts"][0]["cue_data"].append(row("999", "PAN", 5))
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        for item in post["cues"][0]["parts"][0]["cue_data"]:
            channel = item.get("channel") or {}
            if channel.get("fixture_id") == "999" and channel.get("attribute_name") == "PAN":
                item["raw_values"]["Value"] = "6"
                break
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, post)

    def test_parent_effect_row_requires_unambiguous_channel_identity(self):
        pre = target_discovery()
        observed = effect_row(101, 2500)
        observed["channel"].pop("subfixture_id", None)
        pre["cues"][0]["parts"][0]["cue_data"].append(observed)
        result = effect_ids_by_cue_ref(
            pre, cue_numbers=[1], target_fixture_refs=["101.1"],
            cue_channel_refs={"101.1": "101.1"},
        )
        self.assertEqual(result["1"]["101.1"], [2500])
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PARENT_ROW_AMBIGUOUS"):
            effect_ids_by_cue_ref(
                pre, cue_numbers=[1], target_fixture_refs=["101.1", "101.2"],
                cue_channel_refs={"101.1": "101.1", "101.2": "101.2"},
            )

    def test_unverified_effect_or_application_capability_fails_closed(self):
        bad = effects()
        bad[1].pop(2501)
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EFFECT_NOT_VERIFIED"):
            build_dynamic(verified_effects=bad)
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EFFECT_APPLICATION_UNVERIFIED"):
            build_dynamic(capability={})

    def test_single_effect_state_is_rejected_as_non_dynamic(self):
        plan = artistic_plan()
        for cue_item in plan["cues"]:
            cue_item["actions"] = [{
                "operation": "CALL_EFFECT",
                "target": {"type": "group", "ref": 1},
                "effect_ref": {"id": 2500},
            }]
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EFFECT_VARIATION_REQUIRED"):
            build_dynamic(plan=plan)

    def test_missing_position_or_unrelated_executable_action_is_noncompliant(self):
        plan = artistic_plan()
        plan["cues"][0].pop("position_pattern")
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "POSITION_INTENT_MISSING"):
            build_dynamic(plan=plan)
        plan = artistic_plan()
        plan["cues"][0]["actions"].append({
            "operation": "SET_DIMMER", "target": {"type": "group", "ref": 1}, "level": 100,
        })
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "UNSUPPORTED_EXECUTABLE_ACTION"):
            build_dynamic(plan=plan)

    def test_post_write_position_effect_and_protected_content_verify(self):
        pre = target_discovery()
        # Static target-fixture values remain protected even when an Effect is intentionally attached.
        pre["cues"][0]["parts"][0]["cue_data"].append(row("101", "DIM", 55))
        pos = build_position(target=pre)
        preview = build_dynamic(pre=pre, pos=pos)
        post = post_from(pre, preview)
        verified = verify_existing_cue_dynamic_program_merge(preview, post)
        self.assertEqual(verified["status"], "VERIFIED")
        self.assertEqual(verified["position_value_matches"], 16)
        self.assertEqual(verified["effect_fixture_matches"], 6)
        self.assertEqual(verified["protected_content"], "UNCHANGED")

    def test_static_dimmer_value_drift_is_not_hidden_by_effect_allowance(self):
        pre = target_discovery()
        pre["cues"][0]["parts"][0]["cue_data"].append(row("101", "DIM", 55))
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        for item in post["cues"][0]["parts"][0]["cue_data"]:
            channel = item.get("channel") or {}
            if channel.get("fixture_id") == "101" and channel.get("attribute_name") == "DIM" and (item.get("raw_values") or {}).get("Value") == "55":
                item["raw_values"]["Value"] = "56"
                break
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, post)

    def test_unplanned_color_or_effect_on_no_effect_cue_fails_closed(self):
        pre = target_discovery()
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        post["cues"][1]["parts"][0]["cue_data"].append(effect_row(101, 2502))
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "PROTECTED_CONTENT_CHANGED"):
            verify_existing_cue_dynamic_program_merge(preview, post)

    def test_existing_effect_mutation_is_blocked_until_replacement_grammar_is_verified(self):
        pre = target_discovery()
        pre["cues"][0]["parts"][0]["cue_data"].extend([effect_row(101, 2500), effect_row(102, 2500)])
        plan = artistic_plan()
        plan["cues"][0]["actions"] = [{
            "operation": "CALL_EFFECT",
            "target": {"type": "group", "ref": 1},
            "effect_ref": {"id": 2501},
        }]
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "EXISTING_EFFECT_MUTATION_UNVERIFIED"):
            build_dynamic(pre=pre, pos=build_position(target=pre), plan=plan)

        plan["cues"][0]["replace_effect_ids"] = [2500]
        with self.assertRaisesRegex(ExistingCueDynamicProgramMergeError, "REPLACEMENT_GRAMMAR_UNVERIFIED"):
            build_dynamic(pre=pre, pos=build_position(target=pre), plan=plan)

    def test_no_new_effect_call_preserves_preexisting_effect_set(self):
        pre = target_discovery()
        pre["cues"][1]["parts"][0]["cue_data"].extend([effect_row(101, 2502), effect_row(102, 2502)])
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        self.assertIsNone(preview["cue_effects"]["2"] )
        post = post_from(pre, preview)
        verified = verify_existing_cue_dynamic_program_merge(preview, post)
        self.assertEqual(verified["status"], "VERIFIED")
        sets = effect_ids_by_cue_ref(
            post, cue_numbers=[2], target_fixture_refs=preview["group"]["exact_refs"],
            cue_channel_refs=preview["group"]["cue_channel_refs"],
        )
        self.assertEqual(
            sorted({effect_id for ids in sets["2"].values() for effect_id in ids}),
            [2502],
        )

    def test_effect_metadata_is_the_only_scrubbed_nonposition_family(self):
        pre = target_discovery()
        preview = build_dynamic(pre=pre, pos=build_position(target=pre))
        post = post_from(pre, preview)
        effects_map = {int(k): v for k, v in preview["cue_effects"].items()}
        before = protected_content_snapshot(
            pre, cue_effects=effects_map, target_fixture_refs=preview["group"]["exact_refs"],
            cue_channel_refs=preview["group"]["cue_channel_refs"],
        )
        after = protected_content_snapshot(
            post, cue_effects=effects_map, target_fixture_refs=preview["group"]["exact_refs"],
            cue_channel_refs=preview["group"]["cue_channel_refs"],
        )
        self.assertEqual(before["sha256"], after["sha256"])


if __name__ == "__main__":
    unittest.main()
