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
SPATIAL_BOOTSTRAP_MODES = frozenset({"NEW_UNDESIGNED_SHOW", "IMPORTED_EXISTING_SHOW"})
ZEN_STAGE_FRAME_ID = "ZEN_STAGE_FRAME_V1"
OPERATOR_STAGE_CONTEXT_SCHEMA = "zen.operator_current_show_stage_context.v0.1"
SHOW_BOUND_CAPABILITY_SCHEMA = "zen.show_bound_fixture_capability_profiles.v0.1"
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")


class LiveShowSnapshotError(ValueError):
    """Raised when a supplied current Show snapshot cannot be trusted."""


@dataclass(frozen=True)
class CurrentShowSnapshotInput:
    """Explicit runtime input built by the caller from saved scan artifacts."""

    snapshot: Mapping[str, Any]
    show_profile: Mapping[str, Any] | None = None
    spatial_bootstrap_mode: str = "IMPORTED_EXISTING_SHOW"
    operator_stage_context: Mapping[str, Any] | None = None
    show_bound_capability_profiles: Mapping[str, Any] | None = None


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


def _source_artifacts(
    value: CurrentShowSnapshotInput | Mapping[str, Any],
) -> tuple[
    Mapping[str, Any], Mapping[str, Any] | None, str,
    Mapping[str, Any] | None, Mapping[str, Any] | None,
]:
    if isinstance(value, CurrentShowSnapshotInput):
        return (
            value.snapshot,
            value.show_profile,
            value.spatial_bootstrap_mode,
            value.operator_stage_context,
            value.show_bound_capability_profiles,
        )
    if not isinstance(value, Mapping):
        raise LiveShowSnapshotError("current_show_snapshot must be a snapshot object or CurrentShowSnapshotInput.")
    # A compact wrapper allows callers to supply both saved Phase A artifacts.
    if isinstance(value.get("snapshot"), Mapping):
        profile = value.get("show_profile")
        stage_context = value.get("operator_stage_context")
        capabilities = value.get("show_bound_capability_profiles")
        return (
            value["snapshot"],
            profile if isinstance(profile, Mapping) else None,
            str(value.get("spatial_bootstrap_mode", "IMPORTED_EXISTING_SHOW")),
            stage_context if isinstance(stage_context, Mapping) else None,
            capabilities if isinstance(capabilities, Mapping) else None,
        )
    return (
        value,
        None,
        str(value.get("spatial_bootstrap_mode", "IMPORTED_EXISTING_SHOW")),
        value.get("operator_stage_context") if isinstance(value.get("operator_stage_context"), Mapping) else None,
        value.get("show_bound_capability_profiles") if isinstance(value.get("show_bound_capability_profiles"), Mapping) else None,
    )


