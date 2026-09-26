"""Approval-gated raw Pan/Tilt transport proof remains separate from bindings."""
import copy
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.operator_api import OpenClawOperatorAdapter, build_operator_status
from zen_ma2_agent.position_application_evidence import PositionEvidenceError
from zen_ma2_agent.position_raw_cue_poc import (
    PositionRawCuePocSkill, build_position_raw_cue_preview,
    verify_raw_position_cue_content,
)
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class NoWriteClient:
    state = ConnectionState.READY
    authenticated_user = "MM"
    audit_entries = []

    def execute(self, command):
        raise AssertionError(f"Preview must not send MA2 command: {command}")


def profile():
    return {
        "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "a" * 64, "confidence": "PARTIAL"},
        "resources": {key: {"status": "SUPPORTED"} for key in (
            "groups", "group_membership", "fixtures", "fixture_geometry", "fixture_type_profiles", "sequences", "presets")},
        "fixtures": [{"fixture_id": 101, "fixture_type": "2 MOVING",
                      "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}},
                     {"fixture_id": 102, "fixture_type": "2 MOVING",
                      "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}}],
        "fixture_type_profiles": [{"status": "SHOW_BOUND_VERIFIED", "fixture_type": {"list_label": "2 MOVING"},
                                   "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}}}],
        "groups": [{"group_id": 1, "name": "HYBRID", "fixture_refs_in_selection_order": ["101", "102"],
                    "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"}}],
        "sequences": [{"number": 1, "name": "Foreign"}],
    }


def discovery(sequence=2, refs=("101", "102"), attributes=("PAN", "TILT")):
    rows = []
    for ref in refs:
        fixture, *sub = ref.split(".", 1)
        for attr in attributes:
            channel = {"fixture_id": fixture, "attribute_name": attr}
            if sub:
                channel["subfixture_id"] = sub[0]
            rows.append({"channel": channel,
                         "raw_values": {"Value": "20" if attr == "PAN" else "30"}})
    return {"schema": "zen.sequence_export_discovery.v0.1", "status": "VERIFIED",
            "sequence_no": sequence, "xml_discovery": {"sha256": "b" * 64},
            "cues": [{"number": {"number": "1", "sub_number": None},
                      "parts": [{"index": "0", "cue_data": rows}]}]}


class RawPositionCuePocTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-raw-position-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.core = AgentCore(AgentRuntime(root))
        self.core.runtime.client = NoWriteClient()
        for resource in ("groups", "group_membership", "fixtures", "fixture_geometry",
                         "fixture_type_profiles", "sequences", "presets"):
            self.core.state.put(resource, [], source="test_fresh_fixture")
        self.profile = profile()
        self.preview = build_position_raw_cue_preview(self.profile, group_id=1)
        self.expected = dict(expected_show_fingerprint="a" * 64, group_id=1,
                             expected_group_name="HYBRID", expected_exact_refs=["101", "102"])

    def tearDown(self):
        self.temp.cleanup()

    def register(self):
        with patch.object(self.core, "_fresh_position_raw_preview", return_value=(self.profile, self.preview)):
            return self.core.preview_position_raw_cue_poc(**self.expected)

    def test_preview_registers_action_without_approval_or_write(self):
        with patch.object(self.core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute, \
             patch.object(self.core, "approve_action", side_effect=AssertionError("approval")) as approve, \
             patch.object(self.core.position_application_bindings, "record_after_readback", side_effect=AssertionError("binding")) as binding:
            action = self.register()["action"]
        self.assertTrue(action["id"])
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual((action["root_state"], action["phase"]), ("READY", "PREVIEW"))
        self.assertEqual(self.core.preview_action(action["id"])["action"]["preview_id"], self.preview["preview_id"])
        self.assertIsNone(self.preview["sequence"]["executor"])
        self.assertFalse(self.core.position_application_bindings.has_candidates())
        execute.assert_not_called(); approve.assert_not_called(); binding.assert_not_called()

    def test_explicit_pan_tilt_commands_and_no_naked_at(self):
        self.assertEqual(self.preview["candidate_commands"][2:4],
                         ['Attribute "Pan" At 20', 'Attribute "Tilt" At 30'])
        self.assertNotIn("At 20", self.preview["candidate_commands"])
        self.assertTrue(all(command.isascii() for command in self.preview["candidate_commands"]))
        self.assertEqual(self.preview["position_application_evidence"], "UNVERIFIED")

    def test_show_and_group_drift_reject_before_action(self):
        for key, value, error in (
            ("expected_show_fingerprint", "b" * 64, "FINGERPRINT_DRIFT"),
            ("expected_group_name", "RENAMED", "GROUP_IDENTITY_DRIFT"),
            ("expected_exact_refs", ["102", "101"], "GROUP_IDENTITY_DRIFT"),
        ):
            with self.subTest(key=key), patch.object(self.core, "_fresh_position_raw_preview", return_value=(self.profile, self.preview)):
                with self.assertRaisesRegex(PositionEvidenceError, error):
                    self.core.preview_position_raw_cue_poc(**{**self.expected, key: value})
                self.assertFalse(self.core.actions)

    def test_position_capability_multi_instance_and_fixture9999_fail_closed(self):
        for kind in ("capability", "multi_instance", "fixture9999"):
            changed = copy.deepcopy(self.profile)
            if kind == "capability":
                changed["fixture_type_profiles"][0]["capabilities"]["POSITION"]["status"] = "UNKNOWN"
            elif kind == "multi_instance":
                changed["fixtures"][0]["stage_geometry"]["subfixtures"].append({"subfixture_id": 2})
            else:
                changed["groups"][0]["fixture_refs_in_selection_order"] = ["9999", "102"]
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                build_position_raw_cue_preview(changed, group_id=1)

    def test_occupied_sequence_allocates_fresh_and_protected_skips(self):
        changed = copy.deepcopy(self.profile)
        changed["sequences"].append({"number": 2, "name": "Foreign 2"})
        self.assertEqual(build_position_raw_cue_preview(changed, group_id=1)["sequence"]["id"], 3)
        with patch("zen_ma2_agent.position_raw_cue_poc.PROTECTED_SEQUENCES", frozenset({2})):
            self.assertEqual(build_position_raw_cue_preview(self.profile, group_id=1)["sequence"]["id"], 3)

    def test_label_collision_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["sequences"].append({"number": 3, "name": "ZEN_POSITION_RAW_POC_SEQ2"})
        with self.assertRaisesRegex(PositionEvidenceError, "LABEL_COLLISION"):
            build_position_raw_cue_preview(changed, group_id=1)

    def test_approval_time_sequence_or_group_drift_rejects_before_write(self):
        action = self.register()["action"]
        for field in ("sequence", "group"):
            changed = copy.deepcopy(self.preview)
            if field == "sequence":
                changed["sequence"]["id"] = 3
            else:
                changed["group"]["exact_refs"] = ["102", "101"]
            with self.subTest(field=field), patch.object(self.core, "_fresh_position_raw_preview", return_value=(self.profile, changed)), \
                 patch.object(self.core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute:
                with self.assertRaisesRegex(PositionEvidenceError, "STALE_APPROVED_PREVIEW"):
                    self.core.approve_action(action["id"])
                execute.assert_not_called()
        self.assertEqual(self.core.actions[action["id"]].status, "PENDING_APPROVAL")

    def test_fresh_discovery_reads_exact_groups_and_preset_inventory_for_show_identity(self):
        self.core.state.put_groups([{"number": 1}, {"number": 2}])
        reads = []
        def refresh(resource, **kwargs):
            reads.append((resource, kwargs)); return {"status": "available"}
        with patch.object(self.core, "refresh_state", side_effect=refresh), \
             patch.object(self.core, "scan_show_profile", return_value=self.profile), \
             patch.object(self.core, "_recover_bounded_test_show_evidence", return_value=([], [])):
            self.core._fresh_position_raw_preview(group_id=1)
        self.assertIn(("group_membership", {"group_no": 1}), reads)
        self.assertIn(("group_membership", {"group_no": 2}), reads)
        self.assertIn(("fixture_type_profiles", {}), reads)
        self.assertIn(("presets", {}), reads)

    def test_operator_tool_routes_only_to_preview(self):
        calls = []
        adapter = OpenClawOperatorAdapter(
            lambda: build_operator_status(field_core_available=True),
            raw_position_preview_handler=lambda **kwargs: calls.append(kwargs) or {"action": {"status": "PENDING_APPROVAL"}},
        )
        self.assertEqual(adapter.invoke("zen.position.raw.preview", self.expected)["status"], "SUCCESS")
        self.assertEqual(calls, [self.expected])
        self.assertEqual(adapter.invoke("zen.position.raw.preview", {"group_id": 1})["status"], "REJECTED")

    def test_skill_rejects_non_ascii_or_altered_command(self):
        skill = self.core.skills._implementations["position.raw_cue_poc"]
        action = self.register()["action"]
        workflow = self.core.actions[action["id"]].workflow
        for replacement in ('At 20', 'Attribute "Pan" At 20 藝術'):
            steps = list(workflow.steps)
            steps[2] = replace(steps[2], command=replacement)
            with self.subTest(replacement=replacement), self.assertRaisesRegex(PositionEvidenceError, "INVALID"):
                skill.validate(replace(workflow, steps=tuple(steps)), self.core.state)

    def test_empty_cuedata_pan_only_tilt_only_foreign_and_partial_reject(self):
        for kind in ("empty", "pan_only", "tilt_only", "foreign", "partial"):
            result = discovery()
            rows = result["cues"][0]["parts"][0]["cue_data"]
            if kind == "empty": rows.clear()
            elif kind == "pan_only": rows[:] = [r for r in rows if r["channel"]["attribute_name"] == "PAN"]
            elif kind == "tilt_only": rows[:] = [r for r in rows if r["channel"]["attribute_name"] == "TILT"]
            elif kind == "foreign": rows.append({"channel": {"fixture_id": "999", "subfixture_id": "1", "attribute_name": "PAN"}})
            else: rows[:] = [r for r in rows if r["channel"]["fixture_id"] == "101"]
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                verify_raw_position_cue_content(self.profile, self.preview, result)

    def test_exact_pan_tilt_all_members_passes_without_binding(self):
        result = verify_raw_position_cue_content(self.profile, self.preview, discovery())
        self.assertEqual(result["status"], "RAW_POSITION_CUE_CONTENT_VERIFIED")
        self.assertEqual(result["matched_channel_refs"], ["101", "102"])
        self.assertEqual(result["value_semantics"], "NOT_VERIFIED")
        self.assertEqual(result["position_application_evidence"], "UNVERIFIED")
        self.assertFalse(result["position_application_binding_recorded"])

    def test_pan_tilt_channel_without_exported_value_fails(self):
        result = discovery()
        result["cues"][0]["parts"][0]["cue_data"][0]["raw_values"]["Value"] = None
        with self.assertRaisesRegex(PositionEvidenceError, "VALUE_FIELD_UNAVAILABLE"):
            verify_raw_position_cue_content(self.profile, self.preview, result)

    def test_approved_failure_attempts_clearall_without_delete_or_binding(self):
        action = self.register()["action"]
        sent = []
        def execute(commands):
            sent.extend(commands); return ["OK"]
        with patch.object(self.core.runtime, "execute_approved_commands", side_effect=execute), \
             patch.object(self.core, "verify_first_song_metadata"), \
             patch.object(self.core.sequence_export_provider, "export_and_discover", return_value=discovery(attributes=("PAN",))), \
             patch.object(self.core, "_fresh_position_raw_profile", return_value=self.profile), \
             patch.object(self.core.position_application_bindings, "record_after_readback", side_effect=AssertionError("binding")) as binding:
            with self.assertRaisesRegex(PositionEvidenceError, "CONTENT_INCOMPLETE"):
                self.core._execute_position_raw_cue_poc(self.core.actions[action["id"]])
        self.assertEqual(sent[-1], "ClearAll")
        self.assertFalse(any(command.startswith("Delete ") for command in sent))
        binding.assert_not_called()

    def test_approved_content_success_retains_export_but_never_records_binding(self):
        action = self.register()["action"]
        sent = []
        def execute(commands):
            sent.extend(commands); return ["OK"]
        with patch.object(self.core.runtime, "execute_approved_commands", side_effect=execute), \
             patch.object(self.core, "verify_first_song_metadata"), \
             patch.object(self.core.sequence_export_provider, "export_and_discover", return_value=discovery()) as exported, \
             patch.object(self.core, "_fresh_position_raw_profile", return_value=self.profile), \
             patch.object(self.core.position_application_bindings, "record_after_readback", side_effect=AssertionError("binding")) as binding:
            result = self.core._execute_position_raw_cue_poc(self.core.actions[action["id"]])
        self.assertIn("RAW_POSITION_CUE_CONTENT_VERIFIED", result)
        self.assertEqual(sent, self.preview["candidate_commands"])
        exported.assert_called_once()
        self.assertTrue(exported.call_args.kwargs["retain_export"])
        binding.assert_not_called()
        self.assertFalse(self.core.position_application_bindings.has_candidates())


if __name__ == "__main__":
    unittest.main()
