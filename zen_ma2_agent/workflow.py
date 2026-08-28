from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any

from .models import CommandPlan, Intent, SafetyLevel


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    intent: Intent
    skill_id: str
    required_state: tuple[str, ...] = ()


@dataclass(frozen=True)
class Subtask:
    id: str
    title: str
    phase: str
    status: str = "PLANNED"


@dataclass(frozen=True)
class SkillGraphNode:
    id: str
    skill_id: str
    title: str
    parent_id: str | None = None


@dataclass(frozen=True)
class ActionStep:
    id: str
    title: str
    kind: str
    command: str | None = None
    safety: str = "SAFE"
    depends_on: tuple[str, ...] = ()
    verification: str | None = None
    rollback: str | None = None


@dataclass(frozen=True)
class WorkflowPlan:
    task: Task
    subtasks: tuple[Subtask, ...]
    skill_graph: tuple[SkillGraphNode, ...]
    steps: tuple[ActionStep, ...]
    safety: str
    preview_note: str
    approval_gates: tuple[str, ...]
    verification_strategy: str
    rollback_strategy: str | None = None
    executable: bool = True

    @classmethod
    def from_command(cls, skill_id: str, intent: Intent, command: CommandPlan) -> "WorkflowPlan":
        task = Task(uuid.uuid4().hex[:12], command.intent.kind.replace("_", " ").title(), intent, skill_id)
        subtasks = (
            Subtask("inspect", "Validate deterministic request", "Planning"),
            Subtask("execute", "Execute approved MA2 command", "Execution"),
            Subtask("verify", "Record MA2 response", "Verification"),
        )
        step = ActionStep("command-1", "MA2 command", "command", command.command, command.safety.value, verification="Record Telnet response")
        gates = ("PREVIEW", "SECOND_CONFIRMATION") if command.safety is SafetyLevel.DANGEROUS else ("PREVIEW",)
        graph = (SkillGraphNode("root", skill_id, task.title),)
        return cls(task, subtasks, graph, (step,), command.safety.value, command.preview_note, gates, "Record MA2 response", executable=command.executable)

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(step.command for step in self.steps if step.kind == "command" and step.command)

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["intent"] = asdict(self.task.intent)
        result["command"] = "; ".join(self.commands) or None
        result["preview_note"] = self.preview_note
        return result

    def with_child(self, child: "WorkflowPlan") -> "WorkflowPlan":
        """Merge a planned sub-Skill before the parent workflow is approved."""
        prefix = f"{child.task.id}-"
        child_nodes = tuple(SkillGraphNode(prefix + node.id, node.skill_id, node.title, "root" if node.parent_id is None else prefix + node.parent_id) for node in child.skill_graph)
        child_steps = tuple(ActionStep(prefix + step.id, step.title, step.kind, step.command, step.safety, tuple(prefix + dependency for dependency in step.depends_on), step.verification, step.rollback) for step in child.steps)
        safety = max((self.safety, child.safety), key=lambda value: {"SAFE": 0, "MODIFY": 1, "DANGEROUS": 2}[value])
        gates = tuple(dict.fromkeys(self.approval_gates + child.approval_gates))
        return WorkflowPlan(self.task, self.subtasks + child.subtasks, self.skill_graph + child_nodes, self.steps + child_steps, safety, self.preview_note, gates, self.verification_strategy, self.rollback_strategy or child.rollback_strategy, self.executable and child.executable)
