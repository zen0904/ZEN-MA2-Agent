"""Narrow, allow-listed execution Skill for the first-song Sequence PoC."""
from __future__ import annotations

import re
from typing import Any

from .builder import FirstSongBuildError, ShowPlanBuilder
from .models import Intent
from .workflow import Task, WorkflowPlan


class FirstSongBuildSkill:
    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind in self.manifest.intents

    def create_task(self, intent: Intent) -> Task:
        return Task("first-song-build", "Build First Song", intent, self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        data = task.intent.parameters.get("first_song_spec")
        if not isinstance(data, dict) or not isinstance(data.get("show_plan"), dict) or not isinstance(data.get("profile"), dict):
            raise FirstSongBuildError("First Song Builder received no typed plan/profile context.")
        return ShowPlanBuilder().build_first_song(data["show_plan"], data["profile"])

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY" or not plan.commands:
            raise FirstSongBuildError("Invalid First Song build workflow.")
        sequence = plan.task.intent.parameters.get("sequence")
        label = plan.task.intent.parameters.get("sequence_label")
        if not isinstance(sequence, int) or not isinstance(label, str) or not label.startswith("ZEN_AI_TEST_"):
            raise FirstSongBuildError("First Song workflow must own an explicitly labelled new Sequence.")
        for command in plan.commands:
            allowed = (
                command == "ClearAll"
                or re.fullmatch(r"Group [1-9]\d*", command)
                or re.fullmatch(r"Effect [1-9]\d*", command)
                or re.fullmatch(r"At Preset [1-9]\d*\.[1-9]\d*", command)
                or re.fullmatch(r"At (?:100|[1-9]?\d)", command)
                or re.fullmatch(rf'Store Cue [1-9]\d* Sequence {sequence} "[^"\r\n]+" Fade \d+(?:\.\d+)? /nc', command)
                or command == f'Label Sequence {sequence} "{label}" /nc'
            )
            if not allowed:
                raise FirstSongBuildError(f"First Song Builder rejected non-allow-listed command: {command}")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise FirstSongBuildError("First Song Builder cannot execute another workflow.")
        return approved_plan.commands

    @staticmethod
    def narrow_rollback_command(sequence: int, label: str, observed_sequence: dict[str, Any] | None) -> str:
        """Expose the ownership-gated recovery proposal without transport access."""
        return ShowPlanBuilder.narrow_rollback_command(sequence, label, observed_sequence)
