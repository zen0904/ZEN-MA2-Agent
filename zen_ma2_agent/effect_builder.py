"""Deterministic grandMA2 3.9 Dimmer Chase workflow builder.

The command construction here is deliberately narrow: it is based on MA2's
documented Store/Assign grammar and must still pass the real-console controlled
test before this builtin is enabled.  It never receives a Telnet client.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .allocation import AllocationError, first_free_from_front
from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


DEFAULT_DIMMER_CHASE = {
    "attribute": "Dim",
    "form": "PWM",
    "low": 0,
    "high": 100,
    "speed_bpm": 60,
    "phase": "0..360",
    "direction": "forward",
    "groups": 1,
}


class EffectBuildError(ValueError):
    pass


class EffectTargetAmbiguous(EffectBuildError):
    pass


@dataclass(frozen=True)
class EffectSpec:
    effect_number: int
    name: str
    effect_type: str
    target_type: str
    target_number: int
    target_name: str
    attribute: str
    form: str
    low: int
    high: int
    speed_bpm: int
    phase: str
    direction: str
    groups: int
    source_request: str

    def summary(self) -> dict[str, Any]:
        return asdict(self)


def allocate_effect_number(effects: list[dict[str, Any]]) -> int:
    """Choose the first safe gap from fresh observed Effect inventory."""
    numbers = {item.get("number") for item in effects if isinstance(item.get("number"), int)}
    if not numbers:
        raise EffectBuildError("Effect number is required because the current Effect inventory cannot prove a free slot.")
    try:
        return first_free_from_front(numbers)
    except AllocationError as exc:
        raise EffectBuildError("No safe free Effect ID is available.") from exc


def resolve_effect_spec(intent: Intent, *, groups: list[dict[str, Any]], fixtures: list[dict[str, Any]], effects: list[dict[str, Any]]) -> EffectSpec:
    """Bind a parsed Dimmer Chase request to verified State cache identities."""
    if intent.kind != "build_dimmer_chase":
        raise EffectBuildError("Effect Builder v1 supports Dimmer Chase only.")
    parameters = intent.parameters
    target_kind = parameters.get("target_type")
    target_value = parameters.get("target")
    if target_kind == "group_number":
        matches = [item for item in groups if item.get("number") == target_value]
    elif target_kind == "group_name":
        matches = [item for item in groups if str(item.get("name") or "").casefold() == str(target_value).casefold()]
    elif target_kind == "fixture_number":
        matches = [item for item in fixtures if item.get("number") == target_value]
    else:
        raise EffectBuildError("Dimmer Chase requires a Group name, Group number, or Fixture number.")
    if not matches:
        raise EffectBuildError(f"Target {target_value!r} was not found in the current MA2 inventory.")
    if len(matches) > 1:
        raise EffectTargetAmbiguous(f"Multiple Groups named {target_value!r} are available; use Group <number>.")
    target = matches[0]
    target_type = "group" if target_kind.startswith("group") else "fixture"
    target_number = int(target["number"])
    target_name = str(target.get("name") or f"{target_type.title()} {target_number}")
    requested_number = parameters.get("effect_number")
    if requested_number is None:
        effect_number = allocate_effect_number(effects)
    elif isinstance(requested_number, int) and requested_number > 0:
        effect_number = requested_number
    else:
        raise EffectBuildError("Effect number must be a positive integer.")
    if effect_number in {item.get("number") for item in effects}:
        raise EffectBuildError(f"Effect {effect_number} already exists. Effect Builder v1 never overwrites an existing Effect.")
    speed = parameters.get("speed_bpm", DEFAULT_DIMMER_CHASE["speed_bpm"])
    if not isinstance(speed, int) or not 1 <= speed <= 999:
        raise EffectBuildError("Dimmer Chase BPM must be an integer from 1 to 999.")
    direction = parameters.get("direction", DEFAULT_DIMMER_CHASE["direction"])
    if direction not in {"forward", "reverse"}:
        raise EffectBuildError("Only forward or reverse Dimmer Chase direction is supported.")
    # grandMA2's direction option is not independently verified in v1. Keep
    # reverse visible in the proposal but refuse execution rather than guess it.
    if direction == "reverse":
        raise EffectBuildError("Reverse direction is not yet command-verified for grandMA2 3.9 Dimmer Chase.")
    name = str(parameters.get("effect_name") or f"{target_name} Dimmer Chase").strip()
    return EffectSpec(
        effect_number=effect_number,
        name=name,
        effect_type="DIMMER_CHASE",
        target_type=target_type,
        target_number=target_number,
        target_name=target_name,
        attribute=DEFAULT_DIMMER_CHASE["attribute"],
        form=DEFAULT_DIMMER_CHASE["form"],
        low=DEFAULT_DIMMER_CHASE["low"],
        high=DEFAULT_DIMMER_CHASE["high"],
        speed_bpm=speed,
        phase=DEFAULT_DIMMER_CHASE["phase"],
        direction=direction,
        groups=DEFAULT_DIMMER_CHASE["groups"],
        source_request=intent.source_text,
    )


class EffectBuilderSkill:
    """Workflow-only builtin: AgentCore remains the approval/transport owner."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind == "build_dimmer_chase"

    def create_task(self, intent: Intent) -> Task:
        return Task("effect-builder", "Build Dimmer Chase", intent, self.manifest.id, ("groups", "effects"))

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        data = task.intent.parameters.get("effect_spec")
        if not isinstance(data, dict):
            raise EffectBuildError("Effect Builder received an unresolved Effect specification.")
        spec = EffectSpec(**data)
        target_command = f"Group {spec.target_number}" if spec.target_type == "group" else f"Fixture {spec.target_number}"
        line = f"1.{spec.effect_number}.1"
        commands = (
            ("create-effect", f"Store Effect {spec.effect_number} /nc", "Create empty Effect pool object"),
            ("create-line", f"Store Effect {line} /nc", "Create Dimmer effect line"),
            ("assign-attribute", f'Assign Attribute "{spec.attribute}" At Effect {line}', "Configure Dimmer attribute"),
            ("assign-form", f'Assign Form "{spec.form}" At Effect {line}', "Configure PWM chase form"),
            ("configure-values", f"Assign Effect {spec.effect_number} /lowvalue={spec.low} /highvalue={spec.high} /speed={spec.speed_bpm} /phase={spec.phase} /groups={spec.groups}", "Configure low/high, BPM, phase, and groups"),
            ("select-target", target_command, f"Select {spec.target_type} {spec.target_number} for the selective effect"),
            ("take-selection", f"Store Effect 1.{spec.effect_number}.* /nc", "Store target selection on all effect lines"),
            ("label", f'Label Effect {spec.effect_number} "{spec.name}" /nc', "Assign effect label"),
        )
        steps = tuple(ActionStep(step_id, title, "command", command, "MODIFY", verification="Verify pool object and label" if step_id == "label" else None, rollback=f"Delete Effect {spec.effect_number}" if step_id == "create-effect" else None) for step_id, command, title in commands)
        preview = "\n".join((
            "Effect Builder Preview", "", f'Target: {spec.target_type.title()} {spec.target_number} "{spec.target_name}"',
            f'Effect: {spec.effect_number} "{spec.name}"', "Type: Dimmer Chase", f"Attribute: {spec.attribute}",
            f"Low: {spec.low}", f"High: {spec.high}", f"Speed: {spec.speed_bpm} BPM", f"Phase: {spec.phase}",
            f"Direction: {spec.direction}", "", "Safety: MODIFY", "Approval required.",
        ))
        return WorkflowPlan(
            task,
            (
                Subtask("resolve", "Resolve target and protect existing Effect", "Planning"),
                Subtask("build", "Create and configure deterministic Dimmer Chase", "Execution"),
                Subtask("selection", "Store target as selective effect membership", "Execution"),
                Subtask("verify", "Read Effect pool object and label", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Effect Builder"),),
            steps,
            "MODIFY",
            preview,
            ("PREVIEW", "APPROVAL"),
            "List Effect <number>; verify Effect exists and label matches. Parameter verification is partial.",
            f"Suggested rollback: Delete Effect {spec.effect_number} (never automatic).",
            True,
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY" or not plan.commands:
            raise EffectBuildError("Invalid Effect Builder workflow.")
        if any("Delete Effect" in command for command in plan.commands):
            raise EffectBuildError("Effect Builder v1 must not include automatic deletion.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise EffectBuildError("Effect Builder cannot execute another workflow.")
        return approved_plan.commands
