"""Compile provider-facing artistic cue intent into the strict internal ShowPlan.

The provider owns artistic choices. ZEN owns operational metadata and exact
internal schema shape. The compiler is deliberately song-agnostic: cue count
and cue naming belong to the calling design task, not to this module.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Iterable

from .schema import ShowPlanSchemaError, validate_show_plan


class ArtisticPlanCompileError(ValueError):
    """Provider artistic intent could not be compiled without changing meaning."""


_FORBIDDEN_KEYS = {"command", "commands", "telnet", "ma_command", "raw_command", "lua"}


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


def _compile_action(
    action: object,
    *,
    verified_group_ids: set[int],
    verified_preset_refs: set[str],
) -> dict[str, object]:
    if not isinstance(action, dict):
        raise ArtisticPlanCompileError("Each artistic action must be an object.")

    # Backward compatibility: legacy typed provider actions remain readable.
    operation = action.get("operation")
    if operation is not None:
        target = action.get("target")
        if not isinstance(target, dict):
            raise ArtisticPlanCompileError("Typed action target must identify one verified Group.")
        group = _group_id(target.get("ref"), verified_group_ids)
        if operation == "SET_DIMMER":
            return {
                "operation": "SET_DIMMER",
                "target": {"type": "group", "ref": group},
                "level": _dimmer_level(action.get("level")),
            }
        if operation == "CALL_PRESET":
            return {
                "operation": "CALL_PRESET",
                "target": {"type": "group", "ref": group},
                "preset_ref": _preset_ref(action.get("preset_ref"), verified_preset_refs),
            }
        raise ArtisticPlanCompileError(f"Unsupported artistic operation: {operation!r}.")

    # Preferred provider-facing compact form.
    group = _group_id(action.get("group"), verified_group_ids)
    has_dimmer = "dimmer" in action
    has_preset = "preset" in action
    if has_dimmer == has_preset:
        raise ArtisticPlanCompileError(
            "Compact artistic action must contain exactly one of 'dimmer' or 'preset'."
        )
    if has_dimmer:
        return {
            "operation": "SET_DIMMER",
            "target": {"type": "group", "ref": group},
            "level": _dimmer_level(action.get("dimmer")),
        }
    return {
        "operation": "CALL_PRESET",
        "target": {"type": "group", "ref": group},
        "preset_ref": _preset_ref(action.get("preset"), verified_preset_refs),
    }


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
    cue_labels: Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, object]]:
    """Compile provider art intent into strict zen.show_plan.v0.1.

    This module does not decide how many cues a song should have and does not
    contain song-specific section names. A bounded experiment may supply cue
    labels/count constraints at its caller boundary.
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

    labels = _cue_labels(cues, cue_labels)
    compiled_cues: list[dict[str, object]] = []
    for index, source_cue in enumerate(cues, start=1):
        if not isinstance(source_cue, dict):
            raise ArtisticPlanCompileError(f"Cue {index} must be an object.")
        actions = source_cue.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ArtisticPlanCompileError(f"Cue {index} must contain at least one artistic action.")
        compiled_actions = [
            _compile_action(
                item,
                verified_group_ids=verified_group_ids,
                verified_preset_refs=verified_preset_refs,
            )
            for item in actions
        ]
        compiled_cues.append({
            "id": f"cue_{index:03d}",
            "cue_number": index,
            "label": labels[index - 1],
            "fade": _fade(source_cue.get("fade")),
            "actions": compiled_actions,
        })

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
        "provider_contract": "ARTISTIC_CUES_V0_1",
        "backend_owned_fields": [
            "schema",
            "song",
            "target_executor",
            "active_sequence_range",
            "cues[].id",
            "cues[].cue_number",
        ],
        "provider_owned_fields": ["cues[].fade", "cues[].actions"],
        "cue_labels_source": "CALLER" if cue_labels is not None else "PROVIDER_OR_GENERIC",
        "legacy_typed_actions_accepted": True,
        "artistic_values_changed": False,
    }
    return deepcopy(compiled), audit
