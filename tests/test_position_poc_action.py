"""Approval-aware Position probe stops before every MA2 mutation."""
import copy
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.operator_api import OpenClawOperatorAdapter, build_operator_status
from zen_ma2_agent.position_application_evidence import (
    PositionEvidenceError, build_position_poc_preview,
)
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class NoWriteClient:
    state = ConnectionState.READY
    authenticated_user = "MM"
    audit_entries = []

    def execute(self, command):
        raise AssertionError(f"MA2 command forbidden in Preview test: {command}")


def profile():
    return {
        "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "a" * 64, "confidence": "PARTIAL"},
        "resources": {key: {"status": "SUPPORTED"} for key in (
            "groups", "group_membership", "fixtures", "fixture_geometry", "fixture_type_profiles", "presets", "sequences")},
        "fixtures": [{"fixture_id": 101, "fixture_type": "2 MOVING",
                      "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}}],
        "fixture_type_profiles": [{"status": "SHOW_BOUND_VERIFIED", "fixture_type": {"list_label": "2 MOVING"},
                                   "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}}}],
        "groups": [{"group_id": 1, "name": "HYBRID", "fixture_refs_in_selection_order": ["101"],
                    "membership": {"status": "SUPPORTED", "source": "ma2_group_export_xml"}}],
        "presets": [{"reference": "2.1", "preset_type": "POSITION", "name": "HOME"}],
        "sequences": [{"number": 1, "name": "Foreign"}],
    }


class PositionPocActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-position-action-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.core = AgentCore(AgentRuntime(root))
        self.core.runtime.client = NoWriteClient()
        for resource in ("groups", "group_membership", "fixtures", "fixture_geometry",
                         "fixture_type_profiles", "presets", "sequences"):
            self.core.state.put(resource, [], source="test_fresh_fixture")
        self.profile = profile()
        self.preview = build_position_poc_preview(self.profile, group_id=1, preset_ref="2.1")
        self.expected = dict(expected_show_fingerprint="a" * 64, group_id=1,
                             expected_group_name="HYBRID", expected_exact_refs=["101"],
                             preset_ref="2.1", expected_preset_label="HOME")

    def tearDown(self):
        self.temp.cleanup()

    def register(self):
        with patch.object(self.core, "_fresh_position_poc_preview", return_value=(self.profile, self.preview)):
            return self.core.preview_position_application_poc(**self.expected)

    def test_fresh_identity_registers_real_action_without_approval_or_write(self):
        with patch.object(self.core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute, \
             patch.object(self.core.position_application_bindings, "record_after_readback", side_effect=AssertionError("binding")) as record:
            result = self.register()
        action = result["action"]
        self.assertTrue(action["id"])
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual((action["root_state"], action["current_phase"]), ("READY", "PREVIEW"))
        self.assertEqual(action["preview_id"], self.preview["preview_id"])
        self.assertEqual(action["intent"]["parameters"]["position_preview"]["sequence"]["executor"], None)
        self.assertEqual(self.core.root_workflow_status()["action_id"], action["id"])
        self.assertEqual(self.core.preview_action(action["id"])["status"], "PENDING_APPROVAL")
        execute.assert_not_called()
        record.assert_not_called()

    def test_show_group_and_preset_drift_reject_before_action(self):
        for key, value, error in (
            ("expected_show_fingerprint", "b" * 64, "FINGERPRINT_DRIFT"),
            ("expected_group_name", "RENAMED", "GROUP_IDENTITY_DRIFT"),
            ("expected_exact_refs", ["102"], "GROUP_IDENTITY_DRIFT"),
            ("expected_preset_label", "RENAMED", "PRESET_IDENTITY_DRIFT"),
        ):
            with self.subTest(key=key), patch.object(self.core, "_fresh_position_poc_preview", return_value=(self.profile, self.preview)):
                changed = {**self.expected, key: value}
                with self.assertRaisesRegex(PositionEvidenceError, error):
                    self.core.preview_position_application_poc(**changed)
                self.assertFalse(self.core.actions)

    def test_capability_multi_instance_fixture_9999_and_preset_identity_fail_closed(self):
        for kind in ("capability", "parent", "fixture9999", "preset_ref", "preset_type", "preset_label"):
            changed = copy.deepcopy(self.profile)
            if kind == "capability":
                changed["fixture_type_profiles"][0]["capabilities"]["POSITION"]["status"] = "UNKNOWN"
            elif kind == "parent":
                changed["fixtures"][0]["stage_geometry"]["subfixtures"].append({"subfixture_id": 2})
            elif kind == "fixture9999":
                changed["groups"][0]["fixture_refs_in_selection_order"] = ["9999"]
            elif kind == "preset_ref":
                changed["presets"][0]["reference"] = "2.2"
            elif kind == "preset_type":
                changed["presets"][0]["preset_type"] = "COLOR"
            else:
                changed["presets"][0]["name"] = ""
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                build_position_poc_preview(changed, group_id=1, preset_ref="2.1")

    def test_occupied_sequence_reallocates_without_overwriting_or_executor(self):
        changed = copy.deepcopy(self.profile)
        changed["sequences"].append({"number": 2, "name": "Foreign Seq 2"})
        preview = build_position_poc_preview(changed, group_id=1, preset_ref="2.1")
        self.assertEqual(preview["sequence"]["id"], 3)
        self.assertIsNone(preview["sequence"]["executor"])
        self.assertIn("Store Cue 1 Sequence 3", preview["candidate_commands"][3])
        changed["sequences"].append({"number": 3, "name": "ZEN_POSITION_APPLICATION_POC_SEQ4"})
        with self.assertRaisesRegex(PositionEvidenceError, "LABEL_COLLISION"):
            build_position_poc_preview(changed, group_id=1, preset_ref="2.1")

    def test_approval_time_state_drift_rejects_before_execution(self):
        result = self.register()
        changed = copy.deepcopy(self.preview)
        changed["sequence"]["id"] = 3
        with patch.object(self.core, "_fresh_position_poc_preview", return_value=(self.profile, changed)), \
             patch.object(self.core.runtime, "execute_approved_commands", side_effect=AssertionError("write")) as execute:
            with self.assertRaisesRegex(PositionEvidenceError, "STALE_APPROVED_PREVIEW"):
                self.core.approve_action(result["action"]["id"])
        execute.assert_not_called()
        self.assertEqual(self.core.actions[result["action"]["id"]].status, "PENDING_APPROVAL")

    def test_fresh_discovery_reads_direct_preset_and_all_group_memberships(self):
        self.core.state.put_groups([{"number": 1}, {"number": 2}])
        reads = []
        def refresh(resource, **kwargs):
            reads.append((resource, kwargs))
            return {"status": "available"}
        with patch.object(self.core, "refresh_state", side_effect=refresh), \
             patch.object(self.core, "scan_show_profile", return_value=self.profile), \
             patch.object(self.core, "_recover_bounded_test_show_evidence", return_value=([], [])), \
             patch.object(self.core.runtime, "read_state", return_value="Position 2.1 2.1 HOME Normal") as direct:
            _, preview = self.core._fresh_position_poc_preview(group_id=1, preset_ref="2.1")
        self.assertEqual(preview["group"]["exact_refs"], ["101"])
        self.assertIn(("group_membership", {"group_no": 1}), reads)
        self.assertIn(("group_membership", {"group_no": 2}), reads)
        self.assertIn(("fixture_type_profiles", {}), reads)
        direct.assert_called_once_with("List Preset 2.1")

    def test_direct_preset_type_or_label_drift_blocks_registration(self):
        self.core.state.put_groups([{"number": 1}])
        for raw in ("Color 2.1 2.1 HOME Normal", "Position 2.1 2.1 AWAY Normal"):
            with self.subTest(raw=raw), patch.object(self.core, "refresh_state", return_value={"status": "available"}), \
                 patch.object(self.core, "scan_show_profile", return_value=self.profile), \
                 patch.object(self.core, "_recover_bounded_test_show_evidence", return_value=([], [])), \
                 patch.object(self.core.runtime, "read_state", return_value=raw):
                with self.assertRaisesRegex(PositionEvidenceError, "DIRECT_IDENTITY_MISMATCH"):
                    self.core.preview_position_application_poc(**self.expected)
                self.assertFalse(self.core.actions)

    def test_protected_sequence_is_skipped_by_allocator(self):
        with patch("zen_ma2_agent.position_application_evidence.PROTECTED_SEQUENCES", frozenset({2})):
            preview = build_position_poc_preview(self.profile, group_id=1, preset_ref="2.1")
        self.assertEqual(preview["sequence"]["id"], 3)

    def test_operator_position_tool_only_calls_preview_handler(self):
        calls = []
        adapter = OpenClawOperatorAdapter(
            lambda: build_operator_status(field_core_available=True),
            position_preview_handler=lambda **kwargs: calls.append(kwargs) or {"action": {"status": "PENDING_APPROVAL"}},
        )
        result = adapter.invoke("zen.position.preview", self.expected)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(calls, [self.expected])
        self.assertEqual(adapter.invoke("zen.position.preview", {"group_id": 1})["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