def build_zen_stage_frame(
    operator_stage_context: Mapping[str, Any],
    *,
    show_fingerprint: str,
) -> dict[str, object]:
    """Build the canonical ZEN design frame from fingerprint-bound stage evidence.

    This frame is deliberately independent of scanned fixture Pos X/Y/Z. Its
    axes are ZEN design-space semantics, not an assertion about the MA2
    fixture-object coordinate signs or a metric transform usable for writes.
    """
    if operator_stage_context.get("schema") != OPERATOR_STAGE_CONTEXT_SCHEMA:
        raise LiveShowSnapshotError("NEW_UNDESIGNED_SHOW requires a supported operator stage-context artifact.")
    if (
        operator_stage_context.get("source_type") != "OPERATOR_SUPPLIED_STAGE_CONTEXT"
        or operator_stage_context.get("status") != "OPERATOR_VERIFIED"
        or operator_stage_context.get("asserted_by") != "OPERATOR"
        or operator_stage_context.get("show_fingerprint") != show_fingerprint
    ):
        raise LiveShowSnapshotError("Operator stage context must be verified and bound to the current Show fingerprint.")
    stage_region = operator_stage_context.get("stage_region")
    orientation = operator_stage_context.get("orientation")
    performer = operator_stage_context.get("performer_context")
    scope = operator_stage_context.get("conceptual_design_scope")
    image = operator_stage_context.get("stage_view_image")
    pan_tilt = operator_stage_context.get("pan_tilt_calibration")
    coordinate_sign_mapping = operator_stage_context.get("coordinate_sign_mapping")
    if (
        not isinstance(stage_region, Mapping)
        or stage_region.get("status") != "OPERATOR_VERIFIED"
        or not isinstance(stage_region.get("shape"), str)
        or not stage_region.get("shape")
        or stage_region.get("visual_bounds_known") is not True
        or not isinstance(orientation, Mapping)
        or orientation.get("viewpoint") != "FACING_STAGE"
        or orientation.get("audience_side") != "IMAGE_BOTTOM_FOREGROUND"
        or orientation.get("upstage_direction") != "IMAGE_TOP_BACKGROUND"
        or orientation.get("stage_right") != "IMAGE_LEFT"
        or orientation.get("stage_left") != "IMAGE_RIGHT"
        or not isinstance(performer, Mapping)
        or performer.get("status") != "OPERATOR_VERIFIED"
        or performer.get("zone") != "FRONT_STAGE_PRIORITY"
        or performer.get("relation") != "CLOSER_TO_AUDIENCE_THAN_UPSTAGE"
        or not isinstance(scope, Mapping)
        or scope.get("enabled") is not True
        or scope.get("scope") != "CONCEPTUAL_VIRTUAL_FIXTURE_PLACEMENT_ONLY"
        or not isinstance(image, Mapping)
        or not isinstance(image.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(image.get("sha256")))
        or not isinstance(pan_tilt, Mapping)
        or pan_tilt.get("derive_xyz_sign_mapping") is not False
        or not isinstance(coordinate_sign_mapping, Mapping)
        or any(coordinate_sign_mapping.get(axis) != "UNKNOWN" for axis in ("x", "y", "z"))
        or coordinate_sign_mapping.get("pan_tilt_may_fill_xyz_mapping") is not False
        or coordinate_sign_mapping.get("image_may_fill_xyz_mapping_without_independent_evidence") is not False
    ):
        raise LiveShowSnapshotError("Operator stage context lacks the verified stage, orientation, performer, scope, or image binding required for spatial bootstrap.")

    # Exact canonical design-space convention supplied by the owner. This is
    # never derived from fixture extrema or Pan/Tilt calibration.
    return {
        "schema": "zen.stage_frame.v0.1",
        "frame_id": ZEN_STAGE_FRAME_ID,
        "authority": "ZEN_DESIGN_SPACE_CONVENTION_BOUND_TO_OPERATOR_STAGE_CONTEXT",
        "show_fingerprint": show_fingerprint,
        "origin": "STAGE_CENTER",
        "axes": {
            "X_POSITIVE": "STAGE_LEFT",
            "X_NEGATIVE": "STAGE_RIGHT",
            "Y_POSITIVE": "UPSTAGE",
            "Y_NEGATIVE": "DOWNSTAGE_AUDIENCE",
            "Z_POSITIVE": "UP",
        },
        "stage_shape": str(stage_region["shape"]),
        "stage_region": str(stage_region.get("region", "OPERATOR_VERIFIED_STAGE_REGION")),
        "audience_direction": "Y_NEGATIVE_DOWNSTAGE",
        "performer_zone": "FRONT_STAGE_PRIORITY",
        "performer_zone_relation": "CLOSER_TO_AUDIENCE_THAN_UPSTAGE",
        "coordinate_units": "ZEN_CONCEPTUAL_STAGE_UNITS",
        "metric_dimensions": "UNKNOWN",
        "operator_stage_view": {
            "sha256": image["sha256"],
            "viewpoint": orientation["viewpoint"],
            "audience_side": orientation["audience_side"],
            "upstage_direction": orientation["upstage_direction"],
            "stage_right": orientation["stage_right"],
            "stage_left": orientation["stage_left"],
        },
        "raw_ma2_fixture_xyz_mapping": "UNKNOWN_AND_NOT_INFERRED",
        "pan_tilt_calibration": {
            "status": pan_tilt.get("status"),
            "tilt_negative_direction": pan_tilt.get("tilt_negative_direction"),
            "tilt_positive_direction": pan_tilt.get("tilt_positive_direction"),
            "pan_negative_direction": pan_tilt.get("pan_negative_direction"),
            "pan_positive_direction": pan_tilt.get("pan_positive_direction"),
            "xyz_sign_mapping_inference": "PROHIBITED",
        },
        "installation_feasibility": "NOT_GRANTED",
    }


