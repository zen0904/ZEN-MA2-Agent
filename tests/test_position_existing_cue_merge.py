import copy
import tempfile
import unittest
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.position_existing_cue_merge import (
    ExistingPositionMergeError,
    build_existing_position_merge_preview,
    commands_from_preview,
    verify_existing_position_merge,
)


def profile(refs=None):
    refs = refs or ["101.1", "102.1"]
    value = {
        "show_identity": {
            "kind": "SCANNED_SHOW_PROFILE_FINGERPRINT",
            "value": "1" * 64,
        },
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
        ],        "fixture_type_profiles": [{
            "status": "SHOW_BOUND_VERIFIED",
            "fixture_type": {"list_label": "2 MOVING"},
            "capabilities": {
                "POSITION": {"status": "SHOW_BOUND_VERIFIED"},
            },
            "channels": [
                {
                    "attribute": "PAN",
                    "functions": [{"from": "-315", "to": "315"}],
                },
                {
                    "attribute": "TILT",
                    "functions": [{"from": "-135", "to": "135"}],
                },
            ],
        }],
        "groups": [{
            "group_id": 1,
            "name": "HYBRID",
            "fixture_refs_in_selection_order": refs,
            "membership": {
                "status": "SUPPORTED",
                "source": "ma2_group_export_xml",
            },
        }],
        "sequences": [{"number": 302, "name": "ZEN_SEQ302"}],
    }
    return value

def binding(refs=None):
    refs = refs or ["101.1", "102.1"]
    return {
        "status": "REAL_MACHINE_CONTENT_VERIFIED",
        "show_identity": profile(refs)["show_identity"],
        "group_id": 1,
        "fixture_refs": sorted(refs),
        "reference": "2.13",
        "preset_label": "ZEN_POSITION_CAL_P13",
        "evidence": {
            "sequence": 12,
            "cue": 2,
            "sequence_export_sha256": "a" * 64,
        },
    }


def row(fixture, attribute, value, *, subfixture="1", preset=None):
    result = {
        "channel": {
            "fixture_id": str(fixture),
            "subfixture_id": subfixture,
            "attribute_name": attribute,
        },
        "raw_values": {"Value": str(value)},
        "preset": None,
    }
    if preset is not None:
        result["preset"] = {"no_components": ["1", "2", str(preset)]}
    return result

def cue(number, label, rows):
    return {
        "number": {"number": str(number), "sub_number": "0"},
        "parts": [{"index": "0", "name": label, "cue_data": rows}],
    }


def calibration_discovery(refs=None):
    refs = refs or ["101.1", "102.1"]
    roots = [item.split(".", 1)[0] for item in refs]
    raw_rows = [
        row(root, attr, value)
        for root in roots
        for attr, value in (("PAN", 20), ("TILT", 30))
    ]
    linked_rows = [
        row(root, attr, 1, preset=13)
        for root in roots
        for attr in ("PAN", "TILT")
    ]
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": 12,
        "xml_discovery": {"sha256": "b" * 64},
        "cues": [
            cue(1, "RAW_POSITION", raw_rows),
            cue(2, "PRESET_POSITION", linked_rows),
        ],
    }

LABELS = [
    "DEEP BLUE CUT",
    "AMBER ACCENT",
    "ASCENT",
    "WHITE HIT",
]


def target_discovery(*, with_position=None):
    cues = []
    for number, label in enumerate(LABELS, 1):
        rows = [
            row("900", "DIM", 100, subfixture=None),
            row("901", "COLORRGB1", 50, subfixture=None),
        ]
        if with_position is not None:
            for fixture in with_position[number - 1]["fixtures"]:
                root, _, sub = fixture["fixture_ref"].partition(".")
                rows.extend([
                    row(root, "PAN", fixture["pan"], subfixture=sub or None),
                    row(root, "TILT", fixture["tilt"], subfixture=sub or None),
                ])
        cues.append(cue(number, label, rows))
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "status": "VERIFIED",
        "sequence_no": 302,
        "xml_discovery": {"sha256": "c" * 64},
        "cues": cues,
    }

def cue_metadata():
    return [
        {"number": index, "name": label, "fade": 0.5, "delay": 0.0}
        for index, label in enumerate(LABELS, 1)
    ]


