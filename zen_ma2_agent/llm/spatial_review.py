"""Review-state and fact-calibration helpers for live spatial design runs.

These helpers classify provider-authored artifacts and verified snapshot
evidence. They do not create or edit artistic content and do not authorize MA2
writes.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


CALIBRATION_SCHEMA = "zen.sheesh_spatial_fact_calibration.v0.2"
STAGE_VIEW_EVIDENCE_SCHEMA = "zen.operator_stage_view_evidence.v0.1"
SHOW_BOUND_CAPABILITY_SCHEMA = "zen.show_bound_fixture_capability_profiles.v0.1"
ALLOWED_CRITIC_SEVERITIES = frozenset(
    {"BLOCKER", "DESIGN_WEAKNESS", "OPTIONAL_IMPROVEMENT", "NONE"}
)
MAX_SPATIAL_REVISION_CYCLES = 2
PROTECTED_FIXTURE_ID = 9999

# These are software-level MA2 concepts, not sign conventions for a particular
# Show/venue. Values are backed by official grandMA2 3.9 help references stored
# separately in each calibration artifact.
MA2_COORDINATE_CONCEPTS = {
    "MA2_X_AXIS_CONCEPT": "HORIZONTAL_STAGE_COORDINATE",
    "MA2_Y_AXIS_CONCEPT": "TOWARD_AWAY_FROM_AUDIENCE_DIMENSION",
    "MA2_Z_AXIS_CONCEPT": "VERTICAL_STAGE_COORDINATE",
}
MA2_FIXTURE_TRANSFORM_SEMANTICS = {
    "fixture_position_fields": ["Pos X", "Pos Y", "Pos Z"],
    "fixture_position_scope": "POSITION_IN_MA2_3D_ENVIRONMENT",
    "fixture_rotation_fields": ["Rot X", "Rot Y", "Rot Z"],
    "fixture_rotation_scope": "ROTATION_IN_MA2_3D_ENVIRONMENT",
    "stage_setup_axis_modes": ["STAGE_AXIS", "OBJECT_AXIS"],
    "venue_sign_mapping": "NOT_ESTABLISHED_BY_SOFTWARE_CONVENTION",
    "fixture_position_units": "NOT_ESTABLISHED_BY_REVIEWED_FIELD_SPECIFIC_SOURCE",
}
MA2_COORDINATE_SOURCE_URL = "https://help.malighting.com/grandMA2/en/help/key_xyz.html"
MA2_FIXTURE_TRANSFORM_SOURCE_URL = "https://help.malighting.com/grandMA2/en/help/key_patch_position_fixtures.html"

CALIBRATION_FACT_FIELDS = (
    "COORDINATE_FRAME_VERIFIED",
    "CURRENT_SHOW_FINGERPRINT_MATCHES_LIVE_SCAN",
    "GEOMETRY_BEARING_RESOURCES_AVAILABLE",
    "PROTECTED_RESOURCES_IDENTIFIED",
    "MA2_X_AXIS_CONCEPT",
    "MA2_Y_AXIS_CONCEPT",
    "MA2_Z_AXIS_CONCEPT",
    "CURRENT_SHOW_X_SIGN_MAPPING",
    "CURRENT_SHOW_Y_SIGN_MAPPING",
    "CURRENT_SHOW_Z_SIGN_MAPPING",
    "COORDINATE_UNITS_VERIFIED",
    "STAGE_VIEW_CAPTURE_SUPPORTED",
    "STAGE_VIEW_EVIDENCE_INPUT_SUPPORTED",
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
    "PAN_TILT_ORIENTATION_SEMANTICS",
    "OPERATOR_PAN_TILT_CALIBRATION",
)

REVISION_READINESS_CATEGORIES = (
    "CURRENT_SHOW_IDENTITY",
    "GEOMETRY_AND_PROTECTED_RESOURCES",
    "MA2_COORDINATE_CONCEPTS",
    "VENUE_COORDINATE_ORIENTATION",
    "STAGE_AND_PERFORMER_CONTEXT",
    "CURRENT_SHOW_CAPABILITIES",
)

_STAGE_ASSERTION_FIELDS = (
    "operator_asserted_audience_direction",
    "operator_asserted_stage_left_right",
    "operator_asserted_upstage_downstage",
    "performer_zone_description",
    "stage_bounds_description",
    "notes",
    "operator_asserted_current_show_x_sign_mapping",
    "operator_asserted_current_show_y_sign_mapping",
    "operator_asserted_current_show_z_sign_mapping",
)
_IMAGE_SIGNATURES = {
    "image/png": lambda raw: raw.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": lambda raw: raw.startswith(b"\xff\xd8\xff"),
    "image/webp": lambda raw: len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP",
}


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


def validate_operator_pan_tilt_calibration(
    value: object,
    *,
    expected_show_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Validate owner-supplied Pan/Tilt convention without deriving XYZ signs."""
    if not isinstance(value, dict):
        raise ValueError("Operator Pan/Tilt calibration must be an object.")
    if value.get("source_type") != "OPERATOR_SUPPLIED_CALIBRATION":
        raise ValueError("Pan/Tilt calibration must retain operator-supplied provenance.")
    if value.get("status") != "OPERATOR_VERIFIED":
        raise ValueError("Pan/Tilt calibration must be explicitly operator verified.")
    fingerprint = value.get("show_fingerprint")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError("Operator calibration requires a Show fingerprint.")
    if expected_show_fingerprint is not None and fingerprint != expected_show_fingerprint:
        raise ValueError("Operator Pan/Tilt calibration fingerprint does not match this Show.")
    if value.get("gate_id") != "SHEESH_SPATIAL_FACT_CALIBRATION_001":
        raise ValueError("Operator Pan/Tilt calibration must remain bound to the current calibration gate.")
    expected = {
        "TILT_NEGATIVE_DIRECTION": "AUDIENCE",
        "TILT_POSITIVE_DIRECTION": "UPSTAGE_OR_INWARD",
        "PAN_NEGATIVE_DIRECTION": "STAGE_RIGHT_WHEN_FACING_STAGE_FROM_AUDIENCE",
        "PAN_POSITIVE_DIRECTION": "STAGE_LEFT_WHEN_FACING_STAGE_FROM_AUDIENCE",
    }
    if value.get("directions") != expected:
        raise ValueError("Operator Pan/Tilt directions do not match the recorded calibration.")
    if value.get("xyz_sign_mapping_inferred") is not False:
        raise ValueError("Pan/Tilt calibration must explicitly prohibit XYZ sign inference.")
    if value.get("universal_ma2_rule") is not False:
        raise ValueError("Show-bound Pan/Tilt calibration cannot be promoted to a universal MA2 rule.")
    return value