def _validate_show_bound_capabilities(
    value: Mapping[str, Any] | None,
    *,
    fingerprint: str,
    fixtures: Mapping[int, Mapping[str, object]],
) -> dict[str, object]:
    """Accept only exact, fingerprint-bound FixtureType capability evidence."""
    if value is None:
        return {
            "status": "UNKNOWN_FOR_CURRENT_FINGERPRINT",
            "show_fingerprint": fingerprint,
            "verified_fixture_type_profiles": [],
            "reason": "No current-fingerprint capability profile artifact was supplied.",
        }
    if (
        value.get("schema") != SHOW_BOUND_CAPABILITY_SCHEMA
        or value.get("show_fingerprint") != fingerprint
        or value.get("source") != "MA2_EXPORT_FIXTURE_TYPE_XML"
        or not isinstance(value.get("profiles"), list)
    ):
        raise LiveShowSnapshotError("Capability profiles must be a supported artifact bound to the current Show fingerprint.")
    seen_fixture_ids: set[int] = set()
    normalized: list[dict[str, object]] = []
    for profile in value["profiles"]:
        if not isinstance(profile, Mapping):
            raise LiveShowSnapshotError("Show-bound capability profile rows must be objects.")
        fixture_id = profile.get("fixture_id")
        fixture = fixtures.get(fixture_id) if isinstance(fixture_id, int) and not isinstance(fixture_id, bool) else None
        type_identity = profile.get("fixture_type_identity")
        fixture_type_id = type_identity.get("fixture_type_id") if isinstance(type_identity, Mapping) else None
        observed = profile.get("observed_attributes")
        capabilities = profile.get("capabilities")
        if (
            fixture is None
            or fixture_id == 9999
            or fixture_id in seen_fixture_ids
            or profile.get("show_fingerprint") != fingerprint
            or profile.get("confidence") != "SHOW_BOUND_VERIFIED"
            or profile.get("artistic_role_inference") != "NONE"
            or not isinstance(profile.get("source"), str)
            or not profile["source"].strip()
            or not profile["source"].startswith("MA2_EXPORT_FIXTURE_TYPE_XML")
            or not isinstance(type_identity, Mapping)
            or isinstance(fixture_type_id, bool)
            or not isinstance(fixture_type_id, int)
            or fixture_type_id < 1
            or not isinstance(type_identity.get("list_label"), str)
            or not type_identity.get("list_label", "").strip()
            or type_identity.get("list_label", "").strip().casefold() == "unknown"
            or type_identity.get("list_label") != fixture.get("fixture_type_identity")
            or not isinstance(observed, list)
            or not observed
            or any(not isinstance(item, str) or not item for item in observed)
            or not isinstance(capabilities, Mapping)
        ):
            raise LiveShowSnapshotError("Capability profile identity/provenance does not exactly match a non-protected current Show fixture.")
        seen_fixture_ids.add(fixture_id)
        normalized.append({
            "show_fingerprint": fingerprint,
            "fixture_id": fixture_id,
            "fixture_type_identity": {
                "fixture_type_id": type_identity.get("fixture_type_id"),
                "list_label": type_identity["list_label"],
            },
            "source": profile["source"],
            "observed_attributes": sorted(set(observed)),
            "capabilities": dict(capabilities),
            "confidence": "SHOW_BOUND_VERIFIED",
            "artistic_role_inference": "NONE",
        })
    expected_ids = {fixture_id for fixture_id in fixtures if fixture_id != 9999}
    complete = bool(expected_ids) and seen_fixture_ids == expected_ids
    declared_count = value.get("capability_profile_count")
    if declared_count is not None and declared_count != len(normalized):
        raise LiveShowSnapshotError("Capability profile count does not match the supplied profile rows.")
    return {
        "status": "SHOW_BOUND_VERIFIED" if complete else "PARTIAL_SHOW_BOUND_VERIFIED",
        "show_fingerprint": fingerprint,
        "verified_fixture_type_profiles": sorted(normalized, key=lambda item: int(item["fixture_id"])),
        "profiled_fixture_count": len(normalized),
        "unprofiled_fixture_ids": sorted(expected_ids - seen_fixture_ids),
        "reason": "Exact FixtureType identity and exported attributes are Show-bound; fixture labels are not artistic roles.",
    }


