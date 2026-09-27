"""Bounded existing-Cue Position + Effect composite merge.

This capability exists specifically to close the gap between artistic per-Cue
dynamic intent and the already verified grandMA2 application grammars. It does
not allocate Sequences, create Effects, assign Executors, or expose a generic MA
command interface.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .cue_effect_application import cue_effect_capability_is_content_verified
from .models import Intent
from .position_existing_cue_merge import (
    ExistingPositionMergeError,
    _POSITION_FAMILY_ATTRS,
    _fmt,
    retarget_position_preview,
    verify_existing_position_merge,
)
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan

PREVIEW_SCHEMA = "zen.existing_cue_dynamic_program_merge.v0.2"
VERIFY_SCHEMA = "zen.existing_cue_dynamic_program_merge_verification.v0.2"


class ExistingCueDynamicProgramMergeError(ValueError):
    pass


def _cue_number(cue: Mapping[str, Any]) -> int:
    value = cue.get("number")
    if not isinstance(value, Mapping):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_NUMBER_MISSING")
    raw = value.get("number")
    sub = value.get("sub_number")
    if not str(raw).isdigit() or sub not in (None, "", "0", 0):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_NUMBER_INVALID")
    return int(raw)


def _cue_label(cue: Mapping[str, Any]) -> str:
    parts = cue.get("parts")
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], Mapping):
        return ""
    return str(parts[0].get("name") or "")


def _row_attr(row: Mapping[str, Any]) -> str:
    channel = row.get("channel")
    return str(channel.get("attribute_name") or "").upper() if isinstance(channel, Mapping) else ""


def _row_root_fixture(row: Mapping[str, Any]) -> str | None:
    channel = row.get("channel")
    if not isinstance(channel, Mapping):
        return None
    raw = channel.get("fixture_id")
    if raw is None or not str(raw).isdigit():
        return None
    return str(int(raw))


def _row_effect_id(row: Mapping[str, Any]) -> int | None:
    effect = row.get("effect")
    parts = effect.get("no_components") if isinstance(effect, Mapping) else None
    if not isinstance(parts, list) or not parts:
        return None
    last = str(parts[-1])
    return int(last) if last.isdigit() and int(last) > 0 else None


def _row_preset_ref(row: Mapping[str, Any]) -> str | None:
    preset = row.get("preset")
    parts = preset.get("no_components") if isinstance(preset, Mapping) else None
    if not isinstance(parts, list) or len(parts) < 2:
        return None
    pool, number = str(parts[-2]), str(parts[-1])
    if not pool.isdigit() or not number.isdigit():
        return None
    return f"{int(pool)}.{int(number)}"


def _row_exact_ref(row: Mapping[str, Any], exact_refs: set[str]) -> str | None:
    channel = row.get("channel")
    if not isinstance(channel, Mapping):
        return None
    fixture = channel.get("fixture_id")
    if not str(fixture).isdigit():
        return None
    root = str(int(str(fixture)))
    sub = channel.get("subfixture_id")
    subref = None
    if sub not in (None, "") and str(sub).isdigit():
        subref = f"{root}.{int(str(sub))}"
    if subref and subref in exact_refs:
        return subref
    if root in exact_refs:
        return root
    return None


def effect_ids_by_cue_ref(
    discovery: Mapping[str, Any],
    *,
    cue_numbers: Sequence[int],
    target_fixture_refs: Sequence[str],
) -> dict[str, dict[str, list[int]]]:
    """Return exact stored Effect identities per Cue and target fixture ref."""
    wanted = {int(value) for value in cue_numbers}
    exact_refs = {str(ref) for ref in target_fixture_refs}
    result: dict[str, dict[str, set[int]]] = {
        str(number): {ref: set() for ref in exact_refs}
        for number in sorted(wanted)
    }
    for cue in discovery.get("cues", []) if isinstance(discovery.get("cues"), list) else []:
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number not in wanted:
            continue
        for part in cue.get("parts", []) if isinstance(cue.get("parts"), list) else []:
            if not isinstance(part, Mapping):
                continue
            for row in part.get("cue_data", []) if isinstance(part.get("cue_data"), list) else []:
                if not isinstance(row, Mapping):
                    continue
                ref = _row_exact_ref(row, exact_refs)
                effect_id = _row_effect_id(row)
                if ref is not None and effect_id is not None:
                    result[str(number)][ref].add(effect_id)
    return {
        number: {ref: sorted(values) for ref, values in sorted(refs.items())}
        for number, refs in sorted(result.items(), key=lambda item: int(item[0]))
    }


def preset_refs_by_cue_ref(
    discovery: Mapping[str, Any],
    *,
    cue_numbers: Sequence[int],
    target_fixture_refs: Sequence[str],
) -> dict[str, dict[str, list[str]]]:
    wanted = {int(value) for value in cue_numbers}
    exact_refs = {str(ref) for ref in target_fixture_refs}
    result: dict[str, dict[str, set[str]]] = {
        str(number): {ref: set() for ref in exact_refs}
        for number in sorted(wanted)
    }
    for cue in discovery.get("cues", []) if isinstance(discovery.get("cues"), list) else []:
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number not in wanted:
            continue
        for part in cue.get("parts", []) if isinstance(cue.get("parts"), list) else []:
            if not isinstance(part, Mapping):
                continue
            for row in part.get("cue_data", []) if isinstance(part.get("cue_data"), list) else []:
                if not isinstance(row, Mapping):
                    continue
                ref = _row_exact_ref(row, exact_refs)
                preset_ref = _row_preset_ref(row)
                if ref is not None and preset_ref is not None:
                    result[str(number)][ref].add(preset_ref)
    return {
        number: {ref: sorted(values) for ref, values in sorted(refs.items())}
        for number, refs in sorted(result.items(), key=lambda item: int(item[0]))
    }


def _canonical_sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _normalize_protected_row(
    row: Mapping[str, Any],
    *,
    effect_change_allowed: bool,
    preset_attributes_allowed: set[str],
) -> dict[str, Any] | None:
    if _row_attr(row) in _POSITION_FAMILY_ATTRS:
        return None
    if _row_attr(row) in preset_attributes_allowed:
        return None
    normalized = deepcopy(dict(row))
    if not effect_change_allowed:
        return normalized

    # Effect application is allowed to alter only Effect identity and Effect*
    # metadata. Static Value/Fade/Delay, Preset identity, channel identity and
    # all unrelated attributes remain protected.
    normalized.pop("effect", None)
    raw_values = normalized.get("raw_values")
    if isinstance(raw_values, dict):
        normalized["raw_values"] = {
            key: value for key, value in raw_values.items()
            if not str(key).startswith("Effect")
        }
    multipart = normalized.get("multipart_indexes")
    if isinstance(multipart, dict):
        normalized["multipart_indexes"] = {
            key: value for key, value in multipart.items() if key != "effect"
        }

    meaningful_raw = normalized.get("raw_values")
    preset = normalized.get("preset")
    if (not isinstance(meaningful_raw, Mapping) or not meaningful_raw) and preset in (None, {}, []):
        # A post-write row that exists solely to carry Effect metadata is an
        # intended representation and must not create a false preservation diff.
        return None
    return normalized


def protected_content_snapshot(
    discovery: Mapping[str, Any],
    *,
    cue_effects: Mapping[int, Mapping[str, Any] | None],
    target_fixture_refs: Sequence[str],
    cue_presets: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    target_roots = {str(ref).split(".", 1)[0] for ref in target_fixture_refs}
    rows: list[dict[str, Any]] = []
    for cue in discovery.get("cues", []) if isinstance(discovery.get("cues"), list) else []:
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number not in cue_effects:
            continue
        allow_effect = cue_effects[number] is not None
        preset_attributes = {
            str(attribute).upper()
            for preset in ((cue_presets or {}).get(number) or [])
            if isinstance(preset, Mapping)
            for attribute in (preset.get("attribute_names") or [])
            if isinstance(attribute, str)
        }
        parts_out = []
        for part in cue.get("parts", []) if isinstance(cue.get("parts"), list) else []:
            if not isinstance(part, Mapping):
                continue
            normalized_rows = []
            for row in part.get("cue_data", []) if isinstance(part.get("cue_data"), list) else []:
                if not isinstance(row, Mapping):
                    continue
                row_effect_allowed = allow_effect and _row_root_fixture(row) in target_roots
                row_preset_attributes = (
                    preset_attributes if _row_root_fixture(row) in target_roots else set()
                )
                normalized = _normalize_protected_row(
                    row,
                    effect_change_allowed=row_effect_allowed,
                    preset_attributes_allowed=row_preset_attributes,
                )
                if normalized is not None:
                    normalized_rows.append(normalized)
            normalized_rows.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
            parts_out.append({
                "index": part.get("index"),
                "name": part.get("name"),
                "cue_data": normalized_rows,
            })
        rows.append({"cue_number": number, "parts": parts_out})
    rows.sort(key=lambda item: item["cue_number"])
    return {"rows": rows, "sha256": _canonical_sha(rows)}


def _effect_inventory(
    verified_effects_by_group: Mapping[int, Mapping[int, str]],
    group_id: int,
) -> dict[int, str]:
    raw = verified_effects_by_group.get(group_id)
    if not isinstance(raw, Mapping):
        return {}
    result: dict[int, str] = {}
    for key, label in raw.items():
        if isinstance(key, bool) or not isinstance(key, int) or key < 1:
            continue
        text = str(label or "").strip()
        if text:
            result[key] = text
    return result


def _preset_inventory(
    verified_presets_by_group: Mapping[int, Mapping[str, Mapping[str, Any]]],
    group_id: int,
) -> dict[str, dict[str, Any]]:
    raw = verified_presets_by_group.get(group_id)
    if not isinstance(raw, Mapping):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        reference = str(key or "")
        if (
            not re.fullmatch(r"[1-9]\d*\.[1-9]\d*", reference)
            or not isinstance(value, Mapping)
            or not isinstance(value.get("name"), str)
            or not value.get("name")
            or not isinstance(value.get("dimension"), str)
            or not isinstance(value.get("attribute_names"), list)
            or not value.get("attribute_names")
        ):
            continue
        result[reference] = deepcopy(dict(value))
    return result


def build_existing_cue_dynamic_program_preview(
    *,
    position_preview: Mapping[str, Any],
    pre_discovery: Mapping[str, Any],
    artistic_plan: Mapping[str, Any],
    verified_effects_by_group: Mapping[int, Mapping[int, str]],
    effect_application_capability: object,
    verified_presets_by_group: Mapping[int, Mapping[str, Mapping[str, Any]]] | None = None,
    verified_capabilities_by_group: Mapping[int, Sequence[str]] | None = None,
    require_effect_variation: bool = True,
    require_explicit_position: bool = True,
) -> dict[str, Any]:
    if position_preview.get("schema") != "zen.position_existing_cue_merge_preview.v0.1":
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_PREVIEW_INVALID")
    target = position_preview.get("target_sequence")
    group = position_preview.get("group")
    if not isinstance(target, Mapping) or not isinstance(group, Mapping):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_PREVIEW_INVALID")
    sequence = target.get("id")
    group_id = group.get("id")
    fixture_refs = group.get("exact_refs")
    if (
        isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1
        or isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1
        or not isinstance(fixture_refs, list) or not fixture_refs
    ):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_TARGET_INVALID")
    if pre_discovery.get("status") != "VERIFIED" or pre_discovery.get("sequence_no") != sequence:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PRE_EXPORT_NOT_VERIFIED")
    pre_sha = (pre_discovery.get("xml_discovery") or {}).get("sha256")
    expected_pre_sha = target.get("pre_export_sha256")
    if expected_pre_sha and pre_sha and expected_pre_sha != pre_sha:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PRE_EXPORT_IDENTITY_MISMATCH")
    if not cue_effect_capability_is_content_verified(effect_application_capability):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_APPLICATION_UNVERIFIED")

    plan_cues = artistic_plan.get("cues")
    if not isinstance(plan_cues, list) or not plan_cues:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_ARTISTIC_PLAN_EMPTY")
    position_updates = position_preview.get("cue_updates")
    if not isinstance(position_updates, list) or not position_updates:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_CUES_EMPTY")
    wanted = [int(row["cue_number"]) for row in position_updates]
    by_number = {
        cue.get("cue_number"): cue for cue in plan_cues
        if isinstance(cue, Mapping) and isinstance(cue.get("cue_number"), int)
    }
    if set(by_number) != set(wanted):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_CUE_SET_MISMATCH")

    effects = _effect_inventory(verified_effects_by_group, group_id)
    presets = _preset_inventory(verified_presets_by_group or {}, group_id)
    available_capabilities = {
        ("POSITION" if str(value).upper() == "MOVEMENT" else str(value).upper())
        for value in ((verified_capabilities_by_group or {}).get(group_id) or [])
    }
    cue_effects: dict[int, dict[str, Any] | None] = {}
    cue_presets: dict[int, list[dict[str, Any]]] = {}
    cue_replacements: dict[int, list[int]] = {}
    position_intent: dict[int, dict[str, Any]] = {}
    cue_intents: dict[int, list[dict[str, Any]]] = {}
    update_labels = {int(row["cue_number"]): str(row.get("cue_label") or "") for row in position_updates}

    for number in wanted:
        cue = by_number[number]
        if str(cue.get("label") or "") != update_labels[number]:
            raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_CUE_LABEL_MISMATCH_{number}")
        pattern = cue.get("position_pattern")
        scale = cue.get("position_scale", 1.0)
        if require_explicit_position and not isinstance(pattern, str):
            raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_POSITION_INTENT_MISSING_CUE_{number}")
        if isinstance(pattern, str):
            position_intent[number] = {"pattern": pattern, "scale": scale}

        capability_intent = cue.get("capability_intent")
        cue_intents[number] = deepcopy(capability_intent) if isinstance(capability_intent, list) else []
        found: dict[str, Any] | None = None
        selected_presets: list[dict[str, Any]] = []
        selected_dimensions: set[str] = set()
        actions = cue.get("actions")
        if not isinstance(actions, list):
            raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_ACTIONS_INVALID_CUE_{number}")
        for action in actions:
            if not isinstance(action, Mapping):
                raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_ACTION_INVALID_CUE_{number}")
            operation = action.get("operation")
            target_ref = (action.get("target") or {}).get("ref") if isinstance(action.get("target"), Mapping) else None
            if target_ref != group_id:
                raise ExistingCueDynamicProgramMergeError(
                    f"DYNAMIC_MERGE_ACTION_GROUP_MISMATCH_CUE_{number}"
                )
            if operation == "CALL_PRESET":
                reference = action.get("preset_ref")
                resource = presets.get(str(reference))
                dimension = str(action.get("preset_type") or "").upper()
                if (
                    not isinstance(resource, Mapping)
                    or dimension != str(resource.get("dimension") or "").upper()
                    or dimension not in {"COLOR", "FOCUS", "BEAM", "GOBO"}
                    or dimension in selected_dimensions
                ):
                    raise ExistingCueDynamicProgramMergeError(
                        f"DYNAMIC_MERGE_PRESET_NOT_VERIFIED_CUE_{number}"
                    )
                selected_dimensions.add(dimension)
                selected_presets.append({
                    "reference": str(reference),
                    "name": resource["name"],
                    "dimension": dimension,
                    "attribute_names": sorted({str(value).upper() for value in resource["attribute_names"]}),
                    "group": group_id,
                    "reuse": "EXISTING_VERIFIED_PRESET",
                })
                continue
            if operation != "CALL_EFFECT":
                raise ExistingCueDynamicProgramMergeError(
                    f"DYNAMIC_MERGE_UNSUPPORTED_EXECUTABLE_ACTION_CUE_{number}_{operation}"
                )
            effect_id = (action.get("effect_ref") or {}).get("id") if isinstance(action.get("effect_ref"), Mapping) else None
            if isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id not in effects:
                raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_EFFECT_NOT_VERIFIED_CUE_{number}")
            if found is not None:
                raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_MULTIPLE_EFFECTS_UNVERIFIED_CUE_{number}")
            found = {"id": effect_id, "label": effects[effect_id], "group": group_id}
        cue_effects[number] = found
        cue_presets[number] = selected_presets
        replacements = cue.get("replace_effect_ids", [])
        if not isinstance(replacements, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in replacements
        ) or len(set(replacements)) != len(replacements):
            raise ExistingCueDynamicProgramMergeError(
                f"DYNAMIC_MERGE_EFFECT_REPLACEMENT_PLAN_INVALID_CUE_{number}"
            )
        cue_replacements[number] = list(replacements)

    planned_effect_ids = {value["id"] for value in cue_effects.values() if value is not None}
    if require_effect_variation and len(planned_effect_ids) < 2:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_EFFECT_VARIATION_REQUIRED")

    pre_effects = effect_ids_by_cue_ref(
        pre_discovery, cue_numbers=wanted, target_fixture_refs=[str(ref) for ref in fixture_refs]
    )
    for number in wanted:
        existing_ids = {
            effect_id
            for values in pre_effects[str(number)].values()
            for effect_id in values
        }
        replacements = set(cue_replacements[number])
        if cue_effects[number] is not None and existing_ids:
            if replacements != existing_ids:
                raise ExistingCueDynamicProgramMergeError(
                    f"DYNAMIC_MERGE_UNRELATED_EFFECT_CONFLICT_CUE_{number}"
                )
        elif replacements:
            raise ExistingCueDynamicProgramMergeError(
                f"DYNAMIC_MERGE_EFFECT_REPLACEMENT_WITHOUT_EXISTING_EFFECT_CUE_{number}"
            )

    try:
        positioned = retarget_position_preview(position_preview, position_intent)
    except ExistingPositionMergeError as exc:
        raise ExistingCueDynamicProgramMergeError(str(exc)) from exc

    protected = protected_content_snapshot(
        pre_discovery,
        cue_effects=cue_effects,
        target_fixture_refs=[str(ref) for ref in fixture_refs],
        cue_presets=cue_presets,
    )
    cue_updates = []
    positioned_by_number = {int(row["cue_number"]): row for row in positioned["cue_updates"]}
    for number in wanted:
        position = positioned_by_number[number]
        effect = cue_effects[number]
        selected_presets = cue_presets[number]
        intents = cue_intents[number]
        intent_by_dimension = {
            ("POSITION" if str(item.get("dimension") or "").upper() == "MOVEMENT"
             else str(item.get("dimension") or "").upper()): item
            for item in intents if isinstance(item, Mapping)
        }
        used_families = {
            "POSITION",
            *(str(item["dimension"]) for item in selected_presets),
            *(["EFFECT", "DIMMER"] if effect else []),
        }
        if any(
            str((intent_by_dimension.get(family) or {}).get("use") or "").upper() == "AVOID"
            for family in used_families
        ):
            raise ExistingCueDynamicProgramMergeError(
                f"DYNAMIC_MERGE_CAPABILITY_INTENT_CONFLICT_CUE_{number}"
            )
        optional_capabilities = sorted(
            family for family in available_capabilities - used_families
            if str((intent_by_dimension.get(family) or {}).get("use") or "").upper() == "OPTIONAL"
        )
        requested_unexecutable = sorted(
            family for family in available_capabilities - used_families
            if str((intent_by_dimension.get(family) or {}).get("use") or "").upper() == "USE"
        )
        intentionally_unused = sorted(
            available_capabilities - used_families
            - set(optional_capabilities) - set(requested_unexecutable)
        )
        unused_details = [
            {
                "family": family,
                "reason": (
                    (intent_by_dimension.get(family) or {}).get("reason")
                    or "NOT_SELECTED_BY_ARTISTIC_PLAN"
                ),
            }
            for family in intentionally_unused
        ]
        cue_updates.append({
            "cue_number": number,
            "cue_label": position["cue_label"],
            "position_pattern": position["pattern"],
            "position_scale": position.get("scale", 1.0),
            "expected_pan_range": [
                min(float(row["pan"]) for row in position["fixtures"]),
                max(float(row["pan"]) for row in position["fixtures"]),
            ],
            "expected_tilt_range": [
                min(float(row["tilt"]) for row in position["fixtures"]),
                max(float(row["tilt"]) for row in position["fixtures"]),
            ],
            "effect": deepcopy(effect),
            "selected_effect": deepcopy(effect),
            "selected_presets": deepcopy(selected_presets),
            "beam_gobo_focus_changes": [
                deepcopy(item) for item in selected_presets
                if item.get("dimension") in {"BEAM", "GOBO", "FOCUS"}
            ],
            "replace_effect_ids": deepcopy(cue_replacements[number]),
            "pre_effect_ids_by_fixture": deepcopy(pre_effects[str(number)]),
            "capability_intent": intents,
            "used_capability_families": sorted(used_families),
            "intentionally_unused_capabilities": intentionally_unused,
            "intentionally_unused_capability_details": unused_details,
            "optional_capabilities": optional_capabilities,
            "requested_but_unexecutable_capabilities": requested_unexecutable,
        })

    result: dict[str, Any] = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY",
        "show_identity": positioned.get("show_identity"),
        "target_sequence": deepcopy(dict(target)),
        "group": deepcopy(dict(group)),
        "position_preview": positioned,
        "cue_updates": cue_updates,
        "cue_effects": {str(key): deepcopy(value) for key, value in cue_effects.items()},
        "cue_presets": {str(key): deepcopy(value) for key, value in cue_presets.items()},
        "pre_effect_ids_by_cue_ref": deepcopy(pre_effects),
        "pre_protected_content_sha256": protected["sha256"],
        "write_scope": {
            "existing_sequence_only": True,
            "existing_cues_only": True,
            "position_family": True,
            "verified_effect_application": True,
            "verified_existing_preset_application": True,
            "create_sequence": False,
            "create_effect": False,
            "create_executor": False,
            "assign_executor": False,
            "modify_label": False,
            "modify_fade_delay": False,
            "modify_unplanned_color": False,
            "modify_unrelated_dimmer_value": False,
            "modify_patch": False,
            "modify_address": False,
            "modify_fixture_identity_or_type": False,
        },
        "approval": "EXPLICIT_OWNER_APPROVAL_REQUIRED",
        "ma2_writes": 0,
    }
    commands = commands_from_dynamic_preview(result)
    result["command_count"] = len(commands)
    result["command_plan_sha256"] = hashlib.sha256("\n".join(commands).encode("ascii")).hexdigest()
    result["preview_id"] = _canonical_sha(result)[:16]
    return result


def _commands_for_update(
    sequence: int,
    group_id: int,
    position: Mapping[str, Any],
    effect: Mapping[str, Any] | None,
    presets: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Compose verified Preset, Effect and Position stores sequentially."""
    commands: list[str] = []
    number = position["cue_number"]
    for preset in presets:
        commands.extend((
            "ClearAll",
            f"Group {group_id}",
            f"At Preset {preset['reference']}",
            f"Store Cue {number} Sequence {sequence} /merge /cueonly /nc",
        ))
    if effect is not None:
        commands.extend((
            "ClearAll",
            f"Group {group_id}",
            f"At Effect {effect['id']}",
            f"Store Cue {number} Sequence {sequence} /merge /cueonly /nc",
        ))

    # Clear the Effect programmer state before applying Position so the second
    # Store contains only the independently verified PAN/TILT merge grammar.
    commands.append("ClearAll")
    grouped: dict[tuple[str, str], list[str]] = {}
    fixtures = position.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POSITION_FIXTURES_INVALID")
    for item in fixtures:
        ref = str(item["fixture_ref"])
        key = (_fmt(float(item["pan"])), _fmt(float(item["tilt"])))
        grouped.setdefault(key, []).append(ref)
    for (pan, tilt), refs in grouped.items():
        commands.append("Fixture " + " + ".join(refs))
        commands.append(f'Attribute "Pan" At {pan}')
        commands.append(f'Attribute "Tilt" At {tilt}')
    commands.append(f"Store Cue {number} Sequence {sequence} /merge /cueonly /nc")
    return commands


