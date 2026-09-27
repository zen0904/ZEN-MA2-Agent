import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from shutil import copytree

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.sequence302_resource_merge import (
    EFFECT_SPECS,
    Sequence302ResourceMergeError,
    TARGET_REFS,
    build_sequence302_resource_merge_preview,
    expand_explicit_raw_plan,
    verify_sequence302_resource_merge,
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


def empty_effect_evidence():
    return {
        effect_id: {
            "fresh": True,
            "effect_id": effect_id,
            "pool_identity": "ABSENT",
            "line_content": "EMPTY",
            "qty_values": [],
            "attribute_names": [],
        }
        for effect_id in (2500, 2501, 2502)
    }


def dimmer_evidence():
    return {
        "status": "SHOW_BOUND_VERIFIED",
        "group_id": 1,
        "exact_refs": list(TARGET_REFS),
        "attribute": "Dim",
        "source": "NATIVE_SEQUENCE_EXPORT",
    }


def raw_row(ref, attribute, value, preset=None, effect=None):
    root, sub = ref.split(".")
    result = {
        "multipart_indexes": {"value": "0"},
        "channel": {"fixture_id": root, "subfixture_id": sub, "attribute_name": attribute},
        "raw_values": {"Value": str(value)},
        "preset": None,
        "effect": None,
    }
    if preset:
        pool, number = preset.split(".")
        result["preset"] = {"no_components": ["1", pool, number]}
    if effect:
        result["effect"] = {"no_components": ["1", str(effect)]}
        result["raw_values"] = {"EffectLow": "0", "EffectHigh": "100"}
    return result


def discovery():
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": 302,
        "xml_discovery": {"sha256": "a" * 64},
        "cues": [
            {
                "number": {"number": str(number), "sub_number": None},
                "parts": [{"index": "0", "name": f"CUE_{number:02d}", "cue_data": [
                    raw_row("201.1", "DIM", number),
                ]}],
            }
            for number in range(1, 30)
        ],
    }


def position_preview():
    return {
        "schema": "zen.position_existing_cue_merge_preview.v0.1",
        "show_identity": {"value": "b" * 64},
        "target_sequence": {
            "id": 302,
            "label": "ZEN_SEQ302",
            "cue_start": 1,
            "cue_end": 29,
            "cue_metadata": [
                {"number": number, "name": f"CUE_{number:02d}", "fade": 0.5, "delay": 0.0}
                for number in range(1, 30)
            ],
            "executor_assignments": [{"page": 2, "executor": 8, "location": "2.8", "label": "ZEN_SEQ302"}],
        },
        "group": {
            "id": 1, "name": "HYBRID", "exact_refs": list(TARGET_REFS),
            "cue_channel_refs": {ref: ref for ref in TARGET_REFS},
        },
    }


def explicit_plan():
    effect_cycle = [None, 2500, 2501, 2502, 2501, 2502, 2502, 2500, None, None, None]
    plan = []
    for number in range(1, 30):
        pattern = (number - 1) % 11
        fixtures = [
            {
                "fixture_ref": ref,
                "pan": 10 + pattern + index / 10,
                "tilt": 20 + pattern,
            }
            for index, ref in enumerate(TARGET_REFS)
        ]
        plan.append({
            "cue_number": number,
            "cue_label": f"CUE_{number:02d}",
            "position_name": f"LOOK_{pattern + 1:02d}",
            "fixtures": fixtures,
            "effect_id": effect_cycle[pattern],
        })
    return plan


def build(**overrides):
    args = {
        "position_preview": position_preview(),
        "pre_discovery": discovery(),
        "explicit_raw_plan": explicit_plan(),
        "current_presets": [{"reference": "2.1", "preset_type": "POSITION", "name": "FOREIGN"}],
        "fresh_effect_empty_evidence": empty_effect_evidence(),
        "dimmer_applicability_evidence": dimmer_evidence(),
        "effect_application_capability": effect_capability(),
    }
    args.update(overrides)
    return build_sequence302_resource_merge_preview(**args)


