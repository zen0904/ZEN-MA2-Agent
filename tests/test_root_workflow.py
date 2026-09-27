import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from shutil import copytree
from unittest.mock import patch

from zen_ma2_agent.operator_api import (
    ComponentState,
    MAConnectionState,
    OpenClawOperatorAdapter,
    build_operator_status,
)
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.core import ActionRecord, AgentCore
from zen_ma2_agent.models import Intent
from zen_ma2_agent.show_program import ROOT_CHILD_CONTEXT_KEY, compose_show_program_child
from zen_ma2_agent.telnet_client import ConnectionState


class ReadyNoopClient:
    def __init__(self):
        self.state = ConnectionState.READY
        self.authenticated_user = "MM"
        self.audit_entries = []

    def execute(self, command):
        raise AssertionError(f"unexpected transport execution: {command}")


class RootTimecodeClient:
    def __init__(self, *_args):
        self.state = ConnectionState.DISCONNECTED
        self.authenticated_user = None
        self.audit_entries = []
        self.commands = []
        self.name = "ZEN Test"
        self.offset = "0s"

    def connect(self, username, password=""):
        self.state, self.authenticated_user = ConnectionState.READY, username
        return "ready"

    def execute(self, command):
        self.commands.append(command)
        if command == "List Timecode":
            offset = "0:15" if self.offset == "0.50s" else "0:00"
            return f"Timecode 9000 {self.name} Intern 0:00 {offset} Endless Repeat\n"
        if command.startswith("Assign Timecode 9000/Offset = "):
            self.offset = command.rsplit("= ", 1)[1]
        return "Executing : " + command

    def close(self):
        self.state = ConnectionState.DISCONNECTED


class RootWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.core = AgentCore(AgentRuntime(Path(".")))

    def test_manifest_and_phase_order(self):
        manifest = next(item for item in self.core.skills.list() if item["id"] == "show.program")
        self.assertTrue(manifest["executable"])
        plan = self.core.skills.plan_intent(
            Intent("program_show", {"request": "unknown design"}, "unknown design"),
            self.core.state,
            self.core.runtime.preferences,
        )
        self.assertEqual([item.phase for item in plan.subtasks[:12]], [
            "UNDERSTAND", "DISCOVER", "RESEARCH_IF_NEEDED", "RESOLVE", "DESIGN", "COMPILE",
            "PREVIEW", "APPROVAL_IF_NEEDED", "EXECUTE", "VERIFY_ACTUAL_CONTENT",
            "SELF_HEAL_IF_NEEDED", "DONE",
        ])
        self.assertFalse(plan.executable)
        self.assertEqual(plan.root_state, "NEEDS_INTELLIGENCE")
        self.assertEqual(plan.commands, ())

    def test_supported_child_is_composed_and_root_has_no_own_command(self):
        result = self.core.program_show_request("Go Sequence 5")
        action = result["action"]
        self.assertEqual(action["task"]["skill_id"], "show.program")
        self.assertEqual(action["skill_graph"][-1]["skill_id"], "sequence.go")
        self.assertEqual(action["command"], "Go Sequence 5")
        self.assertTrue(action["executable"])
        self.assertEqual(action["preview_note"], "Preview required before execution.")
        child = action["continuation_context"]["child_execution"]
        self.assertEqual((child["skill_id"], child["intent_kind"]), ("sequence.go", "go_sequence"))
        self.assertEqual(child["parameters"], {"sequence": 5})
        self.assertLess(len(json.dumps(child).encode("utf-8")), 64 * 1024)

    def test_large_child_uses_bounded_hash_reference_and_resolves_from_action_record(self):
        root = self.core.skills.plan_intent(
            Intent("program_show", {"request": "Go Sequence 5"}, "Go Sequence 5"),
            self.core.state,
            self.core.runtime.preferences,
        )
        child = self.core._plan_routed_intent(Intent("go_sequence", {"sequence": 5}, "Go Sequence 5"))
        large_intent = Intent(
            "go_sequence",
            {"sequence": 5, "review_evidence": "x" * (70 * 1024)},
            "Go Sequence 5",
        )
        child = replace(child, task=replace(child.task, intent=large_intent))
        workflow = compose_show_program_child(root, child)
        child_ref = workflow.continuation_context[ROOT_CHILD_CONTEXT_KEY]
        self.assertEqual(set(child_ref), {"skill_id", "intent_kind", "parameters_sha256", "source_text"})
        self.assertNotIn("parameters", child_ref)
        self.assertEqual(len(child_ref["parameters_sha256"]), 64)

        record = ActionRecord(
            "largechild001", workflow,
            execution_skill_id=child.task.skill_id, execution_intent=large_intent,
        )
        skill_id, resolved = self.core._effective_execution_context(record)
        self.assertEqual(skill_id, "sequence.go")
        self.assertEqual(resolved.parameters, large_intent.parameters)

        public = self.core._public_action_view(record)
        self.assertEqual(public["child_execution"]["parameters_sha256"], child_ref["parameters_sha256"])
        self.assertEqual(public["command_count"], 1)
        self.assertNotIn("steps", public)
        self.assertNotIn("review_evidence", json.dumps(public))
        self.assertLess(len(json.dumps(public).encode("utf-8")), 64 * 1024)

    def test_large_child_reference_tamper_or_missing_action_payload_fails_closed(self):
        root = self.core.skills.plan_intent(
            Intent("program_show", {"request": "Go Sequence 5"}, "Go Sequence 5"),
            self.core.state,
            self.core.runtime.preferences,
        )
        child = self.core._plan_routed_intent(Intent("go_sequence", {"sequence": 5}, "Go Sequence 5"))
        large_intent = Intent(
            "go_sequence", {"sequence": 5, "review_evidence": "y" * (70 * 1024)}, "Go Sequence 5"
        )
        child = replace(child, task=replace(child.task, intent=large_intent))
        workflow = compose_show_program_child(root, child)
        record = ActionRecord(
            "largechild002", workflow,
            execution_skill_id=child.task.skill_id, execution_intent=large_intent,
        )
        context = dict(workflow.continuation_context)
        tampered = dict(context[ROOT_CHILD_CONTEXT_KEY])
        tampered["parameters_sha256"] = "0" * 64
        context[ROOT_CHILD_CONTEXT_KEY] = tampered
        record.workflow = replace(workflow, continuation_context=context)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.core._effective_execution_context(record)

        missing = ActionRecord("largechild003", workflow)
        with self.assertRaisesRegex(ValueError, "does not match its ActionRecord"):
            self.core._effective_execution_context(missing)

    def test_effective_execution_context_uses_child_not_root(self):
        result = self.core.program_show_request("Go Sequence 5")
        record = self.core.actions[result["action"]["id"]]
        skill_id, intent = self.core._effective_execution_context(record)
        self.assertEqual(skill_id, "sequence.go")
        self.assertEqual(intent.kind, "go_sequence")
        self.assertEqual(intent.parameters, {"sequence": 5})

    def test_executable_root_missing_child_context_fails_closed(self):
        result = self.core.program_show_request("Go Sequence 5")
        record = self.core.actions[result["action"]["id"]]
        record.workflow = replace(record.workflow, continuation_context={"request": "Go Sequence 5"})
        with self.assertRaisesRegex(ValueError, "child execution context"):
            self.core._effective_execution_context(record)

    def test_cue_effect_special_executor_dispatch_cannot_be_bypassed_by_root(self):
        result = self.core.program_show_request("Go Sequence 5")
        record = self.core.actions[result["action"]["id"]]
        context = dict(record.workflow.continuation_context or {})
        child = dict(context["child_execution"])
        child.update({
            "skill_id": "effects.cue_application_poc",
            "intent_kind": "verify_cue_effect_application",
            "parameters": {},
        })
        context["child_execution"] = child
        graph = tuple(
            replace(node, skill_id="effects.cue_application_poc")
            if node.skill_id == "sequence.go"
            else node
            for node in record.workflow.skill_graph
        )
        record.workflow = replace(record.workflow, continuation_context=context, skill_graph=graph)
        self.core.runtime.client = ReadyNoopClient()
        with patch.object(self.core, "_execute_cue_effect_application_poc", return_value="SPECIAL_POC_PATH") as special:
            approved = self.core.approve_action(record.id)
        special.assert_called_once_with(record)
        self.assertEqual(approved["result"], "SPECIAL_POC_PATH")

    def test_unrecognized_request_is_resumable_and_command_free(self):
        action = self.core.program_show_request("Design a cinematic song with a drop")["action"]
        self.assertEqual(action["root_state"], "NEEDS_INTELLIGENCE")
        self.assertFalse(action["executable"])
        self.assertEqual(action["steps"], ())
        self.assertIsNone(action["command"])

    def test_configured_operator_callbacks_are_bounded(self):
        snapshot = lambda: build_operator_status(
            field_core_available=True,
            field_core_state=ComponentState.ONLINE,
            ma_connection_state=MAConnectionState.DISCONNECTED,
        )
        calls = []
        adapter = OpenClawOperatorAdapter(
            snapshot,
            design_request_handler=lambda request: calls.append(("design", request)) or {"planned": True},
            preview_handler=lambda action_id: calls.append(("preview", action_id)) or {"preview": True},
            approve_handler=lambda action_id, danger: calls.append(("approve", action_id, danger)) or {"approved": True},
        )
        self.assertEqual(adapter.invoke("zen.design.request", {"request": "Go Sequence 5"})["status"], "SUCCESS")
        self.assertEqual(adapter.invoke("zen.preview")["status"], "SUCCESS")
        self.assertEqual(adapter.invoke("zen.approve", {"action_id": "a1", "danger_confirmed": False})["status"], "SUCCESS")
        self.assertEqual(calls, [("design", "Go Sequence 5"), ("preview", None), ("approve", "a1", False)])
        self.assertEqual(adapter.invoke("zen.design.request", {"request": "x", "extra": 1})["status"], "REJECTED")
        self.assertEqual(adapter.invoke("zen.design.request", {"request": 3})["status"], "REJECTED")
        self.assertEqual(adapter.invoke("zen.approve", {"action_id": "a1", "danger_confirmed": "no"})["status"], "REJECTED")
        self.assertEqual(adapter.invoke("zen.approve", {"action_id": "a1"})["status"], "REJECTED")

    def test_unconfigured_reserved_tools_remain_not_implemented(self):
        snapshot = lambda: build_operator_status(field_core_available=True)
        adapter = OpenClawOperatorAdapter(snapshot)
        self.assertEqual(adapter.invoke("zen.design.request")["status"], "NOT_IMPLEMENTED")
        self.assertEqual(adapter.invoke("zen.preview")["status"], "NOT_IMPLEMENTED")
        self.assertEqual(adapter.invoke("zen.approve")["status"], "NOT_IMPLEMENTED")


class RootStatefulWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-root-stateful-")
        root = Path(self.temp.name)
        copytree(Path(__file__).resolve().parents[1] / "skills", root / "skills")
        self.runtime = AgentRuntime(root, client_factory=RootTimecodeClient)
        self.core = AgentCore(self.runtime)
        self.core.connect("127.0.0.1", 30000, "MM", "")

    def tearDown(self):
        self.temp.cleanup()

    @property
    def client(self):
        return self.runtime.client

    def test_root_reuses_stateful_planner_guard_and_post_write_verifier(self):
        response = self.core.program_show_request("Timecode 9000 往後 500ms")
        action = response["action"]
        self.assertEqual(action["task"]["skill_id"], "show.program")
        self.assertEqual(action["skill_graph"][-1]["skill_id"], "timecode.offset")
        child = action["continuation_context"]["child_execution"]
        self.assertEqual(child["intent_kind"], "offset_timecode")
        self.assertIn("timecode_offset_spec", child["parameters"])
        self.assertEqual(self.client.commands, ["List Timecode"])

        result = self.core.approve_action(action["id"])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(
            self.client.commands,
            [
                "List Timecode",
                "List Timecode",
                "Assign Timecode 9000/Offset = 0.50s",
                "List Timecode",
            ],
        )
        self.assertIn("Verification: VERIFIED", result["result"])
        self.assertEqual(self.core.root_workflow_status()["phase"], "VERIFY_ACTUAL_CONTENT")
        self.assertNotEqual(self.core.root_workflow_status()["phase"], "DONE")

    def test_root_state_change_guard_blocks_before_write(self):
        action = self.core.program_show_request("Timecode 9000 往後 500ms")["action"]
        self.client.name = "Changed outside ZEN"
        with self.assertRaisesRegex(ValueError, "STATE_CHANGED_SINCE_PREVIEW"):
            self.core.approve_action(action["id"])
        self.assertEqual(self.client.commands, ["List Timecode", "List Timecode"])
        self.assertFalse(any(command.startswith("Assign Timecode") for command in self.client.commands))

    def test_direct_non_root_timecode_workflow_remains_direct(self):
        response = self.core.handle_request("Timecode 9000 往後 500ms")
        self.assertEqual(response["action"]["task"]["skill_id"], "timecode.offset")
        self.assertNotIn("child_execution", response["action"].get("continuation_context") or {})


if __name__ == "__main__":
    unittest.main()