def commands_from_dynamic_preview(preview: Mapping[str, Any]) -> tuple[str, ...]:
    if preview.get("schema") != PREVIEW_SCHEMA and preview.get("schema") is not None:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_SCHEMA_INVALID")
    sequence = (preview.get("target_sequence") or {}).get("id")
    group_id = (preview.get("group") or {}).get("id")
    position = (preview.get("position_preview") or {}).get("cue_updates")
    effects = preview.get("cue_effects")
    presets = preview.get("cue_presets")
    if (
        isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1
        or isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1
        or not isinstance(position, list) or not position
        or not isinstance(effects, Mapping)
        or not isinstance(presets, Mapping)
    ):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_INVALID")
    commands: list[str] = []
    for update in position:
        number = update.get("cue_number")
        effect = effects.get(str(number))
        selected = presets.get(str(number))
        if not isinstance(selected, list) or any(not isinstance(item, Mapping) for item in selected):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_PRESETS_INVALID")
        commands.extend(_commands_for_update(
            sequence,
            group_id,
            update,
            effect if isinstance(effect, Mapping) else None,
            selected,
        ))
    commands.append("ClearAll")
    if any(not command.isascii() for command in commands):
        raise ExistingCueDynamicProgramMergeError("NON_ASCII_MA_TEXT")
    return tuple(commands)


