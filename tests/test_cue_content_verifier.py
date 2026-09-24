import unittest
from pathlib import Path

from zen_ma2_agent.builder import FirstSongBuildError, ShowPlanBuilder
from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.cue_content_verifier import verify_cue_content
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers import GroupMembershipProviderUnavailable


SHA = "a" * 64


def row(fixture, *, attribute="DIM", value=None, preset=None, effect=None):
    return {
        "channel": {"fixture_id": str(fixture), "attribute_name": attribute},
        "raw_values": {"Value": None if value is None else str(value)},
        "preset": preset,
        "effect": effect,
    }


def discovery(rows, *, cue_no=1, include_system=True):
    cues = []
    if include_system:
        cues.append({"number": None, "parts": [{"index": "0", "name": None, "cue_data": []}]})
    cues.append({
        "number": {"number": str(cue_no), "sub_number": "0"},
        "parts": [{"index": "0", "name": "CUE", "cue_data": rows}],
    })
    return {
        "schema": "zen.sequence_export_discovery.v0.1",
        "read_only": True,
        "sequence_no": 5,
        "status": "PARTIAL" if include_system else "VERIFIED",
        "source": "MA2_EXPORT_SEQUENCE_XML",
        "cues": cues,
        "xml_discovery": {"sha256": SHA, "root": "MA"},
    }


def plan(actions):
    return {
        "cues": [{
            "cue_number": 1,
            "label": "CUE",
            "fade": 0,
            "actions": actions,
        }]
    }


def target(group=1):
    return {"type": "group", "ref": group}


class FakeGroupProvider:
    def __init__(self, fixtures=(101, 102)):
        self.fixtures = list(fixtures)
        self.calls = []

    def get_group_membership(self, runtime, group_no, settings):
        self.calls.append(group_no)
        return {"group_no": group_no, "fixtures": list(self.fixtures), "source": "fake"}


class FakeSequenceProvider:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def export_and_discover(self, runtime, sequence_no, settings, *, retain_export=False):
        self.calls.append((sequence_no, retain_export))
        return self.result


class UnavailableSequenceProvider:
    def __init__(self):
        self.calls = 0

    def export_and_discover(self, runtime, sequence_no, settings, *, retain_export=False):
        self.calls += 1
        raise GroupMembershipProviderUnavailable("REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM")


class CueContentVerifierTests(unittest.TestCase):
    def test_numbered_cue_actions_verify_and_system_cue_is_reported(self):
        rows = []
        for fixture in (101, 102):
            rows.extend([
                row(fixture, value="50.0"),
                row(
                    fixture,
                    attribute="COLORRGB1",
                    preset={"no_components": ["1", "4", "109"], "name": "DIFFERENT DISPLAY"},
                ),
                row(
                    fixture,
                    effect={"no_components": ["1", "2500"], "name": "IGNORED NAME"},
                ),
            ])
        report = verify_cue_content(
            plan([
                {"operation": "SET_DIMMER", "target": target(), "level": 50},
                {"operation": "CALL_PRESET", "target": target(), "preset_ref": "4.109"},
                {"operation": "CALL_EFFECT", "target": target(), "effect_ref": {"id": 2500, "label": "FX"}},
            ]),
            discovery(rows),
            {1: [101, 102]},
        )
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(report["unnumbered_system_cues"], 1)
        self.assertEqual(report["source_xml_sha256"], SHA)
        self.assertTrue(all(item["status"] == "VERIFIED" for item in report["cues"][0]["actions"]))

    def test_dimmer_requires_every_group_member(self):
        report = verify_cue_content(
            plan([{"operation": "SET_DIMMER", "target": target(), "level": 50}]),
            discovery([row(101, value=50)]),
            {1: [101, 102]},
        )
        action = report["cues"][0]["actions"][0]
        self.assertEqual(report["status"], "MISMATCH")
        self.assertEqual(action["reason"], "DIM_VALUE_MISMATCH_OR_ABSENT")
        self.assertEqual(action["missing_fixtures"], [102])

    def test_wrong_raw_dimmer_value_is_mismatch(self):
        report = verify_cue_content(
            plan([{"operation": "SET_DIMMER", "target": target(), "level": 50}]),
            discovery([row(101, value=20), row(102, value=50)]),
            {1: [101, 102]},
        )
        self.assertEqual(report["status"], "MISMATCH")
        self.assertEqual(report["cues"][0]["actions"][0]["missing_fixtures"], [101])

    def test_preset_uses_no_component_suffix_not_display_name(self):
        rows = [
            row(101, attribute="COLORRGB1", preset={"no_components": ["1", "4", "109"], "name": "WRONG NAME"}),
            row(102, attribute="COLORRGB1", preset={"no_components": ["8", "4", "109"], "name": "ANOTHER NAME"}),
        ]
        report = verify_cue_content(
            plan([{"operation": "CALL_PRESET", "target": target(), "preset_ref": "4.109"}]),
            discovery(rows),
            {1: [101, 102]},
        )
        action = report["cues"][0]["actions"][0]
        self.assertEqual(action["status"], "VERIFIED")
        self.assertIn("labels/display text are not identity evidence", action["claim_scope"])

    def test_preset_name_without_no_components_does_not_verify(self):
        report = verify_cue_content(
            plan([{"operation": "CALL_PRESET", "target": target(), "preset_ref": "4.109"}]),
            discovery([
                row(101, attribute="COLORRGB1", preset={"name": "ZEN_COLOR_09_INDIGO 4.109"}),
                row(102, attribute="COLORRGB1", preset={"name": "ZEN_COLOR_09_INDIGO 4.109"}),
            ]),
            {1: [101, 102]},
        )
        self.assertEqual(report["status"], "MISMATCH")

    def test_effect_requires_exported_effect_identity_for_every_member(self):
        verified = verify_cue_content(
            plan([{"operation": "CALL_EFFECT", "target": target(), "effect_ref": {"id": 2500, "label": "FX"}}]),
            discovery([
                row(101, effect={"no_components": ["1", "2500"]}),
                row(102, effect={"no_components": ["1", "2500"]}),
            ]),
            {1: [101, 102]},
        )
        self.assertEqual(verified["status"], "VERIFIED")

        absent = verify_cue_content(
            plan([{"operation": "CALL_EFFECT", "target": target(), "effect_ref": {"id": 2500, "label": "FX"}}]),
            discovery([row(101, value=20), row(102, value=20)]),
            {1: [101, 102]},
        )
        self.assertEqual(absent["status"], "MISMATCH")
        self.assertEqual(
            absent["cues"][0]["actions"][0]["reason"],
            "EFFECT_IDENTITY_MISMATCH_OR_ABSENT",
        )

    def test_unknown_approved_action_fails_closed(self):
        report = verify_cue_content(
            plan([{"operation": "UNKNOWN", "target": target()}]),
            discovery([row(101, value=50), row(102, value=50)]),
            {1: [101, 102]},
        )
        self.assertEqual(report["status"], "MISMATCH")
        self.assertEqual(report["cues"][0]["actions"][0]["reason"], "UNSUPPORTED_APPROVED_ACTION")


