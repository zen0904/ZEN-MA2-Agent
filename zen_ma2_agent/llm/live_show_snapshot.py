"""Typed, read-only normalization for caller-supplied current Show evidence.

The module consumes an already captured Phase A snapshot.  It performs no MA2
discovery or transport and deliberately removes patch/address details before
the data can become model-facing context.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping


SNAPSHOT_SCHEMA = "zen.sheesh_current_show_redesign_snapshot.v0.1"
PROFILE_SCHEMA = "zen.show_profile.v0.1"
NORMALIZED_SCHEMA = "zen.current_show_snapshot_context.v0.1"
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")


class LiveShowSnapshotError(ValueError):
    """Raised when a supplied current Show snapshot cannot be trusted."""


@dataclass(frozen=True)
class CurrentShowSnapshotInput:
    """Explicit runtime input built by the caller from saved scan artifacts."""

    snapshot: Mapping[str, Any]
    show_profile: Mapping[str, Any] | None = None


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _finite_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise LiveShowSnapshotError(f"Snapshot {field} must be a finite number.")
    return float(value)


def _identity(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LiveShowSnapshotError(f"Snapshot {label} must be a positive integer.")
    return value


def _xyz(value: object, *, field: str) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise LiveShowSnapshotError(f"Snapshot {field} must be an XYZ object.")
    return {axis: _finite_number(value.get(axis), field=f"{field}.{axis}") for axis in ("x", "y", "z")}


def _rotation(value: object, *, field: str) -> dict[str, float] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise LiveShowSnapshotError(f"Snapshot {field} must be a rotation object when present.")
    return {axis: _finite_number(value.get(axis), field=f"{field}.{axis}") for axis in ("x", "y", "z")}


def _source_artifacts(value: CurrentShowSnapshotInput | Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any] | None]:
    if isinstance(value, CurrentShowSnapshotInput):
        return value.snapshot, value.show_profile
    if not isinstance(value, Mapping):
        raise LiveShowSnapshotError("current_show_snapshot must be a snapshot object or CurrentShowSnapshotInput.")
    # A compact wrapper allows callers to supply both saved Phase A artifacts.
    if isinstance(value.get("snapshot"), Mapping):
        profile = value.get("show_profile")
        return value["snapshot"], profile if isinstance(profile, Mapping) else None
    return value, None


def normalize_current_show_snapshot(
    value: CurrentShowSnapshotInput | Mapping[str, Any],
) -> dict[str, object]:
    """Validate and normalize a saved Phase A scan without making MA2 calls.

    Only directly scanned identity and numeric geometry are emitted.  Derived
    axis labels, patch/address information, cached Show evidence, and inferred
    artistic semantics are intentionally excluded.
    """
    snapshot, profile = _source_artifacts(value)
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise LiveShowSnapshotError(f"current_show_snapshot schema must be {SNAPSHOT_SCHEMA}.")
    identity = snapshot.get("show_identity")
    if not isinstance(identity, Mapping):
        raise LiveShowSnapshotError("current_show_snapshot is missing show_identity.")
    fingerprint = identity.get("value")
    if not isinstance(fingerprint, str) or not FINGERPRINT_RE.fullmatch(fingerprint):
        raise LiveShowSnapshotError("current_show_snapshot requires a 64-character scan fingerprint.")
    if profile is not None:
        if profile.get("schema") != PROFILE_SCHEMA:
            raise LiveShowSnapshotError(f"show_profile schema must be {PROFILE_SCHEMA}.")
        profile_identity = profile.get("show_identity")
        if not isinstance(profile_identity, Mapping) or profile_identity.get("value") != fingerprint:
            raise LiveShowSnapshotError("The supplied Show profile fingerprint does not match the current snapshot.")

    resource_status = snapshot.get("resource_status")
    if not isinstance(resource_status, Mapping):
        raise LiveShowSnapshotError("current_show_snapshot is missing resource_status.")

    fixture_state = resource_status.get("fixtures")
    fixture_values = fixture_state.get("values") if isinstance(fixture_state, Mapping) else None
    if not isinstance(fixture_values, list) or not fixture_values:
        raise LiveShowSnapshotError("current_show_snapshot must include a non-empty fixture inventory.")
    if isinstance(fixture_state, Mapping) and (fixture_state.get("stale") is True or str(fixture_state.get("status", "")).casefold() != "available"):
        raise LiveShowSnapshotError("Current Show fixture inventory must be fresh and available.")
    fixture_map: dict[int, dict[str, object]] = {}
    for item in fixture_values:
        if not isinstance(item, Mapping):
            raise LiveShowSnapshotError("Fixture inventory rows must be objects.")
        fixture_id = _identity(item.get("number"), label="fixture number")
        if fixture_id in fixture_map:
            raise LiveShowSnapshotError(f"Duplicate fixture identity {fixture_id} in current snapshot.")
        fixture_type = item.get("fixture_type")
        if fixture_type is not None and not isinstance(fixture_type, str):
            raise LiveShowSnapshotError("Fixture type identity must be a string when supplied.")
        name = item.get("name")
        if name is not None and not isinstance(name, str):
            raise LiveShowSnapshotError("Fixture name identity must be a string when supplied.")
        fixture_map[fixture_id] = {
            "fixture_id": fixture_id,
            "name": name or "UNKNOWN",
            "fixture_type_identity": fixture_type or "UNKNOWN",
            "availability": "PROTECTED_UNAVAILABLE" if fixture_id == 9999 else "AVAILABLE_INVENTORY_ONLY",
            "geometry": [],
        }

    geometry_state = resource_status.get("fixture_geometry")
    geometry_values = geometry_state.get("values") if isinstance(geometry_state, Mapping) else None
    if not isinstance(geometry_values, list) or not geometry_values:
        raise LiveShowSnapshotError("current_show_snapshot must include readable fixture geometry rows.")
    if isinstance(geometry_state, Mapping) and (geometry_state.get("stale") is True or str(geometry_state.get("status", "")).casefold() != "available"):
        raise LiveShowSnapshotError("Current Show fixture geometry must be fresh and available.")
    allowed_subfixture_refs: set[tuple[int, int]] = set()
    normalized_geometry_count = 0
    for item in geometry_values:
        if not isinstance(item, Mapping):
            raise LiveShowSnapshotError("Fixture geometry rows must be objects.")
        fixture_id = _identity(item.get("fixture_id"), label="geometry fixture_id")
        subfixture_id = _identity(item.get("subfixture_id"), label="geometry subfixture_id")
        if fixture_id not in fixture_map:
            raise LiveShowSnapshotError(f"Geometry references unknown fixture {fixture_id}.")
        ref = (fixture_id, subfixture_id)
        if ref in allowed_subfixture_refs:
            raise LiveShowSnapshotError(f"Duplicate geometry identity {fixture_id}.{subfixture_id}.")
        position = _xyz(item.get("position"), field=f"geometry {fixture_id}.{subfixture_id}.position")
        rotation = _rotation(item.get("rotation"), field=f"geometry {fixture_id}.{subfixture_id}.rotation")
        source = item.get("source")
        confidence = item.get("confidence")
        fixture_map[fixture_id]["geometry"].append({
            "subfixture_id": subfixture_id,
            "xyz": position,
            "rotation": rotation,
            "source": source if isinstance(source, str) else "UNKNOWN",
            "confidence": confidence if isinstance(confidence, str) else "UNKNOWN",
        })
        allowed_subfixture_refs.add(ref)
        normalized_geometry_count += 1

    groups = snapshot.get("groups")
    if not isinstance(groups, list) or not groups:
        raise LiveShowSnapshotError("current_show_snapshot must include a non-empty Group inventory.")
    normalized_groups: list[dict[str, object]] = []
    seen_groups: set[int] = set()
    for item in groups:
        if not isinstance(item, Mapping):
            raise LiveShowSnapshotError("Group inventory rows must be objects.")
        group_id = _identity(item.get("group_id"), label="group_id")
        if group_id in seen_groups:
            raise LiveShowSnapshotError(f"Duplicate Group identity {group_id} in current snapshot.")
        members = item.get("fixture_ids_in_selection_order")
        if not isinstance(members, list):
            raise LiveShowSnapshotError(f"Group {group_id} membership must be an array.")
        normalized_members = [_identity(member, label=f"Group {group_id} fixture id") for member in members]
        unknown = sorted(set(normalized_members) - set(fixture_map))
        if unknown:
            raise LiveShowSnapshotError(f"Group {group_id} contains unknown fixtures: {unknown}.")
        group_name = item.get("name")
        if group_name is not None and not isinstance(group_name, str):
            raise LiveShowSnapshotError(f"Group {group_id} name must be a string.")
        normalized_groups.append({
            "group_id": group_id,
            "label_identity_only": group_name or "UNKNOWN",
            "fixture_ids_in_selection_order": normalized_members,
        })
        seen_groups.add(group_id)

    for fixture in fixture_map.values():
        fixture["group_ids"] = [
            group["group_id"] for group in normalized_groups
            if fixture["fixture_id"] in group["fixture_ids_in_selection_order"]
        ]
        fixture["geometry"] = sorted(fixture["geometry"], key=lambda row: row["subfixture_id"])

    fixture_count = snapshot.get("fixture_count")
    if fixture_count is not None and fixture_count != len(fixture_map):
        raise LiveShowSnapshotError("Declared fixture_count does not match the scanned inventory.")
    if snapshot.get("group_count") is not None and snapshot.get("group_count") != len(normalized_groups):
        raise LiveShowSnapshotError("Declared group_count does not match the scanned inventory.")

    source_wrapper = {"snapshot": snapshot, "show_profile": profile}
    source_hash = hashlib.sha256(_canonical(source_wrapper).encode("utf-8")).hexdigest()
    geometry_status = snapshot.get("stage_geometry_readability", {})
    status = geometry_status.get("status") if isinstance(geometry_status, Mapping) else None
    return {
        "schema": NORMALIZED_SCHEMA,
        "show_fingerprint": fingerprint,
        "fingerprint_confidence": identity.get("confidence", "UNKNOWN"),
        "source_artifact_hash": source_hash,
        "captured_at": snapshot.get("captured_at", "UNKNOWN"),
        "source_schema": SNAPSHOT_SCHEMA,
        "coordinate_system": {
            "frame": "SCANNED_MA2_FIXTURE_COORDINATES",
            "axis_semantics": "UNKNOWN",
            "units": "UNKNOWN",
        },
        "fixture_count": len(fixture_map),
        "geometry_record_count": normalized_geometry_count,
        "group_count": len(normalized_groups),
        "fixture_inventory": [fixture_map[key] for key in sorted(fixture_map)],
        "groups": sorted(normalized_groups, key=lambda item: item["group_id"]),
        "technical_capabilities": {
            "status": "UNKNOWN_FOR_CURRENT_FINGERPRINT",
            "verified_fixture_type_profiles": [],
            "reason": "The saved current Show profile exposes no verified fixture capability profiles. Cached capability evidence with a different Show fingerprint is excluded from current truth.",
        },
        "geometry_status": status or "UNKNOWN",
        "limitations": [
            "Fixture and Group labels are identity evidence only, not artistic roles.",
            "Fixture 9999 is visible as protected inventory evidence but unavailable for artistic assignment or placement.",
            "Numeric coordinate axes are not semantically calibrated; do not infer stage-left/right or performer zones.",
            "No current-fingerprint fixture capability claims are supplied.",
        ],
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