def verify_existing_cue_dynamic_program_merge(
    preview: Mapping[str, Any],
    post_discovery: Mapping[str, Any],
) -> dict[str, Any]:
    if preview.get("schema") != PREVIEW_SCHEMA:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_SCHEMA_INVALID")
    sequence = (preview.get("target_sequence") or {}).get("id")
    if post_discovery.get("status") != "VERIFIED" or post_discovery.get("sequence_no") != sequence:
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_POST_EXPORT_NOT_VERIFIED")
    effects_raw = preview.get("cue_effects")
    presets_raw = preview.get("cue_presets")
    fixture_refs = (preview.get("group") or {}).get("exact_refs")
    if (
        not isinstance(effects_raw, Mapping)
        or not isinstance(presets_raw, Mapping)
        or not isinstance(fixture_refs, list)
    ):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_INVALID")
    effects = {int(key): value if isinstance(value, Mapping) else None for key, value in effects_raw.items()}
    presets = {
        int(key): value if isinstance(value, list) else []
        for key, value in presets_raw.items()
    }
    protected = protected_content_snapshot(
        post_discovery,
        cue_effects=effects,
        target_fixture_refs=[str(ref) for ref in fixture_refs],
        cue_presets=presets,
    )
    if protected["sha256"] != preview.get("pre_protected_content_sha256"):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PROTECTED_CONTENT_CHANGED")

    try:
        position_report = verify_existing_position_merge(
            preview["position_preview"], post_discovery, verify_non_position=False
        )
    except ExistingPositionMergeError as exc:
        raise ExistingCueDynamicProgramMergeError(str(exc)) from exc

    pre_effects = preview.get("pre_effect_ids_by_cue_ref")
    if not isinstance(pre_effects, Mapping):
        raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PRE_EFFECT_EVIDENCE_MISSING")
    post_effects = effect_ids_by_cue_ref(
        post_discovery,
        cue_numbers=sorted(effects),
        target_fixture_refs=[str(ref) for ref in fixture_refs],
    )
    post_presets = preset_refs_by_cue_ref(
        post_discovery,
        cue_numbers=sorted(effects),
        target_fixture_refs=[str(ref) for ref in fixture_refs],
    )
    updates = {
        int(item["cue_number"]): item
        for item in preview.get("cue_updates", [])
        if isinstance(item, Mapping) and isinstance(item.get("cue_number"), int)
    }
    effect_matches = 0
    effect_set_checks = 0
    preset_matches = 0
    for number, effect in effects.items():
        update = updates.get(number)
        if not isinstance(update, Mapping):
            raise ExistingCueDynamicProgramMergeError(f"DYNAMIC_MERGE_CUE_UPDATE_MISSING_{number}")
        replacements = set(update.get("replace_effect_ids") or [])
        for ref in fixture_refs:
            expected = set((pre_effects.get(str(number)) or {}).get(str(ref), []))
            if effect is not None:
                expected.difference_update(replacements)
                expected.add(int(effect["id"]))
            actual = set((post_effects.get(str(number)) or {}).get(str(ref), []))
            if actual != expected:
                raise ExistingCueDynamicProgramMergeError(
                    f"DYNAMIC_MERGE_EFFECT_SET_MISMATCH_CUE_{number}_{ref}"
                )
            effect_set_checks += 1
            if effect is not None:
                effect_matches += 1
        for preset in presets.get(number, []):
            if not isinstance(preset, Mapping):
                raise ExistingCueDynamicProgramMergeError(
                    f"DYNAMIC_MERGE_PRESET_PLAN_INVALID_CUE_{number}"
                )
            reference = str(preset.get("reference") or "")
            for ref in fixture_refs:
                if reference not in set((post_presets.get(str(number)) or {}).get(str(ref), [])):
                    raise ExistingCueDynamicProgramMergeError(
                        f"DYNAMIC_MERGE_PRESET_MISMATCH_CUE_{number}_{ref}_{reference}"
                    )
                preset_matches += 1


    return {
        "schema": VERIFY_SCHEMA,
        "status": "VERIFIED",
        "sequence": sequence,
        "cue_count": len(preview.get("cue_updates") or []),
        "position_value_matches": position_report["position_value_matches"],
        "effect_fixture_matches": effect_matches,
        "effect_set_checks": effect_set_checks,
        "preset_fixture_matches": preset_matches,
        "protected_content": "UNCHANGED",
        "cue_labels": "UNCHANGED",
        "post_export_sha256": (post_discovery.get("xml_discovery") or {}).get("sha256"),
    }