def build(**kwargs):
    return build_existing_position_merge_preview(
        kwargs.pop("profile", profile()),
        target_discovery=kwargs.pop("target", target_discovery()),
        calibration_discovery=kwargs.pop("calibration", calibration_discovery()),
        binding=kwargs.pop("binding_row", binding()),
        sequence_no=302,
        group_id=1,
        cue_start=1,
        cue_end=4,
        executor_assignments=[{
            "page": 2,
            "executor": 8,
            "location": "2.8",
            "label": "ZEN_SEQ302",
        }],
        cue_metadata=kwargs.pop("metadata", cue_metadata()),
        **kwargs,
    )


class ExistingCuePositionMergeTests(unittest.TestCase):
    def test_preview_preserves_exact_subfixture_refs_and_direction_semantics(self):
        preview = build()
        self.assertEqual(preview["group"]["exact_refs"], ["101.1", "102.1"])
        self.assertEqual(preview["baseline"]["values_by_fixture"]["101.1"], {"pan": 20.0, "tilt": 30.0})
        self.assertEqual(preview["cue_updates"][0]["pattern"], "LEFT")
        self.assertTrue(all(row["delta_pan"] > 0 for row in preview["cue_updates"][0]["fixtures"]))
        self.assertEqual(preview["cue_updates"][1]["pattern"], "RIGHT")
        self.assertTrue(all(row["delta_pan"] < 0 for row in preview["cue_updates"][1]["fixtures"]))
        self.assertEqual(preview["cue_updates"][2]["pattern"], "UPSTAGE")
        self.assertTrue(all(row["delta_tilt"] > 0 for row in preview["cue_updates"][2]["fixtures"]))
        self.assertEqual(preview["cue_updates"][3]["pattern"], "ALTERNATE")

    def test_commands_are_position_only_merge_and_never_create_or_assign(self):
        commands = commands_from_preview(build())
        joined = "\n".join(commands)
        self.assertIn("Fixture 101.1", joined)
        self.assertIn('Attribute "Pan" At ', joined)
        self.assertIn('Attribute "Tilt" At ', joined)
        self.assertIn("Store Cue 1 Sequence 302 /merge /cueonly /nc", joined)
        self.assertNotIn("Sequence 303", joined)
        self.assertNotIn("Assign ", joined)
        self.assertNotIn("Label ", joined)
        self.assertNotIn("Fade ", joined)
        self.assertNotIn("Dimmer", joined)
        self.assertNotIn("Color", joined)

    def test_foreign_sequence_is_rejected(self):
        changed = profile()
        changed["sequences"][0]["name"] = "FOREIGN_SEQ302"
        with self.assertRaisesRegex(ExistingPositionMergeError, "NOT_AGENT_OWNED"):
            build(profile=changed)

    def test_missing_existing_cue_is_rejected(self):
        changed = target_discovery()
        changed["cues"] = changed["cues"][:-1]
        with self.assertRaisesRegex(ExistingPositionMergeError, "CUE_RANGE_INCOMPLETE"):
            build(target=changed)

    def test_baseline_must_have_verified_raw_and_linked_axes(self):
        changed = calibration_discovery()
        changed["cues"][0]["parts"][0]["cue_data"] = [
            item for item in changed["cues"][0]["parts"][0]["cue_data"]
            if not (
                item["channel"]["fixture_id"] == "101"
                and item["channel"]["attribute_name"] == "TILT"
            )
        ]
        with self.assertRaisesRegex(ExistingPositionMergeError, "BASELINE_INCOMPLETE"):
            build(calibration=changed)

        changed = calibration_discovery()
        changed["cues"][1]["parts"][0]["cue_data"] = [
            item for item in changed["cues"][1]["parts"][0]["cue_data"]
            if not (
                item["channel"]["fixture_id"] == "101"
                and item["channel"]["attribute_name"] == "TILT"
            )
        ]
        with self.assertRaisesRegex(ExistingPositionMergeError, "PRESET_LINK_INCOMPLETE"):
            build(calibration=changed)

    def test_fixture_natural_range_is_enforced(self):
        changed = profile()
        changed["fixture_type_profiles"][0]["channels"][0]["functions"][0] = {
            "from": "-10", "to": "10"
        }
        with self.assertRaisesRegex(ExistingPositionMergeError, "BASELINE_OUTSIDE_FIXTURE_RANGE"):
            build(profile=changed)

    def test_fixture9999_and_ambiguous_multi_instance_parent_fail_closed(self):
        changed = profile(["9999", "102.1"])
        with self.assertRaises(Exception):
            build(profile=changed, binding_row=binding(["9999", "102.1"]))

        changed = profile(["101", "102.1"])
        changed["fixtures"][0]["stage_geometry"]["subfixtures"] = [
            {"subfixture_id": 1},
            {"subfixture_id": 2},
        ]
        with self.assertRaisesRegex(Exception, "MULTI_INSTANCE"):
            build(profile=changed, binding_row=binding(["101", "102.1"]))

    def test_metadata_is_required_and_label_matched(self):
        with self.assertRaisesRegex(ExistingPositionMergeError, "METADATA_INCOMPLETE"):
            build(metadata=[])
        changed = cue_metadata()
        changed[0]["name"] = "CHANGED"
        with self.assertRaisesRegex(ExistingPositionMergeError, "METADATA_LABEL_MISMATCH"):
            build(metadata=changed)

    def test_post_write_exact_position_and_nonposition_content_verify(self):
        preview = build()
        post = target_discovery(with_position=preview["cue_updates"])
        verified = verify_existing_position_merge(preview, post)
        self.assertEqual(verified["status"], "VERIFIED")
        self.assertEqual(verified["position_value_matches"], 16)
        self.assertEqual(verified["non_position_content"], "UNCHANGED")

    def test_post_write_parent_rows_canonicalize_only_when_unambiguous(self):
        preview = build()
        post = target_discovery(with_position=preview["cue_updates"])
        for cue_row in post["cues"]:
            for item in cue_row["parts"][0]["cue_data"]:
                if item["channel"]["attribute_name"] in {"PAN", "TILT"}:
                    item["channel"].pop("subfixture_id", None)
        verified = verify_existing_position_merge(preview, post)
        self.assertEqual(verified["position_value_matches"], 16)

    def test_nonposition_or_label_drift_fails(self):
        preview = build()
        post = target_discovery(with_position=preview["cue_updates"])
        post["cues"][0]["parts"][0]["cue_data"][0]["raw_values"]["Value"] = "99"
        with self.assertRaisesRegex(ExistingPositionMergeError, "NON_POSITION_CONTENT_CHANGED"):
            verify_existing_position_merge(preview, post)

        post = target_discovery(with_position=preview["cue_updates"])
        post["cues"][0]["parts"][0]["name"] = "RENAMED"
        with self.assertRaises(ExistingPositionMergeError):
            verify_existing_position_merge(preview, post)

    def test_post_position_value_mismatch_fails(self):
        preview = build()
        post = target_discovery(with_position=preview["cue_updates"])
        rows = post["cues"][0]["parts"][0]["cue_data"]
        pan = next(item for item in rows if item["channel"]["attribute_name"] == "PAN")
        pan["raw_values"]["Value"] = str(float(pan["raw_values"]["Value"]) + 1)
        with self.assertRaisesRegex(ExistingPositionMergeError, "POST_VALUE_MISMATCH"):
            verify_existing_position_merge(preview, post)


