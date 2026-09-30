import unittest
from pathlib import Path

from zen_ma2_agent.designer.lean_design_mode import assemble_compact_design_context
from zen_ma2_agent.llm.autonomous_designer import build_designer_context
from zen_ma2_agent.tool_capabilities import (
    CONTEXT_SCHEMA,
    REGISTRY_SCHEMA,
    build_agent_tool_context,
    load_agent_tool_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class AgentToolCapabilitiesTests(unittest.TestCase):
    def test_registry_is_machine_readable_and_does_not_grant_lean_designer_tools(self):
        registry = load_agent_tool_registry(REPO_ROOT)
        self.assertEqual(registry["schema"], REGISTRY_SCHEMA)
        capabilities = registry["capabilities"]
        self.assertGreaterEqual(len(capabilities), 10)
        self.assertTrue(any(item["id"] == "gdtf.parse" for item in capabilities))
        self.assertTrue(any(item["id"] == "mvr.parse" for item in capabilities))
        self.assertTrue(any(item["id"] == "ops.execute_bounded" for item in capabilities))
        self.assertTrue(all(item.get("lean_api_designer_direct") is False for item in capabilities))

    def test_compact_tool_context_preserves_execution_boundary(self):
        context = build_agent_tool_context(REPO_ROOT)
        self.assertEqual(context["schema"], CONTEXT_SCHEMA)
        self.assertIn("not execution authority", context["execution_note"].lower())
        by_id = {item["id"]: item for item in context["capabilities"]}
        self.assertEqual(by_id["gdtf.parse"]["invoke_via"], "LOCAL_LIBRARY")
        self.assertFalse(by_id["gdtf.parse"]["lean_api_designer_direct"])

    def test_lean_and_autonomous_designer_contexts_see_shared_catalog(self):
        lean = assemble_compact_design_context(song_context={"song": "TEST"})
        self.assertEqual(lean["context"]["tool_capabilities"]["schema"], CONTEXT_SCHEMA)
        autonomous = build_designer_context(REPO_ROOT)
        self.assertEqual(autonomous["tool_capabilities"]["schema"], CONTEXT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