def preview_text(preview: Mapping[str, Any]) -> str:
    target = preview["target_sequence"]
    group = preview["group"]
    lines = [
        "EXISTING CUE DYNAMIC PROGRAM MERGE - PREVIEW",
        "",
        f"Sequence: {target['id']} {target['label']}",
        f"Cues: {target['cue_start']}-{target['cue_end']}",
        f"Group: {group['id']} {group['name']}",
        "Mode: existing Cue /merge /cueonly; verified Preset + Effect + Position",
        "",
        "Per-Cue design:",
    ]
    for cue in preview["cue_updates"]:
        effect = cue.get("effect")
        if effect is None:
            effect_text = "NO_NEW_EFFECT_CALL (preserve existing)"
        else:
            replacement = cue.get("replace_effect_ids") or []
            effect_text = f"{effect['id']} {effect['label']} replace={replacement}"
        presets = ",".join(
            f"{item.get('dimension')}:{item.get('reference')}"
            for item in cue.get("selected_presets") or []
            if isinstance(item, Mapping)
        ) or "NONE"
        beam_changes = ",".join(
            str(item.get("dimension"))
            for item in cue.get("beam_gobo_focus_changes") or []
            if isinstance(item, Mapping)
        ) or "NONE"
        unused = ",".join(cue.get("intentionally_unused_capabilities") or []) or "NONE"
        optional = ",".join(cue.get("optional_capabilities") or []) or "NONE"
        blocked = ",".join(cue.get("requested_but_unexecutable_capabilities") or []) or "NONE"
        used = ",".join(cue.get("used_capability_families") or [])
        lines.append(
            f"- Cue {cue['cue_number']} {cue['cue_label']} | Position={cue['position_pattern']} "
            f"x{cue['position_scale']} P={cue['expected_pan_range']} T={cue['expected_tilt_range']} "
            f"| Presets={presets} | Effect={effect_text} | families={used} "
            f"| Beam/Gobo/Focus={beam_changes} | unused={unused} "
            f"| optional={optional} | requested-unexecutable={blocked}"
        )
        for item in cue.get("capability_intent") or []:
            if isinstance(item, Mapping):
                lines.append(
                    f"  intent Group {item.get('group')} {item.get('dimension')}={item.get('use')} "
                    f"execution={item.get('execution_status')} reason={item.get('reason')}"
                )
    lines += [
        "",
        "Protected: unplanned capability families, static Dimmer Value, unrelated Presets/Effects, Cue labels, Fade/Delay, Sequence identity and Executor assignment.",
        "No Sequence/Effect/Executor/Preset/Group creation. No Assign. No Patch/Address/Fixture identity/type write.",
        "Capability intent without a fresh verified execution resource remains intent-only and generates no MA command.",
        "Explicit owner approval required before any MA2 write.",
    ]
    return "\n".join(lines)