class Sequence302ResourceMergeTests(unittest.TestCase):
    def test_committed_explicit_raw_plan_expands_with_fresh_labels(self):
        artifact = json.loads(
            (Path(__file__).resolve().parents[1] / "data" / "sequence302_resource_merge_raw_plan.json").read_text(encoding="utf-8")
        )
        labels = {number: f"LIVE_{number:02d}" for number in range(1, 30)}
        plan = expand_explicit_raw_plan(artifact, labels)
        self.assertEqual(len(plan), 29)
        self.assertEqual(plan[0]["cue_label"], "LIVE_01")
        self.assertEqual(tuple(row["fixture_ref"] for row in plan[0]["fixtures"]), TARGET_REFS)

    def test_preview_authors_resources_then_merge_only_existing_cues(self):
        preview = build()
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertEqual(len(preview["position_presets_to_create"]), 11)
        self.assertEqual([item["effect_id"] for item in preview["effects_to_create"]], [2500, 2501, 2502])
        commands = preview["candidate_commands"]
        self.assertTrue(all("Sequence 302" in command for command in commands if command.startswith("Store Cue")))
        self.assertTrue(all("/merge /cueonly /nc" in command for command in commands if command.startswith("Store Cue")))
        self.assertFalse(any(command.startswith("Assign Sequence") or "Executor" in command for command in commands))
        self.assertFalse(any("9999" in command for command in commands))
        for spec in EFFECT_SPECS:
            self.assertIn(f'Store Effect {spec.effect_id} /nc', commands)
            self.assertIn(f'Assign Attribute "Dim" At Effect 1.{spec.effect_id}.1', commands)
        self.assertEqual(preview["ma2_writes"], 0)

    def test_core_registers_new_preview_through_normal_action_gate(self):
        with tempfile.TemporaryDirectory(prefix="zen-seq302-resource-") as temp:
            root = Path(temp)
            copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
            core = AgentCore(AgentRuntime(root))
            for resource in (
                "groups", "group_membership", "fixtures", "fixture_geometry",
                "fixture_type_profiles", "presets", "effects", "sequences",
                "cues", "executors",
            ):
                core.state.put(resource, [], source="test")
            result = core.preview_sequence302_resource_merge(
                position_preview=position_preview(),
                pre_discovery=discovery(),
                explicit_raw_plan=explicit_plan(),
                current_presets=[{"reference": "2.1", "preset_type": "POSITION", "name": "FOREIGN"}],
                fresh_effect_empty_evidence=empty_effect_evidence(),
                dimmer_applicability_evidence=dimmer_evidence(),
                effect_application_capability=effect_capability(),
            )
            self.assertEqual(result["action"]["status"], "PENDING_APPROVAL")
            self.assertEqual(result["action"]["phase"], "PREVIEW")
            inspected = core.preview_action(result["action"]["id"])
            self.assertEqual(inspected["action"]["preview_id"], result["action"]["preview_id"])
            self.assertIsNone(core.runtime.client)

    def _approval_guard_core(self):
        with tempfile.TemporaryDirectory(prefix="zen-seq302-approval-") as temp:
            root = Path(temp)
            copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
            core = AgentCore(AgentRuntime(root))
            for resource in (
                "groups", "group_membership", "fixtures", "fixture_geometry",
                "fixture_type_profiles", "presets", "effects", "sequences",
                "cues", "executors",
            ):
                core.state.put(resource, [], source="test")
            result = core.preview_sequence302_resource_merge(
                position_preview=position_preview(),
                pre_discovery=discovery(),
                explicit_raw_plan=explicit_plan(),
                current_presets=[{"reference": "2.1", "preset_type": "POSITION", "name": "FOREIGN"}],
                fresh_effect_empty_evidence=empty_effect_evidence(),
                dimmer_applicability_evidence=dimmer_evidence(),
                effect_application_capability=effect_capability(),
            )
            yield core, core.actions[result["action"]["id"]]

    def test_approval_time_executor_drift_fails_before_write(self):
        for core, action in self._approval_guard_core():
            preview = action.workflow.task.intent.parameters["sequence302_resource_merge_preview"]
            expected_meta = preview["target_sequence"]["cue_metadata"]
            with patch.object(core.sequence_export_provider, "export_and_discover", return_value=discovery()), \
                 patch.object(core, "_fresh_existing_cue_metadata", return_value=expected_meta), \
                 patch.object(core, "_sequence_executor_assignments", return_value=[]), \
                 patch.object(core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute:
                with self.assertRaisesRegex(Sequence302ResourceMergeError, "APPROVAL_TIME_EXECUTOR_DRIFT"):
                    core._ensure_sequence302_resource_state_unchanged(action)
            execute.assert_not_called()

    def test_approval_time_effect_line_drift_fails_before_write(self):
        for core, action in self._approval_guard_core():
            preview = action.workflow.task.intent.parameters["sequence302_resource_merge_preview"]
            expected_meta = preview["target_sequence"]["cue_metadata"]
            expected_exec = preview["target_sequence"]["executor_assignments"]
            def read_state(command):
                if command == "List Effect 1.2501.*":
                    return "Effectline 1 None None DIM Abs Pwm\nQTY=None\n"
                return "WARNING, NO OBJECTS FOUND FOR LIST\n"
            with patch.object(core.sequence_export_provider, "export_and_discover", return_value=discovery()), \
                 patch.object(core, "_fresh_existing_cue_metadata", return_value=expected_meta), \
                 patch.object(core, "_sequence_executor_assignments", return_value=expected_exec), \
                 patch.object(core.runtime, "read_state", side_effect=read_state), \
                 patch.object(core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute:
                with self.assertRaisesRegex(Sequence302ResourceMergeError, "APPROVAL_TIME_EFFECT_LINE_DRIFT"):
                    core._ensure_sequence302_resource_state_unchanged(action)
            execute.assert_not_called()

    def test_rejects_nonempty_effect_slot(self):
        evidence = empty_effect_evidence()
        evidence[2501]["qty_values"] = [8]
        evidence[2501]["line_content"] = "NONEMPTY"
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "NOT_FRESH_EMPTY"):
            build(fresh_effect_empty_evidence=evidence)

    def test_rejects_missing_or_drifted_effect_identity(self):
        evidence = empty_effect_evidence()
        del evidence[2502]
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "EVIDENCE_INCOMPLETE"):
            build(fresh_effect_empty_evidence=evidence)
        evidence = empty_effect_evidence()
        evidence[2500]["effect_id"] = 2509
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "NOT_FRESH_EMPTY"):
            build(fresh_effect_empty_evidence=evidence)

    def test_rejects_group_fixture_or_cue_drift(self):
        preview = position_preview()
        preview["group"]["exact_refs"][0] = "101.2"
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "EXACT_GROUP_IDENTITY"):
            build(position_preview=preview)
        pre = discovery()
        pre["cues"].pop()
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "EXACT_CUES"):
            build(pre_discovery=pre)

    def test_rejects_unverified_dimmer_or_effect_grammar(self):
        dim = dimmer_evidence()
        dim["status"] = "UNVERIFIED"
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "DIM_APPLICABILITY"):
            build(dimmer_applicability_evidence=dim)
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "APPLICATION_GRAMMAR"):
            build(effect_application_capability={})

    def test_rejects_legacy_action_replay(self):
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "LEGACY_ACTION_REPLAY_FORBIDDEN"):
            build(source_action_id="97d3a82f1220")
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "LEGACY_ACTION_REPLAY_FORBIDDEN"):
            build(source_action_id="a9dd416ef92b")

    def test_native_postwrite_verifier_requires_qty_dim_and_raw_position(self):
        preview = build()
        post = copy.deepcopy(discovery())
        post["xml_discovery"]["sha256"] = "c" * 64
        cues = {int(row["number"]["number"]): row for row in post["cues"]}
        for update in preview["cue_updates"]:
            rows = cues[update["cue_number"]]["parts"][0]["cue_data"]
            for fixture in update["fixtures"]:
                rows.append(raw_row(fixture["fixture_ref"], "PAN", fixture["pan"], update["position_preset_ref"]))
                rows.append(raw_row(fixture["fixture_ref"], "TILT", fixture["tilt"], update["position_preset_ref"]))
                if update["effect_id"]:
                    rows.append(raw_row(fixture["fixture_ref"], "DIM", 0, effect=update["effect_id"]))
        preset_rows = [
            {"reference": row["reference"], "preset_type": "POSITION", "name": row["label"]}
            for row in preview["position_presets_to_create"]
        ]
        effect_rows = [
            {
                "number": spec.effect_id,
                "name": spec.label,
                "attributes": ["Dim"],
                "template_detail": {"status": "VERIFIED", "kind": "TEMPLATE", "qty_values": ["NONE"]},
            }
            for spec in EFFECT_SPECS
        ]
        report = verify_sequence302_resource_merge(
            preview, post, post_preset_rows=preset_rows, post_effect_rows=effect_rows
        )
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(report["raw_position_values_verified"], 29 * 8 * 2)
        bad = copy.deepcopy(effect_rows)
        bad[0]["template_detail"]["qty_values"] = []
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "CONTENT_UNVERIFIED"):
            verify_sequence302_resource_merge(preview, post, post_preset_rows=preset_rows, post_effect_rows=bad)
        drift = copy.deepcopy(post)
        for row in drift["cues"][0]["parts"][0]["cue_data"]:
            if row.get("channel", {}).get("attribute_name") == "PAN":
                row["raw_values"]["Value"] = "999"
                break
        with self.assertRaisesRegex(Sequence302ResourceMergeError, "RAW_POSITION_MISMATCH"):
            verify_sequence302_resource_merge(preview, drift, post_preset_rows=preset_rows, post_effect_rows=effect_rows)


if __name__ == "__main__":
    unittest.main()
