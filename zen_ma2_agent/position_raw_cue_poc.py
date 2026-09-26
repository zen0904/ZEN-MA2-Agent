"""Bounded raw PAN/TILT Cue content proof, separate from Preset applicability."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from .allocation import first_free_from_front
from .models import Intent
from .position_application_evidence import (
    PositionEvidenceError, _exact_refs, _group,
    _identity, _position_capability, _row_ref,
)
from .protected_objects import PROTECTED_SEQUENCES
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


PREVIEW_SCHEMA = "zen.position_raw_cue_poc_preview.v0.1"
CONTENT_SCHEMA = "zen.position_raw_cue_content_proof.v0.1"
PAN_VALUE = 20
TILT_VALUE = 30
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def build_position_raw_cue_preview(profile: Mapping[str, Any], *, group_id: int) -> dict[str, Any]:
    """Use fresh exact Show resources; values are fixed engineering probe data."""
    if group_id != 1 or isinstance(group_id, bool):
        raise PositionEvidenceError("RAW_POSITION_POC_GROUP_NOT_ALLOWLISTED")
    resources = profile.get("resources")
    required = ("groups", "group_membership", "fixtures", "fixture_geometry",
                "fixture_type_profiles", "sequences", "presets")
    if not isinstance(resources, Mapping) or any(
        not isinstance(resources.get(key), Mapping) or resources[key].get("status") != "SUPPORTED"
        for key in required
    ):
        raise PositionEvidenceError("FRESH_READ_ONLY_STATE_REQUIRED")
    identity = _identity(profile)
    group = _group(profile, group_id)
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    sequences = profile.get("sequences")
    if not isinstance(sequences, list):
        raise PositionEvidenceError("SEQUENCE_INVENTORY_UNAVAILABLE")
    occupied = {item.get("number") for item in sequences if isinstance(item, Mapping)}
    sequence = first_free_from_front(occupied, protected=PROTECTED_SEQUENCES, start=1, end=9999)
    label = f"ZEN_POSITION_RAW_POC_SEQ{sequence}"
    if label in {item.get("name") for item in sequences if isinstance(item, Mapping)}:
        raise PositionEvidenceError("AGENT_OWNED_SEQUENCE_LABEL_COLLISION")
    commands = [
        "ClearAll", f"Group {group_id}", f'Attribute "Pan" At {PAN_VALUE}',
        f'Attribute "Tilt" At {TILT_VALUE}',
        f'Store Cue 1 Sequence {sequence} "POSITION_RAW_POC" Fade 0 /nc',
        f'Label Sequence {sequence} "{label}" /nc', "ClearAll",
    ]
    if not all(command.isascii() for command in commands):
        raise PositionEvidenceError("RAW_POSITION_POC_COMMAND_NOT_ASCII")
    preview = {
        "schema": PREVIEW_SCHEMA, "status": "PREVIEW_ONLY_NOT_REGISTERED_FOR_APPROVAL",
        "show_identity": identity,
        "group": {"id": group_id, "name": group.get("name"), "exact_refs": refs},
        "values": {"Pan": PAN_VALUE, "Tilt": TILT_VALUE, "semantics": "MA2_ATTRIBUTE_NATURAL_VALUE_UNVERIFIED"},
        "sequence": {"id": sequence, "label": label, "cue": 1, "executor": None},
        "candidate_commands": commands,
        "expected_readback": "Native Sequence Export Cue 1 has PAN and TILT CueData for every exact selected member and no foreign member",
        "rollback_scope": f"Only newly created Agent-owned Sequence {sequence}, after exact identity proof; no automatic Delete",
        "position_application_evidence": "UNVERIFIED",
        "ma2_writes": 0,
    }
    encoded = json.dumps(preview, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    preview["preview_id"] = hashlib.sha256(encoded).hexdigest()[:16]
    return preview


class PositionRawCuePocSkill:
    """Existing WorkflowPlan/Approval boundary for one exact raw-position probe."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return (self.manifest.enabled and intent.kind == "verify_position_raw_cue"
                and state.has(self.manifest.required_state))

    def create_task(self, intent: Intent) -> Task:
        return Task("position-raw-cue-poc", "Raw Position Cue POC", intent,
                    self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("position_raw_preview")
        if not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA:
            raise PositionEvidenceError("RAW_POSITION_POC_PREVIEW_INVALID")
        commands = preview.get("candidate_commands")
        if not isinstance(commands, list) or len(commands) != 7:
            raise PositionEvidenceError("RAW_POSITION_POC_COMMAND_PLAN_INVALID")
        titles = ("Clear programmer", "Select exact Group", "Set Pan", "Set Tilt",
                  "Store new Cue", "Label Agent-owned Sequence", "Clear programmer")
        steps = tuple(ActionStep(f"step-{index}", title, "command", command, "MODIFY",
                                 depends_on=(f"step-{index-1}",) if index > 1 else ())
                      for index, (title, command) in enumerate(zip(titles, commands), start=1))
        summary = json.dumps({key: preview[key] for key in (
            "preview_id", "show_identity", "group", "values", "sequence",
            "candidate_commands", "expected_readback", "rollback_scope",
        )}, sort_keys=True, ensure_ascii=True, indent=2)
        return WorkflowPlan(task, (
            Subtask("fresh-verify", "Fresh read-only identity check", "Planning"),
            Subtask("preview", "Human review of exact command plan", "Planning"),
            Subtask("execute", "Approved raw Cue probe only", "Execution"),
            Subtask("readback", "Native Sequence Export PAN/TILT content proof", "Verification"),
        ), (SkillGraphNode("root", self.manifest.id, "Raw Position Cue POC"),),
            steps, "MODIFY", "RAW POSITION CUE POC — PREVIEW ONLY\n" + summary,
            ("PREVIEW",), preview["expected_readback"], preview["rollback_scope"],
            True, "PREVIEW", "READY")

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("position_raw_preview")
        if (plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY"
                or not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA
                or preview.get("group", {}).get("id") != 1
                or preview.get("values", {}).get("Pan") != PAN_VALUE
                or preview.get("values", {}).get("Tilt") != TILT_VALUE
                or plan.commands != tuple(preview.get("candidate_commands") or ())
                or preview.get("sequence", {}).get("executor", "INVALID") is not None):
            raise PositionEvidenceError("RAW_POSITION_POC_WORKFLOW_INVALID")
        sequence = preview["sequence"].get("id")
        label = preview["sequence"].get("label")
        if (isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1
                or sequence in PROTECTED_SEQUENCES
                or label != f"ZEN_POSITION_RAW_POC_SEQ{sequence}"
                or preview["sequence"].get("cue") != 1):
            raise PositionEvidenceError("RAW_POSITION_POC_SEQUENCE_INVALID")
        expected = (
            "ClearAll", "Group 1", 'Attribute "Pan" At 20', 'Attribute "Tilt" At 30',
            f'Store Cue 1 Sequence {sequence} "POSITION_RAW_POC" Fade 0 /nc',
            f'Label Sequence {sequence} "{label}" /nc', "ClearAll",
        )
        if plan.commands != expected or not all(command.isascii() for command in plan.commands):
            raise PositionEvidenceError("RAW_POSITION_POC_COMMAND_PLAN_INVALID")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands


def verify_raw_position_cue_content(
    profile: Mapping[str, Any], preview: Mapping[str, Any], discovery: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove PAN/TILT CueData presence, never Preset applicability or value units."""
    if preview.get("schema") != PREVIEW_SCHEMA or preview.get("show_identity") != _identity(profile):
        raise PositionEvidenceError("RAW_POSITION_POC_SHOW_IDENTITY_DRIFT")
    group = _group(profile, preview.get("group", {}).get("id"))
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    if (preview["group"].get("name") != group.get("name")
            or preview["group"].get("exact_refs") != refs):
        raise PositionEvidenceError("RAW_POSITION_POC_GROUP_IDENTITY_DRIFT")
    if (discovery.get("schema") != "zen.sequence_export_discovery.v0.1"
            or discovery.get("status") != "VERIFIED"
            or discovery.get("sequence_no") != preview["sequence"]["id"]):
        raise PositionEvidenceError("RAW_POSITION_SEQUENCE_CONTENT_UNVERIFIED")
    sha = (discovery.get("xml_discovery") or {}).get("sha256")
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise PositionEvidenceError("RAW_POSITION_SEQUENCE_EXPORT_SHA_UNAVAILABLE")
    cues = discovery.get("cues")
    if not isinstance(cues, list) or len(cues) != 1:
        raise PositionEvidenceError("RAW_POSITION_CUE_NOT_EXACTLY_ONE")
    cue = cues[0]
    number = cue.get("number") if isinstance(cue, Mapping) else None
    if (not isinstance(number, Mapping) or number.get("number") != "1"
            or number.get("sub_number") not in (None, "", "0")):
        raise PositionEvidenceError("RAW_POSITION_CUE_ONE_UNVERIFIED")
    rows = [row for part in cue.get("parts", []) if isinstance(part, Mapping)
            for row in part.get("cue_data", []) if isinstance(row, Mapping)]
    if not rows:
        raise PositionEvidenceError("RAW_POSITION_CUE_DATA_EMPTY")
    # Raw Attribute writes preserve the exact Group selection identity in the
    # native Sequence export.  Do not apply the Preset-binding subfixture
    # normalization here: a single-instance parent selected as "101" exports
    # PAN/TILT as fixture_id="101", not synthetic "101.1".
    expected = set(refs)
    observed: dict[str, set[str]] = {}
    for row in rows:
        channel = row.get("channel")
        ref = _row_ref(channel) if isinstance(channel, Mapping) else None
        if ref is None or ref not in expected:
            raise PositionEvidenceError("RAW_POSITION_FOREIGN_OR_UNKNOWN_MEMBER")
        attribute = str(channel.get("attribute_name") or "").upper()
        if attribute in {"PAN", "TILT"}:
            values = row.get("raw_values")
            if not isinstance(values, Mapping) or not isinstance(values.get("Value"), str) or not values["Value"].strip():
                raise PositionEvidenceError("RAW_POSITION_VALUE_FIELD_UNAVAILABLE")
            observed.setdefault(ref, set()).add(attribute)
    if set(observed) != expected or any(attrs != {"PAN", "TILT"} for attrs in observed.values()):
        raise PositionEvidenceError("RAW_POSITION_PAN_TILT_CONTENT_INCOMPLETE")
    return {
        "schema": CONTENT_SCHEMA, "status": "RAW_POSITION_CUE_CONTENT_VERIFIED",
        "show_identity": _identity(profile), "group_id": group["group_id"],
        "group_name": group["name"], "exact_group_refs": refs,
        "sequence": preview["sequence"]["id"], "cue": 1,
        "sequence_export_sha256": sha,
        "matched_channel_refs": sorted(observed),
        "observed_attributes_by_ref": {ref: sorted(attrs) for ref, attrs in sorted(observed.items())},
        "value_semantics": "NOT_VERIFIED", "position_application_evidence": "UNVERIFIED",
        "position_application_binding_recorded": False,
    }