def validate_operator_stage_view_evidence(
    value: object,
    *,
    expected_show_fingerprint: str,
    evidence_root: Path,
) -> dict[str, Any]:
    """Verify an explicit operator-supplied Stage View image and annotations.

    This validates file identity/provenance only. It does not infer physical
    facts from pixels or promote visual observations into verified facts.
    """
    if not isinstance(value, dict) or value.get("schema") != STAGE_VIEW_EVIDENCE_SCHEMA:
        raise ValueError(f"Stage View evidence schema must be {STAGE_VIEW_EVIDENCE_SCHEMA}.")
    if value.get("source_type") != "OPERATOR_SUPPLIED_STAGE_VIEW_IMAGE":
        raise ValueError("Stage View evidence must be explicitly operator supplied.")
    if value.get("show_fingerprint") != expected_show_fingerprint:
        raise ValueError("Stage View evidence Show fingerprint does not match the current Show.")
    captured_at = value.get("captured_at")
    try:
        parsed_time = datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Stage View evidence captured_at must be an ISO-8601 timestamp.") from exc
    if parsed_time.tzinfo is None:
        raise ValueError("Stage View evidence captured_at must include a timezone.")

    image = value.get("image")
    if not isinstance(image, Mapping):
        raise ValueError("Stage View evidence requires an image file reference.")
    relative_path = image.get("relative_path")
    expected_hash = image.get("sha256")
    media_type = image.get("media_type")
    if (
        not isinstance(relative_path, str)
        or not relative_path.strip()
        or Path(relative_path).is_absolute()
        or ".." in Path(relative_path).parts
    ):
        raise ValueError("Stage View image path must be relative to the evidence root.")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("Stage View image requires a SHA-256 digest.")
    if media_type not in _IMAGE_SIGNATURES:
        raise ValueError("Stage View image media_type must be PNG, JPEG, or WebP.")
    root = Path(evidence_root).resolve(strict=True)
    image_path = (root / relative_path).resolve(strict=True)
    try:
        image_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Stage View image path escapes the evidence root.") from exc
    raw_image = image_path.read_bytes()
    if hashlib.sha256(raw_image).hexdigest() != expected_hash:
        raise ValueError("Stage View image hash does not match the supplied artifact.")
    if not _IMAGE_SIGNATURES[media_type](raw_image):
        raise ValueError("Stage View image bytes do not match the declared media_type.")

    assertions = value.get("operator_assertions")
    if not isinstance(assertions, Mapping):
        raise ValueError("Stage View operator annotations require separate provenance metadata.")
    for field in _STAGE_ASSERTION_FIELDS:
        annotation = value.get(field)
        if annotation is None:
            continue
        if not isinstance(annotation, Mapping) or not isinstance(annotation.get("value"), str) or not annotation["value"].strip():
            raise ValueError(f"Stage View annotation {field} must contain a non-empty value.")
        provenance = assertions.get(field)
        if not isinstance(provenance, Mapping):
            raise ValueError(f"Stage View annotation {field} is missing provenance.")
        if (
            provenance.get("source_type") != "OPERATOR_SUPPLIED_ANNOTATION"
            or provenance.get("asserted_by") != "OPERATOR"
            or provenance.get("show_fingerprint") != expected_show_fingerprint
            or provenance.get("value") != annotation["value"]
        ):
            raise ValueError(f"Stage View annotation {field} provenance is invalid.")

    observations = value.get("visual_observations", [])
    if not isinstance(observations, list):
        raise ValueError("visual_observations must be an array.")
    for observation in observations:
        if not isinstance(observation, Mapping) or not isinstance(observation.get("observation"), str):
            raise ValueError("Each visual observation must contain observation text.")
        if observation.get("evidence_class") != "VISUAL_OBSERVATION":
            raise ValueError("Image-derived notes must remain tagged VISUAL_OBSERVATION.")
        if observation.get("verified_physical_fact") is not False:
            raise ValueError("Visual observations cannot silently become verified physical facts.")
        if observation.get("source_image_sha256") != expected_hash:
            raise ValueError("Visual observation must reference the supplied Stage View image hash.")

    result = deepcopy(value)
    result["image_integrity_status"] = "VERIFIED_HASH_AND_MEDIA_SIGNATURE"
    result["operator_annotations_status"] = "PROVENANCE_SEPARATE_FROM_IMAGE"
    return result


