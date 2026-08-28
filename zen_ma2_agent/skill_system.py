from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .models import Intent, SafetyLevel
from .safety import build_plan
from .state.store import StateStore
from .workflow import Task, WorkflowPlan


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class SkillManifest:
    id: str
    name: str
    version: str
    description: str
    intents: tuple[str, ...]
    required_state: tuple[str, ...]
    safety: str
    source: str
    enabled: bool = True
    executable: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str, *, enabled: bool = True, executable: bool = False) -> "SkillManifest":
        required = {"id", "name", "version", "description", "intents", "required_state", "safety"}
        if not required.issubset(data) or not isinstance(data["intents"], list) or not isinstance(data["required_state"], list):
            raise SkillError("Invalid skill manifest.")
        if not re.fullmatch(r"[a-z][a-z0-9_.-]*", str(data["id"])):
            raise SkillError("Skill id must be lowercase and portable.")
        if data["safety"] not in {level.value for level in SafetyLevel}:
            raise SkillError("Skill safety is invalid.")
        return cls(str(data["id"]), str(data["name"]), str(data["version"]), str(data["description"]), tuple(map(str, data["intents"])), tuple(map(str, data["required_state"])), str(data["safety"]), source, enabled, executable)

    def summary(self) -> dict[str, Any]:
        return asdict(self)


class Skill(Protocol):
    manifest: SkillManifest

    def can_handle(self, intent: Intent, state: StateStore) -> bool: ...
    def create_task(self, intent: Intent) -> Task: ...
    def plan(self, task: Task, state: StateStore, preferences: dict[str, Any]) -> WorkflowPlan: ...
    def validate(self, plan: WorkflowPlan, state: StateStore) -> None: ...
    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]: ...


class BuiltinCommandSkill:
    """The simplest workflow: inspect, one approved command, then verify."""

    def __init__(self, manifest: SkillManifest):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: StateStore) -> bool:
        return self.manifest.enabled and intent.kind in self.manifest.intents and state.has(self.manifest.required_state)

    def create_task(self, intent: Intent) -> Task:
        from uuid import uuid4
        return Task(uuid4().hex[:12], self.manifest.name, intent, self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: StateStore, preferences: dict[str, Any]) -> WorkflowPlan:
        plan = build_plan(task.intent, preferences)
        if plan.safety.value != self.manifest.safety:
            raise SkillError(f"Skill {self.manifest.id} produced an unexpected safety level.")
        return WorkflowPlan.from_command(self.manifest.id, task.intent, plan)

    def validate(self, plan: WorkflowPlan, state: StateStore) -> None:
        if plan.task.skill_id != self.manifest.id or not plan.commands and plan.executable:
            raise SkillError("Invalid builtin workflow plan.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        """Return only approved commands; AgentCore remains the transport owner."""
        if approved_plan.task.skill_id != self.manifest.id:
            raise SkillError("Skill cannot execute another Skill's workflow.")
        return approved_plan.commands


class SkillRegistry:
    """Manifest registry; installed code is never imported or executed automatically."""

    def __init__(self, root: Path):
        self.root = root
        self._manifests: dict[str, SkillManifest] = {}
        self._implementations: dict[str, Skill] = {}

    def discover(self) -> None:
        self._manifests.clear()
        self._implementations.clear()
        for source, executable in (("builtin", True), ("installed", False)):
            directory = self.root / "skills" / source
            directory.mkdir(parents=True, exist_ok=True)
            for path in sorted(directory.glob("*/manifest.json")):
                raw = json.loads(path.read_text(encoding="utf-8"))
                manifest = SkillManifest.from_dict(raw, source, enabled=bool(raw.get("enabled", True)), executable=executable)
                if manifest.id in self._manifests:
                    raise SkillError(f"Duplicate skill id: {manifest.id}")
                self._manifests[manifest.id] = manifest
                if executable:
                    self._implementations[manifest.id] = BuiltinCommandSkill(manifest)

    def list(self) -> list[dict[str, Any]]:
        return [manifest.summary() for manifest in sorted(self._manifests.values(), key=lambda item: item.id)]

    def get(self, skill_id: str) -> SkillManifest:
        try:
            return self._manifests[skill_id]
        except KeyError as exc:
            raise SkillError(f"Unknown skill: {skill_id}") from exc

    def capability_for_intent(self, intent_kind: str) -> SkillManifest | None:
        """Find known capability even when it is a disabled placeholder."""
        return next((item for item in sorted(self._manifests.values(), key=lambda value: value.id) if intent_kind in item.intents), None)

    def set_enabled(self, skill_id: str, enabled: bool) -> SkillManifest:
        manifest = self.get(skill_id)
        path = self.root / "skills" / manifest.source / skill_id / "manifest.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["enabled"] = bool(enabled)
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.discover()
        return self.get(skill_id)

    def resolve(self, intent: Intent, state: StateStore) -> Skill:
        for skill_id in sorted(self._implementations):
            skill = self._implementations[skill_id]
            if skill.can_handle(intent, state):
                return skill
        required = [item for item in self._manifests.values() if intent.kind in item.intents and item.enabled]
        if required:
            missing = sorted({resource for item in required for resource in item.required_state if not state.has([resource])})
            raise SkillError(f"Required MA2 state unavailable: {', '.join(missing) or 'no executable implementation'}")
        raise SkillError(f"No enabled skill handles intent: {intent.kind}")

    def plan_intent(self, intent: Intent, state: StateStore, preferences: dict[str, Any]) -> WorkflowPlan:
        """Core entrypoint for root or future child Skill graph planning."""
        skill = self.resolve(intent, state)
        task = skill.create_task(intent)
        workflow = skill.plan(task, state, preferences)
        skill.validate(workflow, state)
        return workflow

    def plan_subskill(self, parent: WorkflowPlan, intent: Intent, state: StateStore, preferences: dict[str, Any]) -> WorkflowPlan:
        """Merge a child Skill graph into a parent before preview/approval."""
        return parent.with_child(self.plan_intent(intent, state, preferences))

    def approved_commands(self, skill_id: str, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        skill = self._implementations.get(skill_id)
        if not skill:
            raise SkillError("Installed Skills do not have an approved executable implementation.")
        return skill.execute(approved_plan)
