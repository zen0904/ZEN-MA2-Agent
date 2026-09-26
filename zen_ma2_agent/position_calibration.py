"""One approval-gated Position calibration transaction.

The calibration proves two facts in one bounded transaction:
1. explicit PAN/TILT values reach native CueData;
2. one newly created Agent-owned Position Preset can be called back into CueData.

It never grants raw MA transport authority to a model. AgentCore remains the
sole executor after Preview and explicit owner approval.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .allocation import first_free_from_front
from .effect_resources import show_identity
from .models import Intent
from .position_application_evidence import (
    PREVIEW_SCHEMA as APPLICATION_PREVIEW_SCHEMA,
    PositionEvidenceError,
    _exact_refs,
    _group,
    _identity,
    _position_capability,
    _row_ref,
)
from .protected_objects import PROTECTED_SEQUENCES
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


PREVIEW_SCHEMA = "zen.position_calibration_preview.v0.1"
RAW_PROOF_SCHEMA = "zen.position_calibration_raw_proof.v0.1"
PAN_VALUE = 20
TILT_VALUE = 30
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_POSITION_REF = re.compile(r"2\.([1-9]\d*)\Z")


def _fresh_resources(profile: Mapping[str, Any]) -> None:
    resources = profile.get("resources")
    required = (
        "groups", "group_membership", "fixtures", "fixture_geometry",
        "fixture_type_profiles", "presets", "sequences",
    )
    if not isinstance(resources, Mapping) or any(
        not isinstance(resources.get(key), Mapping)
        or resources[key].get("status") != "SUPPORTED"
        for key in required
    ):
        raise PositionEvidenceError("POSITION_CALIBRATION_FRESH_STATE_REQUIRED")


def _allocate_position_preset(profile: Mapping[str, Any]) -> tuple[str, str]:
    occupied: set[int] = set()
    labels: set[str] = set()
    for row in profile.get("presets", []):
        if not isinstance(row, Mapping):
            continue
        reference = row.get("reference")
        if isinstance(reference, str):
            match = _POSITION_REF.fullmatch(reference)
            if match:
                occupied.add(int(match.group(1)))
        if isinstance(row.get("name"), str):
            labels.add(row["name"])
    number = first_free_from_front(occupied, protected=frozenset(), start=1, end=9999)
    reference = f"2.{number}"
    label = f"ZEN_POSITION_CAL_P{number}"
    if label in labels:
        raise PositionEvidenceError("POSITION_CALIBRATION_PRESET_LABEL_COLLISION")
    return reference, label


def _predicted_postwrite_identity(
    profile: Mapping[str, Any], reference: str, label: str,
) -> dict[str, str]:
    virtual = copy.deepcopy(dict(profile))
    presets = list(virtual.get("presets") or [])
    presets.append({"reference": reference, "preset_type": "POSITION", "name": label})
    virtual["presets"] = presets
    return show_identity(virtual)


def build_position_calibration_preview(
    profile: Mapping[str, Any], *, group_id: int,
) -> dict[str, Any]:
    """Build one deterministic Raw + Preset application calibration Preview."""
    if group_id != 1 or isinstance(group_id, bool):
        raise PositionEvidenceError("POSITION_CALIBRATION_GROUP_NOT_ALLOWLISTED")
    _fresh_resources(profile)
    identity = _identity(profile)
    group = _group(profile, group_id)
    refs = _exact_refs(group)
    _position_capability(profile, refs)

    sequences = profile.get("sequences")
    if not isinstance(sequences, list):
        raise PositionEvidenceError("POSITION_CALIBRATION_SEQUENCE_INVENTORY_UNAVAILABLE")
    occupied = {row.get("number") for row in sequences if isinstance(row, Mapping)}
    sequence = first_free_from_front(
        occupied, protected=PROTECTED_SEQUENCES, start=1, end=9999,
    )
    sequence_label = f"ZEN_POSITION_CAL_SEQ{sequence}"
    if sequence_label in {
        row.get("name") for row in sequences if isinstance(row, Mapping)
    }:
        raise PositionEvidenceError("POSITION_CALIBRATION_SEQUENCE_LABEL_COLLISION")

    preset_ref, preset_label = _allocate_position_preset(profile)
    post_identity = _predicted_postwrite_identity(profile, preset_ref, preset_label)
    commands = [
        "ClearAll",
        f"Group {group_id}",
        f'Attribute "Pan" At {PAN_VALUE}',
        f'Attribute "Tilt" At {TILT_VALUE}',
        f'Store Cue 1 Sequence {sequence} "RAW_POSITION" Fade 0 /nc',
        f'Store Preset {preset_ref} "{preset_label}" /selective /nc',
        "ClearAll",
        f"Group {group_id}",
        f"At Preset {preset_ref}",
        f'Store Cue 2 Sequence {sequence} "PRESET_POSITION" Fade 0 /nc',
        f'Label Sequence {sequence} "{sequence_label}" /nc',
        "ClearAll",
    ]
    if not all(command.isascii() for command in commands):
        raise PositionEvidenceError("POSITION_CALIBRATION_COMMAND_NOT_ASCII")

    preview = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY_NOT_REGISTERED_FOR_APPROVAL",
        "show_identity": identity,
        "expected_postwrite_show_identity": post_identity,
        "group": {"id": group_id, "name": group.get("name"), "exact_refs": refs},
        "values": {
            "Pan": PAN_VALUE,
            "Tilt": TILT_VALUE,
            "semantics": "MA2_EXPORTED_RAW_VALUE_NOT_PHYSICAL_UNIT",
        },
        "preset": {
            "reference": preset_ref,
            "type": "POSITION",
            "label": preset_label,
            "agent_owned": True,
        },
        "sequence": {
            "id": sequence,
            "label": sequence_label,
            "raw_cue": 1,
            "preset_cue": 2,
            "executor": None,
        },
        "candidate_commands": commands,
        "expected_readback": (
            "Cue 1 exact PAN/TILT raw values and Cue 2 exact Position Preset "
            "references for every selected member; no foreign member"
        ),
        "cleanup_after_verified": False,
        "position_application_evidence": "UNVERIFIED",
        "ma2_writes": 0,
    }
    encoded = json.dumps(
        preview, sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    ).encode("ascii")
    preview["preview_id"] = hashlib.sha256(encoded).hexdigest()[:16]
    return preview


class PositionCalibrationSkill:
    """Existing WorkflowPlan/Approval boundary for one calibration transaction."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return (
            self.manifest.enabled
            and intent.kind == "verify_position_calibration"
            and state.has(self.manifest.required_state)
        )

    def create_task(self, intent: Intent) -> Task:
        return Task(
            "position-calibration", "Position Calibration", intent,
            self.manifest.id, self.manifest.required_state,
        )

    def plan(
        self, task: Task, state: Any, preferences: dict[str, Any],
    ) -> WorkflowPlan:
        preview = task.intent.parameters.get("position_calibration_preview")
        if not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA:
            raise PositionEvidenceError("POSITION_CALIBRATION_PREVIEW_INVALID")
        commands = preview.get("candidate_commands")
        if not isinstance(commands, list) or len(commands) != 12:
            raise PositionEvidenceError("POSITION_CALIBRATION_COMMAND_PLAN_INVALID")
        titles = (
            "Clear programmer", "Select exact Group", "Set Pan", "Set Tilt",
            "Store raw Cue", "Store Agent-owned Position Preset",
            "Clear programmer", "Reselect exact Group", "Call new Position Preset",
            "Store Preset-linked Cue", "Label Agent-owned Sequence",
            "Clear programmer",
        )
        steps = tuple(
            ActionStep(
                f"step-{index}", title, "command", command, "MODIFY",
                depends_on=(f"step-{index-1}",) if index > 1 else (),
            )
            for index, (title, command) in enumerate(zip(titles, commands), start=1)
        )
        summary = json.dumps(
            {key: preview[key] for key in (
                "preview_id", "show_identity", "expected_postwrite_show_identity",
                "group", "values", "preset", "sequence", "candidate_commands",
                "expected_readback", "cleanup_after_verified",
            )},
            sort_keys=True, ensure_ascii=True, indent=2,
        )
        return WorkflowPlan(
            task,
            (
                Subtask("fresh-verify", "Fresh exact Show/resource check", "Planning"),
                Subtask("preview", "Human review of one calibration transaction", "Planning"),
                Subtask("execute", "Approved calibration writes only", "Execution"),
                Subtask("readback", "One native Sequence Export verification", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Position Calibration"),),
            steps,
            "MODIFY",
            "POSITION CALIBRATION — PREVIEW ONLY\n" + summary,
            ("PREVIEW",),
            preview["expected_readback"],
            "Retain new Agent-owned Preset/Sequence for audit; no automatic Delete",
            True,
            "PREVIEW",
            "READY",
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("position_calibration_preview")
        if (
            plan.task.skill_id != self.manifest.id
            or plan.safety != "MODIFY"
            or not isinstance(preview, dict)
            or preview.get("schema") != PREVIEW_SCHEMA
            or preview.get("group", {}).get("id") != 1
            or preview.get("values", {}).get("Pan") != PAN_VALUE
            or preview.get("values", {}).get("Tilt") != TILT_VALUE
            or preview.get("sequence", {}).get("executor", "INVALID") is not None
            or plan.commands != tuple(preview.get("candidate_commands") or ())
        ):
            raise PositionEvidenceError("POSITION_CALIBRATION_WORKFLOW_INVALID")
        sequence = preview["sequence"].get("id")
        sequence_label = preview["sequence"].get("label")
        preset_ref = preview["preset"].get("reference")
        preset_label = preview["preset"].get("label")
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 1
            or sequence in PROTECTED_SEQUENCES
            or sequence_label != f"ZEN_POSITION_CAL_SEQ{sequence}"
            or not isinstance(preset_ref, str)
            or not _POSITION_REF.fullmatch(preset_ref)
            or preset_label != f"ZEN_POSITION_CAL_P{preset_ref.split('.', 1)[1]}"
        ):
            raise PositionEvidenceError("POSITION_CALIBRATION_OBJECT_IDENTITY_INVALID")
        expected = (
            "ClearAll", "Group 1",
            'Attribute "Pan" At 20', 'Attribute "Tilt" At 30',
            f'Store Cue 1 Sequence {sequence} "RAW_POSITION" Fade 0 /nc',
            f'Store Preset {preset_ref} "{preset_label}" /selective /nc',
            "ClearAll", "Group 1", f"At Preset {preset_ref}",
            f'Store Cue 2 Sequence {sequence} "PRESET_POSITION" Fade 0 /nc',
            f'Label Sequence {sequence} "{sequence_label}" /nc',
            "ClearAll",
        )
        if plan.commands != expected or not all(command.isascii() for command in plan.commands):
            raise PositionEvidenceError("POSITION_CALIBRATION_COMMAND_PLAN_INVALID")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands
def _cue_rows(discovery: Mapping[str, Any], cue_number: int) -> list[Mapping[str, Any]]:
    cues = discovery.get("cues")
    if not isinstance(cues, list):
        raise PositionEvidenceError("POSITION_CALIBRATION_CUES_UNAVAILABLE")
    matches = [
        cue for cue in cues
        if isinstance(cue, Mapping)
        and isinstance(cue.get("number"), Mapping)
        and cue["number"].get("number") == str(cue_number)
        and cue["number"].get("sub_number") in (None, "", "0")
    ]
    if len(matches) != 1:
        raise PositionEvidenceError("POSITION_CALIBRATION_CUE_IDENTITY_UNVERIFIED")
    return [
        row
        for part in matches[0].get("parts", [])
        if isinstance(part, Mapping)
        for row in part.get("cue_data", [])
        if isinstance(row, Mapping)
    ]


def _raw_value_equals(value: object, expected: int) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        return Decimal(value.strip()) == Decimal(expected)
    except InvalidOperation:
        return False


def verify_calibration_raw_content(
    profile: Mapping[str, Any],
    preview: Mapping[str, Any],
    discovery: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify Cue 1 raw PAN/TILT content from the calibration Sequence export."""
    if preview.get("schema") != PREVIEW_SCHEMA:
        raise PositionEvidenceError("POSITION_CALIBRATION_PREVIEW_INVALID")
    if (
        discovery.get("schema") != "zen.sequence_export_discovery.v0.1"
        or discovery.get("status") != "VERIFIED"
        or discovery.get("sequence_no") != preview["sequence"]["id"]
    ):
        raise PositionEvidenceError("POSITION_CALIBRATION_SEQUENCE_CONTENT_UNVERIFIED")
    sha = (discovery.get("xml_discovery") or {}).get("sha256")
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise PositionEvidenceError("POSITION_CALIBRATION_SEQUENCE_SHA_UNAVAILABLE")

    group = _group(profile, preview["group"]["id"])
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    if (
        preview["group"].get("name") != group.get("name")
        or preview["group"].get("exact_refs") != refs
    ):
        raise PositionEvidenceError("POSITION_CALIBRATION_GROUP_IDENTITY_DRIFT")
    expected = set(refs)
    rows = _cue_rows(discovery, preview["sequence"]["raw_cue"])
    if not rows:
        raise PositionEvidenceError("POSITION_CALIBRATION_RAW_CUE_DATA_EMPTY")

    observed: dict[str, set[str]] = {}
    for row in rows:
        channel = row.get("channel")
        ref = _row_ref(channel) if isinstance(channel, Mapping) else None
        if ref is None or ref not in expected:
            raise PositionEvidenceError("POSITION_CALIBRATION_RAW_FOREIGN_MEMBER")
        attribute = str(channel.get("attribute_name") or "").upper()
        if attribute not in {"PAN", "TILT"}:
            continue
        expected_value = PAN_VALUE if attribute == "PAN" else TILT_VALUE
        raw_value = (row.get("raw_values") or {}).get("Value")
        if not _raw_value_equals(raw_value, expected_value):
            raise PositionEvidenceError("POSITION_CALIBRATION_RAW_VALUE_MISMATCH")
        observed.setdefault(ref, set()).add(attribute)

    if set(observed) != expected or any(
        attrs != {"PAN", "TILT"} for attrs in observed.values()
    ):
        raise PositionEvidenceError("POSITION_CALIBRATION_RAW_CONTENT_INCOMPLETE")
    return {
        "schema": RAW_PROOF_SCHEMA,
        "status": "RAW_POSITION_CUE_CONTENT_VERIFIED",
        "sequence": preview["sequence"]["id"],
        "cue": preview["sequence"]["raw_cue"],
        "sequence_export_sha256": sha,
        "matched_channel_refs": sorted(observed),
        "observed_attributes_by_ref": {
            ref: sorted(attrs) for ref, attrs in sorted(observed.items())
        },
        "exported_values": {"PAN": str(PAN_VALUE), "TILT": str(TILT_VALUE)},
        "physical_value_semantics": "NOT_CLAIMED",
    }


def calibration_application_preview(
    profile: Mapping[str, Any], preview: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the narrow application-proof view consumed by the existing binding verifier."""
    preset = preview["preset"]
    return {
        "schema": APPLICATION_PREVIEW_SCHEMA,
        "show_identity": _identity(profile),
        "group": {
            "id": preview["group"]["id"],
            "name": preview["group"]["name"],
            "exact_refs": list(preview["group"]["exact_refs"]),
        },
        "preset": {
            "reference": preset["reference"],
            "type": "POSITION",
            "label": preset["label"],
        },
        "sequence": {
            "id": preview["sequence"]["id"],
            "label": preview["sequence"]["label"],
            "cue": preview["sequence"]["preset_cue"],
            "executor": None,
        },
    }
