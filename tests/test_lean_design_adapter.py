import json
import unittest
from unittest.mock import patch

from zen_ma2_agent.llm.lean_design_adapter import (
    ProviderRouterLeanDesignIntelligence,
    lean_design_intelligence_from_router,
    load_portable_lean_design_intelligence,
)
from zen_ma2_agent.llm.router import ProviderRouter, ProviderSlot, ProviderUnavailable


def slot(number, *, cost, priority=100, roles=("LIGHTING_DESIGNER",), model=None):
    return ProviderSlot(
        number=number,
        provider_type="OPENAI_COMPATIBLE",
        model=model or f"model-{number}",
        base_url="https://example.invalid/v1",
        api_key=f"SECRET-{number}",
        roles=roles,
        timeout_seconds=5,
        priority=priority,
        cost_class=cost,
        response_format="JSON_OBJECT",
    )


class FakeAdapter:
    def __init__(self, failures=()):
        self.failures = set(failures)
        self.calls = []

    def complete(self, provider_slot, *, system, user, visual_evidence=None):
        self.calls.append({
            "slot": provider_slot.number,
            "system": system,
            "user": user,
            "visual": visual_evidence,
        })
        if provider_slot.number in self.failures:
            raise ProviderUnavailable(f"slot {provider_slot.number} unavailable")
        return '{"cues":[{"label":"OPEN","fade":0,"actions":[{"group":1,"dimmer":50}]}]}'


class LeanDesignAdapterTests(unittest.TestCase):
    def test_only_explicit_free_or_local_slots_are_runtime_eligible(self):
        adapter = FakeAdapter()
        router = ProviderRouter(
            "FREE_FIRST",
            (
                slot(1, cost="UNKNOWN", priority=1),
                slot(2, cost="PAID", priority=2),
                slot(3, cost="LOCAL", priority=3),
                slot(4, cost="FREE", priority=60),
            ),
            adapter=adapter,
            parallelism=2,
            parallel_roles=("LIGHTING_DESIGNER",),
        )
        design = ProviderRouterLeanDesignIntelligence(router)
        result = design.design("program song", {"verified_resource_contract": {"group_resources": []}})
        self.assertIn('"cues"', result)
        # FREE_FIRST is preserved after unsafe slots are removed.
        self.assertEqual([row["slot"] for row in adapter.calls], [4])
        summary = design.safe_summary()
        self.assertEqual(
            [row["cost_class"] for row in summary["eligible_slots"]],
            ["FREE", "LOCAL"],
        )
        self.assertFalse(summary["paid_provider_allowed"])
        self.assertFalse(summary["parallel_candidates"])
        self.assertNotIn("SECRET-", json.dumps(summary))

    def test_logical_single_design_call_may_fallback_only_across_free_local(self):
        adapter = FakeAdapter(failures={1})
        router = ProviderRouter(
            "FALLBACK",
            (
                slot(1, cost="FREE"),
                slot(2, cost="LOCAL"),
                slot(3, cost="PAID"),
            ),
            adapter=adapter,
        )
        design = ProviderRouterLeanDesignIntelligence(router)
        result = design.design("program song", {"verified_resource_contract": {}})
        self.assertIn('"cues"', result)
        self.assertEqual([row["slot"] for row in adapter.calls], [1, 2])
        self.assertEqual(design.last_diagnostics["provider_identity"]["slot"], 2)
        self.assertEqual(
            [row["slot_number"] for row in design.last_diagnostics["attempts"]],
            [1, 2],
        )
        self.assertNotIn("SECRET-", json.dumps(design.last_diagnostics))

    def test_non_designer_role_and_unknown_paid_slots_do_not_make_adapter(self):
        router = ProviderRouter(
            "FREE_FIRST",
            (
                slot(1, cost="FREE", roles=("CRITIC",)),
                slot(2, cost="UNKNOWN"),
                slot(3, cost="PAID"),
            ),
            adapter=FakeAdapter(),
        )
        self.assertIsNone(lean_design_intelligence_from_router(router))

    def test_prompt_is_artistic_only_and_does_not_contain_credentials(self):
        adapter = FakeAdapter()
        router = ProviderRouter("PRIMARY_ONLY", (slot(1, cost="FREE"),), adapter=adapter)
        design = ProviderRouterLeanDesignIntelligence(router)
        design.design(
            "make this song dramatic",
            {"verified_resource_contract": {"group_resources": [{"group_id": 1}]}},
        )
        call = adapter.calls[0]
        self.assertIn("ARTISTIC_CUES_V0_2", call["system"])
        self.assertIn("Never emit MA2 commands", call["system"])
        self.assertIn("exact field `group`", call["system"])
        self.assertIn("Never use `group_id`", call["system"])
        payload = json.loads(call["user"])
        self.assertEqual(payload["request"], "make this song dramatic")
        self.assertEqual(
            payload["context"]["verified_resource_contract"]["group_resources"][0]["group_id"],
            1,
        )
        self.assertNotIn("SECRET-", call["system"] + call["user"])

    def test_portable_factory_is_configuration_only(self):
        adapter = FakeAdapter()
        router = ProviderRouter("PRIMARY_ONLY", (slot(1, cost="FREE"),), adapter=adapter)
        with patch(
            "zen_ma2_agent.llm.lean_design_adapter.ProviderRouter.from_portable_config",
            return_value=router,
        ) as load:
            design = load_portable_lean_design_intelligence()
        load.assert_called_once_with(None)
        self.assertIsNotNone(design)
        self.assertEqual(adapter.calls, [])


if __name__ == "__main__":
    unittest.main()
