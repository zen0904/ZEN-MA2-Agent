"""Build a conservative current-Show artistic resource map.

The resource map separates three facts that must not be conflated:

* an MA2 object exists;
* a fixture/group is technically capable of an artistic dimension;
* a specific Preset/Effect is verified and applicable to that Group.

Names never create capability or applicability.  Unknown stays unknown.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

ARTISTIC_RESOURCE_MAP_SCHEMA = "zen.artistic_resource_map.v0.1"

ARTISTIC_DIMENSIONS = (
    "DIMMER",
    "COLOR",
    "POSITION",
    "FOCUS",
    "BEAM",
    "GOBO",
    "PRISM",
    "ZOOM",
    "FROST",
    "EFFECT",
    "MOVEMENT",
    "STROBE",
)

_PRESET_DIMENSIONS = {"COLOR", "POSITION", "FOCUS", "BEAM", "GOBO"}
_STRICT_EFFECT_TEMPLATES = {
    "FX_DIM_CHASE_SLOW": ("DIMMER_CHASE", "SLOW"),
    "FX_DIM_CHASE_MED": ("DIMMER_CHASE", "MED"),
    "FX_DIM_CHASE_FAST": ("DIMMER_CHASE", "FAST"),
}

_CAPABILITY_KEYS = {
    "DIMMER": "DIMMER",
    "COLOR": "COLOR",
    "POSITION": "POSITION",
    "FOCUS": "FOCUS",
    "BEAM": "BEAM",
    "GOBO": "GOBO",
    "PRISM": "PRISM",
    "ZOOM": "ZOOM",
    "FROST": "FROST",
    "STROBE": "SHUTTER_STROBE",
}


def _show_identity(profile: Mapping[str, Any]) -> dict[str, Any]:
    value = profile.get("show_identity")
    return deepcopy(value) if isinstance(value, Mapping) else {}


def _same_identity(left: object, right: object) -> bool:
    return isinstance(left, Mapping) and isinstance(right, Mapping) and dict(left) == dict(right)


def _fixture_type_label(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _profile_lookup(profile: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    rows = profile.get("fixture_type_profiles")
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, Mapping) or item.get("status") != "SHOW_BOUND_VERIFIED":
            continue
        fixture_type = item.get("fixture_type")
        if not isinstance(fixture_type, Mapping):
            continue
        label = str(fixture_type.get("list_label") or "").strip()
        if label:
            result[label] = item
    return result


def _technical_dimension_status(
    dimension: str,
    fixture_type_labels: Sequence[str],
    profiles: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    capability_key = _CAPABILITY_KEYS.get(dimension)
    if capability_key is None:
        if dimension == "MOVEMENT":
            capability_key = "POSITION"
        else:
            return {
                "status": "UNKNOWN",
                "reason": "No verified technical capability classifier exists for this artistic dimension.",
            }
    if not fixture_type_labels:
        return {"status": "UNKNOWN", "reason": "Group has no verified fixture membership."}

    statuses: list[str] = []
    evidence: list[dict[str, Any]] = []
    for label in fixture_type_labels:
        profile = profiles.get(label)
        if not profile:
            statuses.append("UNKNOWN")
            evidence.append({"fixture_type": label, "status": "PROFILE_UNAVAILABLE"})
            continue
        capabilities = profile.get("capabilities")
        capability = capabilities.get(capability_key) if isinstance(capabilities, Mapping) else None
        status = str((capability or {}).get("status") or "UNKNOWN") if isinstance(capability, Mapping) else "UNKNOWN"
        statuses.append(status)
        evidence.append({"fixture_type": label, "status": status, "capability": capability_key})

    if statuses and all(status == "SHOW_BOUND_VERIFIED" for status in statuses):
        status = "SHOW_BOUND_VERIFIED"
    elif statuses and all(status == "NOT_PRESENT_IN_EXPORTED_PROFILE" for status in statuses):
        status = "NOT_PRESENT_IN_GROUP_FIXTURE_TYPES"
    elif any(status == "SHOW_BOUND_VERIFIED" for status in statuses):
        status = "PARTIAL"
    else:
        status = "UNKNOWN"
    return {"status": status, "evidence": evidence}


def _preset_inventory(profile: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    rows = profile.get("presets")
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        reference = str(item.get("reference") or "").strip()
        if reference:
            result[reference] = item
    return result


def _effect_inventory(profile: Mapping[str, Any]) -> dict[int, Mapping[str, Any]]:
    result: dict[int, Mapping[str, Any]] = {}
    rows = profile.get("effects")
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        effect_id = item.get("effect_id")
        if isinstance(effect_id, int) and not isinstance(effect_id, bool) and effect_id > 0:
            result[effect_id] = item
    return result


def _verified_preset_bindings(
    *,
    profile: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    current_identity = _show_identity(profile)
    inventory = _preset_inventory(profile)
    result: dict[int, list[dict[str, Any]]] = {}
    seen: set[tuple[int, str]] = set()
    for binding in bindings:
        if not isinstance(binding, Mapping) or binding.get("status") not in {"VERIFIED", "SHOW_BOUND_VERIFIED"}:
            continue
        if not _same_identity(binding.get("show_identity"), current_identity):
            continue
        group_id = binding.get("group_id")
        reference = str(binding.get("reference") or "").strip()
        if isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1 or not reference:
            continue
        preset = inventory.get(reference)
        if not preset:
            continue
        requested_type = str(binding.get("preset_type") or "").upper()
        current_type = str(preset.get("preset_type") or "").upper()
        if requested_type and current_type != requested_type:
            continue
        if current_type not in _PRESET_DIMENSIONS:
            continue
        key = (group_id, reference)
        if key in seen:
            continue
        seen.add(key)
        result.setdefault(group_id, []).append({
            "dimension": current_type,
            "reference": reference,
            "name": preset.get("name"),
            "preset_type": current_type,
            "verification": str(binding.get("status")),
            "source": binding.get("source"),
        })
    for rows in result.values():
        rows.sort(key=lambda item: (item["dimension"], item["reference"]))
    return result


def _verified_dimmer_bindings(
    *,
    profile: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
) -> dict[int, dict[str, Any]]:
    current_identity = _show_identity(profile)
    result: dict[int, dict[str, Any]] = {}
    for binding in bindings:
        if not isinstance(binding, Mapping) or binding.get("status") not in {"VERIFIED", "SHOW_BOUND_VERIFIED"}:
            continue
        if not _same_identity(binding.get("show_identity"), current_identity):
            continue
        if str(binding.get("capability") or "").upper() != "DIMMER":
            continue
        group_id = binding.get("group_id")
        if isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1:
            continue
        result[group_id] = {
            "status": str(binding.get("status")),
            "source": binding.get("source"),
            "implementation": binding.get("implementation") or "SET_DIMMER",
            "evidence": deepcopy(binding.get("evidence") or {}),
        }
    return result


def _verified_effect_bindings(
    *,
    profile: Mapping[str, Any],
    catalog_entries: Iterable[Mapping[str, Any]],
    effect_application_capability: Mapping[str, Any] | None,
) -> dict[int, list[dict[str, Any]]]:
    current_identity = _show_identity(profile)
    inventory = _effect_inventory(profile)
    application_verified = bool(
        isinstance(effect_application_capability, Mapping)
        and effect_application_capability.get("status") == "REAL_MACHINE_VERIFIED"
        and effect_application_capability.get("grammar") == "EFFECT_POOL_CALL"
    )
    result: dict[int, list[dict[str, Any]]] = {}
    for entry in catalog_entries:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("ownership") != "ZEN_AGENT" or not _same_identity(entry.get("show_identity"), current_identity):
            continue
        effect_id = entry.get("effect_id")
        requirement = entry.get("requirement")
        verification = entry.get("verification")
        if not isinstance(effect_id, int) or effect_id < 1 or not isinstance(requirement, Mapping) or not isinstance(verification, Mapping):
            continue
        if requirement.get("target_type") != "group":
            continue
        group_id = requirement.get("target_ref")
        if not isinstance(group_id, int) or group_id < 1:
            continue
        observed = inventory.get(effect_id)
        if not observed or observed.get("name") != entry.get("label"):
            continue
        object_ok = str(verification.get("object") or "").upper() in {"VERIFIED", "FRESH_LIST_VERIFIED"}
        label_ok = str(verification.get("label") or "").upper() in {"VERIFIED", "STRICT_SEMANTIC_TEMPLATE"}
        if not (object_ok and label_ok):
            continue
        result.setdefault(group_id, []).append({
            "effect_id": effect_id,
            "name": observed.get("name"),
            "semantic_label": requirement.get("semantic_label"),
            "kind": requirement.get("kind"),
            "verification": deepcopy(dict(verification)),
            "application_status": "REAL_MACHINE_VERIFIED" if application_verified else "APPLICATION_UNVERIFIED",
            "source": entry.get("source"),
        })
    for rows in result.values():
        rows.sort(key=lambda item: item["effect_id"])
    return result


def _strict_template_effect_inventory(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for effect_id, item in sorted(_effect_inventory(profile).items()):
        label = str(item.get("name") or "").strip().upper()
        template = _STRICT_EFFECT_TEMPLATES.get(label)
        if template is None or str(item.get("kind") or "").upper() != "TEMPLATE":
            continue
        kind, speed_class = template
        rows.append({
            "effect_id": effect_id,
            "name": item.get("name"),
            "semantic_label": label,
            "kind": kind,
            "speed_class": speed_class,
            "verification": {
                "object": "FRESH_LIST_VERIFIED",
                "label": "STRICT_SEMANTIC_TEMPLATE",
                "parameters": "UNAVAILABLE",
            },
            "source": "EFFECT_RESOURCE_RESOLVER_STRICT_TEMPLATE",
        })
    return rows


def build_artistic_resource_map(
    profile: Mapping[str, Any],
    *,
    preset_bindings: Iterable[Mapping[str, Any]] = (),
    dimmer_bindings: Iterable[Mapping[str, Any]] = (),
    effect_catalog_entries: Iterable[Mapping[str, Any]] = (),
    effect_application_capability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a model-safe Group x capability x resource map.

    Presets become Group-eligible only through explicit, current-Show binding
    evidence. Effects become Group-eligible only through the current-Show
    Agent-owned Effect catalog and exact current inventory identity.
    """
    identity = _show_identity(profile)
    fixtures = {
        item.get("fixture_id"): item
        for item in (profile.get("fixtures") or [])
        if isinstance(item, Mapping) and isinstance(item.get("fixture_id"), int)
    }
    profiles = _profile_lookup(profile)
    bound_presets = _verified_preset_bindings(profile=profile, bindings=preset_bindings)
    bound_dimmers = _verified_dimmer_bindings(profile=profile, bindings=dimmer_bindings)
    bound_effects = _verified_effect_bindings(
        profile=profile,
        catalog_entries=effect_catalog_entries,
        effect_application_capability=effect_application_capability,
    )
    application_verified = bool(
        isinstance(effect_application_capability, Mapping)
        and effect_application_capability.get("status") == "REAL_MACHINE_VERIFIED"
        and effect_application_capability.get("grammar") == "EFFECT_POOL_CALL"
    )
    strict_template_effects = _strict_template_effect_inventory(profile)

    groups_out: list[dict[str, Any]] = []
    groups = profile.get("groups")
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping):
            continue
        group_id = group.get("group_id")
        if isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1:
            continue
        member_ids = [
            value for value in (group.get("fixture_ids_in_selection_order") or [])
            if isinstance(value, int) and not isinstance(value, bool)
        ]
        type_labels = sorted({
            label
            for fixture_id in member_ids
            if (label := _fixture_type_label((fixtures.get(fixture_id) or {}).get("fixture_type")))
        })

        dimensions: dict[str, Any] = {}
        for dimension in ARTISTIC_DIMENSIONS:
            if dimension == "DIMMER":
                direct_evidence = bound_dimmers.get(group_id)
                dimensions[dimension] = {
                    "execution_status": (
                        "SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL"
                        if direct_evidence
                        else ("DIRECT_GROUP_LEVEL_UNVERIFIED_CAPABILITY" if member_ids else "UNAVAILABLE_EMPTY_GROUP")
                    ),
                    "implementation": "SET_DIMMER",
                    "technical_capability": _technical_dimension_status("DIMMER", type_labels, profiles),
                    "application_evidence": deepcopy(direct_evidence) if direct_evidence else None,
                }
                continue
            technical = _technical_dimension_status(dimension, type_labels, profiles)
            dimensions[dimension] = {
                "execution_status": "NO_VERIFIED_RESOURCE",
                "technical_capability": technical,
            }

        presets = bound_presets.get(group_id, [])
        for preset in presets:
            dimensions[preset["dimension"]]["execution_status"] = "VERIFIED_PRESET_RESOURCE"
        effects = list(bound_effects.get(group_id, []))
        dimmer_verified = (
            dimensions["DIMMER"]["technical_capability"].get("status") == "SHOW_BOUND_VERIFIED"
            or dimensions["DIMMER"]["execution_status"] == "SHOW_BOUND_VERIFIED_DIRECT_GROUP_LEVEL"
        )
        if application_verified and dimmer_verified:
            existing_ids = {item.get("effect_id") for item in effects}
            for template in strict_template_effects:
                if template["effect_id"] in existing_ids:
                    continue
                effects.append({
                    **deepcopy(template),
                    "application_status": "REAL_MACHINE_VERIFIED",
                    "group_binding": "GROUP_SELECTED_BEFORE_EFFECT_CALL",
                })
        effects.sort(key=lambda item: int(item.get("effect_id") or 0))
        if any(item.get("application_status") == "REAL_MACHINE_VERIFIED" for item in effects):
            dimensions["EFFECT"]["execution_status"] = "VERIFIED_EFFECT_RESOURCE"
        elif effects:
            dimensions["EFFECT"]["execution_status"] = "RESOURCE_VERIFIED_APPLICATION_UNVERIFIED"

        groups_out.append({
            "group_id": group_id,
            "name": group.get("name"),
            "member_count": len(member_ids),
            "fixture_types": type_labels,
            "dimensions": dimensions,
            "preset_resources": presets,
            "effect_resources": effects,
        })

    groups_out.sort(key=lambda item: item["group_id"])
    bound_refs = {
        item["reference"]
        for group in groups_out
        for item in group["preset_resources"]
    }
    unbound_presets = [
        {
            "reference": reference,
            "preset_type": preset.get("preset_type"),
            "name": preset.get("name"),
            "group_applicability": "UNVERIFIED",
        }
        for reference, preset in sorted(_preset_inventory(profile).items())
        if reference not in bound_refs
    ]
    executable_effect_ids = {
        effect["effect_id"]
        for group in groups_out
        for effect in group["effect_resources"]
        if effect.get("application_status") == "REAL_MACHINE_VERIFIED"
    }
    return {
        "schema": ARTISTIC_RESOURCE_MAP_SCHEMA,
        "show_identity": identity,
        "groups": groups_out,
        "unbound_presets": unbound_presets,
        "effect_inventory_summary": {
            "current_show_total": len(_effect_inventory(profile)),
            "strict_semantic_template_count": len(strict_template_effects),
            "verified_group_bound": sum(len(group["effect_resources"]) for group in groups_out),
            "executable_effect_ids": sorted(executable_effect_ids),
            "unverified_effects_exposed_to_designer": 0,
        },
        "rules": {
            "group_name_implies_capability": False,
            "preset_type_implies_group_applicability": False,
            "effect_id_implies_artistic_verification": False,
            "unsupported_dimensions_are_substituted": False,
        },
    }


