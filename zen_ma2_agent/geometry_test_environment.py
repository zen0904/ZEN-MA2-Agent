"""Explicit, opt-in isolated-show setup for Geometry Clone verification.

This module is not a general show-management feature.  It exists solely for
the packaged real-MA2 verifier and remains unreachable unless its environment
gate is enabled.  Its allow-list deliberately prevents a request from loading
or editing the running production show.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


TEST_MODE_ENV = "ZEN_MA2_GEOMETRY_TEST_MODE"
TEST_SHOW = "MA2_EFFECT_PROBE_WORK"
PRODUCTION_SHOW = "zen templ show"
# Legacy numbers are retained only as historical documentation. New isolated
# test Groups are allocated from the first free slots by AgentCore.
SOURCE_GROUP = 90
DESTINATION_GROUP = 91
SOURCE_LABEL = "ZEN Clone Src TEST"
DESTINATION_LABEL = "ZEN Clone Dst TEST"


class GeometryTestEnvironmentError(ValueError):
    pass


def test_mode_enabled() -> bool:
    return os.environ.get(TEST_MODE_ENV) == "1"


@dataclass(frozen=True)
class GeometryTestGroupSpec:
    source_fixture: int
    destination_fixture: int
    source_group: int
    destination_group: int

    def summary(self) -> dict[str, int]:
        return {
            "source_fixture": self.source_fixture,
            "destination_fixture": self.destination_fixture,
            "source_group": self.source_group,
            "destination_group": self.destination_group,
        }


class GeometryTestEnvironmentSkill:
    """A narrow ActionPlan-only test setup skill.

    Every write is a documented MA2 command and is emitted only from an
    approved plan.  It never accepts arbitrary show names, group numbers, or
    fixture selections.
    """

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return test_mode_enabled() and intent.kind in self.manifest.intents

    def create_task(self, intent: Intent) -> Task:
        title = {
            "geometry_test_load_show": "Load isolated Geometry Clone test show",
            "geometry_test_restore_show": "Restore recorded production show",
            "geometry_test_setup_groups": "Create isolated Geometry Clone test Groups",
        }[intent.kind]
        return Task("geometry-test-" + intent.kind.rsplit("_", 1)[-1], title, intent, self.manifest.id)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        if not test_mode_enabled():
            raise GeometryTestEnvironmentError("Isolated Geometry test workflows require explicit test mode.")
        kind = task.intent.kind
        if kind == "geometry_test_load_show":
            command = f'LoadShow "{TEST_SHOW}" /nc'
            return self._workflow(
                task,
                (ActionStep("load-test-show", "Load allow-listed isolated show", "command", command, "MODIFY", verification="Read Fixture inventory after loading"),),
                "Geometry Clone Test Show Preview\n\n"
                f'Load isolated Show: "{TEST_SHOW}"\n'
                f'Production restore target: "{PRODUCTION_SHOW}"\n'
                "Scope: Show data only; current global/user/network settings are retained.\n\n"
                "Safety: MODIFY\nApproval required.",
                "Read the Test Show Fixture inventory before any setup.",
            )
        if kind == "geometry_test_restore_show":
            command = f'LoadShow "{PRODUCTION_SHOW}" /nc'
            return self._workflow(
                task,
                (ActionStep("restore-production-show", "Restore recorded production show", "command", command, "MODIFY", verification="Re-read production Group inventory"),),
                "Production Show Restore Preview\n\n"
                f'Restore Show: "{PRODUCTION_SHOW}"\n'
                "Scope: Show data only; current global/user/network settings are retained.\n\n"
                "Safety: MODIFY\nApproval required.",
                "Re-read Groups 1–7 and Fixture inventory after restoring.",
            )
        if kind == "geometry_test_setup_groups":
            raw = task.intent.parameters.get("geometry_test_group_spec")
            if not isinstance(raw, dict):
                raise GeometryTestEnvironmentError("Geometry test Group setup has no verified Fixture pair.")
            spec = GeometryTestGroupSpec(
                int(raw["source_fixture"]),
                int(raw["destination_fixture"]),
                int(raw["source_group"]),
                int(raw["destination_group"]),
            )
            if spec.source_fixture < 1 or spec.destination_fixture < 1 or spec.source_fixture == spec.destination_fixture:
                raise GeometryTestEnvironmentError("Geometry test Group setup requires two distinct positive Fixture IDs.")
            if spec.source_group < 1 or spec.destination_group < 1 or spec.source_group == spec.destination_group:
                raise GeometryTestEnvironmentError("Geometry test Group setup requires two distinct positive Group IDs.")
            steps = (
                ActionStep("select-source", f"Select test Fixture {spec.source_fixture}", "command", f"Fixture {spec.source_fixture}", "MODIFY"),
                ActionStep("store-source", f"Store Group {spec.source_group}", "command", f"Store Group {spec.source_group} /nc", "MODIFY", depends_on=("select-source",)),
                ActionStep("label-source", "Label test source Group", "command", f'Label Group {spec.source_group} "{SOURCE_LABEL}"', "MODIFY", depends_on=("store-source",)),
                ActionStep("select-destination", f"Select test Fixture {spec.destination_fixture}", "command", f"Fixture {spec.destination_fixture}", "MODIFY", depends_on=("label-source",)),
                ActionStep("store-destination", f"Store Group {spec.destination_group}", "command", f"Store Group {spec.destination_group} /nc", "MODIFY", depends_on=("select-destination",)),
                ActionStep("label-destination", "Label test destination Group", "command", f'Label Group {spec.destination_group} "{DESTINATION_LABEL}"', "MODIFY", depends_on=("store-destination",)),
                ActionStep("clear-test-selection", "Clear test setup selection", "command", "ClearAll", "MODIFY", depends_on=("label-destination",)),
            )
            return self._workflow(
                task,
                steps,
                "Geometry Clone Test Groups Preview\n\n"
                f'Source: Group {spec.source_group} "{SOURCE_LABEL}" ← Fixture {spec.source_fixture}\n'
                f'Destination: Group {spec.destination_group} "{DESTINATION_LABEL}" ← Fixture {spec.destination_fixture}\n'
                "Only the currently loaded isolated Test Show is affected.\n\n"
                "Safety: MODIFY\nApproval required.",
                f"Export Group {spec.source_group} and Group {spec.destination_group}, then verify each has exactly its expected Fixture.",
            )
        raise GeometryTestEnvironmentError("Unsupported isolated Geometry test operation.")

    def _workflow(self, task: Task, steps: tuple[ActionStep, ...], preview: str, verification: str) -> WorkflowPlan:
        return WorkflowPlan(
            task,
            (Subtask("guard", "Validate explicit isolated-test guard", "Planning"), Subtask("execute", "Run approved MA2 test setup", "Execution"), Subtask("verify", "Read back isolated test state", "Verification")),
            (SkillGraphNode("root", self.manifest.id, task.title),),
            steps,
            "MODIFY",
            preview,
            ("PREVIEW", "APPROVAL"),
            verification,
            f'No automatic cleanup. Restore only through approved LoadShow "{PRODUCTION_SHOW}" /nc.',
            True,
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if not test_mode_enabled() or plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY":
            raise GeometryTestEnvironmentError("Invalid isolated Geometry test workflow.")
        allowed = {
            f'LoadShow "{TEST_SHOW}" /nc',
            f'LoadShow "{PRODUCTION_SHOW}" /nc',
            "ClearAll",
        }
        raw = plan.task.intent.parameters.get("geometry_test_group_spec")
        if isinstance(raw, dict):
            source_group = raw.get("source_group")
            destination_group = raw.get("destination_group")
            if all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in (source_group, destination_group)):
                allowed.update({
                    f"Store Group {source_group} /nc",
                    f"Store Group {destination_group} /nc",
                    f'Label Group {source_group} "{SOURCE_LABEL}"',
                    f'Label Group {destination_group} "{DESTINATION_LABEL}"',
                })
        for command in plan.commands:
            if command not in allowed and not command.startswith("Fixture "):
                raise GeometryTestEnvironmentError("Isolated Geometry test workflow contains a disallowed command.")
        if any(command.startswith("Fixture ") and not command.split(" ", 1)[1].isdigit() for command in plan.commands):
            raise GeometryTestEnvironmentError("Isolated Geometry test workflow may select only one numeric Fixture at a time.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands
