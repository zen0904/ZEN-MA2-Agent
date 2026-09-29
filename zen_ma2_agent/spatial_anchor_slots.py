"""Reserved, pre-named Position Preset slots for Spatial System vNext.

This module is deliberately identity-only.  A named Position Preset can be
reserved as a future semantic anchor without claiming that its native content
is empty.  Hydration stays fail-closed until the exact target slot has separate
native emptiness evidence.  The store/merge grammar is a distinct capability.
"""
from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping, Sequence

from .spatial_semantics import normalize_semantic_position_target
from .spatial_anchor_empty_evidence import verified_empty_refs
from .spatial_anchor_hydration import spatial_anchor_hydration_capability_is_verified


SPATIAL_ANCHOR_SLOT_SCHEMA = "zen.spatial_anchor_slot.v0.1"
SPATIAL_ANCHOR_CATALOG_SCHEMA = "zen.spatial_anchor_slot_catalog.v0.1"
IDENTITY_STATUS = "IDENTITY_VERIFIED_CONTENT_UNVERIFIED"
HYDRATION_STATUS = "BLOCKED_EMPTY_CONTENT_UNVERIFIED"
_POSITION_REF = re.compile(r"2\.[1-9]\d*\Z")


class SpatialAnchorSlotError(ValueError):
    """A pre-named Position Preset cannot be safely reserved as a Space anchor."""


def _preset_reference(value: object) -> str:
    if not isinstance(value, str):
        raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_REF_INVALID")
    reference = value.strip()
    if not _POSITION_REF.fullmatch(reference):
        raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_REF_INVALID")
    return reference


def _show_identity(profile: Mapping[str, Any]) -> Mapping[str, Any]:
    identity = profile.get("show_identity")
    if not isinstance(identity, Mapping):
        raise SpatialAnchorSlotError("SPATIAL_ANCHOR_SHOW_IDENTITY_UNAVAILABLE")
    return identity


def _position_inventory(profile: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    rows = profile.get("presets")
    if not isinstance(rows, list):
        raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_INVENTORY_UNAVAILABLE")
    result: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        reference = row.get("reference")
        if isinstance(reference, str):
            result.setdefault(reference.strip(), []).append(row)
    return result


def reserve_spatial_anchor_slots(
    profile: Mapping[str, Any],
    requests: Sequence[Mapping[str, Any]],
    *,
    empty_evidence: Mapping[str, Any] | None = None,
    hydration_capability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reserve exact existing Position Presets for future semantic hydration.

    Each request must name the exact semantic target, Preset reference, and
    expected existing label.  No fuzzy matching, label inference, MA command,
    emptiness claim, or Position value is produced here.
    """
    if not isinstance(requests, Sequence) or isinstance(requests, (str, bytes)) or not requests:
        raise SpatialAnchorSlotError("SPATIAL_ANCHOR_REQUESTS_REQUIRED")

    inventory = _position_inventory(profile)
    empty_refs = verified_empty_refs(profile, empty_evidence)
    grammar_verified = spatial_anchor_hydration_capability_is_verified(hydration_capability)
    seen_targets: set[str] = set()
    seen_refs: set[str] = set()
    slots: list[dict[str, Any]] = []

    for request in requests:
        if not isinstance(request, Mapping):
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_REQUEST_INVALID")
        target = normalize_semantic_position_target(request.get("semantic_target"))
        reference = _preset_reference(request.get("preset_ref"))
        expected_label = request.get("expected_label")
        if not isinstance(expected_label, str) or not expected_label.strip():
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_EXPECTED_LABEL_INVALID")
        expected_label = expected_label.strip()
        if target in seen_targets:
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_TARGET_DUPLICATE")
        if reference in seen_refs:
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_DUPLICATE")

        candidates = inventory.get(reference, [])
        if len(candidates) != 1:
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_IDENTITY_AMBIGUOUS")
        preset = candidates[0]
        if str(preset.get("preset_type") or "").upper() != "POSITION":
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_NOT_POSITION")
        if preset.get("name") != expected_label:
            raise SpatialAnchorSlotError("SPATIAL_ANCHOR_PRESET_LABEL_DRIFT")

        empty_verified = reference in empty_refs
        prerequisites_verified = empty_verified and grammar_verified
        slots.append({
            "schema": SPATIAL_ANCHOR_SLOT_SCHEMA,
            "semantic_target": target,
            "target_kind": "POINT",
            "preset_ref": reference,
            "preset_label": expected_label,
            "identity_status": IDENTITY_STATUS,
            "native_content_status": "EMPTY_VERIFIED" if empty_verified else "UNVERIFIED",
            "hydration_grammar_status": "REAL_MACHINE_CONTENT_VERIFIED" if grammar_verified else "UNVERIFIED",
            "hydration_preconditions_verified": prerequisites_verified,
            "hydration_status": "READY_FOR_PREVIEW" if prerequisites_verified else HYDRATION_STATUS,
            "hydration_allowed": False,
            "source": "EXACT_EXISTING_POSITION_PRESET_IDENTITY",
        })
        seen_targets.add(target)
        seen_refs.add(reference)

    slots.sort(key=lambda item: item["semantic_target"])
    return {
        "schema": SPATIAL_ANCHOR_CATALOG_SCHEMA,
        "status": IDENTITY_STATUS,
        "show_identity": deepcopy(dict(_show_identity(profile))),
        "slots": slots,
        "constraints": [
            *([] if empty_refs else ["PRESET_CONTENT_EMPTY_NOT_PROVEN"]),
            *([] if grammar_verified else ["VERIFIED_HYDRATION_GRAMMAR_CAPABILITY_REQUIRED"]),
            "PREVIEW_AND_EXPLICIT_APPROVAL_REQUIRED_FOR_WRITE",
        ],
        "ma2_writes": 0,
    }


def spatial_anchor_catalog_matches_profile(
    profile: Mapping[str, Any],
    catalog: Mapping[str, Any],
    *,
    empty_evidence: Mapping[str, Any] | None = None,
    hydration_capability: Mapping[str, Any] | None = None,
) -> bool:
    """Require current Show and exact Position identity/labels to still match."""
    try:
        if (
            not isinstance(catalog, Mapping)
            or catalog.get("schema") != SPATIAL_ANCHOR_CATALOG_SCHEMA
            or catalog.get("status") != IDENTITY_STATUS
            or catalog.get("show_identity") != profile.get("show_identity")
            or catalog.get("ma2_writes") != 0
        ):
            return False
        slots = catalog.get("slots")
        if not isinstance(slots, list) or not slots:
            return False
        requests = [
            {
                "semantic_target": slot.get("semantic_target"),
                "preset_ref": slot.get("preset_ref"),
                "expected_label": slot.get("preset_label"),
            }
            for slot in slots
            if isinstance(slot, Mapping)
        ]
        rebuilt = reserve_spatial_anchor_slots(
            profile, requests, empty_evidence=empty_evidence,
            hydration_capability=hydration_capability,
        )
        return rebuilt.get("slots") == slots
    except (SpatialAnchorSlotError, TypeError, ValueError):
        return False