class ReadyClient:
    state = ConnectionState.READY
    authenticated_user = "MM"
    audit_entries = []

    def execute(self, command):
        raise AssertionError(f"unexpected direct transport: {command}")


class ExistingCuePositionMergeCoreTests(unittest.TestCase):
    request = (
        "只更新 Position 既有 Sequence 302 Group 1 Preset 2.13 "
        "Cues 1-4 Executor 2.8"
    )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-existing-position-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.core = AgentCore(AgentRuntime(root))
        self.core.runtime.client = ReadyClient()
        for resource in (
            "groups", "group_membership", "fixtures", "fixture_geometry",
            "fixture_type_profiles", "presets", "sequences", "executors",
        ):
            self.core.state.put(resource, [], source="test")
        self.preview = build()
    def tearDown(self):
        self.temp.cleanup()

    def child(self):
        return self.core.skills.plan_intent(
            Intent(
                "merge_existing_cue_position",
                {"position_merge_preview": self.preview},
                self.request,
            ),
            self.core.state,
            self.core.runtime.preferences,
        )

    def register(self):
        with patch.object(
            self.core,
            "_plan_existing_position_merge_child",
            return_value=self.child(),
        ), patch.object(
            self.core,
            "_plan_lean_design_child",
            side_effect=AssertionError("generic provider path must not run"),
        ):
            return self.core.program_show_request(self.request)["action"]

    def test_explicit_parser_requires_existing_position_only_scope(self):
        spec = self.core._parse_existing_position_merge_request(self.request)
        self.assertEqual(spec, {
            "sequence_no": 302,
            "group_id": 1,
            "preset_ref": "2.13",
            "cue_start": 1,
            "cue_end": 4,
            "expected_executor": "2.8",
        })
        self.assertIsNone(
            self.core._parse_existing_position_merge_request(
                "Design Position for Sequence 302 Group 1 Preset 2.13 Cues 1-4"
            )
        )
    def test_root_routes_explicit_existing_merge_without_generic_provider(self):
        action = self.register()
        self.assertEqual(action["task"]["skill_id"], "show.program")
        self.assertEqual(
            action["skill_graph"][-1]["skill_id"],
            "position.existing_cue_merge",
        )
        child = action["continuation_context"]["child_execution"]
        self.assertEqual(child["intent_kind"], "merge_existing_cue_position")
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertIn("P=26", action["preview_note"])
        self.assertIn("T=30", action["preview_note"])

    def test_approval_time_stale_preview_blocks_before_write(self):
        action = self.register()
        changed = copy.deepcopy(self.preview)
        changed["target_sequence"]["pre_non_position_sha256"] = "9" * 64
        with patch.object(
            self.core,
            "_fresh_existing_position_merge_preview",
            return_value=(profile(), changed),
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=AssertionError("write"),
        ) as execute:
            with self.assertRaisesRegex(
                ExistingPositionMergeError,
                "STALE_APPROVED_PREVIEW",
            ):
                self.core.approve_action(action["id"])
        execute.assert_not_called()
    def test_approved_root_executes_special_verifier_and_finishes_done(self):
        action = self.register()
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["Executing : OK"]

        post = target_discovery(with_position=self.preview["cue_updates"])
        with patch.object(
            self.core,
            "_ensure_existing_position_merge_state_unchanged",
            return_value=self.preview,
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=execute,
        ), patch.object(
            self.core.sequence_export_provider,
            "export_and_discover",
            return_value=post,
        ), patch.object(
            self.core,
            "_fresh_existing_cue_metadata",
            return_value=cue_metadata(),
        ), patch.object(
            self.core,
            "_fresh_position_poc_profile",
            return_value=profile(),
        ), patch.object(
            self.core,
            "_sequence_executor_assignments",
            return_value=[{
                "page": 2,
                "executor": 8,
                "location": "2.8",
                "label": "ZEN_SEQ302",
            }],
        ):
            result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertIn("POSITION_MERGE VERIFIED", result["result"])
        self.assertIn("Cue labels/Fade/Delay", result["result"])
        self.assertEqual(sent[-1], "ClearAll")
        self.assertFalse(any(command.startswith("Delete ") for command in sent))
        self.assertFalse(any("Sequence 303" in command for command in sent))
        self.assertEqual(self.core.root_workflow_status()["phase"], "DONE")

    def test_executor_drift_fails_closed_and_still_clears_programmer(self):
        action = self.register()
        sent = []

        def execute(commands):
            sent.extend(commands)
            return ["OK"]

        post = target_discovery(with_position=self.preview["cue_updates"])
        with patch.object(
            self.core,
            "_ensure_existing_position_merge_state_unchanged",
            return_value=self.preview,
        ), patch.object(
            self.core.runtime,
            "execute_approved_commands",
            side_effect=execute,
        ), patch.object(
            self.core.sequence_export_provider,
            "export_and_discover",
            return_value=post,
        ), patch.object(
            self.core,
            "_fresh_existing_cue_metadata",
            return_value=cue_metadata(),
        ), patch.object(
            self.core,
            "_fresh_position_poc_profile",
            return_value=profile(),
        ), patch.object(
            self.core,
            "_sequence_executor_assignments",
            return_value=[],
        ):
            with self.assertRaisesRegex(
                ExistingPositionMergeError,
                "EXECUTOR_ASSIGNMENT_CHANGED",
            ):
                self.core.approve_action(action["id"])

        self.assertEqual(sent[-1], "ClearAll")
        self.assertFalse(any(command.startswith("Delete ") for command in sent))


if __name__ == "__main__":
    unittest.main()
