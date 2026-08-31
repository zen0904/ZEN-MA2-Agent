"""Narrow, evidence-backed grandMA2 3.9 Timecode Offset workflow.

Only the documented whole-show positive ``Timecode/Offset`` property is
compiled.  Event editing, negative movement, and range movement remain
explicitly unsupported until a stable MA2 read/write representation is proven.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


class TimecodeOffsetError(ValueError):
    pass


def format_ms(milliseconds: int) -> str:
    sign = "-" if milliseconds < 0 else ""
    value = abs(milliseconds)
    hours, remainder = divmod(value, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{sign}{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


def ma2_seconds(milliseconds: int) -> str:
    if milliseconds <= 0:
        raise TimecodeOffsetError("grandMA2 Timecode Offset must be a positive whole-show forward offset.")
    # The 3.9 controlled test established decimal-second input is not a stable
    # representation for an exact 500 ms intent.  MA2 accepts an integer ms
    # literal and reports it in its 1/100-second table column.
    return f"{milliseconds}ms"


@dataclass(frozen=True)
class TimecodeOffsetSpec:
    timecode_number: int
    timecode_name: str
    offset_ms: int
    range_start_ms: int | None
    range_end_ms: int | None
    direction: str
    selected_event_count: int | None
    source_request: str
    state_fingerprint: str

    def summary(self) -> dict[str, Any]:
        return asdict(self)


def fingerprint_timecode(timecode: dict[str, Any]) -> str:
    # Only values obtained from the fresh read-only provider participate.  The
    # unavailable event list is intentionally not invented as a fingerprint.
    stable = {key: timecode.get(key) for key in ("timecode_number", "name", "offset_raw", "offset_ms", "source")}
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def resolve_timecode_offset_spec(intent: Intent, timecodes: list[dict[str, Any]]) -> TimecodeOffsetSpec:
    if intent.kind != "offset_timecode":
        raise TimecodeOffsetError("Timecode Offset received an unsupported intent.")
    number = intent.parameters.get("timecode_number")
    if not isinstance(number, int) or number < 1:
        raise TimecodeOffsetError("Timecode Offset requires a positive Timecode number.")
    timecode = next((item for item in timecodes if item.get("timecode_number") == number), None)
    if not timecode:
        raise TimecodeOffsetError(f"Timecode {number} was not found in the current Timecode inventory.")
    offset = intent.parameters.get("offset_ms")
    if not isinstance(offset, int) or offset == 0:
        raise TimecodeOffsetError("Timecode Offset requires a non-zero integer millisecond offset.")
    if offset < 0:
        raise TimecodeOffsetError("UNSUPPORTED: grandMA2 3.9 exposes only a positive whole-show Timecode Offset property; moving Timecode earlier is not command-verified.")
    start, end = intent.parameters.get("range_start_ms"), intent.parameters.get("range_end_ms")
    if start is not None or end is not None:
        raise TimecodeOffsetError("UNSUPPORTED: range-based Timecode event movement has no verified grandMA2 3.9 read/write command path.")
    return TimecodeOffsetSpec(
        timecode_number=number,
        timecode_name=str(timecode.get("name") or number),
        offset_ms=offset,
        range_start_ms=None,
        range_end_ms=None,
        direction="forward",
        selected_event_count=None,
        source_request=intent.source_text,
        state_fingerprint=fingerprint_timecode(timecode),
    )


class TimecodeOffsetSkill:
    """Workflow-only whole-show offset builder; AgentCore owns transport."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind in {"offset_timecode", "timecode_test_setup"} and state.has(("timecodes",))

    def create_task(self, intent: Intent) -> Task:
        title = "Create isolated Timecode test object" if intent.kind == "timecode_test_setup" else "Offset Timecode"
        return Task("timecode-test-setup" if intent.kind == "timecode_test_setup" else "timecode-offset", title, intent, self.manifest.id, ("timecodes",))

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        if task.intent.kind == "timecode_test_setup":
            number = task.intent.parameters.get("timecode_number")
            if not isinstance(number, int) or number < 1:
                raise TimecodeOffsetError("Test Timecode setup requires a positive number.")
            return WorkflowPlan(
                task,
                (Subtask("protect", "Confirm isolated Timecode slot is empty", "Planning"), Subtask("create", "Create isolated test Timecode", "Execution")),
                (SkillGraphNode("root", self.manifest.id, "Timecode Offset test setup"),),
                (ActionStep("create-test-timecode", "Create isolated Timecode object", "command", f"Store Timecode {number} /nc", "MODIFY", verification="List Timecode"),),
                "MODIFY",
                f"TEST-ONLY Timecode Setup Preview\n\nCreate empty Timecode {number}.\nSafety: MODIFY\nApproval required.",
                ("PREVIEW", "APPROVAL"),
                "List Timecode after creation.",
                f"Test object {number} is retained; no automatic cleanup.",
                True,
            )
        raw = task.intent.parameters.get("timecode_offset_spec")
        if not isinstance(raw, dict):
            raise TimecodeOffsetError("Timecode Offset received an unresolved specification.")
        spec = TimecodeOffsetSpec(**raw)
        command = f"Assign Timecode {spec.timecode_number}/Offset = {ma2_seconds(spec.offset_ms)}"
        preview = "\n".join((
            "Timecode Offset Preview", "", f'Timecode: {spec.timecode_number} "{spec.timecode_name}"',
            "Range: Entire Timecode", f"Offset: +{spec.offset_ms / 1000:.3f} s",
            "Events affected: unavailable (event-level Timecode state is not exposed by a verified read-only MA2 3.9 provider)",
            "", "Safety: MODIFY", "Approval required.",
        ))
        return WorkflowPlan(
            task,
            (
                Subtask("refresh", "Read fresh Timecode inventory", "Planning"),
                Subtask("validate", "Validate whole-show forward offset", "Planning"),
                Subtask("offset", "Assign native Timecode Offset", "Execution"),
                Subtask("verify", "Re-read Timecode inventory", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Timecode Offset"),),
            (ActionStep("assign-offset", "Set native whole-show Timecode Offset", "command", command, "MODIFY", verification="Re-read Timecode inventory"),),
            "MODIFY",
            preview,
            ("PREVIEW", "APPROVAL"),
            "Re-read Timecode inventory and verify the target object remains present. Event-time verification is unavailable.",
            "Snapshot metadata stores the fresh Timecode inventory identity. Original event times/offset are unavailable; no automatic rollback is attempted.",
            True,
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY" or len(plan.commands) != 1:
            raise TimecodeOffsetError("Invalid Timecode Offset workflow.")
        if plan.task.intent.kind == "timecode_test_setup":
            if not plan.commands[0].startswith("Store Timecode "):
                raise TimecodeOffsetError("Test setup may only Store an isolated Timecode object.")
            return
        if not plan.commands[0].startswith("Assign Timecode "):
            raise TimecodeOffsetError("Timecode Offset may only use the verified Assign Timecode command.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise TimecodeOffsetError("Timecode Offset cannot execute another workflow.")
        return approved_plan.commands
