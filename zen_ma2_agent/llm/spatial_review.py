"""Review-state and fact-calibration helpers for live spatial design runs.

These helpers classify provider-authored artifacts and verified snapshot
evidence.  They do not create or edit artistic content and do not authorize
MA2 writes.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from collections.abc import Mapping
from typing import Any


CALIBRATION_SCHEMA = "zen.sheesh_spatial_fact_calibration.v0.1"
ALLOWED_CRITIC_SEVERITIES = frozenset(
    {"BLOCKER", "DESIGN_WEAKNESS", "OPTIONAL_IMPROVEMENT", "NONE"}
)
MAX_SPATIAL_REVISION_CYCLES = 2

CALIBRATION_FACT_FIELDS = (
    "COORDINATE_FRAME_VERIFIED",
    "X_AXIS_SEMANTICS",
    "Y_AXIS_SEMANTICS",
    "Z_AXIS_SEMANTICS",
    "COORDINATE_UNITS_VERIFIED",
    "STAGE_VIEW_CAPTURE_SUPPORTED",
    "STAGE_VIEW_IMAGE_AVAILABLE",
    "STAGE_BOUNDS_KNOWN",
    "PERFORMER_ZONE_KNOWN",
    "AUDIENCE_DIRECTION_KNOWN",
    "UPSTAGE_DOWNSTAGE_KNOWN",
    "STAGE_LEFT_RIGHT_KNOWN",
    "FIXTURE_MOUNTING_POSITIONS_KNOWN",
    "FIXTURE_ORIENTATION_WRITABLE",
    "FIXTURE_ORIENTATION_READABLE",
    "OBSTRUCTION_DATA_AVAILABLE",
    "TRUSS_OR_SUPPORT_GEOMETRY_AVAILABLE",
    "CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE",
)

REVISION_REQUIRED_VERIFIED_FACTS = (
    "COORDINATE_FRAME_VERIFIED",
    "X_AXIS_SEMANTICS",
    "Y_AXIS_SEMANTICS",
    "Z_AXIS_SEMANTICS",
    "COORDINATE_UNITS_VERIFIED",
    "STAGE_VIEW_IMAGE_AVAILABLE",
    "STAGE_BOUNDS_KNOWN",
    "PERFORMER_ZONE_KNOWN",
    "AUDIENCE_DIRECTION_KNOWN",
    "UPSTAGE_DOWNSTAGE_KNOWN",
    "STAGE_LEFT_RIGHT_KNOWN",
    "FIXTURE_MOUNTING_POSITIONS_KNOWN",
    "FIXTURE_ORIENTATION_READABLE",
    "CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE",
)


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def critic_severity_classification(critic_artifact: object) -> str:
    """Return the explicit qualitative Critic classification, fail closed."""
    if not isinstance(critic_artifact, Mapping):
        raise ValueError("Critic artifact must be an object.")
    severity = critic_artifact.get("severity")
    if isinstance(severity, str):
        classification = severity
    elif isinstance(severity, Mapping):
        classification = severity.get("classification")
    else:
        classification = None
    if not isinstance(classification, str) or classification not in ALLOWED_CRITIC_SEVERITIES:
        raise ValueError("Critic severity classification is missing or unsupported.")
    return classification


def build_design_review_state(
    critic_artifact: Mapping[str, Any] | None,
    *,
    live_show: bool,
    revision_cycles_completed: int = 0,
    max_revision_cycles: int = MAX_SPATIAL_REVISION_CYCLES,
    execution_status: str = "RUNNING",
) -> dict[str, Any]:
    """Create non-artistic review/eligibility metadata from a validated Critic."""
    if not 0 <= revision_cycles_completed <= max_revision_cycles:
        raise ValueError("revision_cycles_completed must be within the configured bound.")
    if max_revision_cycles < 0 or max_revision_cycles > MAX_SPATIAL_REVISION_CYCLES:
        raise ValueError(f"max_revision_cycles must be from 0 to {MAX_SPATIAL_REVISION_CYCLES}.")
    if not live_show:
        status = "NOT_APPLICABLE"
        classification = None
    elif critic_artifact is None:
        status = "PENDING"
        classification = None
    else:
        classification = critic_severity_classification(critic_artifact)
        if classification == "BLOCKER":
            status = (
                "BLOCKED_AFTER_REVISION_LIMIT"
                if revision_cycles_completed >= max_revision_cycles and max_revision_cycles > 0
                else "BLOCKED_BY_CRITIC"
            )
        else:
            status = "REVIEW_PASSED"
    requests = critic_artifact.get("revision_requests", []) if isinstance(critic_artifact, Mapping) else []
    return {
        "design_review_status": status,
        "execution_status": execution_status,
        "critic_severity": classification,
        "critic_artifact_hash": canonical_hash(critic_artifact) if critic_artifact is not None else None,
        "revision_requests": deepcopy(requests),
        "revision_cycles_completed": revision_cycles_completed,
        "max_spatial_revision_cycles": max_revision_cycles,
        "WRITEBACK_ELIGIBLE": "NO",
        "RESOLVER_ELIGIBLE": "NO",
        "PREVIEW_FOR_WRITEBACK_ELIGIBLE": "NO",
        "SPATIAL_WRITEBACK_APPROVED": "NO",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }


def validate_spatial_fact_calibration(
    value: object,
    *,
    expected_show_fingerprint: str | None = None,
    expected_snapshot_source_hash: str | None = None,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    """Validate a fact matrix while allowing any unsupported fact to be UNKNOWN."""
    if not isinstance(value, dict) or value.get("schema") != CALIBRATION_SCHEMA:
        raise ValueError(f"Spatial fact calibration schema must be {CALIBRATION_SCHEMA}.")
    fingerprint = value.get("show_fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Spatial fact calibration requires a Show fingerprint.")
    if expected_show_fingerprint is not None and fingerprint != expected_show_fingerprint:
        raise ValueError("Spatial fact calibration fingerprint does not match the current Show.")
    sources = value.get("source_artifacts")
    if not isinstance(sources, dict):
        raise ValueError("Spatial fact calibration requires source_artifacts provenance.")
    source_hash = sources.get("normalized_snapshot_source_hash")
    source_run_id = sources.get("run_id")
    if not isinstance(source_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise ValueError("Spatial fact calibration requires the normalized snapshot source hash.")
    if expected_snapshot_source_hash is not None and source_hash != expected_snapshot_source_hash:
        raise ValueError("Spatial fact calibration snapshot source hash does not match the current Show input.")
    if not isinstance(source_run_id, str) or not source_run_id:
        raise ValueError("Spatial fact calibration requires its source run ID.")
    if expected_run_id is not None and source_run_id != expected_run_id:
        raise ValueError("Spatial fact calibration source run ID does not match the revision source run.")
    facts = value.get("facts")
    if not isinstance(facts, dict):
        raise ValueError("Spatial fact calibration requires a facts object.")
    missing = [field for field in CALIBRATION_FACT_FIELDS if field not in facts]
    if missing:
        raise ValueError("Spatial fact calibration is missing facts: " + ", ".join(missing))
    evidence = value.get("fact_evidence")
    missing_evidence = [
        field for field in CALIBRATION_FACT_FIELDS
        if not isinstance(evidence, dict)
        or not isinstance(evidence.get(field), str)
        or not evidence[field].strip()
    ]
    if missing_evidence:
        raise ValueError("Spatial fact calibration lacks per-fact provenance: " + ", ".join(missing_evidence))
    unsupported_assertions = [
        field for field in CALIBRATION_FACT_FIELDS
        if facts[field] in ("YES", "VERIFIED", "KNOWN")
        and evidence[field].casefold().startswith(("unknown", "not tested", "not available"))
    ]
    if unsupported_assertions:
        raise ValueError("Spatial fact calibration marks unsupported facts verified: " + ", ".join(unsupported_assertions))
    if value.get("CODEX_ARTISTIC_INTERVENTION") != "NONE":
        raise ValueError("Spatial fact calibration must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    return value


def spatial_revision_readiness(calibration: Mapping[str, Any]) -> dict[str, Any]:
    """Determine whether essential physical semantics exist for another design.

    Unknown facts are valid calibration results, but they block this spatial
    revision experiment because its known Critic issues concern physical
    coordinate and performer/audience interpretation.
    """
    facts = calibration.get("facts", {})
    blockers = [
        field for field in REVISION_REQUIRED_VERIFIED_FACTS
        if facts.get(field) not in ("YES", "VERIFIED", "KNOWN")
    ]
    return {
        "ready": not blockers,
        "status": "READY" if not blockers else "BLOCKED_MISSING_EVIDENCE",
        "blocking_facts": blockers,
    }


def geometry_delta(
    snapshot: Mapping[str, Any],
    position_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare a proposal with scanned numeric geometry without judging it."""
    originals: dict[tuple[int, int], Mapping[str, Any]] = {}
    for fixture in snapshot.get("fixture_inventory", []):
        if not isinstance(fixture, Mapping):
            continue
        fixture_id = fixture.get("fixture_id")
        if isinstance(fixture_id, bool) or not isinstance(fixture_id, int):
            continue
        for geometry in fixture.get("geometry", []):
            if not isinstance(geometry, Mapping):
                continue
            subfixture_id = geometry.get("subfixture_id")
            if isinstance(subfixture_id, int) and not isinstance(subfixture_id, bool):
                originals[(fixture_id, subfixture_id)] = geometry
    changed = 0
    unchanged = 0
    rotation_changed = 0
    rotation_unchanged = 0
    rotation_unreported = 0
    unmatched = 0
    for placement in position_artifact.get("placements", []):
        if not isinstance(placement, Mapping):
            continue
        key = (placement.get("fixture_id"), placement.get("subfixture_id"))
        original = originals.get(key)
        if original is None:
            unmatched += 1
            continue
        current_xyz = original.get("xyz")
        proposed_xyz = placement.get("xyz")
        if isinstance(current_xyz, Mapping) and isinstance(proposed_xyz, Mapping) and all(
            current_xyz.get(axis) == proposed_xyz.get(axis) for axis in ("x", "y", "z")
        ):
            unchanged += 1
        else:
            changed += 1
        original_rotation = original.get("rotation")
        proposed_rotation = placement.get("rotation")
        if proposed_rotation is None:
            rotation_unreported += 1
        elif isinstance(original_rotation, Mapping) and isinstance(proposed_rotation, Mapping) and all(
            original_rotation.get(axis) == proposed_rotation.get(axis) for axis in ("x", "y", "z")
        ):
            rotation_unchanged += 1
        else:
            rotation_changed += 1
    total = len(position_artifact.get("placements", []))
    return {
        "geometry_delta_from_snapshot": "ZERO" if changed == 0 and unmatched == 0 else "NON_ZERO_OR_UNMATCHED",
        "placements_changed_count": changed,
        "placements_unchanged_count": unchanged,
        "rotations_changed_count": rotation_changed,
        "rotations_unchanged_count": rotation_unchanged,
        "rotations_unreported_count": rotation_unreported,
        "unmatched_placement_count": unmatched,
        "placement_count": total,
        "is_artistic_validation_failure": False,
    }
