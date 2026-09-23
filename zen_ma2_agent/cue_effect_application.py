"""Bounded real-machine validation for calling an existing Effect into a Cue.

This is deliberately *not* a generic MA command interface.  The one grammar
being verified is constructed only from a fresh, Agent-owned Effect catalogue
entry and a freshly scanned target Group.  The Core executes the steps in two
phases so a Cue is never stored after an MA2 command error.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Intent
from .allocation import AllocationError, first_free_from_front
from .protected_objects import PROTECTED_SEQUENCES
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


CAPABILITY_SCHEMA = "zen.cue_effect_application.v0.2"
GRAMMAR_ID = "EFFECT_POOL_CALL"
MA2_VERSION_FAMILY = "grandMA2_3.9"


class CueEffectApplicationError(ValueError):
    pass


@dataclass(frozen=True)
class CueEffectApplicationSpec:
    effect_id: int
    effect_label: str
    target_group: int
    target_group_name: str
    sequence: int
    sequence_label: str
    cue_number: int = 1
    cue_label: str = "FX_CALL_TEST"

    def summary(self) -> dict[str, Any]:
        return asdict(self)


def allocate_sequence(
    sequences: list[dict[str, Any]],
    active_range: tuple[int, int] | None = None,
) -> int:
    """Allocate the first safe Sequence from the front after a fresh scan.

    An explicit range remains supported for a caller that truly needs one,
    but the default no longer hides test objects in a high-number reserve.
    """
    start, end = active_range if active_range is not None else (1, 9999)
    if start < 1 or end < start:
        raise CueEffectApplicationError("Cue Effect POC has an invalid active Sequence range.")
    used = {
        item.get("number")
        for item in sequences
        if isinstance(item, dict) and isinstance(item.get("number"), int)
    }
    try:
        return first_free_from_front(
            used,
            protected=PROTECTED_SEQUENCES,
            start=start,
            end=end,
        )
    except AllocationError as exc:
        raise CueEffectApplicationError("BLOCKED: no unused Sequence is available in the requested range.") from exc


def resolve_spec(*, effect: dict[str, Any] | None, catalog_entry: dict[str, Any] | None, group: dict[str, Any] | None, membership: dict[str, Any] | None, sequences: list[dict[str, Any]], active_range: tuple[int, int] | None = None) -> CueEffectApplicationSpec:
    """Bind every POC object from fresh evidence; never trust a stale catalog alone."""
    if not effect or not isinstance(effect.get("effect_id"), int) or not isinstance(effect.get("name"), str):
        raise CueEffectApplicationError("STALE_EFFECT_RESOURCE: Effect was not found by fresh List Effect.")
    if not catalog_entry or catalog_entry.get("ownership") != "ZEN_AGENT":
        raise CueEffectApplicationError("STALE_EFFECT_RESOURCE: no Agent-owned Effect catalog evidence is available.")
    if catalog_entry.get("effect_id") != effect["effect_id"] or catalog_entry.get("label") != effect["name"]:
        raise CueEffectApplicationError("STALE_EFFECT_RESOURCE: Effect label no longer matches the Agent catalog.")
    requirement = catalog_entry.get("requirement") or {}
    if requirement.get("target_type") != "group" or not isinstance(requirement.get("target_ref"), int):
        raise CueEffectApplicationError("STALE_EFFECT_RESOURCE: catalog Effect target is not a verified Group requirement.")
    target = requirement["target_ref"]
    if not group or group.get("number") != target:
        raise CueEffectApplicationError("MISSING_TARGET_GROUP: catalog target Group was not found by fresh List Group.")
    if not membership or membership.get("group_no") != target or not isinstance(membership.get("fixtures"), list) or not membership["fixtures"]:
        raise CueEffectApplicationError("MISSING_TARGET_GROUP: target Group has no fresh non-empty membership evidence.")
    sequence = allocate_sequence(sequences, active_range)
    return CueEffectApplicationSpec(
        effect_id=effect["effect_id"], effect_label=effect["name"], target_group=target,
        target_group_name=str(group.get("name") or f"Group {target}"), sequence=sequence,
        sequence_label=f"ZEN_AI_EFFECT_CALL_TEST_{sequence}",
    )


class CueEffectApplicationSkill:
    """One candidate grammar: selection followed by the Effect pool object call."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind == "verify_cue_effect_application"

    def create_task(self, intent: Intent) -> Task:
        return Task("cue-effect-application", "Cue Effect Application POC", intent, self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        raw = task.intent.parameters.get("cue_effect_spec")
        if not isinstance(raw, dict):
            raise CueEffectApplicationError("Cue Effect POC received no verified typed specification.")
        try:
            spec = CueEffectApplicationSpec(**raw)
        except TypeError as exc:
            raise CueEffectApplicationError("Cue Effect POC specification is malformed.") from exc
        steps = (
            ActionStep("clear-before", "Clear Programmer before isolated probe", "command", "ClearAll", "MODIFY"),
            ActionStep("select-target", f"Select verified Group {spec.target_group} {spec.target_group_name}", "command", f"Group {spec.target_group}", "MODIFY", depends_on=("clear-before",)),
            ActionStep("call-effect", f"Apply existing verified Effect {spec.effect_id}", "command", f"Effect {spec.effect_id}", "MODIFY", depends_on=("select-target",), verification="MA2 command feedback must contain no error before Cue storage."),
            ActionStep("store-cue", f"Store new Agent-owned Cue {spec.cue_number}", "command", f'Store Cue {spec.cue_number} Sequence {spec.sequence} "{spec.cue_label}" Fade 0 /nc', "MODIFY", depends_on=("call-effect",)),
            ActionStep("label-sequence", "Label new Agent-owned Sequence", "command", f'Label Sequence {spec.sequence} "{spec.sequence_label}" /nc', "MODIFY", depends_on=("store-cue",)),
            ActionStep("clear-after", "Clear Programmer after isolated probe", "command", "ClearAll", "MODIFY", depends_on=("label-sequence",)),
        )
        preview = "\n".join((
            "CUE EFFECT APPLICATION POC", "", f"Effect: {spec.effect_id} — {spec.effect_label}",
            f"Target: Group {spec.target_group} {spec.target_group_name}", f"New Sequence: {spec.sequence} — {spec.sequence_label}",
            f"New Cue: {spec.cue_number} — {spec.cue_label}", "", "Grammar candidate: select Group, then call existing Effect pool object.",
            "Cue storage is conditional: it will run only when MA2 reports no error for the Effect call.", "Programmer is cleared before and after every outcome.", "", "Safety: MODIFY", "Approval required.",
        ))
        return WorkflowPlan(
            task, (Subtask("fresh-verify", "Verify Effect, Group, membership, and a free Sequence", "Planning"), Subtask("probe", "Apply one Effect-call grammar candidate", "Execution"), Subtask("store", "Store only after accepted application", "Execution"), Subtask("verify", "Read Sequence and Cue metadata", "Verification")),
            (SkillGraphNode("root", self.manifest.id, "Cue Effect Application POC"),), steps, "MODIFY", preview, ("PREVIEW",),
            "Verify fresh Effect/Group evidence, exact Agent-owned Sequence label, and Cue metadata; Cue-content Effect read-back remains PARTIAL.",
            "Manual only: retain the exact Agent-owned Sequence as audit evidence; no Delete command is generated.", True,
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY" or len(plan.commands) != 6:
            raise CueEffectApplicationError("Invalid Cue Effect POC workflow.")
        raw = plan.task.intent.parameters.get("cue_effect_spec") or {}
        sequence = raw.get("sequence")
        label = raw.get("sequence_label")
        effect = raw.get("effect_id")
        group = raw.get("target_group")
        expected = (
            "ClearAll", f"Group {group}", f"Effect {effect}",
            f'Store Cue 1 Sequence {sequence} "FX_CALL_TEST" Fade 0 /nc',
            f'Label Sequence {sequence} "{label}" /nc', "ClearAll",
        )
        if plan.commands != expected:
            raise CueEffectApplicationError("Cue Effect POC rejected a non-allow-listed command plan.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise CueEffectApplicationError("Cue Effect POC cannot execute another workflow.")
        return approved_plan.commands


def cue_effect_capability_is_content_verified(value: object) -> bool:
    """Single source of truth for whether CALL_EFFECT may become executable."""
    if not isinstance(value, dict):
        return False
    verification = value.get("verification")
    return bool(
        value.get("schema") == CAPABILITY_SCHEMA
        and value.get("status") == "REAL_MACHINE_CONTENT_VERIFIED"
        and value.get("grammar") == GRAMMAR_ID
        and value.get("ma2_version_family") == MA2_VERSION_FAMILY
        and isinstance(verification, dict)
        and verification.get("cue_content_readback") == "VERIFIED"
        and verification.get("application") == "REAL_MACHINE_CONTENT_VERIFIED"
    )


class CueEffectApplicationCapability:
    """Persist only a completed real-machine grammar verification, never a proposal."""

    def __init__(self, root: Path):
        self.path = root / "data" / "ZEN_CUE_EFFECT_APPLICATION_CAPABILITY.json"

    def load_verified(self) -> dict[str, Any] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if not isinstance(value, dict) or value.get("schema") != CAPABILITY_SCHEMA:
            return None
        verification = value.get("verification") if isinstance(value.get("verification"), dict) else {}
        if (
            value.get("status") != "REAL_MACHINE_CONTENT_VERIFIED"
            or value.get("grammar") != GRAMMAR_ID
            or value.get("ma2_version_family") != MA2_VERSION_FAMILY
            or verification.get("cue_content_readback") != "VERIFIED"
        ):
            return None
        return value

    def record_content_verified(self, spec: CueEffectApplicationSpec, *, sequence_export_sha256: str) -> dict[str, Any]:
        """Persist executable capability only after content-level Sequence readback."""
        if not re.fullmatch(r"[0-9a-f]{64}", sequence_export_sha256 or ""):
            raise CueEffectApplicationError("Content verification requires a lowercase SHA-256.")
        value = {
            "schema": CAPABILITY_SCHEMA,
            "status": "REAL_MACHINE_CONTENT_VERIFIED",
            "grammar": GRAMMAR_ID,
            "ma2_version_family": MA2_VERSION_FAMILY,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "evidence": {
                "effect_id": spec.effect_id,
                "effect_label": spec.effect_label,
                "target_group": spec.target_group,
                "sequence": spec.sequence,
                "cue": spec.cue_number,
                "sequence_export_sha256": sequence_export_sha256,
            },
            "verification": {
                "effect_reference": "VERIFIED",
                "target": "VERIFIED",
                "sequence": "VERIFIED",
                "cue": "VERIFIED",
                "application": "REAL_MACHINE_CONTENT_VERIFIED",
                "cue_content_readback": "VERIFIED",
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return value

    def record(self, spec: CueEffectApplicationSpec) -> dict[str, Any]:
        value = {
            "schema": CAPABILITY_SCHEMA,
            "status": "REAL_MACHINE_METADATA_ONLY",
            "grammar": GRAMMAR_ID,
            "ma2_version_family": MA2_VERSION_FAMILY,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "evidence": {
                "effect_id": spec.effect_id,
                "effect_label": spec.effect_label,
                "target_group": spec.target_group,
                "sequence": spec.sequence,
                "cue": spec.cue_number,
            },
            "verification": {
                "effect_reference": "VERIFIED",
                "target": "VERIFIED",
                "sequence": "VERIFIED",
                "cue": "VERIFIED",
                "application": "COMMAND_ACCEPTED_ONLY",
                "cue_content_readback": "PARTIAL",
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return value


def ma2_response_has_error(response: str) -> bool:
    """Conservative feedback classifier used only to stop before Store Cue."""
    return bool(re.search(r"\b(?:error|illegal|failed|cannot|unknown|syntax|login incorrect)\b", response or "", re.I))
