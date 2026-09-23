from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

from .models import Intent
from .state.store import StateStore
from .workflow import SkillGraphNode, Subtask, Task, WorkflowPlan


ROOT_PHASES = (
    "UNDERSTAND",
    "DISCOVER",
    "RESEARCH_IF_NEEDED",
    "RESOLVE",
    "DESIGN",
    "COMPILE",
    "PREVIEW",
    "APPROVAL_IF_NEEDED",
    "EXECUTE",
    "VERIFY_ACTUAL_CONTENT",
    "SELF_HEAL_IF_NEEDED",
    "DONE",
)

ROOT_CHILD_CONTEXT_KEY = "child_execution"
MAX_CHILD_CONTEXT_BYTES = 64 * 1024
MAX_CONTEXT_TEXT = 2048
MAX_CONTEXT_ID = 128


def _bounded_child_execution_context(child: WorkflowPlan) -> dict[str, Any]:
    skill_id = child.task.skill_id
    intent = child.task.intent
    if not isinstance(skill_id, str) or not skill_id or len(skill_id) > MAX_CONTEXT_ID:
        raise ValueError("show.program child skill id is invalid.")
    if not isinstance(intent.kind, str) or not intent.kind or len(intent.kind) > MAX_CONTEXT_ID:
        raise ValueError("show.program child intent kind is invalid.")
    if not isinstance(intent.source_text, str) or len(intent.source_text) > MAX_CONTEXT_TEXT:
        raise ValueError("show.program child source text is invalid.")
    if not isinstance(intent.parameters, dict):
        raise ValueError("show.program child intent parameters must be an object.")
    payload = {
        "skill_id": skill_id,
        "intent_kind": intent.kind,
        "parameters": intent.parameters,
        "source_text": intent.source_text,
    }
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("show.program child execution context must be JSON-safe.") from exc
    if len(encoded) > MAX_CHILD_CONTEXT_BYTES:
        raise ValueError("show.program child execution context is too large.")
    return payload


def compose_show_program_child(root: WorkflowPlan, child: WorkflowPlan) -> WorkflowPlan:
    """Compose one already-planned child under the normal show.program root."""
    if root.task.skill_id != "show.program":
        raise ValueError("show.program composition requires a show.program root plan.")
    combined = root.with_child(child)
    context = dict(root.continuation_context or {})
    context[ROOT_CHILD_CONTEXT_KEY] = _bounded_child_execution_context(child)
    executable = bool(child.executable and child.commands)
    return replace(
        combined,
        executable=executable,
        preview_note=child.preview_note,
        verification_strategy=child.verification_strategy,
        rollback_strategy=child.rollback_strategy or combined.rollback_strategy,
        current_phase="PREVIEW" if executable else "RESEARCH_IF_NEEDED",
        root_state="READY" if executable else "NEEDS_RESEARCH",
        continuation_context=context,
    )


def set_show_program_state(
    plan: WorkflowPlan,
    state: str,
    note: str,
    *,
    phase: str | None = None,
) -> WorkflowPlan:
    if plan.task.skill_id != "show.program":
        raise ValueError("Root workflow state can only be applied to show.program.")
    context = dict(plan.continuation_context or {})
    context["phase"] = phase or state
    return replace(
        plan,
        preview_note=note,
        executable=False,
        root_state=state,
        current_phase=phase or state,
        continuation_context=context,
    )


class ShowProgramSkill:
    """Normal root orchestration. AgentCore supplies already-safe child plans."""

    def __init__(self, manifest: Any, registry: Any):
        self.manifest = manifest
        self.registry = registry

    def can_handle(self, intent: Intent, state: StateStore) -> bool:
        return self.manifest.enabled and intent.kind in self.manifest.intents

    def create_task(self, intent: Intent) -> Task:
        return Task(uuid4().hex[:12], self.manifest.name, intent, self.manifest.id)

    def plan(self, task: Task, state: StateStore, preferences: dict[str, Any]) -> WorkflowPlan:
        request = task.intent.parameters.get("request")
        if not isinstance(request, str) or not request.strip():
            return self._root_plan(task, "NEEDS_INPUT", "UNDERSTAND", "A bounded design request is required.")
        return self._root_plan(
            task,
            "NEEDS_INTELLIGENCE",
            "UNDERSTAND",
            "The root request is ready for AgentCore routing and child planning.",
        )

    def validate(self, plan: WorkflowPlan, state: StateStore) -> None:
        if plan.task.skill_id != self.manifest.id:
            raise ValueError("Invalid show.program workflow plan.")
        if any(step.command for step in plan.steps) and not any(
            node.skill_id != self.manifest.id for node in plan.skill_graph
        ):
            raise ValueError("show.program cannot fabricate MA2 commands.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise ValueError("show.program cannot execute another root workflow.")
        context = approved_plan.continuation_context or {}
        if ROOT_CHILD_CONTEXT_KEY not in context:
            raise ValueError("Executable show.program workflow has no child execution context.")
        return approved_plan.commands

    def _root_plan(self, task: Task, state: str, phase: str, note: str) -> WorkflowPlan:
        subtasks = tuple(
            Subtask(
                f"root-{index}",
                value.replace("_", " ").title(),
                value,
                "PLANNED",
            )
            for index, value in enumerate(ROOT_PHASES, 1)
        )
        return WorkflowPlan(
            task=task,
            subtasks=subtasks,
            skill_graph=(SkillGraphNode("root", self.manifest.id, "Show Program"),),
            steps=(),
            safety="SAFE",
            preview_note=note,
            approval_gates=(),
            verification_strategy="Verify actual MA2 outcome through the composed child's existing verifier.",
            executable=False,
            current_phase=phase,
            root_state=state,
            continuation_context={"request": task.intent.parameters.get("request"), "phase": phase},
        )
