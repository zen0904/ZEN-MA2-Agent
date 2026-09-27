"""Compile provider-facing artistic cue intent into the strict internal ShowPlan.

The provider owns artistic choices. ZEN owns operational metadata and exact
internal schema shape. The compiler is deliberately song-agnostic and
transport-agnostic.

ARTISTIC_CUES_V0_2 keeps the provider-facing language richer than the MA2
command boundary. It accepts verified resource selections for multiple
artistic dimensions while still compiling only to typed ShowPlan actions.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Iterable, Mapping

from .schema import ShowPlanSchemaError, validate_show_plan
from ..artistic_capabilities import (
    ARTISTIC_DIMENSIONS,
    CAPABILITY_INTENT_USES,
    normalize_artistic_dimensions,
)


class ArtisticPlanCompileError(ValueError):
    """Provider artistic intent could not be compiled without changing meaning."""


_FORBIDDEN_KEYS = {"command", "commands", "telnet", "ma_command", "raw_command", "lua"}

_PRESET_DIMENSION_KEYS = {
    "color_preset": "COLOR",
    "position_preset": "POSITION",
    "focus_preset": "FOCUS",
    "beam_preset": "BEAM",
    "gobo_preset": "GOBO",
}

_COMPACT_ACTION_KEYS = {
    "dimmer",
    "preset",
    "effect",
    *_PRESET_DIMENSION_KEYS.keys(),
}


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        hit = _FORBIDDEN_KEYS & set(value)
        if hit:
            raise ArtisticPlanCompileError(
                "Provider artistic plan contains forbidden transport/command fields: "
                + ", ".join(sorted(hit))
            )
        for nested in value.values():
            _walk_forbidden(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_forbidden(nested)


def _group_id(value: object, verified: set[int]) -> int:
    if isinstance(value, bool):
        raise ArtisticPlanCompileError("Group reference must be a verified integer Group ID.")
    if isinstance(value, int):
        group = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        group = int(value.strip())
    else:
        raise ArtisticPlanCompileError("Group reference must be a verified integer Group ID.")
    if group not in verified:
        raise ArtisticPlanCompileError(f"Group {group} is not in the verified Group allowlist.")
    return group


def _dimmer_level(value: object) -> int:
    if isinstance(value, bool):
        raise ArtisticPlanCompileError("Dimmer level must be an integer 0..100.")
    if isinstance(value, int):
        level = value
    elif isinstance(value, str) and re.fullmatch(r"[0-9]+", value.strip()):
        level = int(value.strip())
    else:
        raise ArtisticPlanCompileError("Dimmer level must be an integer 0..100.")
    if not 0 <= level <= 100:
        raise ArtisticPlanCompileError("Dimmer level must be within 0..100.")
    return level


def _fade(value: object) -> int | float:
    if isinstance(value, bool):
        raise ArtisticPlanCompileError("Cue fade must be a finite non-negative number.")
    if isinstance(value, (int, float)):
        fade = float(value)
    elif isinstance(value, str):
        try:
            fade = float(value.strip())
        except ValueError as exc:
            raise ArtisticPlanCompileError("Cue fade must be a finite non-negative number.") from exc
    else:
        raise ArtisticPlanCompileError("Cue fade must be a finite non-negative number.")
    if not math.isfinite(fade) or fade < 0:
        raise ArtisticPlanCompileError("Cue fade must be a finite non-negative number.")
    return int(fade) if fade.is_integer() else fade


def _preset_ref(value: object, verified: set[str]) -> str:
    reference = str(value).strip() if value is not None else ""
    if not reference or reference not in verified:
        raise ArtisticPlanCompileError(
            f"Preset reference {reference!r} is not in the verified Preset allowlist."
        )
    return reference


def _effect_id(value: object, verified: set[int]) -> int:
    candidate = value
    if isinstance(value, Mapping):
        candidate = value.get("id")
    if isinstance(candidate, bool):
        raise ArtisticPlanCompileError("Effect reference must be a verified integer Effect ID.")
    if isinstance(candidate, int):
        effect_id = candidate
    elif isinstance(candidate, str) and re.fullmatch(r"[0-9]+", candidate.strip()):
        effect_id = int(candidate.strip())
    else:
        raise ArtisticPlanCompileError("Effect reference must be a verified integer Effect ID.")
    if effect_id not in verified:
        raise ArtisticPlanCompileError(
            f"Effect {effect_id} is not in the verified Effect allowlist."
        )
    return effect_id


def _preset_action(
    *,
    group: int,
    value: object,
    verified_preset_refs: set[str],
    verified_preset_types: Mapping[str, str],
    verified_preset_applicability: Mapping[int, set[str]] | None,
    required_type: str | None = None,
) -> dict[str, object]:
    reference = _preset_ref(value, verified_preset_refs)
    if verified_preset_applicability is not None:
        allowed = verified_preset_applicability.get(group, set())
        if reference not in allowed:
            raise ArtisticPlanCompileError(
                f"Preset {reference} is not verified applicable to Group {group}."
            )
    if required_type is not None:
        actual = str(verified_preset_types.get(reference) or "").upper()
        if not actual:
            raise ArtisticPlanCompileError(
                f"Preset {reference} has no verified Preset type; cannot use it as {required_type}."
            )
        if actual != required_type:
            raise ArtisticPlanCompileError(
                f"Preset {reference} is verified as {actual}, not {required_type}."
            )
    action: dict[str, object] = {
        "operation": "CALL_PRESET",
        "target": {"type": "group", "ref": group},
        "preset_ref": reference,
    }
    if required_type is not None:
        action["preset_type"] = required_type
    return action


def _compile_action(
    action: object,
    *,
    verified_group_ids: set[int],
    verified_preset_refs: set[str],
    verified_preset_types: Mapping[str, str],
    verified_effect_ids: set[int],
    verified_preset_applicability: Mapping[int, set[str]] | None,
    verified_effect_applicability: Mapping[int, set[int]] | None,
    verified_dimmer_applicability: Mapping[int, Any] | None,
) -> dict[str, object]:
    if not isinstance(action, dict):
        raise ArtisticPlanCompileError("Each artistic action must be an object.")

    # Backward compatibility: typed provider actions remain readable, but the
    # provider still never supplies MA command text.
    operation = action.get("operation")
    if operation is not None:
        target = action.get("target")
        if not isinstance(target, dict):
            raise ArtisticPlanCompileError("Typed action target must identify one verified Group.")
        group = _group_id(target.get("ref"), verified_group_ids)
        if operation == "SET_DIMMER":
            if verified_dimmer_applicability is not None and group not in verified_dimmer_applicability:
                raise ArtisticPlanCompileError(f"Dimmer application is not verified for Group {group}.")
            return {
                "operation": "SET_DIMMER",
                "target": {"type": "group", "ref": group},
                "level": _dimmer_level(action.get("level")),
            }
        if operation == "CALL_PRESET":
            required_type = str(action.get("preset_type") or "").upper() or None
            return _preset_action(
                group=group,
                value=action.get("preset_ref"),
                verified_preset_refs=verified_preset_refs,
                verified_preset_types=verified_preset_types,
                verified_preset_applicability=verified_preset_applicability,
                required_type=required_type,
            )
        if operation == "CALL_EFFECT":
            effect_id = _effect_id(action.get("effect_ref"), verified_effect_ids)
            if verified_effect_applicability is not None and effect_id not in verified_effect_applicability.get(group, set()):
                raise ArtisticPlanCompileError(
                    f"Effect {effect_id} is not verified applicable to Group {group}."
                )
            return {
                "operation": "CALL_EFFECT",
                "target": {"type": "group", "ref": group},
                "effect_ref": {"id": effect_id},
            }
        raise ArtisticPlanCompileError(f"Unsupported artistic operation: {operation!r}.")

    group = _group_id(action.get("group"), verified_group_ids)
    present = [key for key in _COMPACT_ACTION_KEYS if key in action]
    if len(present) != 1:
        raise ArtisticPlanCompileError(
            "Compact artistic action must contain exactly one artistic value "
            "from dimmer, preset, effect, color_preset, position_preset, "
            "focus_preset, beam_preset, or gobo_preset."
        )
    key = present[0]
    if key == "dimmer":
        if verified_dimmer_applicability is not None and group not in verified_dimmer_applicability:
            raise ArtisticPlanCompileError(f"Dimmer application is not verified for Group {group}.")
        return {
            "operation": "SET_DIMMER",
            "target": {"type": "group", "ref": group},
            "level": _dimmer_level(action.get("dimmer")),
        }
    if key == "effect":
        effect_id = _effect_id(action.get("effect"), verified_effect_ids)
        if verified_effect_applicability is not None and effect_id not in verified_effect_applicability.get(group, set()):
            raise ArtisticPlanCompileError(
                f"Effect {effect_id} is not verified applicable to Group {group}."
            )
        return {
            "operation": "CALL_EFFECT",
            "target": {"type": "group", "ref": group},
            "effect_ref": {"id": effect_id},
        }
    if key == "preset":
        return _preset_action(
            group=group,
            value=action.get("preset"),
            verified_preset_refs=verified_preset_refs,
            verified_preset_types=verified_preset_types,
            verified_preset_applicability=verified_preset_applicability,
        )
    return _preset_action(
        group=group,
        value=action.get(key),
        verified_preset_refs=verified_preset_refs,
        verified_preset_types=verified_preset_types,
        verified_preset_applicability=verified_preset_applicability,
        required_type=_PRESET_DIMENSION_KEYS[key],
    )




_POSITION_PATTERNS = frozenset({
    "CENTER", "LEFT", "RIGHT", "FRONT", "UPSTAGE", "NARROW_FAN",
    "WIDE_FAN", "CROSS", "ALTERNATE", "EXPLODE", "COLLAPSE",
})

def _position_intent(source_cue: Mapping[str, Any]) -> tuple[str | None, float | None]:
    raw_pattern = source_cue.get("position_pattern")
    pattern = str(raw_pattern).strip().upper() if raw_pattern is not None else None
    if pattern is not None and pattern not in _POSITION_PATTERNS:
        raise ArtisticPlanCompileError(f"Unsupported Position pattern: {pattern}.")
    raw_scale = source_cue.get("position_scale")
    if raw_scale is None:
        return pattern, None
    if isinstance(raw_scale, bool) or not isinstance(raw_scale, (int, float)):
        raise ArtisticPlanCompileError("Position scale must be numeric.")
    scale = float(raw_scale)
    if not math.isfinite(scale) or not 0.5 <= scale <= 2.5:
        raise ArtisticPlanCompileError("Position scale must be within 0.5..2.5.")
    return pattern, scale


def _replace_effect_ids(source_cue: Mapping[str, Any]) -> list[int]:
    raw = source_cue.get("replace_effect_ids", [])
    if not isinstance(raw, list):
        raise ArtisticPlanCompileError("replace_effect_ids must be a list.")
    result: list[int] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ArtisticPlanCompileError("replace_effect_ids must contain positive Effect IDs.")
        if value in result:
            raise ArtisticPlanCompileError("replace_effect_ids must not contain duplicates.")
        result.append(value)
    return result

def _compile_capability_intent(
    value: object,
    *,
    verified_group_ids: set[int],
    verified_capability_status: Mapping[int, Mapping[str, Mapping[str, str]]] | None,
) -> list[dict[str, object]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ArtisticPlanCompileError("Cue capability_intent must be a list.")
    compiled: list[dict[str, object]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise ArtisticPlanCompileError(f"Capability intent {index} must be an object.")
        group = _group_id(item.get("group"), verified_group_ids)
        dimensions = normalize_artistic_dimensions(item.get("dimension"))
        use = str(item.get("use") or "").strip().upper()
        reason = str(item.get("reason") or "").strip()
        if not dimensions or any(dimension not in ARTISTIC_DIMENSIONS for dimension in dimensions):
            raw_dimension = str(item.get("dimension") or "").strip().upper()
            raise ArtisticPlanCompileError(
                f"Unsupported artistic capability dimension: {raw_dimension or '<empty>'}."
            )
        if use not in CAPABILITY_INTENT_USES:
            raise ArtisticPlanCompileError(f"Capability intent use must be one of {sorted(CAPABILITY_INTENT_USES)}.")
        if len(reason) > 512:
            raise ArtisticPlanCompileError("Capability intent reason exceeds 512 characters.")
        for dimension in dimensions:
            evidence = (verified_capability_status or {}).get(group, {}).get(dimension, {})
            technical_status = str(evidence.get("technical_status") or "UNKNOWN")
            execution_status = str(evidence.get("execution_status") or "NO_VERIFIED_RESOURCE")
            if use in {"USE", "OPTIONAL"} and verified_capability_status is not None and technical_status != "SHOW_BOUND_VERIFIED":
                raise ArtisticPlanCompileError(
                    f"{dimension} technical capability is not SHOW_BOUND_VERIFIED for Group {group}."
                )
            compiled.append({
                "group": group,
                "dimension": dimension,
                "use": use,
                "reason": reason,
                "technical_status": technical_status,
                "execution_status": execution_status,
                "execution_authorized": execution_status in {
                    "VERIFIED_PRESET_RESOURCE",
                    "VERIFIED_EFFECT_RESOURCE",
                    "SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL",
                    "SHOW_BOUND_VERIFIED_FIXTURE_TYPE_CAPABILITY",
                },
            })
    return compiled

def _cue_labels(
    provider_cues: list[object],
    supplied: Iterable[str] | None,
) -> list[str]:
    if supplied is not None:
        labels = [str(value).strip() for value in supplied]
        if len(labels) != len(provider_cues):
            raise ArtisticPlanCompileError(
                "Caller-supplied cue labels must match the provider cue count."
            )
        if any(not label for label in labels):
            raise ArtisticPlanCompileError("Caller-supplied cue labels may not be empty.")
        return labels

    labels: list[str] = []
    for index, cue in enumerate(provider_cues, start=1):
        label = cue.get("label") if isinstance(cue, dict) else None
        text = str(label).strip() if label is not None else ""
        labels.append(text or f"CUE_{index:03d}")
    return labels


def compile_artistic_cue_plan(
    provider_plan: dict[str, Any],
    *,
    song: str,
    target_executor: str,
    active_sequence_range: Iterable[int],
    verified_group_ids: set[int],
    verified_preset_refs: set[str],
    verified_preset_types: Mapping[str, str] | None = None,
    verified_effect_ids: set[int] | None = None,
    verified_preset_applicability: Mapping[int, Iterable[str]] | None = None,
    verified_effect_applicability: Mapping[int, Iterable[int]] | None = None,
    verified_dimmer_applicability: Mapping[int, Any] | None = None,
    verified_capability_status: Mapping[int, Mapping[str, Mapping[str, str]]] | None = None,
    cue_labels: Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, object]]:
    """Compile provider art intent into strict zen.show_plan.v0.1.

    The generic compiler does not decide cue count or song structure. It also
    does not invent unverified artistic resources. Dimension-specific Preset
    actions require a verified Preset type; Effect actions require a verified
    Effect ID.
    """
    if not isinstance(provider_plan, dict):
        raise ArtisticPlanCompileError("Provider artistic plan must be a JSON object.")
    _walk_forbidden(provider_plan)

    cues = provider_plan.get("cues")
    if not isinstance(cues, list) or not cues:
        raise ArtisticPlanCompileError("Provider artistic plan must contain at least one cue.")

    limits = list(active_sequence_range)
    if len(limits) != 2 or any(not isinstance(item, int) or isinstance(item, bool) for item in limits):
        raise ArtisticPlanCompileError("Internal active Sequence range is invalid.")

    preset_types = {
        str(reference): str(kind).upper()
        for reference, kind in (verified_preset_types or {}).items()
        if reference is not None and kind is not None
    }
    effect_ids = set(verified_effect_ids or ())
    preset_applicability = (
        {
            int(group): {str(reference) for reference in references}
            for group, references in verified_preset_applicability.items()
        }
        if verified_preset_applicability is not None
        else None
    )
    effect_applicability = (
        {
            int(group): {int(effect_id) for effect_id in effect_ids_for_group}
            for group, effect_ids_for_group in verified_effect_applicability.items()
        }
        if verified_effect_applicability is not None
        else None
    )
    labels = _cue_labels(cues, cue_labels)
    compiled_cues: list[dict[str, object]] = []
    for index, source_cue in enumerate(cues, start=1):
        if not isinstance(source_cue, dict):
            raise ArtisticPlanCompileError(f"Cue {index} must be an object.")
        actions = source_cue.get("actions")
        if not isinstance(actions, list):
            raise ArtisticPlanCompileError(f"Cue {index} actions must be a list.")
        position_pattern, position_scale = _position_intent(source_cue)
        if not actions and position_pattern is None:
            raise ArtisticPlanCompileError(
                f"Cue {index} must contain an artistic action or explicit Position pattern."
            )
        compiled_actions = [
            _compile_action(
                item,
                verified_group_ids=verified_group_ids,
                verified_preset_refs=verified_preset_refs,
                verified_preset_types=preset_types,
                verified_effect_ids=effect_ids,
                verified_preset_applicability=preset_applicability,
                verified_effect_applicability=effect_applicability,
                verified_dimmer_applicability=verified_dimmer_applicability,
            )
            for item in actions
        ]
        replace_effect_ids = _replace_effect_ids(source_cue)
        capability_intent = _compile_capability_intent(
            source_cue.get("capability_intent"),
            verified_group_ids=verified_group_ids,
            verified_capability_status=verified_capability_status,
        )
        compiled_cue = {
            "id": f"cue_{index:03d}",
            "cue_number": index,
            "label": labels[index - 1],
            "fade": _fade(source_cue.get("fade")),
            "actions": compiled_actions,
        }
        if position_pattern is not None:
            compiled_cue["position_pattern"] = position_pattern
        if replace_effect_ids:
            compiled_cue["replace_effect_ids"] = replace_effect_ids
        if position_scale is not None:
            compiled_cue["position_scale"] = position_scale
        if capability_intent:
            compiled_cue["capability_intent"] = capability_intent
        compiled_cues.append(compiled_cue)

    compiled: dict[str, Any] = {
        "schema": "zen.show_plan.v0.1",
        "song": str(song),
        "target_executor": str(target_executor),
        "active_sequence_range": limits,
        "cues": compiled_cues,
    }
    try:
        compiled = validate_show_plan(compiled)
    except ShowPlanSchemaError as exc:
        raise ArtisticPlanCompileError(f"Compiled ShowPlan failed strict validation: {exc}") from exc

    audit = {
        "provider_contract": "ARTISTIC_CUES_V0_2",
        "backend_owned_fields": [
            "schema",
            "song",
            "target_executor",
            "active_sequence_range",
            "cues[].id",
            "cues[].cue_number",
        ],
        "provider_owned_fields": [
            "cues[].fade", "cues[].actions", "cues[].capability_intent",
            "cues[].position_pattern", "cues[].position_scale", "cues[].replace_effect_ids",
        ],
        "supported_compact_dimensions": [
            "DIMMER",
            "PRESET",
            "COLOR_PRESET",
            "POSITION_PRESET",
            "FOCUS_PRESET",
            "BEAM_PRESET",
            "GOBO_PRESET",
            "EFFECT",
        ],
        "artistic_capability_intents_preserved": True,
        "capability_execution_is_separate_from_intent": True,
        "cue_labels_source": "CALLER" if cue_labels is not None else "PROVIDER_OR_GENERIC",
        "legacy_typed_actions_accepted": True,
        "preset_applicability_enforced": preset_applicability is not None,
        "effect_applicability_enforced": effect_applicability is not None,
        "artistic_values_changed": False,
    }
    return deepcopy(compiled), audit
