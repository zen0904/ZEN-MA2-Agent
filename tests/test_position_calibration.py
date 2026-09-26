import copy
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.effect_resources import show_identity
from zen_ma2_agent.operator_api import OpenClawOperatorAdapter, build_operator_status
from zen_ma2_agent.position_application_evidence import (
    PositionApplicationBindingStore,
    PositionEvidenceError,
    derive_position_application_binding,
)
from zen_ma2_agent.position_calibration import (
    build_position_calibration_preview,
    calibration_application_preview,
    verify_calibration_raw_content,
)
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


class ReadyNoWriteClient:
    state = ConnectionState.READY
    authenticated_user = "MM"
    audit_entries = []

    def execute(self, command):
        if command.startswith("List Preset "):
            return "read-only preset identity"
        raise AssertionError(f"Preview must not write: {command}")


def profile():
    value = {
        "resources": {key: {"status": "SUPPORTED"} for key in (
            "groups", "group_membership", "fixtures", "fixture_geometry",
            "fixture_type_profiles", "presets", "sequences",
        )},
        "fixtures": [
            {
                "fixture_id": 101,
                "fixture_type": "2 MOVING",
                "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]},
            },
            {
                "fixture_id": 102,
                "fixture_type": "2 MOVING",
                "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]},
            },
        ],
        "fixture_type_profiles": [{
            "status": "SHOW_BOUND_VERIFIED",
            "fixture_type": {"list_label": "2 MOVING"},
            "capabilities": {"POSITION": {"status": "SHOW_BOUND_VERIFIED"}},
        }],
        "groups": [{
            "group_id": 1,
            "name": "HYBRID",
            "fixture_ids_in_selection_order": [101, 102],
            "fixture_refs_in_selection_order": ["101", "102"],
            "membership": {
                "status": "SUPPORTED",
                "source": "ma2_group_export_xml",
            },
        }],
        "presets": [
            {"reference": "2.1", "preset_type": "POSITION", "name": "HOME"},
            {"reference": "2.2", "preset_type": "POSITION", "name": "CENTER"},
        ],
        "sequences": [{"number": 1, "name": "Foreign"}],
        "effects": [],
    }
    value["show_identity"] = show_identity(value)
    return value


def post_profile(preview):
    value = copy.deepcopy(profile())
    value["presets"].append({
        "reference": preview["preset"]["reference"],
        "preset_type": "POSITION",
        "name": preview["preset"]["label"],
    })
    value["sequences"].append({
        "number": preview["sequence"]["id"],
        "name": preview["sequence"]["label"],
    })
    value["show_identity"] = show_identity(value)
    return value


def discovery(preview):
    raw_rows = []
    for fixture in ("101", "102"):
        for attribute, value in (("PAN", "20"), ("TILT", "30")):
            raw_rows.append({
                "channel": {
                    "fixture_id": fixture,
                    "attribute_name": attribute,
                },
                "raw_values": {"Value": value},
                "preset": None,
            })

    preset_number = preview["preset"]["reference"].split(".", 1)[1]
    preset_rows = []
    for fixture in ("101", "102"):
        for attribute in ("PAN", "TILT"):
            preset_rows.append({
                "channel": {
                    "fixture_id": fixture,
                    "attribute_name": attribute,
                },
                "raw_values": {"Value": "1"},
                "preset": {"no_components": ["1", "2", preset_number]},
            })
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": preview["sequence"]["id"],
        "xml_discovery": {"sha256": "b" * 64},
        "cues": [
            {
                "number": {"number": "1", "sub_number": "0"},
                "parts": [{"index": "0", "cue_data": raw_rows}],
            },
            {
                "number": {"number": "2", "sub_number": "0"},
                "parts": [{"index": "0", "cue_data": preset_rows}],
            },
        ],
    }


class PositionCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.profile = profile()
        self.preview = build_position_calibration_preview(
            self.profile, group_id=1
        )
        self.post = post_profile(self.preview)

    def test_preview_allocates_one_preset_one_sequence_and_two_cues(self):
        self.assertEqual(self.preview["preset"]["reference"], "2.3")
        self.assertEqual(self.preview["preset"]["label"], "ZEN_POSITION_CAL_P3")
        self.assertEqual(self.preview["sequence"]["id"], 2)
        self.assertEqual(self.preview["sequence"]["executor"], None)
        self.assertEqual(
            self.preview["candidate_commands"],
            [
                "ClearAll",
                "Group 1",
                'Attribute "Pan" At 20',
                'Attribute "Tilt" At 30',
                'Store Cue 1 Sequence 2 "RAW_POSITION" Fade 0 /nc',
                "ClearAll",
                "Group 1",
                'Attribute "Pan" At 20',
                'Attribute "Tilt" At 30',
                'Store Preset 2.3 "ZEN_POSITION_CAL_P3" /selective /nc',
                "ClearAll",
                "Group 1",
                "At Preset 2.3",
                'Store Cue 2 Sequence 2 "PRESET_POSITION" Fade 0 /nc',
                'Label Sequence 2 "ZEN_POSITION_CAL_SEQ2" /nc',
                "ClearAll",
            ],
        )
        self.assertEqual(self.preview["ma2_writes"], 0)
        self.assertFalse(self.preview["cleanup_after_verified"])
        self.assertEqual(
            self.preview["expected_postwrite_show_identity"],
            self.post["show_identity"],
        )

    def test_raw_and_preset_application_verify_from_one_export(self):
        exported = discovery(self.preview)
        raw = verify_calibration_raw_content(
            self.post, self.preview, exported
        )
        self.assertEqual(raw["status"], "RAW_POSITION_CUE_CONTENT_VERIFIED")
        self.assertEqual(raw["matched_channel_refs"], ["101", "102"])
        app_preview = calibration_application_preview(
            self.post, self.preview
        )
        binding = derive_position_application_binding(
            self.post, app_preview, exported
        )
        self.assertEqual(binding["status"], "REAL_MACHINE_CONTENT_VERIFIED")
        self.assertEqual(binding["reference"], "2.3")
        self.assertEqual(binding["evidence"]["cue"], 2)
        self.assertEqual(
            binding["evidence"]["observed_attributes_by_ref"],
            {"101.1": ["PAN", "TILT"], "102.1": ["PAN", "TILT"]},
        )

    def test_binding_store_records_calibration_cue_two(self):
        exported = discovery(self.preview)
        app_preview = calibration_application_preview(
            self.post, self.preview
        )
        with tempfile.TemporaryDirectory() as folder:
            store = PositionApplicationBindingStore(Path(folder))
            stored = store.record_after_readback(
                self.post, app_preview, exported
            )
            self.assertEqual(stored["evidence"]["cue"], 2)
            self.assertEqual(store.load_verified(self.post), [stored])

    def test_raw_value_foreign_or_missing_axis_rejects(self):
        for kind in ("wrong_value", "foreign", "missing_tilt"):
            exported = discovery(self.preview)
            rows = exported["cues"][0]["parts"][0]["cue_data"]
            if kind == "wrong_value":
                rows[0]["raw_values"]["Value"] = "21"
            elif kind == "foreign":
                rows.append({
                    "channel": {
                        "fixture_id": "999",
                        "attribute_name": "PAN",
                    },
                    "raw_values": {"Value": "20"},
                })
            else:
                rows[:] = [
                    row for row in rows
                    if not (
                        row["channel"]["fixture_id"] == "101"
                        and row["channel"]["attribute_name"] == "TILT"
                    )
                ]
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                verify_calibration_raw_content(
                    self.post, self.preview, exported
                )

    def test_application_wrong_preset_or_missing_axis_rejects(self):
        for kind in ("wrong_preset", "missing_tilt"):
            exported = discovery(self.preview)
            rows = exported["cues"][1]["parts"][0]["cue_data"]
            if kind == "wrong_preset":
                rows[0]["preset"]["no_components"] = ["2", "99"]
            else:
                rows[:] = [
                    row for row in rows
                    if not (
                        row["channel"]["fixture_id"] == "101"
                        and row["channel"]["attribute_name"] == "TILT"
                    )
                ]
            app_preview = calibration_application_preview(
                self.post, self.preview
            )
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                derive_position_application_binding(
                    self.post, app_preview, exported
                )

    def test_group_capability_and_fixture9999_fail_closed(self):
        for kind in ("capability", "fixture9999"):
            changed = copy.deepcopy(self.profile)
            if kind == "capability":
                changed["fixture_type_profiles"][0]["capabilities"][
                    "POSITION"
                ]["status"] = "UNKNOWN"
            else:
                changed["groups"][0][
                    "fixture_refs_in_selection_order"
                ] = ["9999", "102"]
            with self.subTest(kind=kind), self.assertRaises(PositionEvidenceError):
                build_position_calibration_preview(changed, group_id=1)

    def test_preview_rejects_preset_label_collision(self):
        changed = copy.deepcopy(self.profile)
        changed["presets"].append({
            "reference": "2.9",
            "preset_type": "POSITION",
            "name": "ZEN_POSITION_CAL_P3",
        })
        with self.assertRaisesRegex(PositionEvidenceError, "LABEL_COLLISION"):
            build_position_calibration_preview(changed, group_id=1)


class PositionCalibrationCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="zen-position-calibration-"
        )
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.core = AgentCore(AgentRuntime(root))
        self.core.runtime.client = ReadyNoWriteClient()
        for resource in (
            "groups", "group_membership", "fixtures", "fixture_geometry",
            "fixture_type_profiles", "presets", "sequences",
        ):
            self.core.state.put(resource, [], source="test")
        self.profile = profile()
        self.preview = build_position_calibration_preview(
            self.profile, group_id=1
        )
        self.post = post_profile(self.preview)
        self.expected = {
            "expected_show_fingerprint": self.profile["show_identity"]["value"],
            "group_id": 1,
            "expected_group_name": "HYBRID",
            "expected_exact_refs": ["101", "102"],
        }

    def tearDown(self):
        self.temp.cleanup()

    def register(self):
        with patch.object(
            self.core,
            "_fresh_position_calibration_preview",
            return_value=(self.profile, self.preview),
        ):
            return self.core.preview_position_calibration(**self.expected)

    def test_preview_registers_without_write(self):
        with patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=AssertionError("write"),
        ) as execute:
            action = self.register()["action"]
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual(
            (action["root_state"], action["phase"]),
            ("READY", "PREVIEW"),
        )
        self.assertTrue(action["id"])
        execute.assert_not_called()

    def test_approval_time_drift_fails_before_write(self):
        action = self.register()["action"]
        changed = copy.deepcopy(self.preview)
        changed["sequence"]["id"] += 1
        with patch.object(
            self.core,
            "_fresh_position_calibration_preview",
            return_value=(self.profile, changed),
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=AssertionError("write"),
        ) as execute:
            with self.assertRaisesRegex(
                PositionEvidenceError, "STALE_APPROVED_PREVIEW"
            ):
                self.core.approve_action(action["id"])
        execute.assert_not_called()

    def test_created_preset_identity_gate_blocks_phase_b(self):
        action = self.register()["action"]
        record = self.core.actions[action["id"]]
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["Executing : OK"]

        with patch.object(
            self.core.runtime, "execute_approved_commands", side_effect=execute
        ), patch(
            "zen_ma2_agent.core.PresetProvider.parse", return_value=[]
        ):
            with self.assertRaisesRegex(
                PositionEvidenceError, "CREATED_PRESET_IDENTITY_UNVERIFIED"
            ):
                self.core._execute_position_calibration(record)

        self.assertEqual(
            sent[:10], self.preview["candidate_commands"][:10]
        )
        self.assertNotIn(
            f"At Preset {self.preview['preset']['reference']}", sent
        )
        self.assertEqual(sent[-1], "ClearAll")

    def test_execution_uses_one_export_and_records_binding(self):
        action = self.register()["action"]
        record = self.core.actions[action["id"]]
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["Executing : OK"]

        direct = [{
            "reference": self.preview["preset"]["reference"],
            "preset_type": "POSITION",
            "name": self.preview["preset"]["label"],
        }]
        exported = discovery(self.preview)
        with patch.object(
            self.core.runtime, "execute_approved_commands", side_effect=execute
        ), patch(
            "zen_ma2_agent.core.PresetProvider.parse", return_value=direct
        ), patch.object(
            self.core, "verify_first_song_metadata", return_value="VERIFIED"
        ), patch.object(
            self.core.sequence_export_provider,
            "export_and_discover",
            return_value=exported,
        ) as export_call, patch.object(
            self.core,
            "_fresh_position_raw_profile",
            return_value=post_profile(self.preview),
        ):
            result = self.core._execute_position_calibration(record)

        self.assertIn("RAW_POSITION_CUE_CONTENT_VERIFIED", result)
        self.assertIn("REAL_MACHINE_CONTENT_VERIFIED", result)
        self.assertEqual(sent, self.preview["candidate_commands"])
        export_call.assert_called_once()
        self.assertTrue(
            self.core.position_application_bindings.has_candidates()
        )
        self.assertFalse(any(command.startswith("Delete ") for command in sent))

    def test_operator_route_is_preview_only(self):
        calls = []
        adapter = OpenClawOperatorAdapter(
            lambda: build_operator_status(field_core_available=True),
            position_calibration_preview_handler=(
                lambda **kwargs: calls.append(kwargs)
                or {"action": {"status": "PENDING_APPROVAL"}}
            ),
        )
        result = adapter.invoke(
            "zen.position.calibration.preview", self.expected
        )
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(calls, [self.expected])
        rejected = adapter.invoke(
            "zen.position.calibration.preview", {"group_id": 1}
        )
        self.assertEqual(rejected["status"], "REJECTED")

    def test_approved_transaction_verifies_both_proofs_and_records_binding(self):
        action = self.register()["action"]
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["OK" for _ in commands]

        direct = [{
            "reference": self.preview["preset"]["reference"],
            "preset_type": "POSITION",
            "name": self.preview["preset"]["label"],
        }]
        exported = discovery(self.preview)
        with patch.object(
            self.core,
            "_fresh_position_calibration_preview",
            return_value=(self.profile, self.preview),
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=execute,
        ), patch(
            "zen_ma2_agent.core.PresetProvider.parse",
            return_value=direct,
        ), patch.object(
            self.core, "verify_first_song_metadata",
        ), patch.object(
            self.core.sequence_export_provider,
            "export_and_discover",
            return_value=exported,
        ), patch.object(
            self.core,
            "_fresh_position_raw_profile",
            return_value=self.post,
        ):
            result = self.core.approve_action(action["id"])

        self.assertEqual(result["status"], "EXECUTED")
        self.assertIn("RAW_POSITION_CUE_CONTENT_VERIFIED", result["result"])
        self.assertIn("REAL_MACHINE_CONTENT_VERIFIED", result["result"])
        self.assertEqual(sent, self.preview["candidate_commands"])
        self.assertTrue(self.core.position_application_bindings.has_candidates())
        stored = self.core.position_application_bindings.load_verified(self.post)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["evidence"]["cue"], 2)

    def test_created_preset_identity_must_verify_before_preset_call(self):
        action = self.register()["action"]
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["OK" for _ in commands]

        with patch.object(
            self.core,
            "_fresh_position_calibration_preview",
            return_value=(self.profile, self.preview),
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=execute,
        ), patch(
            "zen_ma2_agent.core.PresetProvider.parse",
            return_value=[],
        ):
            with self.assertRaisesRegex(
                PositionEvidenceError,
                "CREATED_PRESET_IDENTITY_UNVERIFIED",
            ):
                self.core.approve_action(action["id"])

        self.assertNotIn(
            f'At Preset {self.preview["preset"]["reference"]}',
            sent,
        )
        self.assertEqual(sent[:10], self.preview["candidate_commands"][:10])
        self.assertEqual(sent[-1], "ClearAll")
        self.assertFalse(self.core.position_application_bindings.has_candidates())


if __name__ == "__main__":
    unittest.main()
