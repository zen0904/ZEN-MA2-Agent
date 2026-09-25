"""Provider-independent boundary for the ordinary one-call design path."""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping, Protocol

from .artistic_plan import ArtisticPlanCompileError, compile_artistic_cue_plan
from ..artistic_resources import (
    SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL,
    SHOW_BOUND_VERIFIED_FIXTURE_TYPE_CAPABILITY,
    effect_applicability_from_map,
    model_resource_contract,
    preset_applicability_from_map,
)


class LeanDesignIntelligence(Protocol):
    """One bounded artistic-intent call; implementations must not execute MA2."""

    def design(self, request: str, context: Mapping[str, Any]) -> Mapping[str, Any] | str: ...


class LeanDesignProviderError(RuntimeError):
    """The injected artistic provider failed before deterministic compilation."""


MAX_PROVIDER_OUTPUT_BYTES = 256 * 1024


def invoke_primary_design(
    provider: LeanDesignIntelligence,
    request: str,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Perform exactly one primary artistic call, with no hidden retry/fallback."""
    if not isinstance(request, str) or not request.strip() or len(request) > 2048:
        raise LeanDesignProviderError("Lean design request must be a non-empty bounded string.")
    if not isinstance(context, Mapping):
        raise LeanDesignProviderError("Lean design context must be a mapping.")
    try:
        raw = provider.design(request, context)
    except Exception as exc:
        raise LeanDesignProviderError(f"Primary artistic provider failed: {type(exc).__name__}: {exc}") from exc
    if isinstance(raw, str):
        size = len(raw.encode("utf-8"))
    else:
        try:
            size = len(json.dumps(raw, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise LeanDesignProviderError("Primary artistic provider returned non-JSON-safe data.") from exc
    if size > MAX_PROVIDER_OUTPUT_BYTES:
        raise LeanDesignProviderError("Primary artistic provider output exceeds the bounded response size.")
    return parse_artistic_json(raw)


def build_provider_resource_contract(resource_map: Mapping[str, Any]) -> dict[str, Any]:
    """Compact song-agnostic contract containing only executable resources."""
    return {
        "group_resources": model_resource_contract(resource_map),
        "resource_rules": dict(resource_map.get("rules") or {}),
    }


def parse_artistic_json(value: Mapping[str, Any] | str) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ArtisticPlanCompileError(f"Provider output is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, Mapping):
        raise ArtisticPlanCompileError("Provider artistic output must be one JSON object.")
    return deepcopy(dict(value))


def reject_transport_fields(value: Any, *, path: str = "root") -> None:
    forbidden = {
        "command", "commands", "console_command", "raw_command",
        "ma_command", "telnet", "lua", "shell",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in forbidden:
                raise ArtisticPlanCompileError(
                    f"Provider output contains forbidden transport field: {path}.{key}"
                )
            reject_transport_fields(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_transport_fields(child, path=f"{path}[{index}]")


def _verified_preset_inventory(
    resource_map: Mapping[str, Any],
) -> tuple[set[str], dict[str, str]]:
    """Derive the compiler allow-list only from Group-bound verified resources."""
    references: set[str] = set()
    types: dict[str, str] = {}
    groups = resource_map.get("groups")
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping):
            continue
        resources = group.get("preset_resources")
        for preset in resources if isinstance(resources, list) else []:
            if not isinstance(preset, Mapping):
                continue
            reference = str(preset.get("reference") or "").strip()
            dimension = str(preset.get("dimension") or preset.get("preset_type") or "").strip().upper()
            if not reference:
                continue
            previous = types.get(reference)
            if previous and dimension and previous != dimension:
                raise ArtisticPlanCompileError(
                    f"Verified Preset {reference} has conflicting dimension identities."
                )
            references.add(reference)
            if dimension:
                types[reference] = dimension
    return references, types


def canonicalize_provider_artistic_shape(value: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize only schema aliases that preserve an already-verified identity.

    group_id is accepted solely as an integer alias for compact-action group.
    Names, strings, conflicting identities, and any broader semantic guessing
    remain rejected.
    """
    normalized = deepcopy(dict(value))
    cues = normalized.get("cues")
    if not isinstance(cues, list):
        return normalized
    for cue_index, cue in enumerate(cues, start=1):
        if not isinstance(cue, Mapping):
            continue
        actions = cue.get("actions")
        if not isinstance(actions, list):
            continue
        for action_index, action in enumerate(actions, start=1):
            if not isinstance(action, dict) or "group_id" not in action:
                continue
            alias = action.get("group_id")
            if not isinstance(alias, int) or isinstance(alias, bool):
                raise ArtisticPlanCompileError(
                    f"Cue {cue_index} action {action_index} group_id alias must be an integer."
                )
            if "group" in action and action.get("group") != alias:
                raise ArtisticPlanCompileError(
                    f"Cue {cue_index} action {action_index} contains conflicting Group identities."
                )
            action["group"] = alias
            action.pop("group_id", None)
    return normalized


def compile_lean_artistic_intent(
    provider_output: Mapping[str, Any] | str,
    *,
    request: str,
    resource_map: Mapping[str, Any],
    active_sequence_range: tuple[int, int] = (301, 400),
    target_executor: str = "2.001",
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(request, str) or not request.strip() or len(request) > 2048:
        raise ArtisticPlanCompileError("Lean design request must be a non-empty bounded string.")
    artistic = parse_artistic_json(provider_output)
    reject_transport_fields(artistic)
    artistic = canonicalize_provider_artistic_shape(artistic)
    groups = [item for item in resource_map.get("groups", []) if isinstance(item, Mapping)]
    verified_groups = {
        int(item["group_id"])
        for item in groups
        if isinstance(item.get("group_id"), int) and not isinstance(item.get("group_id"), bool)
    }
    verified_presets, preset_types = _verified_preset_inventory(resource_map)
    dimmer_applicability = {
        int(group["group_id"]): {"SET_DIMMER"}
        for group in groups
        if isinstance(group.get("group_id"), int)
        and not isinstance(group.get("group_id"), bool)
        and isinstance((group.get("dimensions") or {}).get("DIMMER"), Mapping)
        and group["dimensions"]["DIMMER"].get("execution_status")
        in {
            SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL,
            SHOW_BOUND_VERIFIED_FIXTURE_TYPE_CAPABILITY,
        }
    }
    effect_applicability = effect_applicability_from_map(resource_map)
    plan, audit = compile_artistic_cue_plan(
        artistic,
        song=request,
        target_executor=target_executor,
        active_sequence_range=active_sequence_range,
        verified_group_ids=verified_groups,
        verified_preset_refs=verified_presets,
        verified_preset_types=preset_types,
        verified_effect_ids={
            effect_id for ids in effect_applicability.values() for effect_id in ids
        },
        verified_preset_applicability=preset_applicability_from_map(resource_map),
        verified_effect_applicability=effect_applicability,
        verified_dimmer_applicability=dimmer_applicability,
    )
    return attach_verified_effect_identity_labels(plan, resource_map), audit


def attach_verified_effect_identity_labels(
    plan: Mapping[str, Any],
    resource_map: Mapping[str, Any],
) -> dict[str, Any]:
    labels: dict[tuple[int, int], str] = {}
    groups = resource_map.get("groups")
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping) or not isinstance(group.get("group_id"), int):
            continue
        resources = group.get("effect_resources")
        for effect in resources if isinstance(resources, list) else []:
            if (
                isinstance(effect, Mapping)
                and effect.get("application_status") == "REAL_MACHINE_CONTENT_VERIFIED"
                and isinstance(effect.get("effect_id"), int)
                and str(effect.get("name") or "").strip()
            ):
                key = (int(group["group_id"]), int(effect["effect_id"]))
                label = str(effect["name"]).strip()
                if key in labels and labels[key] != label:
                    raise ArtisticPlanCompileError(
                        f"Verified Effect {effect['effect_id']} has conflicting labels "
                        f"for Group {group['group_id']}."
                    )
                labels[key] = label
    normalized = deepcopy(dict(plan))
    for cue in normalized.get("cues", []):
        for action in cue.get("actions", []):
            if action.get("operation") == "CALL_EFFECT":
                group = (action.get("target") or {}).get("ref")
                effect = (action.get("effect_ref") or {}).get("id")
                label = labels.get((group, effect))
                if not label:
                    raise ArtisticPlanCompileError(
                        f"Effect {effect} for Group {group} has no content-verified identity label."
                    )
                action["effect_ref"] = {**action["effect_ref"], "label": label}
    return normalized


__all__ = [
    "LeanDesignIntelligence",
    "LeanDesignProviderError",
    "invoke_primary_design",
    "build_provider_resource_contract",
    "parse_artistic_json",
    "reject_transport_fields",
    "canonicalize_provider_artistic_shape",
    "compile_lean_artistic_intent",
    "attach_verified_effect_identity_labels",
]
