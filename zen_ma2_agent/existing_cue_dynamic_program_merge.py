"""Bounded Effect + Position merge for verified existing grandMA2 Cues.

This capability consumes an explicit artistic per-Cue plan plus fresh native
Sequence, Group, Effect, geometry and Position-calibration evidence.  It can
only emit the real-machine-verified ``Group <n>; At Effect <n>`` grammar and
explicit PAN/TILT values followed by ``Store Cue ... /merge /cueonly``.

It never allocates or creates a Sequence, Effect, Group, Executor or fixture,
and it is not a generic MA command interface.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .cue_effect_application import cue_effect_capability_is_content_verified
from .models import Intent
from .position_application_evidence import _canonical_position_row_ref
from .position_existing_cue_merge import (
    ExistingPositionMergeError,
    _bounded_value,
    _cue_label,
    _cue_number,
    _cue_rows,
    _fmt,
    _pattern_offsets,
    _row_attribute,
    build_existing_position_merge_preview,
)
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


PREVIEW_SCHEMA = "zen.existing_cue_dynamic_program_merge_preview.v0.1"
VERIFY_SCHEMA = "zen.existing_cue_dynamic_program_merge_verification.v0.1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_POSITION_FAMILY = {
    "PAN", "TILT", "VIRTUAL_POSITION_MODE", "MARK", "STAGEX", "STAGEY",
    "STAGEZ", "FLIP", "DIST",
}
_DYNAMIC_INTENTS = {
    "DIMMER_CHASE_SLOW", "DIMMER_CHASE_MED", "DIMMER_CHASE_FAST",
    "ALTERNATE", "PULSE", "HIT", "BUILD",
}
_NO_EFFECT_INTENTS = {"STATIC_LOOK", "RELEASE", "BLACKOUT", "RESET"}
_POSITION_PATTERNS = {
    "CENTER", "LEFT", "RIGHT", "FRONT", "UPSTAGE", "NARROW_FAN",
    "WIDE_FAN", "CROSS", "ALTERNATE", "EXPLODE", "COLLAPSE",
}


class ExistingCueDynamicProgramMergeError(ValueError):
    pass


def _require_sha(value: object, code: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ExistingCueDynamicProgramMergeError(code)
    return value


def _show_identity(profile: Mapping[str, Any]) -> Mapping[str, Any]:
    identity = profile.get("show_identity")
    if not isinstance(identity, Mapping) or not identity.get("value"):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_SHOW_IDENTITY_UNAVAILABLE")
    return identity


def _effect_id(row: Mapping[str, Any]) -> int | None:
    effect = row.get("effect")
    parts = effect.get("no_components") if isinstance(effect, Mapping) else None
    if not isinstance(parts, list) or not parts:
        return None
    last = str(parts[-1])
    return int(last) if last.isdigit() and int(last) > 0 else None


def _canonical_ref(profile: Mapping[str, Any], row: Mapping[str, Any]) -> str | None:
    channel = row.get("channel")
    if not isinstance(channel, Mapping):
        return None
    try:
        return _canonical_position_row_ref(profile, channel)
    except Exception:
        fixture = channel.get("fixture_id")
        sub = channel.get("subfixture_id")
        if not str(fixture).isdigit():
            return None
        result = str(int(str(fixture)))
        if sub not in (None, "") and str(sub).isdigit():
            result += f".{int(str(sub))}"
        return result


def _effect_resources(
    profile: Mapping[str, Any],
    resources: Sequence[Mapping[str, Any]],
    *,
    group_id: int,
) -> dict[int, dict[str, Any]]:
    identity = _show_identity(profile)
    inventory = {
        item.get("effect_id"): item
        for item in profile.get("effects", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("effect_id"), int)
        and not isinstance(item.get("effect_id"), bool)
    }
    result: dict[int, dict[str, Any]] = {}
    for item in resources:
        effect_id = item.get("effect_id")
        if isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id < 1:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_ID_INVALID")
        current = inventory.get(effect_id)
        if not isinstance(current, Mapping) or current.get("name") != item.get("label"):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_FRESH_LIST_MISMATCH")
        if (
            item.get("fresh") is not True
            or item.get("ownership") != "ZEN_AGENT"
            or item.get("show_identity") != identity
            or item.get("group_id") != group_id
        ):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_EVIDENCE_STALE")
        _require_sha(item.get("list_effect_sha256"), "DYNAMIC_MERGE_EFFECT_LIST_SHA_INVALID")
        _require_sha(item.get("catalog_sha256"), "DYNAMIC_MERGE_EFFECT_CATALOG_SHA_INVALID")
        result[effect_id] = dict(item)
    if not result:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_RESOURCES_EMPTY")
    return result


def _cue_map(discovery: Mapping[str, Any], sequence_no: int) -> dict[int, Mapping[str, Any]]:
    if (
        discovery.get("schema") != "zen.sequence_export_discovery.v0.1"
        or discovery.get("status") != "VERIFIED"
        or discovery.get("sequence_no") != sequence_no
    ):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_SEQUENCE_EXPORT_NOT_FRESH_VERIFIED")
    _require_sha(
        (discovery.get("xml_discovery") or {}).get("sha256"),
        "DYNAMIC_MERGE_SEQUENCE_EXPORT_SHA_INVALID",
    )
    result: dict[int, Mapping[str, Any]] = {}
    for cue in discovery.get("cues", []):
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number in result:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_DUPLICATE_CUE")
        result[number] = cue
    return result


def _protected_snapshot(
    profile: Mapping[str, Any],
    discovery: Mapping[str, Any],
    cue_plan: Sequence[Mapping[str, Any]],
    exact_refs: Sequence[str],
) -> dict[str, Any]:
    planned_effect_cues = {
        int(item["cue_number"])
        for item in cue_plan
        if item.get("effect_id") is not None
    }
    exact = set(exact_refs)
    rows: list[dict[str, Any]] = []
    by_cue: dict[str, str] = {}
    for cue in discovery.get("cues", []):
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        planned = next((item for item in cue_plan if item.get("cue_number") == number), None)
        if planned is None:
            continue
        parts: list[dict[str, Any]] = []
        for part in cue.get("parts", []):
            if not isinstance(part, Mapping):
                continue
            kept: list[dict[str, Any]] = []
            for source in part.get("cue_data", []):
                if not isinstance(source, Mapping):
                    continue
                if _row_attribute(source) in _POSITION_FAMILY:
                    continue
                row = copy.deepcopy(dict(source))
                if number in planned_effect_cues and _canonical_ref(profile, row) in exact:
                    row.pop("effect", None)
                kept.append(row)
            parts.append({
                "index": part.get("index"),
                "name": part.get("name"),
                "cue_data": kept,
            })
        cue_snapshot = {"cue_number": number, "parts": parts}
        rows.append(cue_snapshot)
        cue_canonical = json.dumps(
            cue_snapshot, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode("ascii")
        by_cue[str(number)] = hashlib.sha256(cue_canonical).hexdigest()
    rows.sort(key=lambda item: item["cue_number"])
    canonical = json.dumps(rows, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return {
        "rows": rows,
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "by_cue": by_cue,
    }


def _effects_by_cue_ref(
    profile: Mapping[str, Any],
    discovery: Mapping[str, Any],
    cue_numbers: Sequence[int],
    exact_refs: Sequence[str],
) -> dict[str, dict[str, list[int]]]:
    wanted = set(cue_numbers)
    exact = set(exact_refs)
    result: dict[str, dict[str, set[int]]] = {
        str(number): {ref: set() for ref in exact_refs} for number in cue_numbers
    }
    for cue in discovery.get("cues", []):
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number not in wanted:
            continue
        for row in _cue_rows(cue):
            ref = _canonical_ref(profile, row)
            effect = _effect_id(row)
            if ref in exact and effect is not None:
                result[str(number)][ref].add(effect)
    return {
        number: {ref: sorted(values) for ref, values in refs.items()}
        for number, refs in result.items()
    }


def _scaled_position_updates(
    position_preview: Mapping[str, Any],
    cue_plan: Sequence[Mapping[str, Any]],
    scale: float,
) -> list[dict[str, Any]]:
    baseline = position_preview["baseline"]["values_by_fixture"]
    limits = position_preview["fixture_limits"]
    refs = list(position_preview["group"]["exact_refs"])
    result: list[dict[str, Any]] = []
    by_number = {int(row["cue_number"]): row for row in cue_plan}
    for original in position_preview["cue_updates"]:
        number = int(original["cue_number"])
        plan = by_number[number]
        pattern = str(plan["position_pattern"])
        offsets = _pattern_offsets(pattern, len(refs))
        fixture_rows = []
        for ref, (raw_pan, raw_tilt) in zip(refs, offsets):
            dpan, dtilt = raw_pan * scale, raw_tilt * scale
            base = baseline[ref]
            pan_bounds = tuple(float(value) for value in limits[ref]["pan"])
            tilt_bounds = tuple(float(value) for value in limits[ref]["tilt"])
            pan = _bounded_value(float(base["pan"]), dpan, pan_bounds)
            tilt = _bounded_value(float(base["tilt"]), dtilt, tilt_bounds)
            fixture_rows.append({
                "fixture_ref": ref,
                "baseline_pan": float(base["pan"]),
                "baseline_tilt": float(base["tilt"]),
                "delta_pan": dpan,
                "delta_tilt": dtilt,
                "pan": pan,
                "tilt": tilt,
            })
        result.append({
            "cue_number": number,
            "cue_label": original["cue_label"],
            "effect_intent": plan["effect_intent"],
            "effect_id": plan.get("effect_id"),
            "target_group": position_preview["group"]["id"],
            "position_pattern": pattern,
            "expected_pan_range": [
                min(item["pan"] for item in fixture_rows),
                max(item["pan"] for item in fixture_rows),
            ],
            "expected_tilt_range": [
                min(item["tilt"] for item in fixture_rows),
                max(item["tilt"] for item in fixture_rows),
            ],
            "intended_attribute_families_changed": [
                "POSITION", *( ["EFFECT"] if plan.get("effect_id") is not None else [] )
            ],
            "fixtures": fixture_rows,
        })
    return result


def build_existing_cue_dynamic_program_preview(
    profile: Mapping[str, Any],
    *,
    target_discovery: Mapping[str, Any],
    calibration_discovery: Mapping[str, Any],
    position_binding: Mapping[str, Any],
    effect_application_capability: Mapping[str, Any],
    effect_resources: Sequence[Mapping[str, Any]],
    artistic_cue_plan: Sequence[Mapping[str, Any]],
    stage_view_evidence: Mapping[str, Any],
    sequence_no: int,
    group_id: int,
    cue_start: int,
    cue_end: int,
    executor_assignments: Sequence[Mapping[str, Any]] = (),
    cue_metadata: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not cue_effect_capability_is_content_verified(dict(effect_application_capability)):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_GRAMMAR_NOT_VERIFIED")
    group_rows = [
        row for row in profile.get("groups", [])
        if isinstance(row, Mapping) and row.get("group_id") == group_id
    ]
    if len(group_rows) != 1:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_GROUP_EVIDENCE_UNAVAILABLE")
    if any(str(ref).split(".", 1)[0] == "9999" for ref in group_rows[0].get("fixture_refs_in_selection_order", [])):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_FIXTURE_9999_FORBIDDEN")
    cues = _cue_map(target_discovery, sequence_no)
    wanted = list(range(cue_start, cue_end + 1))
    if set(cues) < set(wanted):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_RANGE_INCOMPLETE")
    plan_by_number = {
        item.get("cue_number"): item
        for item in artistic_cue_plan
        if isinstance(item, Mapping)
    }
    if set(plan_by_number) != set(wanted) or len(artistic_cue_plan) != len(wanted):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_ARTISTIC_PLAN_MUST_COVER_EVERY_CUE")
    resources = _effect_resources(profile, effect_resources, group_id=group_id)
    for number in wanted:
        item = plan_by_number[number]
        intent = item.get("effect_intent")
        pattern = item.get("position_pattern")
        if intent not in _DYNAMIC_INTENTS | _NO_EFFECT_INTENTS:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_INTENT_UNKNOWN")
        if pattern not in _POSITION_PATTERNS:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_PATTERN_UNKNOWN")
        effect_id = item.get("effect_id")
        if intent in _DYNAMIC_INTENTS and effect_id not in resources:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_DYNAMIC_CUE_REQUIRES_VERIFIED_EFFECT")
        if intent in _NO_EFFECT_INTENTS and effect_id is not None:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_STATIC_CUE_MUST_NOT_ATTACH_EFFECT")
        if item.get("cue_label") != _cue_label(cues[number]):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_LABEL_MISMATCH")

    if (
        stage_view_evidence.get("capture_readable") is not True
        or stage_view_evidence.get("stage_view_visible") is not True
        or stage_view_evidence.get("operator_assessment") != "PRIOR_VARIATION_TOO_SMALL"
    ):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_SCALE_EVIDENCE_INSUFFICIENT")
    _require_sha(stage_view_evidence.get("capture_sha256"), "DYNAMIC_MERGE_STAGE_CAPTURE_SHA_INVALID")
    scale = stage_view_evidence.get("recommended_scale")
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or not math.isfinite(float(scale)) or not 1.0 < float(scale) <= 2.5:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_SCALE_INVALID")

    position_preview = build_existing_position_merge_preview(
        profile,
        target_discovery=target_discovery,
        calibration_discovery=calibration_discovery,
        binding=position_binding,
        sequence_no=sequence_no,
        group_id=group_id,
        cue_start=cue_start,
        cue_end=cue_end,
        executor_assignments=executor_assignments,
        cue_metadata=cue_metadata,
    )
    exact_refs = position_preview["group"]["exact_refs"]
    if any(str(ref).split(".", 1)[0] == "9999" for ref in exact_refs):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_FIXTURE_9999_FORBIDDEN")
    updates = _scaled_position_updates(position_preview, artistic_cue_plan, float(scale))
    protected = _protected_snapshot(profile, target_discovery, artistic_cue_plan, exact_refs)
    pre_effects = _effects_by_cue_ref(
        profile, target_discovery, wanted, exact_refs
    )
    plan_by_number = {int(item["cue_number"]): item for item in artistic_cue_plan}
    for update in updates:
        cue_no = int(update["cue_number"])
        planned_replacements = plan_by_number[cue_no].get("replace_effect_ids", [])
        if not isinstance(planned_replacements, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in planned_replacements
        ):
            raise ExistingCueDynamicProgramMergeError(
                "DYNAMIC_MERGE_EFFECT_REPLACEMENT_PLAN_INVALID"
            )
        existing_ids = {
            effect
            for values in pre_effects[str(cue_no)].values()
            for effect in values
        }
        if update.get("effect_id") is not None and existing_ids:
            if set(planned_replacements) != existing_ids:
                raise ExistingCueDynamicProgramMergeError(
                    "DYNAMIC_MERGE_UNRELATED_EFFECT_CONFLICT"
                )
        elif planned_replacements:
            raise ExistingCueDynamicProgramMergeError(
                "DYNAMIC_MERGE_EFFECT_REPLACEMENT_WITHOUT_EXISTING_EFFECT"
            )
        update["replace_effect_ids"] = sorted(planned_replacements)
        update["preserved_content_fingerprint"] = protected["by_cue"][str(update["cue_number"])]
    preview: dict[str, Any] = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY",
        "show_identity": _show_identity(profile),
        "target_sequence": {
            **position_preview["target_sequence"],
            "pre_protected_content_sha256": protected["sha256"],
        },
        "group": position_preview["group"],
        "baseline": position_preview["baseline"],
        "direction_semantics": position_preview["direction_semantics"],
        "fixture_limits": position_preview["fixture_limits"],
        "effect_application": {
            "grammar": "AT_EFFECT_POOL_CALL",
            "capability_status": effect_application_capability.get("status"),
            "resources": [resources[key] for key in sorted(resources)],
        },
        "position_amplitude": {
            "scale": float(scale),
            "basis": "OPERATOR_FEEDBACK_PLUS_STAGE_VIEW_OBSERVATION_AND_FIXTURE_LIMITS",
            "capture_sha256": stage_view_evidence["capture_sha256"],
            "physical_targeting_claimed": False,
        },
        "cue_updates": updates,
        "write_scope": {
            "existing_sequence_only": True,
            "existing_cues_only": True,
            "store_mode": "MERGE_CUEONLY",
            "create_sequence": False,
            "allocate_sequence": False,
            "create_effect": False,
            "modify_executor_assignment": False,
            "modify_patch_address_fixture_identity_or_type": False,
            "fixture_9999_forbidden": True,
            "allowed_attribute_families": ["POSITION", "EFFECT"],
        },
        "preservation": {
            "pre_protected_content_sha256": protected["sha256"],
            "pre_protected_content_by_cue": protected["by_cue"],
            "pre_effect_ids_by_cue_ref": pre_effects,
            "must_remain_unchanged": [
                "Cue labels", "Fade/Delay", "Color", "unrelated Dimmer static values",
                "unrelated Presets", "unrelated Effects", "Sequence identity",
                "Executor assignment",
            ],
        },
        "approval": "EXPLICIT_OWNER_APPROVAL_REQUIRED",
        "ma2_writes": 0,
    }
    commands = commands_from_preview(preview)
    preview["command_count"] = len(commands)
    preview["command_plan_sha256"] = hashlib.sha256("\n".join(commands).encode("ascii")).hexdigest()
    canonical = json.dumps(preview, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    preview["preview_id"] = hashlib.sha256(canonical).hexdigest()[:16]
    return preview


def commands_from_preview(preview: Mapping[str, Any]) -> tuple[str, ...]:
    if preview.get("schema") != PREVIEW_SCHEMA:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_SCHEMA_INVALID")
    sequence = (preview.get("target_sequence") or {}).get("id")
    group = (preview.get("group") or {}).get("id")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_SEQUENCE_INVALID")
    if isinstance(group, bool) or not isinstance(group, int) or group < 1:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_GROUP_INVALID")
    updates = preview.get("cue_updates")
    if not isinstance(updates, list) or not updates:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_APPLICATIONS_MISSING")
    commands: list[str] = []
    effect_applications = 0
    for cue in updates:
        fixtures = cue.get("fixtures") if isinstance(cue, Mapping) else None
        if not isinstance(fixtures, list) or not fixtures:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_APPLICATION_MISSING")
        number = cue["cue_number"]
        effect = cue.get("effect_id")
        if effect is not None:
            effect_applications += 1
            commands.extend((
                "ClearAll", f"Group {group}", f"At Effect {effect}",
                f"Store Cue {number} Sequence {sequence} /merge /cueonly /nc",
            ))
        commands.append("ClearAll")
        grouped: dict[tuple[str, str], list[str]] = {}
        for fixture in fixtures:
            key = (_fmt(float(fixture["pan"])), _fmt(float(fixture["tilt"])))
            grouped.setdefault(key, []).append(str(fixture["fixture_ref"]))
        for (pan, tilt), refs in grouped.items():
            commands.extend((
                "Fixture " + " + ".join(refs),
                f'Attribute "Pan" At {pan}',
                f'Attribute "Tilt" At {tilt}',
            ))
        commands.append(f"Store Cue {number} Sequence {sequence} /merge /cueonly /nc")
    if effect_applications == 0:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_CUE_APPLICATION_MISSING")
    commands.append("ClearAll")
    if any(not command.isascii() for command in commands):
        raise ExistingCueDynamicProgramMergeError("NON_ASCII_MA_TEXT")
    return tuple(commands)


def verify_existing_cue_dynamic_program_merge(
    preview: Mapping[str, Any],
    profile: Mapping[str, Any],
    post_discovery: Mapping[str, Any],
) -> dict[str, Any]:
    if preview.get("schema") != PREVIEW_SCHEMA:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_SCHEMA_INVALID")
    sequence = preview["target_sequence"]["id"]
    cues = _cue_map(post_discovery, sequence)
    protected = _protected_snapshot(
        profile, post_discovery, preview["cue_updates"], preview["group"]["exact_refs"]
    )
    if protected["sha256"] != preview["preservation"]["pre_protected_content_sha256"]:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PROTECTED_CONTENT_CHANGED")
    reverse = {
        str(value): str(key)
        for key, value in preview["group"]["cue_channel_refs"].items()
    }
    position_matches = 0
    effect_matches = 0
    for update in preview["cue_updates"]:
        number = update["cue_number"]
        cue = cues.get(number)
        if not isinstance(cue, Mapping) or _cue_label(cue) != update["cue_label"]:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_IDENTITY_CHANGED")
        rows = _cue_rows(cue)
        observed_position: dict[tuple[str, str], float] = {}
        observed_effects: dict[str, set[int]] = {ref: set() for ref in reverse.values()}
        for row in rows:
            ref = _canonical_ref(profile, row)
            selection = reverse.get(ref or "")
            if selection is None:
                continue
            attr = _row_attribute(row)
            if attr in {"PAN", "TILT"}:
                raw = row.get("raw_values")
                value = raw.get("Value") if isinstance(raw, Mapping) else None
                if value is not None:
                    observed_position[(selection, attr)] = float(value)
            effect_id = _effect_id(row)
            if effect_id is not None:
                observed_effects.setdefault(selection, set()).add(effect_id)
        for fixture in update["fixtures"]:
            ref = fixture["fixture_ref"]
            for attr, key in (("PAN", "pan"), ("TILT", "tilt")):
                actual = observed_position.get((ref, attr))
                if actual is None or not math.isclose(actual, float(fixture[key]), abs_tol=0.001, rel_tol=0):
                    raise ExistingCueDynamicProgramMergeError(
                        f"DYNAMIC_MERGE_POSITION_MISMATCH_CUE_{number}_{ref}_{attr}"
                    )
                position_matches += 1
            if update.get("effect_id") is not None:
                expected_effects = set(
                    preview["preservation"]["pre_effect_ids_by_cue_ref"]
                    [str(number)][ref]
                )
                if update.get("replace_effect_ids"):
                    expected_effects.difference_update(update["replace_effect_ids"])
                expected_effects.add(int(update["effect_id"]))
                if observed_effects.get(ref, set()) != expected_effects:
                    raise ExistingCueDynamicProgramMergeError(
                        f"DYNAMIC_MERGE_EFFECT_MISMATCH_CUE_{number}_{ref}"
                    )
                effect_matches += 1
    return {
        "schema": VERIFY_SCHEMA,
        "status": "VERIFIED",
        "sequence": sequence,
        "cue_count": len(preview["cue_updates"]),
        "position_value_matches": position_matches,
        "effect_fixture_matches": effect_matches,
        "protected_content": "UNCHANGED",
        "post_export_sha256": (post_discovery.get("xml_discovery") or {}).get("sha256"),
    }


def preview_text(preview: Mapping[str, Any]) -> str:
    lines = [
        "EXISTING CUE DYNAMIC PROGRAM MERGE - PREVIEW ONLY",
        "",
        f"Sequence: {preview['target_sequence']['id']} {preview['target_sequence']['label']}",
        f"Cues: {preview['target_sequence']['cue_start']}-{preview['target_sequence']['cue_end']}",
        f"Group: {preview['group']['id']} {preview['group']['name']}",
        f"Position amplitude scale: {preview['position_amplitude']['scale']}",
        "",
        "Per-Cue plan:",
    ]
    for cue in preview["cue_updates"]:
        effect = cue.get("effect_id") or "NONE"
        lines.append(
            f"- Cue {cue['cue_number']} {cue['cue_label']} | Effect={cue['effect_intent']}:{effect} "
            f"| Group={cue['target_group']} | Position={cue['position_pattern']} "
            f"| PAN={cue['expected_pan_range']} TILT={cue['expected_tilt_range']} "
            f"| change={','.join(cue['intended_attribute_families_changed'])} "
            f"| preserve={cue['preserved_content_fingerprint'][:12]}"
        )
    lines.extend((
        "",
        "Preserved: labels, Fade/Delay, Color, unrelated Dimmer/Preset/Effect content, Sequence identity, Executor assignment.",
        "No Sequence or Effect allocation. Fixture 9999 forbidden. Explicit owner approval required.",
        "MA2_WRITES=0",
    ))
    return "\n".join(lines)


class ExistingCueDynamicProgramMergeSkill:
    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind == "merge_existing_cue_dynamic_program" and state.has(self.manifest.required_state)

    def create_task(self, intent: Intent) -> Task:
        return Task("existing-cue-dynamic-program-merge", "Existing Cue Dynamic Program Merge", intent, self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("dynamic_program_merge_preview")
        if not isinstance(preview, Mapping) or preview.get("schema") != PREVIEW_SCHEMA:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_INVALID")
        commands = commands_from_preview(preview)
        steps = tuple(
            ActionStep(
                f"dynamic-merge-{index}",
                "Deterministic existing-Cue Effect/Position merge command",
                "command",
                command,
                "MODIFY",
                depends_on=(f"dynamic-merge-{index - 1}",) if index > 1 else (),
            )
            for index, command in enumerate(commands, 1)
        )
        return WorkflowPlan(
            task,
            (
                Subtask("fresh-evidence", "Fresh Sequence/Group/Effect/geometry evidence", "Planning"),
                Subtask("preview", "Review per-Cue Effect and Position preservation diff", "Planning"),
                Subtask("execute", "Merge only approved Effect and Position families", "Execution"),
                Subtask("verify", "Native Sequence Export preservation verification", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Existing Cue Dynamic Program Merge"),),
            steps,
            "MODIFY",
            preview_text(preview),
            ("PREVIEW",),
            "Fresh native Sequence Export must verify planned Effect/PAN/TILT values and unchanged protected content.",
            "No automatic rollback or deletion; retain native exports as evidence.",
            True,
            "PREVIEW",
            "READY",
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("dynamic_program_merge_preview")
        if not isinstance(preview, Mapping) or plan.commands != commands_from_preview(preview):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_WORKFLOW_INVALID")
        for command in plan.commands:
            if command == "ClearAll":
                continue
            if re.fullmatch(r"Group [1-9]\d*", command):
                continue
            if re.fullmatch(r"At Effect [1-9]\d*", command):
                continue
            if re.fullmatch(r"Fixture [1-9]\d*(?:\.[1-9]\d*)?(?: \+ [1-9]\d*(?:\.[1-9]\d*)?)*", command):
                continue
            if re.fullmatch(r'Attribute "(?:Pan|Tilt)" At -?\d+(?:\.\d+)?', command):
                continue
            if re.fullmatch(r"Store Cue [1-9]\d* Sequence [1-9]\d* /merge /cueonly /nc", command):
                continue
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_COMMAND_NOT_ALLOWLISTED")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands
