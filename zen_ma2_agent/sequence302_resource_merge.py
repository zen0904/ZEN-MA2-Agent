"""Approval-gated resource authoring and existing-Cue merge for Sequence 302.

This is intentionally a narrow acceptance workflow.  It may create only new
Agent-owned Position Presets and empty, reserved Effects 2500-2502, then merge
those resources into existing Sequence 302 Cues 1-29 for exact Group 1 members.
It never allocates a Sequence/Executor and never accepts names as content proof.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .cue_effect_application import cue_effect_capability_is_content_verified
from .existing_cue_dynamic_program_merge import (
    effect_ids_by_cue_ref,
    preset_refs_by_cue_ref,
    protected_content_snapshot,
)
from .position_existing_cue_merge import _fmt
from .test_show_resources import TemplateEffectSpec, template_effect_commands
from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan

PREVIEW_SCHEMA = "zen.sequence302_resource_merge_preview.v0.1"
VERIFY_SCHEMA = "zen.sequence302_resource_merge_verification.v0.1"
TARGET_SEQUENCE = 302
TARGET_GROUP = 1
TARGET_CUES = tuple(range(1, 30))
TARGET_REFS = tuple(f"{number}.1" for number in range(101, 109))
EFFECT_SPECS = (
    TemplateEffectSpec(2500, "FX_DIM_CHASE_SLOW", 30),
    TemplateEffectSpec(2501, "FX_DIM_CHASE_MED", 60),
    TemplateEffectSpec(2502, "FX_DIM_CHASE_FAST", 120),
)
LEGACY_ACTION_IDS = frozenset({"97d3a82f1220", "a9dd416ef92b"})
_POSITION_REF = re.compile(r"2\.([1-9]\d*)\Z")


class Sequence302ResourceMergeError(ValueError):
    pass


def expand_explicit_raw_plan(
    artifact: Mapping[str, Any], cue_labels: Mapping[int, str],
) -> list[dict[str, Any]]:
    """Expand the committed raw plan while binding only fresh native Cue labels."""
    if artifact.get("schema") != "zen.sequence302_explicit_raw_plan.v0.1":
        raise Sequence302ResourceMergeError("SEQ302_RAW_PLAN_ARTIFACT_INVALID")
    target = artifact.get("target")
    if not isinstance(target, Mapping) or target.get("sequence") != 302 or target.get("group") != 1 or tuple(target.get("exact_refs") or ()) != TARGET_REFS:
        raise Sequence302ResourceMergeError("SEQ302_RAW_PLAN_TARGET_INVALID")
    patterns = {
        row.get("position_name"): row.get("fixtures")
        for row in artifact.get("patterns", [])
        if isinstance(row, Mapping)
    }
    cues = artifact.get("cues")
    if not isinstance(cues, list) or len(cues) != 29 or set(cue_labels) != set(TARGET_CUES):
        raise Sequence302ResourceMergeError("SEQ302_RAW_PLAN_CUES_INVALID")
    result = []
    for expected, cue in zip(TARGET_CUES, cues):
        if not isinstance(cue, Mapping) or cue.get("cue_number") != expected:
            raise Sequence302ResourceMergeError("SEQ302_RAW_PLAN_CUES_INVALID")
        name = cue.get("position_name")
        if name not in patterns:
            raise Sequence302ResourceMergeError("SEQ302_RAW_PLAN_PATTERN_MISSING")
        result.append({
            "cue_number": expected,
            "cue_label": str(cue_labels[expected]),
            "position_name": str(name),
            "fixtures": deepcopy(patterns[name]),
            "effect_id": cue.get("effect_id"),
        })
    return _normalize_plan(result)


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _require_target(position_preview: Mapping[str, Any], pre_discovery: Mapping[str, Any]) -> None:
    target = position_preview.get("target_sequence")
    group = position_preview.get("group")
    if not isinstance(target, Mapping) or not isinstance(group, Mapping):
        raise Sequence302ResourceMergeError("SEQ302_TARGET_EVIDENCE_MISSING")
    if target.get("id") != TARGET_SEQUENCE or target.get("cue_start") != 1 or target.get("cue_end") != 29:
        raise Sequence302ResourceMergeError("SEQ302_EXACT_SEQUENCE_AND_CUE_RANGE_REQUIRED")
    if group.get("id") != TARGET_GROUP or tuple(group.get("exact_refs") or ()) != TARGET_REFS:
        raise Sequence302ResourceMergeError("SEQ302_EXACT_GROUP_IDENTITY_REQUIRED")
    if "9999" in {str(ref).split(".", 1)[0] for ref in group.get("exact_refs") or ()}:
        raise Sequence302ResourceMergeError("PROTECTED_FIXTURE_9999")
    if pre_discovery.get("status") != "VERIFIED" or pre_discovery.get("sequence_no") != TARGET_SEQUENCE:
        raise Sequence302ResourceMergeError("SEQ302_FRESH_NATIVE_PRE_EXPORT_REQUIRED")
    cue_numbers = []
    for cue in pre_discovery.get("cues", []):
        if not isinstance(cue, Mapping) or not isinstance(cue.get("number"), Mapping):
            continue
        raw = cue["number"].get("number")
        sub = cue["number"].get("sub_number")
        if str(raw).isdigit() and sub in (None, "", "0", 0):
            cue_numbers.append(int(raw))
    if tuple(sorted(cue_numbers)) != TARGET_CUES:
        raise Sequence302ResourceMergeError("SEQ302_EXACT_CUES_1_29_REQUIRED")


def _validate_effect_empty_evidence(evidence: Mapping[int, Mapping[str, Any]]) -> None:
    if set(evidence) != {2500, 2501, 2502}:
        raise Sequence302ResourceMergeError("SEQ302_EFFECT_SLOT_EVIDENCE_INCOMPLETE")
    for effect_id in (2500, 2501, 2502):
        row = evidence[effect_id]
        if (
            row.get("fresh") is not True
            or row.get("effect_id") != effect_id
            or row.get("pool_identity") != "ABSENT"
            or row.get("line_content") != "EMPTY"
            or row.get("qty_values") not in ([], ())
            or row.get("attribute_names") not in ([], ())
        ):
            raise Sequence302ResourceMergeError(f"SEQ302_EFFECT_{effect_id}_NOT_FRESH_EMPTY")


def _validate_dimmer_evidence(evidence: Mapping[str, Any]) -> None:
    if (
        evidence.get("status") != "SHOW_BOUND_VERIFIED"
        or evidence.get("group_id") != TARGET_GROUP
        or tuple(evidence.get("exact_refs") or ()) != TARGET_REFS
        or str(evidence.get("attribute") or "").upper() != "DIM"
    ):
        raise Sequence302ResourceMergeError("SEQ302_DIM_APPLICABILITY_UNVERIFIED")


def _normalize_plan(plan: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(plan, Sequence) or isinstance(plan, (str, bytes)) or len(plan) != 29:
        raise Sequence302ResourceMergeError("SEQ302_EXPLICIT_RAW_PLAN_29_CUES_REQUIRED")
    result: list[dict[str, Any]] = []
    for expected, item in zip(TARGET_CUES, plan):
        if not isinstance(item, Mapping) or item.get("cue_number") != expected:
            raise Sequence302ResourceMergeError("SEQ302_EXPLICIT_RAW_PLAN_CUE_ORDER_INVALID")
        fixtures = item.get("fixtures")
        if not isinstance(fixtures, list) or tuple(str(row.get("fixture_ref")) for row in fixtures if isinstance(row, Mapping)) != TARGET_REFS:
            raise Sequence302ResourceMergeError(f"SEQ302_RAW_REFS_INVALID_CUE_{expected}")
        normalized_fixtures = []
        for row in fixtures:
            pan, tilt = row.get("pan"), row.get("tilt")
            if isinstance(pan, bool) or not isinstance(pan, (int, float)) or isinstance(tilt, bool) or not isinstance(tilt, (int, float)):
                raise Sequence302ResourceMergeError(f"SEQ302_RAW_POSITION_INVALID_CUE_{expected}")
            normalized_fixtures.append({"fixture_ref": str(row["fixture_ref"]), "pan": float(pan), "tilt": float(tilt)})
        effect_id = item.get("effect_id")
        if effect_id is not None and effect_id not in {2500, 2501, 2502}:
            raise Sequence302ResourceMergeError(f"SEQ302_EFFECT_PLAN_INVALID_CUE_{expected}")
        result.append({
            "cue_number": expected,
            "cue_label": str(item.get("cue_label") or ""),
            "position_name": str(item.get("position_name") or f"CUE_{expected:02d}"),
            "fixtures": normalized_fixtures,
            "effect_id": effect_id,
        })
    return result


def _allocate_position_presets(current_presets: Sequence[Mapping[str, Any]], plan: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    occupied: set[int] = set()
    labels: set[str] = set()
    for row in current_presets:
        if not isinstance(row, Mapping):
            continue
        match = _POSITION_REF.fullmatch(str(row.get("reference") or ""))
        if match:
            occupied.add(int(match.group(1)))
        if isinstance(row.get("name"), str):
            labels.add(row["name"])
    resources: list[dict[str, Any]] = []
    by_matrix: dict[str, str] = {}
    next_number = 1
    for cue in plan:
        matrix = _sha(cue["fixtures"])
        if matrix in by_matrix:
            continue
        while next_number in occupied:
            next_number += 1
        reference = f"2.{next_number}"
        safe_name = re.sub(r"[^A-Z0-9_]+", "_", str(cue["position_name"]).upper()).strip("_") or f"P{next_number}"
        label = f"ZEN_SEQ302_POS_{safe_name}"[:32]
        if label in labels:
            raise Sequence302ResourceMergeError("SEQ302_POSITION_LABEL_COLLISION")
        resource = {
            "reference": reference,
            "label": label,
            "type": "POSITION",
            "agent_owned": True,
            "raw_plan_sha256": matrix,
            "fixtures": deepcopy(cue["fixtures"]),
        }
        resources.append(resource)
        by_matrix[matrix] = reference
        occupied.add(next_number)
        labels.add(label)
        next_number += 1
    return resources, by_matrix


def _position_store_commands(resource: Mapping[str, Any]) -> list[str]:
    commands = ["ClearAll"]
    grouped: dict[tuple[str, str], list[str]] = {}
    for row in resource["fixtures"]:
        grouped.setdefault((_fmt(row["pan"]), _fmt(row["tilt"])), []).append(row["fixture_ref"])
    for (pan, tilt), refs in grouped.items():
        commands.extend(("Fixture " + " + ".join(refs), f'Attribute "Pan" At {pan}', f'Attribute "Tilt" At {tilt}'))
    commands.extend((f'Store Preset {resource["reference"]} "{resource["label"]}" /selective /nc', "ClearAll"))
    return commands


def build_sequence302_resource_merge_preview(
    *,
    position_preview: Mapping[str, Any],
    pre_discovery: Mapping[str, Any],
    explicit_raw_plan: Sequence[Mapping[str, Any]],
    current_presets: Sequence[Mapping[str, Any]],
    fresh_effect_empty_evidence: Mapping[int, Mapping[str, Any]],
    dimmer_applicability_evidence: Mapping[str, Any],
    effect_application_capability: object,
    source_action_id: str | None = None,
) -> dict[str, Any]:
    if source_action_id in LEGACY_ACTION_IDS:
        raise Sequence302ResourceMergeError("SEQ302_LEGACY_ACTION_REPLAY_FORBIDDEN")
    _require_target(position_preview, pre_discovery)
    if not cue_effect_capability_is_content_verified(effect_application_capability):
        raise Sequence302ResourceMergeError("SEQ302_EFFECT_APPLICATION_GRAMMAR_UNVERIFIED")
    _validate_effect_empty_evidence(fresh_effect_empty_evidence)
    _validate_dimmer_evidence(dimmer_applicability_evidence)
    plan = _normalize_plan(explicit_raw_plan)
    metadata = {int(row["number"]): str(row.get("name") or "") for row in position_preview["target_sequence"].get("cue_metadata", [])}
    if set(metadata) != set(TARGET_CUES):
        raise Sequence302ResourceMergeError("SEQ302_CUE_METADATA_INCOMPLETE")
    for cue in plan:
        if cue["cue_label"] != metadata[cue["cue_number"]]:
            raise Sequence302ResourceMergeError(f"SEQ302_CUE_LABEL_DRIFT_{cue['cue_number']}")

    # No existing target-Group Effect may be silently replaced or accumulated.
    existing = effect_ids_by_cue_ref(pre_discovery, cue_numbers=TARGET_CUES, target_fixture_refs=TARGET_REFS)
    if any(ids for refs in existing.values() for ids in refs.values()):
        raise Sequence302ResourceMergeError("SEQ302_EXISTING_TARGET_EFFECT_CONTENT_CONFLICT")

    presets, matrix_refs = _allocate_position_presets(current_presets, plan)
    preset_by_ref = {item["reference"]: item for item in presets}
    cue_updates = []
    for cue in plan:
        reference = matrix_refs[_sha(cue["fixtures"])]
        cue_updates.append({**deepcopy(cue), "position_preset_ref": reference, "position_preset_label": preset_by_ref[reference]["label"]})

    protected = protected_content_snapshot(
        pre_discovery,
        cue_effects={number: ({"id": next(item["effect_id"] for item in cue_updates if item["cue_number"] == number)} if next(item["effect_id"] for item in cue_updates if item["cue_number"] == number) else None) for number in TARGET_CUES},
        target_fixture_refs=TARGET_REFS,
        cue_presets={number: [{"attribute_names": ["PAN", "TILT"]}] for number in TARGET_CUES},
    )
    commands: list[str] = []
    for resource in presets:
        commands.extend(_position_store_commands(resource))
    for spec in EFFECT_SPECS:
        commands.extend(template_effect_commands(spec))
    for cue in cue_updates:
        commands.extend(("ClearAll", f"Group {TARGET_GROUP}", f"At Preset {cue['position_preset_ref']}", f"Store Cue {cue['cue_number']} Sequence {TARGET_SEQUENCE} /merge /cueonly /nc"))
        if cue["effect_id"] is not None:
            commands.extend(("ClearAll", f"Group {TARGET_GROUP}", f"At Effect {cue['effect_id']}", f"Store Cue {cue['cue_number']} Sequence {TARGET_SEQUENCE} /merge /cueonly /nc"))
    commands.append("ClearAll")
    if any(not command.isascii() for command in commands):
        raise Sequence302ResourceMergeError("NON_ASCII_MA_TEXT")

    preview = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY",
        "show_identity": deepcopy(position_preview.get("show_identity")),
        "target_sequence": deepcopy(position_preview["target_sequence"]),
        "group": deepcopy(position_preview["group"]),
        "position_presets_to_create": presets,
        "effects_to_create": [spec.summary() for spec in EFFECT_SPECS],
        "effect_preconditions": deepcopy(dict(fresh_effect_empty_evidence)),
        "dimmer_applicability_evidence": deepcopy(dict(dimmer_applicability_evidence)),
        "cue_updates": cue_updates,
        "pre_protected_content_sha256": protected["sha256"],
        "candidate_commands": commands,
        "command_plan_sha256": hashlib.sha256("\n".join(commands).encode("ascii")).hexdigest(),
        "write_scope": {
            "existing_sequence": 302, "existing_cues": [1, 29], "group": 1,
            "create_position_presets": True, "create_effect_ids": [2500, 2501, 2502],
            "allocate_sequence": False, "allocate_executor": False, "assign_executor": False,
            "modify_patch": False, "modify_fixture_identity_or_type": False,
        },
        "approval": "EXPLICIT_OWNER_APPROVAL_REQUIRED",
        "native_postwrite_verification": "SEQUENCE_EXPORT_RAW_PAN_TILT_PRESET_EFFECT_AND_PROTECTED_CONTENT",
        "legacy_action_replay": False,
        "ma2_writes": 0,
    }
    preview["preview_id"] = _sha(preview)[:16]
    return preview


def verify_sequence302_resource_merge(
    preview: Mapping[str, Any],
    post_discovery: Mapping[str, Any],
    *,
    post_preset_rows: Sequence[Mapping[str, Any]],
    post_effect_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if preview.get("schema") != PREVIEW_SCHEMA or post_discovery.get("status") != "VERIFIED" or post_discovery.get("sequence_no") != 302:
        raise Sequence302ResourceMergeError("SEQ302_POST_EXPORT_UNVERIFIED")
    presets = preview.get("position_presets_to_create")
    if not isinstance(presets, list):
        raise Sequence302ResourceMergeError("SEQ302_PREVIEW_INVALID")
    by_ref = {str(row.get("reference")): row for row in post_preset_rows if isinstance(row, Mapping)}
    for resource in presets:
        row = by_ref.get(resource["reference"])
        if not row or row.get("preset_type") != "POSITION" or row.get("name") != resource["label"]:
            raise Sequence302ResourceMergeError(f"SEQ302_POSITION_PRESET_IDENTITY_MISMATCH_{resource['reference']}")
    by_effect = {row.get("number"): row for row in post_effect_rows if isinstance(row, Mapping)}
    for spec in EFFECT_SPECS:
        row = by_effect.get(spec.effect_id)
        detail = row.get("template_detail") if isinstance(row, Mapping) else None
        if not row or row.get("name") != spec.label or not isinstance(detail, Mapping) or detail.get("status") != "VERIFIED" or detail.get("kind") != "TEMPLATE" or not detail.get("qty_values"):
            raise Sequence302ResourceMergeError(f"SEQ302_EFFECT_CONTENT_UNVERIFIED_{spec.effect_id}")
        attrs = {str(value).upper() for value in row.get("attributes") or []}
        if "DIM" not in attrs:
            raise Sequence302ResourceMergeError(f"SEQ302_EFFECT_DIM_ATTRIBUTE_UNVERIFIED_{spec.effect_id}")

    expected_effects = {item["cue_number"]: item["effect_id"] for item in preview["cue_updates"]}
    actual_effects = effect_ids_by_cue_ref(post_discovery, cue_numbers=TARGET_CUES, target_fixture_refs=TARGET_REFS)
    actual_presets = preset_refs_by_cue_ref(post_discovery, cue_numbers=TARGET_CUES, target_fixture_refs=TARGET_REFS)
    expected_raw = {(item["cue_number"], row["fixture_ref"], attr): str(value) for item in preview["cue_updates"] for row in item["fixtures"] for attr, value in (("PAN", row["pan"]), ("TILT", row["tilt"]))}
    observed_raw: dict[tuple[int, str, str], str] = {}
    for cue in post_discovery.get("cues", []):
        if not isinstance(cue, Mapping) or not isinstance(cue.get("number"), Mapping) or not str(cue["number"].get("number")).isdigit():
            continue
        number = int(cue["number"]["number"])
        for part in cue.get("parts", []):
            for row in part.get("cue_data", []) if isinstance(part, Mapping) else []:
                channel = row.get("channel") if isinstance(row, Mapping) else None
                if not isinstance(channel, Mapping):
                    continue
                root, sub = channel.get("fixture_id"), channel.get("subfixture_id")
                ref = f"{root}.{sub}" if sub not in (None, "") else str(root)
                attr = str(channel.get("attribute_name") or "").upper()
                if (number, ref, attr) in expected_raw:
                    observed_raw[(number, ref, attr)] = str((row.get("raw_values") or {}).get("Value"))
    for key, expected in expected_raw.items():
        try:
            if float(observed_raw[key]) != float(expected):
                raise KeyError
        except (KeyError, TypeError, ValueError):
            raise Sequence302ResourceMergeError(f"SEQ302_RAW_POSITION_MISMATCH_{key[0]}_{key[1]}_{key[2]}")
    for item in preview["cue_updates"]:
        number = str(item["cue_number"])
        for ref in TARGET_REFS:
            if item["position_preset_ref"] not in actual_presets[number][ref]:
                raise Sequence302ResourceMergeError(f"SEQ302_PRESET_APPLICATION_MISMATCH_{number}_{ref}")
            expected = {item["effect_id"]} if item["effect_id"] is not None else set()
            if set(actual_effects[number][ref]) != expected:
                raise Sequence302ResourceMergeError(f"SEQ302_EFFECT_APPLICATION_MISMATCH_{number}_{ref}")
    protected = protected_content_snapshot(
        post_discovery,
        cue_effects={item["cue_number"]: ({"id": item["effect_id"]} if item["effect_id"] else None) for item in preview["cue_updates"]},
        target_fixture_refs=TARGET_REFS,
        cue_presets={item["cue_number"]: [{"attribute_names": ["PAN", "TILT"]}] for item in preview["cue_updates"]},
    )
    if protected["sha256"] != preview.get("pre_protected_content_sha256"):
        raise Sequence302ResourceMergeError("SEQ302_PROTECTED_CONTENT_CHANGED")
    return {
        "schema": VERIFY_SCHEMA, "status": "VERIFIED", "sequence": 302,
        "cue_count": 29, "position_preset_count": len(presets), "effect_count": 3,
        "raw_position_values_verified": len(expected_raw), "protected_content": "UNCHANGED",
        "post_export_sha256": (post_discovery.get("xml_discovery") or {}).get("sha256"),
    }


class Sequence302ResourceMergeSkill:
    """Existing approval boundary for the exact validated Preview artifact."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return (
            self.manifest.enabled
            and intent.kind == "merge_sequence302_authored_resources"
            and state.has(self.manifest.required_state)
        )

    def create_task(self, intent: Intent) -> Task:
        return Task(
            "sequence302-resource-merge",
            "Sequence 302 Resource Authoring Merge",
            intent,
            self.manifest.id,
            self.manifest.required_state,
        )

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("sequence302_resource_merge_preview")
        if not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA:
            raise Sequence302ResourceMergeError("SEQ302_PREVIEW_INVALID")
        commands = preview.get("candidate_commands")
        if not isinstance(commands, list) or not commands or commands[-1] != "ClearAll":
            raise Sequence302ResourceMergeError("SEQ302_COMMAND_PLAN_INVALID")
        steps = tuple(
            ActionStep(
                f"sequence302-resource-merge-{index}",
                "Approved bounded resource authoring / existing-Cue merge",
                "command",
                command,
                "MODIFY",
                depends_on=(f"sequence302-resource-merge-{index - 1}",) if index > 1 else (),
            )
            for index, command in enumerate(commands, 1)
        )
        summary = (
            "SEQUENCE 302 RESOURCE AUTHORING MERGE - PREVIEW\n"
            f"Position Presets to create: {len(preview['position_presets_to_create'])}\n"
            "Effects to create: 2500-2502 (fresh empty evidence required)\n"
            "Target: existing Sequence 302 Cues 1-29, Group 1 exact Fixtures 101.1-108.1\n"
            "Store mode: /merge /cueonly\n"
            "No Sequence/Executor allocation or assignment. Explicit owner approval required."
        )
        return WorkflowPlan(
            task,
            (
                Subtask("fresh-evidence", "Verify exact target and empty resource identities", "Planning"),
                Subtask("author-resources", "Create Agent-owned Position Presets and Effects", "Execution"),
                Subtask("merge", "Apply resources to existing Cues with /merge /cueonly", "Execution"),
                Subtask("verify", "Native Sequence Export and resource-content verification", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Sequence 302 Resource Authoring Merge"),),
            steps,
            "MODIFY",
            summary,
            ("PREVIEW",),
            preview["native_postwrite_verification"],
            "No automatic rollback; retain native evidence and stop on first mismatch.",
            True,
            "PREVIEW",
            "READY",
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("sequence302_resource_merge_preview")
        if (
            plan.task.skill_id != self.manifest.id
            or plan.safety != "MODIFY"
            or not isinstance(preview, dict)
            or preview.get("schema") != PREVIEW_SCHEMA
            or preview.get("legacy_action_replay") is not False
            or plan.commands != tuple(preview.get("candidate_commands") or ())
            or hashlib.sha256("\n".join(plan.commands).encode("ascii")).hexdigest()
            != preview.get("command_plan_sha256")
        ):
            raise Sequence302ResourceMergeError("SEQ302_WORKFLOW_INVALID")
        forbidden = ("Fixture 9999", "Assign Sequence", "At Executor", "Store Sequence")
        if any(any(token in command for token in forbidden) for command in plan.commands):
            raise Sequence302ResourceMergeError("SEQ302_FORBIDDEN_COMMAND")
        for command in plan.commands:
            if command.startswith("Store Cue ") and not re.fullmatch(
                r"Store Cue (?:[1-9]|1\d|2\d) Sequence 302 /merge /cueonly /nc", command
            ):
                raise Sequence302ResourceMergeError("SEQ302_STORE_GRAMMAR_INVALID")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands


__all__ = [
    "EFFECT_SPECS", "LEGACY_ACTION_IDS", "PREVIEW_SCHEMA", "Sequence302ResourceMergeError",
    "TARGET_CUES", "TARGET_GROUP", "TARGET_REFS", "TARGET_SEQUENCE",
    "build_sequence302_resource_merge_preview", "verify_sequence302_resource_merge",
    "expand_explicit_raw_plan", "Sequence302ResourceMergeSkill",
]