class CoreCueContentIntegrationTests(unittest.TestCase):
    def data(self):
        return {
            "sequence": 5,
            "cues": [{
                "cue_number": 1,
                "label": "CUE",
                "fade": 0,
                "actions": [{"operation": "SET_DIMMER", "target": target(), "level": 50}],
            }],
        }

    def test_injected_content_provider_can_verify_without_real_export(self):
        seq = FakeSequenceProvider(discovery([row(101, value=50), row(102, value=50)]))
        groups = FakeGroupProvider()
        core = AgentCore(
            AgentRuntime(Path(".")),
            group_membership_provider=groups,
            sequence_export_provider=seq,
        )
        message, report = core._verify_first_song_cue_content(self.data())
        self.assertIn("Cue-content verification: VERIFIED", message)
        self.assertEqual(report["status"], "VERIFIED")
        self.assertEqual(seq.calls, [(5, True)])
        self.assertEqual(groups.calls, [1])

    def test_unavailable_provider_degrades_to_partial(self):
        seq = UnavailableSequenceProvider()
        core = AgentCore(
            AgentRuntime(Path(".")),
            group_membership_provider=FakeGroupProvider(),
            sequence_export_provider=seq,
        )
        message, report = core._verify_first_song_cue_content(self.data())
        self.assertIn("Verification: PARTIAL", message)
        self.assertIsNone(report)
        self.assertEqual(seq.calls, 1)

    def test_content_mismatch_fails_postwrite_helper(self):
        seq = FakeSequenceProvider(discovery([row(101, value=20), row(102, value=50)]))
        core = AgentCore(
            AgentRuntime(Path(".")),
            group_membership_provider=FakeGroupProvider(),
            sequence_export_provider=seq,
        )
        with self.assertRaisesRegex(FirstSongBuildError, "Cue-content verification mismatch"):
            core._verify_first_song_cue_content(self.data())

    def test_planning_does_not_call_sequence_export_provider(self):
        seq = FakeSequenceProvider(discovery([]))
        core = AgentCore(AgentRuntime(Path(".")), sequence_export_provider=seq)
        workflow = ShowPlanBuilder().build_first_song(
            {
                "schema": "zen.show_plan.v0.1",
                "song": "TEST",
                "active_sequence_range": [301, 400],
                "cues": [{
                    "id": "c1",
                    "cue_number": 1,
                    "label": "CUE",
                    "fade": 0,
                    "actions": [{"operation": "SET_DIMMER", "target": target(), "level": 50}],
                }],
            },
            {"groups": [{"group_id": 1, "name": "KEY"}], "presets": [], "effects": [], "sequences": []},
        )
        self.assertTrue(workflow.executable)
        self.assertEqual(seq.calls, [])


if __name__ == "__main__":
    unittest.main()
