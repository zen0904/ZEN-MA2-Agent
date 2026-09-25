import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.designer.artistic_plan import ArtisticPlanCompileError
from zen_ma2_agent.designer.lean_provider import (
    attach_verified_effect_identity_labels,
    build_provider_resource_contract,
    compile_lean_artistic_intent,
)
from zen_ma2_agent.runtime import AgentRuntime


class FakeDesignProvider:
    def __init__(self, output=None):
        self.calls = []
        self.output = output or {
            "cues": [
                {"label": "OPEN", "fade": 0, "actions": [{"group": 1, "dimmer": 40}]},
                {"label": "DROP", "fade": 1, "actions": [{"group": 1, "dimmer": 90}]},
            ]
        }

    def design(self, request, context):
        self.calls.append((request, context))
        return self.output


def resource_map(dimmer_status="SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL"):
    return {
        "groups": [{
            "group_id": 1,
            "name": "KEY",
            "dimensions": {"DIMMER": {"execution_status": dimmer_status}},
            "preset_resources": [],
            "effect_resources": [],
        }],
        "unbound_presets": [],
        "rules": {
            "group_name_implies_capability": False,
            "preset_type_implies_group_applicability": False,
            "effect_id_implies_artistic_verification": False,
            "unsupported_dimensions_are_substituted": False,
        },
    }


def seed_native_state(core):
    for resource, values in {
        "groups": [{"number": 1, "name": "KEY"}],
        "fixtures": [{"number": 1, "name": "LED 1", "fixture_type": "LED"}],
        "group_membership": [{"group_no": 1, "fixtures": [1], "source": "fake"}],
        "presets": [],
        "effects": [],
        "sequences": [],
        "executors": [],
        "fixture_type_profiles": [],
    }.items():
        core.state.put(resource, values, source="fake")