def preset_applicability_from_map(resource_map: Mapping[str, Any]) -> dict[int, set[str]]:
    result: dict[int, set[str]] = {}
    for group in resource_map.get("groups", []) if isinstance(resource_map.get("groups"), list) else []:
        if not isinstance(group, Mapping) or not isinstance(group.get("group_id"), int):
            continue
        refs = {
            str(item.get("reference"))
            for item in (group.get("preset_resources") or [])
            if isinstance(item, Mapping) and item.get("reference")
        }
        result[group["group_id"]] = refs
    return result


def effect_applicability_from_map(resource_map: Mapping[str, Any]) -> dict[int, set[int]]:
    result: dict[int, set[int]] = {}
    for group in resource_map.get("groups", []) if isinstance(resource_map.get("groups"), list) else []:
        if not isinstance(group, Mapping) or not isinstance(group.get("group_id"), int):
            continue
        ids = {
            int(item["effect_id"])
            for item in (group.get("effect_resources") or [])
            if isinstance(item, Mapping)
            and isinstance(item.get("effect_id"), int)
            and item.get("application_status") == "REAL_MACHINE_VERIFIED"
        }
        result[group["group_id"]] = ids
    return result


def model_resource_contract(resource_map: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return only Group-bound executable resources for the designer prompt."""
    rows: list[dict[str, Any]] = []
    groups = resource_map.get("groups")
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping):
            continue
        executable_presets = [
            {
                "dimension": item.get("dimension"),
                "reference": item.get("reference"),
                "name": item.get("name"),
            }
            for item in (group.get("preset_resources") or [])
            if isinstance(item, Mapping)
        ]
        executable_effects = [
            {
                "effect_id": item.get("effect_id"),
                "name": item.get("name"),
                "semantic_label": item.get("semantic_label"),
                "kind": item.get("kind"),
            }
            for item in (group.get("effect_resources") or [])
            if isinstance(item, Mapping) and item.get("application_status") == "REAL_MACHINE_VERIFIED"
        ]
        rows.append({
            "group_id": group.get("group_id"),
            "name": group.get("name"),
            "dimensions": deepcopy(group.get("dimensions") or {}),
            "presets": executable_presets,
            "effects": executable_effects,
        })
    return rows