class ExistingCueDynamicProgramMergeSkill:
    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return self.manifest.enabled and intent.kind == "merge_existing_cue_dynamic_program" and state.has(self.manifest.required_state)

    def create_task(self, intent: Intent) -> Task:
        return Task(
            "existing-cue-dynamic-program-merge",
            "Existing Cue Dynamic Program Merge",
            intent,
            self.manifest.id,
            self.manifest.required_state,
        )

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("dynamic_merge_preview")
        if not isinstance(preview, Mapping) or preview.get("schema") != PREVIEW_SCHEMA:
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_PREVIEW_INVALID")
        commands = commands_from_dynamic_preview(preview)
        steps = tuple(
            ActionStep(
                f"dynamic-merge-{index}",
                "Deterministic existing-Cue Preset/Effect/Position merge command",
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
                Subtask("fresh-evidence", "Verify existing Sequence, Group, FixtureType, Preset, Effect and Position evidence", "Planning"),
                Subtask("artistic-plan", "Review per-Cue selected and intentionally unused capabilities", "Planning"),
                Subtask("execute", "Merge approved Preset/Effect/Position into existing Cues", "Execution"),
                Subtask("verify", "Native Sequence Export + protected-content verification", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Existing Cue Dynamic Program Merge"),),
            steps,
            "MODIFY",
            preview_text(preview),
            ("PREVIEW",),
            "Native Sequence Export must match approved Preset, Position and Effect identities while protected content stays unchanged.",
            "No automatic rollback; retain native pre/post evidence.",
            True,
            "PREVIEW",
            "READY",
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("dynamic_merge_preview")
        if (
            plan.task.skill_id != self.manifest.id
            or plan.safety != "MODIFY"
            or not isinstance(preview, Mapping)
            or plan.commands != commands_from_dynamic_preview(preview)
        ):
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_WORKFLOW_INVALID")
        for command in plan.commands:
            if command == "ClearAll":
                continue
            if re.fullmatch(r"Fixture [1-9]\d*(?:\.[1-9]\d*)?(?: \+ [1-9]\d*(?:\.[1-9]\d*)?)*", command):
                continue
            if re.fullmatch(r'Attribute "(?:Pan|Tilt)" At -?\d+(?:\.\d+)?', command):
                continue
            if re.fullmatch(r"Group [1-9]\d*", command):
                continue
            if re.fullmatch(r"At Effect [1-9]\d*", command):
                continue
            if re.fullmatch(r"At Preset [1-9]\d*\.[1-9]\d*", command):
                continue
            if re.fullmatch(r"Store Cue [1-9]\d* Sequence [1-9]\d* /merge /cueonly /nc", command):
                continue
            raise ExistingCueDynamicProgramMergeError("DYNAMIC_MERGE_COMMAND_NOT_ALLOWLISTED")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands


__all__ = [
    "ExistingCueDynamicProgramMergeError",
    "ExistingCueDynamicProgramMergeSkill",
    "PREVIEW_SCHEMA",
    "VERIFY_SCHEMA",
    "build_existing_cue_dynamic_program_preview",
    "commands_from_dynamic_preview",
    "effect_ids_by_cue_ref",
    "preset_refs_by_cue_ref",
    "protected_content_snapshot",
    "verify_existing_cue_dynamic_program_merge",
]