class LeanRootProviderTests(unittest.TestCase):
    def test_no_provider_preserves_needs_intelligence_and_zero_calls(self):
        core = AgentCore(AgentRuntime(Path(".")))
        action = core.program_show_request("design/program this song")["action"]
        self.assertEqual(action["root_state"], "NEEDS_INTELLIGENCE")
        self.assertFalse(action["executable"])

    def test_provider_gets_exactly_one_compact_call_and_builder_is_composed(self):
        provider = FakeDesignProvider()
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        seed_native_state(core)
        with patch("zen_ma2_agent.core.build_artistic_resource_map", return_value=resource_map()):
            action = core.program_show_request("design/program this song")["action"]

        self.assertEqual(len(provider.calls), 1)
        request, context = provider.calls[0]
        self.assertEqual(request, "design/program this song")
        self.assertIn("verified_resource_contract", context)
        self.assertNotIn("command", context)
        self.assertNotIn("telnet", str(context).lower())
        self.assertEqual(action["skill_graph"][-1]["skill_id"], "show.builder")
        self.assertTrue(action["executable"])
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertIsNotNone(action["id"])
        self.assertEqual(core.runtime.client, None)

    def test_root_lean_path_threads_bounded_show_bindings_into_resource_map(self):
        provider = FakeDesignProvider()
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        seed_native_state(core)
        preset_bindings = [{"status": "SHOW_BOUND_VERIFIED", "group_id": 1, "reference": "4.101"}]
        dimmer_bindings = [{"status": "SHOW_BOUND_VERIFIED", "group_id": 1, "capability": "DIMMER"}]

        with patch.object(
            core,
            "_recover_bounded_test_show_evidence",
            return_value=(preset_bindings, dimmer_bindings),
        ), patch.object(
            core,
            "_recover_bounded_template_effect_inventory",
            return_value=[],
        ), patch(
            "zen_ma2_agent.core.build_artistic_resource_map",
            return_value=resource_map(),
        ) as build_map:
            action = core.program_show_request("design/program this song")["action"]

        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual(build_map.call_args.kwargs["preset_bindings"], preset_bindings)
        self.assertEqual(build_map.call_args.kwargs["dimmer_bindings"], dimmer_bindings)

    def test_root_lean_path_threads_only_direct_readback_matching_position_binding(self):
        provider = FakeDesignProvider()
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        seed_native_state(core)
        verified = {"reference": "2.1", "preset_label": "HOME", "preset_type": "POSITION"}
        stale = {"reference": "2.2", "preset_label": "OLD", "preset_type": "POSITION"}
        with patch.object(core, "_recover_bounded_test_show_evidence", return_value=([], [])), \
             patch.object(core, "_recover_bounded_template_effect_inventory", return_value=[]), \
             patch.object(core.position_application_bindings, "load_verified", return_value=[verified, stale]), \
             patch.object(core.runtime, "read_state", side_effect=lambda command:
                          "Position 2.1 2.1 HOME Normal" if command.endswith("2.1")
                          else "Position 2.2 2.2 CHANGED Normal"), \
             patch("zen_ma2_agent.core.build_artistic_resource_map", return_value=resource_map()) as build_map:
            action = core.program_show_request("design/program this song")["action"]
        self.assertEqual(action["status"], "PENDING_APPROVAL")
        self.assertEqual(build_map.call_args.kwargs["preset_bindings"], [verified])

    def test_bounded_show_recovery_fails_closed_without_matching_current_show(self):
        core = AgentCore(AgentRuntime(Path(".")))
        seed_native_state(core)
        profile = core.scan_show_profile()
        preset_bindings, dimmer_bindings = core._recover_bounded_test_show_evidence(profile)
        self.assertEqual(preset_bindings, [])
        self.assertEqual(dimmer_bindings, [])

    def test_bounded_template_effect_recovery_promotes_only_verified_template(self):
        core = AgentCore(AgentRuntime(Path(".")))
        core.runtime.client = type("Client", (), {
            "state": __import__("zen_ma2_agent.telnet_client", fromlist=["ConnectionState"]).ConnectionState.READY,
            "execute": lambda self, command: "Effect 1.2500.1\nQTY=None\n",
        })()
        profile = {
            "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "x", "confidence": "PARTIAL"},
            "effects": [
                {"effect_id": 2500, "name": "FX_DIM_CHASE_SLOW"},
                {"effect_id": 9999, "name": "SOME_OTHER_EFFECT"},
            ],
        }
        evidence = core._recover_bounded_template_effect_inventory(profile)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(profile["effects"][0]["kind"], "TEMPLATE")
        self.assertNotIn("kind", profile["effects"][1])

    def test_provider_failure_becomes_resumable_root_state_without_retry(self):
        class FailingProvider:
            def __init__(self):
                self.calls = 0

            def design(self, request, context):
                self.calls += 1
                raise RuntimeError("provider unavailable")

        provider = FailingProvider()
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        seed_native_state(core)
        with patch("zen_ma2_agent.core.build_artistic_resource_map", return_value=resource_map()):
            action = core.program_show_request("design/program this song")["action"]
        self.assertEqual(provider.calls, 1)
        self.assertEqual(action["root_state"], "NEEDS_RESEARCH")
        self.assertFalse(action["executable"])
        self.assertIn("provider failed", action["preview_note"])

    def test_deterministic_child_remains_provider_free(self):
        provider = FakeDesignProvider()
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        action = core.program_show_request("Go Sequence 5")["action"]
        self.assertEqual(provider.calls, [])
        self.assertEqual(action["skill_graph"][-1]["skill_id"], "sequence.go")

    def test_two_and_three_cue_provider_plans_have_no_six_cue_assumption(self):
        for count in (2, 3):
            artistic = {
                "cues": [
                    {"label": f"CUE_{index}", "fade": 0, "actions": [{"group": 1, "dimmer": 20 + index}]}
                    for index in range(1, count + 1)
                ]
            }
            plan, audit = compile_lean_artistic_intent(
                artistic,
                request="generic song",
                resource_map=resource_map(),
            )
            self.assertEqual(len(plan["cues"]), count)
            self.assertEqual(audit["provider_contract"], "ARTISTIC_CUES_V0_2")
            self.assertEqual(plan["active_sequence_range"], [301, 400])
            self.assertEqual(plan["target_executor"], "2.001")

    def test_integer_group_id_alias_is_canonicalized_without_guessing(self):
        plan, _ = compile_lean_artistic_intent(
            {"cues": [{"fade": 0, "actions": [{"group_id": 1, "dimmer": 50}]}]},
            request="x",
            resource_map=resource_map(),
        )
        action = plan["cues"][0]["actions"][0]
        self.assertEqual(action["target"]["ref"], 1)

        with self.assertRaisesRegex(ArtisticPlanCompileError, "group_id alias must be an integer"):
            compile_lean_artistic_intent(
                {"cues": [{"fade": 0, "actions": [{"group_id": "1", "dimmer": 50}]}]},
                request="x",
                resource_map=resource_map(),
            )

        with self.assertRaisesRegex(ArtisticPlanCompileError, "conflicting Group identities"):
            compile_lean_artistic_intent(
                {"cues": [{"fade": 0, "actions": [{"group": 1, "group_id": 2, "dimmer": 50}]}]},
                request="x",
                resource_map=resource_map(),
            )

    def test_fixture_type_capability_dimmer_status_compiles(self):
        mapped = resource_map("SHOW_BOUND_VERIFIED_FIXTURE_TYPE_CAPABILITY")
        plan, _ = compile_lean_artistic_intent(
            {"cues": [{"fade": 0, "actions": [{"group": 1, "dimmer": 50}]}]},
            request="x",
            resource_map=mapped,
        )
        self.assertEqual(plan["cues"][0]["actions"][0]["level"], 50)

    def test_unknown_dimmer_fails_closed(self):
        with self.assertRaisesRegex(ArtisticPlanCompileError, "Dimmer application"):
            compile_lean_artistic_intent(
                {"cues": [{"fade": 0, "actions": [{"group": 1, "dimmer": 50}]}]},
                request="x",
                resource_map=resource_map("DIRECT_GROUP_LEVEL_UNVERIFIED_CAPABILITY"),
            )

    def test_verified_group_bound_preset_compiles_without_top_level_inventory(self):
        mapped = resource_map()
        mapped["groups"][0]["preset_resources"] = [{
            "dimension": "COLOR", "reference": "4.101", "name": "RED"
        }]
        mapped["groups"][0]["dimensions"]["COLOR"] = {"execution_status": "VERIFIED_PRESET_RESOURCE"}
        plan, _ = compile_lean_artistic_intent(
            {"cues": [{"fade": 0, "actions": [{"group": 1, "color_preset": "4.101"}]}]},
            request="x",
            resource_map=mapped,
        )
        self.assertEqual(plan["cues"][0]["actions"][0]["preset_ref"], "4.101")

    def test_effect_gate_requires_content_verification_and_preserves_exact_label(self):
        raw_plan = {
            "cues": [{
                "actions": [{
                    "operation": "CALL_EFFECT",
                    "target": {"type": "group", "ref": 1},
                    "effect_ref": {"id": 7},
                }]
            }]
        }
        with self.assertRaisesRegex(ArtisticPlanCompileError, "content-verified"):
            attach_verified_effect_identity_labels(
                raw_plan,
                {"groups": [{"group_id": 1, "effect_resources": [{
                    "effect_id": 7, "name": "FX", "application_status": "REAL_MACHINE_VERIFIED"
                }]}]},
            )

        mapped = resource_map()
        mapped["groups"][0]["effect_resources"] = [{
            "effect_id": 7,
            "name": "FX_EXACT",
            "application_status": "REAL_MACHINE_CONTENT_VERIFIED",
        }]
        plan, _ = compile_lean_artistic_intent(
            {"cues": [{"fade": 0, "actions": [{"group": 1, "effect": 7}]}]},
            request="x",
            resource_map=mapped,
        )
        self.assertEqual(
            plan["cues"][0]["actions"][0]["effect_ref"],
            {"id": 7, "label": "FX_EXACT"},
        )

    def test_unverified_effect_is_not_exposed_to_provider_contract(self):
        mapped = resource_map()
        mapped["groups"][0]["effect_resources"] = [{
            "effect_id": 7,
            "name": "FX",
            "application_status": "APPLICATION_UNVERIFIED",
        }]
        contract = build_provider_resource_contract(mapped)
        self.assertEqual(contract["group_resources"][0]["effects"], [])
        with self.assertRaisesRegex(ArtisticPlanCompileError, "verified Effect allowlist"):
            compile_lean_artistic_intent(
                {"cues": [{"fade": 0, "actions": [{"group": 1, "effect": 7}]}]},
                request="x",
                resource_map=mapped,
            )

    def test_command_like_provider_output_is_rejected_before_builder(self):
        provider = FakeDesignProvider({
            "command": "Delete Sequence 1",
            "cues": [{"fade": 0, "actions": [{"group": 1, "dimmer": 50}]}],
        })
        core = AgentCore(AgentRuntime(Path(".")), design_intelligence_provider=provider)
        seed_native_state(core)
        with patch("zen_ma2_agent.core.build_artistic_resource_map", return_value=resource_map()),              patch("zen_ma2_agent.core.ShowPlanBuilder.build_first_song") as builder:
            action = core.program_show_request("design/program this song")["action"]
        self.assertEqual(len(provider.calls), 1)
        builder.assert_not_called()
        self.assertEqual(action["root_state"], "NEEDS_RESEARCH")
        self.assertFalse(action["executable"])

    def test_root_lean_path_does_not_import_historical_multi_agent_runtime(self):
        source = Path("zen_ma2_agent/core.py").read_text(encoding="utf-8")
        lean_source = Path("zen_ma2_agent/designer/lean_provider.py").read_text(encoding="utf-8")
        self.assertNotIn("MultiAgent", source + lean_source)
        self.assertNotIn("multi_agent_runtime", source + lean_source)


if __name__ == "__main__":
    unittest.main()