def normalize_current_show_snapshot(
    value: CurrentShowSnapshotInput | Mapping[str, Any],
) -> dict[str, object]:
    """Validate and normalize a saved Phase A scan without making MA2 calls.

    Imported mode may retain directly scanned numeric geometry for optional
    legacy comparison. Bootstrap mode retains fixture identities only and
    excludes initial XYZ/rotation from design authority. Derived axis labels,
    patch/address information, cached Show evidence, and inferred artistic
    semantics are intentionally excluded in both modes.
    """
    snapshot, profile, bootstrap_mode, operator_stage_context, capability_profiles = _source_artifacts(value)
    if bootstrap_mode not in SPATIAL_BOOTSTRAP_MODES:
        raise LiveShowSnapshotError("spatial_bootstrap_mode must be NEW_UNDESIGNED_SHOW or IMPORTED_EXISTING_SHOW.")
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
    if bootstrap_mode == "IMPORTED_EXISTING_SHOW" and (not isinstance(geometry_values, list) or not geometry_values):
        raise LiveShowSnapshotError("IMPORTED_EXISTING_SHOW requires readable fixture geometry rows for optional legacy calibration.")
    if (
        bootstrap_mode == "IMPORTED_EXISTING_SHOW"
        and isinstance(geometry_state, Mapping)
        and (geometry_state.get("stale") is True or str(geometry_state.get("status", "")).casefold() != "available")
    ):
        raise LiveShowSnapshotError("Current Show fixture geometry must be fresh and available.")
    if bootstrap_mode == "NEW_UNDESIGNED_SHOW" and (
        not isinstance(geometry_state, Mapping)
        or geometry_state.get("stale") is True
        or str(geometry_state.get("status", "")).casefold() != "available"
    ):
        # Stale geometry cannot be used even as identity evidence. Bootstrap
        # falls back to current fixture-inventory identities instead.
        geometry_values = []
    if geometry_values is None:
        geometry_values = []
    if not isinstance(geometry_values, list):
        raise LiveShowSnapshotError("Fixture geometry values must be an array when supplied.")
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
        if bootstrap_mode == "NEW_UNDESIGNED_SHOW":
            # Keep scanned identities for ref validation, but deliberately do
            # not make pre-existing fixture coordinates part of this design
            # input. The raw scan remains available through source_artifact_hash.
            position = None
            rotation = None
        else:
            position = _xyz(item.get("position"), field=f"geometry {fixture_id}.{subfixture_id}.position")
            rotation = _rotation(item.get("rotation"), field=f"geometry {fixture_id}.{subfixture_id}.rotation")
        source = item.get("source")
        confidence = item.get("confidence")
        geometry_row: dict[str, object] = {
            "subfixture_id": subfixture_id,
            "source": source if isinstance(source, str) else "UNKNOWN",
            "confidence": confidence if isinstance(confidence, str) else "UNKNOWN",
        }
        if bootstrap_mode != "NEW_UNDESIGNED_SHOW":
            geometry_row.update({"xyz": position, "rotation": rotation})
        fixture_map[fixture_id]["geometry"].append(geometry_row)
        allowed_subfixture_refs.add(ref)
        normalized_geometry_count += 1

    groups = snapshot.get("groups")
    if bootstrap_mode == "IMPORTED_EXISTING_SHOW" and (not isinstance(groups, list) or not groups):
        raise LiveShowSnapshotError("IMPORTED_EXISTING_SHOW requires a non-empty Group inventory.")
    if groups is None and bootstrap_mode == "NEW_UNDESIGNED_SHOW":
        groups = []
    if not isinstance(groups, list):
        raise LiveShowSnapshotError("Group inventory must be an array when supplied.")
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

    stage_frame: dict[str, object] | None = None
    if bootstrap_mode == "NEW_UNDESIGNED_SHOW":
        if not isinstance(operator_stage_context, Mapping):
            raise LiveShowSnapshotError("NEW_UNDESIGNED_SHOW requires explicit operator or verified Stage context.")
        stage_frame = build_zen_stage_frame(operator_stage_context, show_fingerprint=fingerprint)
    capabilities = _validate_show_bound_capabilities(
        capability_profiles,
        fingerprint=fingerprint,
        fixtures=fixture_map,
    )
    capability_by_fixture = {
        int(item["fixture_id"]): item
        for item in capabilities.get("verified_fixture_type_profiles", [])
        if isinstance(item, Mapping) and isinstance(item.get("fixture_id"), int)
    }
    for fixture_id, fixture in fixture_map.items():
        fixture["capability_profile"] = capability_by_fixture.get(fixture_id)
    source_wrapper = {
        "snapshot": snapshot,
        "show_profile": profile,
        "spatial_bootstrap_mode": bootstrap_mode,
        "operator_stage_context": operator_stage_context,
        "show_bound_capability_profiles": capability_profiles,
    }
    source_hash = hashlib.sha256(_canonical(source_wrapper).encode("utf-8")).hexdigest()
    geometry_status = snapshot.get("stage_geometry_readability", {})
    status = geometry_status.get("status") if isinstance(geometry_status, Mapping) else None
    if bootstrap_mode == "NEW_UNDESIGNED_SHOW":
        placement_resource_refs: list[dict[str, int]] = []
        for fixture in fixture_map.values():
            fixture_id = int(fixture["fixture_id"])
            if fixture_id == 9999:
                continue
            geometry_rows = fixture.get("geometry", [])
            if isinstance(geometry_rows, list) and geometry_rows:
                placement_resource_refs.extend(
                    {"fixture_id": fixture_id, "subfixture_id": int(row["subfixture_id"])}
                    for row in geometry_rows if isinstance(row, Mapping)
                )
            else:
                # A whole-fixture identity is valid when no subfixture identity
                # was scanned; do not fabricate a subfixture number.
                placement_resource_refs.append({"fixture_id": fixture_id})
        coordinate_system: dict[str, object] = dict(stage_frame or {})
    else:
        placement_resource_refs = [
            {"fixture_id": int(fixture["fixture_id"]), "subfixture_id": int(row["subfixture_id"])}
            for fixture in fixture_map.values()
            for row in fixture.get("geometry", [])
            if isinstance(row, Mapping) and int(fixture["fixture_id"]) != 9999
        ]
        coordinate_system = {
            "frame": "SCANNED_MA2_FIXTURE_COORDINATES",
            "axis_semantics": "UNKNOWN",
            "units": "UNKNOWN",
        }
    return {
        "schema": NORMALIZED_SCHEMA,
        "show_fingerprint": fingerprint,
        "fingerprint_confidence": identity.get("confidence", "UNKNOWN"),
        "source_artifact_hash": source_hash,
        "captured_at": snapshot.get("captured_at", "UNKNOWN"),
        "source_schema": SNAPSHOT_SCHEMA,
        "coordinate_system": coordinate_system,
        "ma2_fixture_coordinate_system": {
            "frame": "SCANNED_MA2_FIXTURE_COORDINATES",
            "axis_semantics": "UNKNOWN",
            "units": "UNKNOWN",
            "sign_mapping": "UNKNOWN",
        },
        "spatial_bootstrap_mode": bootstrap_mode,
        "initial_fixture_geometry": "UNDESIGNED" if bootstrap_mode == "NEW_UNDESIGNED_SHOW" else "EXISTING_IMPORTED_GEOMETRY",
        "stage_frame": stage_frame,
        "operator_stage_context": dict(operator_stage_context) if isinstance(operator_stage_context, Mapping) else None,
        "placement_resource_refs": sorted(
            placement_resource_refs,
            key=lambda ref: (int(ref["fixture_id"]), int(ref.get("subfixture_id", 0))),
        ),
        "fixture_count": len(fixture_map),
        "geometry_record_count": normalized_geometry_count,
        "group_count": len(normalized_groups),
        "fixture_inventory": [fixture_map[key] for key in sorted(fixture_map)],
        "groups": sorted(normalized_groups, key=lambda item: item["group_id"]),
        "technical_capabilities": capabilities,
        "geometry_status": status or "UNKNOWN",
        "limitations": [
            "Fixture and Group labels are identity evidence only, not artistic roles.",
            "Fixture 9999 is visible as protected inventory evidence but unavailable for artistic assignment or placement.",
            "Raw MA2 fixture Pos/Rot values are not the ZEN stage frame and are not an authorized write transform.",
            "Metric stage dimensions and physical installation feasibility are not established.",
            *([] if capabilities.get("status") == "SHOW_BOUND_VERIFIED" else ["Current-fingerprint fixture capability profiles are incomplete or unavailable."]),
            *(["Imported fixture geometry is available only as optional historical/comparison evidence."] if bootstrap_mode == "IMPORTED_EXISTING_SHOW" else ["Initial fixture geometry is UNDESIGNED; scanned XYZ/rotation values are excluded from spatial-design authority."]),
        ],
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