def bind_show_bound_capability_profiles(
    snapshot: Mapping[str, Any],
    export_batch: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind exact exported MA2 FixtureType attributes to real fixture IDs.

    Fixture names are deliberately ignored. The Show fingerprint, current
    exported type label, and native profile status must all match exactly.
    Protected Fixture 9999 is never returned as an artistic capability profile.
    """
    show_fingerprint = snapshot.get("show_fingerprint")
    identity = export_batch.get("current_show_identity")
    if (
        export_batch.get("show_identity_match") != "MATCH"
        or not isinstance(identity, Mapping)
        or identity.get("value") != show_fingerprint
        or export_batch.get("binding_status") != "SHOW_BOUND_VERIFIED"
    ):
        raise ValueError("FixtureType export batch is not bound to this exact Show fingerprint.")
    fixtures = snapshot.get("fixture_inventory")
    profiles = export_batch.get("fixture_type_profiles")
    if not isinstance(fixtures, list) or not isinstance(profiles, list):
        raise ValueError("Capability binding requires current fixture inventory and exported profiles.")
    by_exact_label: dict[str, Mapping[str, Any]] = {}
    for profile in profiles:
        if not isinstance(profile, Mapping) or profile.get("status") != "SHOW_BOUND_VERIFIED":
            continue
        identity_data = profile.get("fixture_type")
        label = identity_data.get("list_label") if isinstance(identity_data, Mapping) else None
        if not isinstance(label, str) or not label or label in by_exact_label:
            raise ValueError("Show-bound FixtureType profiles require unique exact List Fixture labels.")
        channels = profile.get("channels")
        if not isinstance(channels, list) or not channels:
            raise ValueError("Show-bound FixtureType profile has no observed ChannelType attributes.")
        if not isinstance(profile.get("source"), str) or not profile["source"].strip():
            raise ValueError("Show-bound FixtureType profile requires source provenance.")
        by_exact_label[label] = profile

    result_profiles: list[dict[str, Any]] = []
    protected_ids: list[int] = []
    for fixture in fixtures:
        if not isinstance(fixture, Mapping):
            raise ValueError("Fixture inventory contains a malformed item.")
        fixture_id = fixture.get("fixture_id")
        if isinstance(fixture_id, bool) or not isinstance(fixture_id, int) or fixture_id < 1:
            raise ValueError("Fixture inventory contains an invalid Fixture ID.")
        if fixture_id == PROTECTED_FIXTURE_ID or fixture.get("availability") == "PROTECTED_UNAVAILABLE":
            protected_ids.append(fixture_id)
            continue
        exact_label = fixture.get("fixture_type_identity")
        profile = by_exact_label.get(exact_label) if isinstance(exact_label, str) else None
        if profile is None:
            raise ValueError(f"No exact show-bound FixtureType profile for Fixture {fixture_id}.")
        type_identity = profile["fixture_type"]
        channel_attributes = sorted({
            str(channel.get("attribute"))
            for channel in profile["channels"]
            if isinstance(channel, Mapping) and isinstance(channel.get("attribute"), str) and channel["attribute"]
        })
        if not channel_attributes:
            raise ValueError(f"Show-bound FixtureType profile for Fixture {fixture_id} has no exact attributes.")
        result_profiles.append({
            "show_fingerprint": show_fingerprint,
            "fixture_id": fixture_id,
            "fixture_type_identity": {
                "fixture_type_id": type_identity.get("fixture_type_id"),
                "list_label": exact_label,
            },
            "source": profile.get("source"),
            "observed_attributes": channel_attributes,
            "capabilities": deepcopy(profile.get("capabilities") or {}),
            "confidence": "SHOW_BOUND_VERIFIED",
            "artistic_role_inference": "NONE",
        })
    return {
        "schema": SHOW_BOUND_CAPABILITY_SCHEMA,
        "show_fingerprint": show_fingerprint,
        "profiles": result_profiles,
        "protected_fixture_ids": sorted(set(protected_ids)),
        "capability_profile_count": len(result_profiles),
        "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
    }


def validate_spatial_fact_calibration(
    value: object,
    *,
    expected_show_fingerprint: str | None = None,
    expected_snapshot_source_hash: str | None = None,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    """Validate sourced calibration while allowing unsupported facts UNKNOWN."""
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

    semantics = value.get("software_coordinate_semantics")
    if (
        not isinstance(semantics, Mapping)
        or semantics.get("values") != MA2_COORDINATE_CONCEPTS
        or semantics.get("fixture_transform") != MA2_FIXTURE_TRANSFORM_SEMANTICS
    ):
        raise ValueError("MA2 software coordinate concepts must be explicitly sourced and kept distinct from venue mapping.")
    semantic_sources = semantics.get("sources")
    if not isinstance(semantic_sources, list) or not semantic_sources:
        raise ValueError("MA2 software coordinate concepts require source provenance.")
    if any(not isinstance(item, Mapping) or not item.get("url") or not item.get("scope") for item in semantic_sources):
        raise ValueError("MA2 coordinate sources require direct URLs and explicit claim scope.")
    source_urls = {item.get("url") for item in semantic_sources if isinstance(item, Mapping)}
    if not {MA2_COORDINATE_SOURCE_URL, MA2_FIXTURE_TRANSFORM_SOURCE_URL}.issubset(source_urls):
        raise ValueError("MA2 coordinate and fixture transform semantics require their field-relevant official sources.")
    for key, expected in MA2_COORDINATE_CONCEPTS.items():
        if facts.get(key) != expected:
            raise ValueError(f"{key} must remain the separately sourced MA2 software concept.")
    operator_calibration = value.get("operator_supplied_pan_tilt_calibration")
    if operator_calibration is not None:
        validate_operator_pan_tilt_calibration(
            operator_calibration,
            expected_show_fingerprint=fingerprint,
        )
    pan_tilt_status = "OPERATOR_VERIFIED" if operator_calibration is not None else "UNKNOWN"
    if facts.get("PAN_TILT_ORIENTATION_SEMANTICS") != pan_tilt_status:
        raise ValueError("Pan/Tilt orientation semantics must retain their operator provenance status.")
    operator_status = "VERIFIED_BY_OPERATOR" if operator_calibration is not None else "UNKNOWN"
    if facts.get("OPERATOR_PAN_TILT_CALIBRATION") != operator_status:
        raise ValueError("Operator Pan/Tilt calibration status must match its separately scoped evidence.")

    live_observation = value.get("current_live_machine_observation")
    if isinstance(live_observation, Mapping):
        observed_identity = live_observation.get("show_fingerprint")
        if observed_identity != fingerprint and facts.get("CURRENT_SHOW_FINGERPRINT_MATCHES_LIVE_SCAN") != "NO":
            raise ValueError("A different live Show identity cannot be represented as matching the source calibration Show.")
        if observed_identity != fingerprint and facts.get("CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE") != "NO":
            raise ValueError("Profiles from a different live Show cannot satisfy this calibration fingerprint.")

    venue_mapping = value.get("current_show_venue_mapping_evidence")
    mapping_fields = (
        "CURRENT_SHOW_X_SIGN_MAPPING",
        "CURRENT_SHOW_Y_SIGN_MAPPING",
        "CURRENT_SHOW_Z_SIGN_MAPPING",
    )
    known_mappings = {field: facts[field] for field in mapping_fields if facts[field] != "UNKNOWN"}
    if known_mappings:
        if not isinstance(venue_mapping, Mapping):
            raise ValueError("Known current-Show coordinate mappings require separate venue evidence.")
        if (
            venue_mapping.get("show_fingerprint") != fingerprint
            or venue_mapping.get("source_type") != "OPERATOR_SUPPLIED_CURRENT_SHOW_COORDINATE_MAPPING"
            or venue_mapping.get("independent_of_pan_tilt") is not True
            or venue_mapping.get("independent_of_software_convention") is not True
            or not isinstance(venue_mapping.get("source_reference"), str)
            or not venue_mapping["source_reference"].strip()
        ):
            raise ValueError("Current-Show coordinate mapping evidence must be independently sourced and Show-bound.")
        evidence_mappings = venue_mapping.get("mappings")
        if not isinstance(evidence_mappings, Mapping) or any(
            evidence_mappings.get(field) != value for field, value in known_mappings.items()
        ):
            raise ValueError("Current-Show coordinate mapping values must match their separate evidence record.")

    if value.get("CODEX_ARTISTIC_INTERVENTION") != "NONE":
        raise ValueError("Spatial fact calibration must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    return value


def _is_known(value: object) -> bool:
    if not isinstance(value, str):
        return False
    upper = value.upper()
    return (
        upper in {"YES", "VERIFIED", "KNOWN", "OPERATOR_VERIFIED"}
        or upper.startswith("OPERATOR_VERIFIED_")
        or upper.startswith("KNOWN_")
    )


def spatial_revision_readiness(calibration: Mapping[str, Any]) -> dict[str, Any]:
    """Require evidence needed for meaningful placement and supported resources.

    This intentionally does not require obstruction/truss data, fixture
    orientation writeability, a Stage View image when equivalent explicit
    evidence exists, or a universal perfection state for every calibration
    field. Unknown scale may be bounded by explicit Stage dimensions in the
    same MA2 coordinate frame; unknown venue signs, stage area, or capabilities
    remain blocking.
    """
    facts = calibration.get("facts", {})
    semantics = calibration.get("software_coordinate_semantics", {})
    geometry = calibration.get("geometry_evidence", {})
    live = calibration.get("current_live_machine_observation", {})
    profiles = calibration.get("show_bound_capability_profiles", {})
    profile_items = profiles.get("profiles", []) if isinstance(profiles, Mapping) else []
    fingerprint = calibration.get("show_fingerprint")
    live_fingerprint = live.get("show_fingerprint") if isinstance(live, Mapping) else fingerprint

    checks = {
        "CURRENT_SHOW_IDENTITY": (
            live_fingerprint == fingerprint
            and facts.get("CURRENT_SHOW_FINGERPRINT_MATCHES_LIVE_SCAN") in {"YES", "VERIFIED", "KNOWN"}
        ),
        "GEOMETRY_AND_PROTECTED_RESOURCES": (
            isinstance(geometry, Mapping)
            and isinstance(geometry.get("geometry_bearing_resource_count"), int)
            and geometry["geometry_bearing_resource_count"] > 0
            and PROTECTED_FIXTURE_ID in geometry.get("protected_fixture_ids", [])
            and facts.get("GEOMETRY_BEARING_RESOURCES_AVAILABLE") in {"YES", "VERIFIED", "KNOWN"}
            and facts.get("PROTECTED_RESOURCES_IDENTIFIED") in {"YES", "VERIFIED", "KNOWN"}
        ),
        "MA2_COORDINATE_CONCEPTS": (
            isinstance(semantics, Mapping) and semantics.get("values") == MA2_COORDINATE_CONCEPTS
        ),
        "VENUE_COORDINATE_ORIENTATION": (
            all(_is_known(facts.get(field)) for field in (
                "CURRENT_SHOW_X_SIGN_MAPPING", "CURRENT_SHOW_Y_SIGN_MAPPING", "CURRENT_SHOW_Z_SIGN_MAPPING"
            ))
            and _is_known(facts.get("AUDIENCE_DIRECTION_KNOWN"))
            and _is_known(facts.get("STAGE_LEFT_RIGHT_KNOWN"))
            and _is_known(facts.get("UPSTAGE_DOWNSTAGE_KNOWN"))
        ),
        "STAGE_AND_PERFORMER_CONTEXT": (
            _is_known(facts.get("STAGE_BOUNDS_KNOWN"))
            and _is_known(facts.get("PERFORMER_ZONE_KNOWN"))
        ),
        "CURRENT_SHOW_CAPABILITIES": (
            facts.get("CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE") in {
                "YES", "VERIFIED", "KNOWN", "SHOW_BOUND_VERIFIED"
            }
            and isinstance(profile_items, list)
            and bool(profile_items)
            and all(
                isinstance(profile, Mapping)
                and profile.get("show_fingerprint") == fingerprint
                and profile.get("confidence") == "SHOW_BOUND_VERIFIED"
                and bool(profile.get("observed_attributes"))
                for profile in profile_items
            )
        ),
    }
    blockers = [category for category in REVISION_READINESS_CATEGORIES if not checks[category]]
    return {
        "ready": not blockers,
        "status": "READY" if not blockers else "BLOCKED_MISSING_EVIDENCE",
        "blocking_categories": blockers,
        "blocking_facts": blockers,
        "checks": checks,
        "non_blocking_limitations": [
            field for field in (
                "COORDINATE_UNITS_VERIFIED",
                "OBSTRUCTION_DATA_AVAILABLE",
                "TRUSS_OR_SUPPORT_GEOMETRY_AVAILABLE",
                "FIXTURE_ORIENTATION_WRITABLE",
                "STAGE_VIEW_IMAGE_AVAILABLE",
            ) if not _is_known(facts.get(field))
        ],
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
