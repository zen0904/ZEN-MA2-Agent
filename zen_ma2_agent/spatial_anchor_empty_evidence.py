"""Current-Show native emptiness evidence for reserved Position Preset slots.

The verified MA2 3.9 method uses the Preset keyword's documented Selfix
behavior with an empty programmer, stores that resulting selection into one
isolated scratch Group, and verifies the Group through native Group Export.
An empty exported Group proves that the exact Preset selected no stored
fixtures.  Evidence is fingerprint- and identity-bound and becomes stale when
current Show identity changes.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


SCHEMA = "zen.spatial_anchor_empty_evidence.v0.1"
STATUS = "NATIVE_EMPTY_VERIFIED"
SOURCE = "PRESET_SELFIX_TO_ISOLATED_GROUP_NATIVE_EXPORT"
_METHOD = "KNOWN_NONEMPTY_AND_KNOWN_EMPTY_AB_CONTROL_VERIFIED"
_POSITION_REF = re.compile(r"2\.[1-9]\d*\Z")


class SpatialAnchorEmptyEvidenceError(ValueError):
    """Preset emptiness evidence cannot be promoted safely."""


def _inventory(profile: Mapping[str, Any]) -> dict[str, list[Mapping[str, Any]]]:
    rows = profile.get("presets")
    if not isinstance(rows, list):
        raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_PRESET_INVENTORY_UNAVAILABLE")
    result: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ref = row.get("reference")
        if isinstance(ref, str):
            result.setdefault(ref, []).append(row)
    return result


def empty_evidence_matches_profile(profile: Mapping[str, Any], evidence: Mapping[str, Any]) -> bool:
    """Require current Show identity plus exact Preset reference/type/label."""
    try:
        if (
            not isinstance(evidence, Mapping)
            or evidence.get("schema") != SCHEMA
            or evidence.get("status") != STATUS
            or evidence.get("source") != SOURCE
            or evidence.get("method_validation") != _METHOD
            or evidence.get("show_identity") != profile.get("show_identity")
        ):
            return False
        slots = evidence.get("slots")
        if not isinstance(slots, list) or not slots:
            return False
        inventory = _inventory(profile)
        seen: set[str] = set()
        for slot in slots:
            if not isinstance(slot, Mapping):
                return False
            ref = slot.get("reference")
            label = slot.get("label")
            if (
                not isinstance(ref, str)
                or not _POSITION_REF.fullmatch(ref)
                or ref in seen
                or slot.get("preset_type") != "POSITION"
                or slot.get("native_content_status") != "EMPTY"
                or slot.get("selected_fixture_refs") != []
                or slot.get("evidence") != SOURCE
            ):
                return False
            candidates = inventory.get(ref, [])
            if len(candidates) != 1:
                return False
            preset = candidates[0]
            if str(preset.get("preset_type") or "").upper() != "POSITION" or preset.get("name") != label:
                return False
            seen.add(ref)
        return True
    except (SpatialAnchorEmptyEvidenceError, TypeError, ValueError):
        return False


def verified_empty_refs(profile: Mapping[str, Any], evidence: Mapping[str, Any] | None) -> set[str]:
    if not isinstance(evidence, Mapping) or not empty_evidence_matches_profile(profile, evidence):
        return set()
    return {str(slot["reference"]) for slot in evidence["slots"]}


class SpatialAnchorEmptyEvidenceStore:
    """Durable current-Show evidence; fingerprint drift invalidates it."""

    def __init__(self, root: Path):
        self.path = Path(root) / "data" / "ZEN_SPATIAL_ANCHOR_EMPTY_EVIDENCE.json"

    def load_verified(self, profile: Mapping[str, Any]) -> dict[str, Any] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        return value if empty_evidence_matches_profile(profile, value) else None

    def record_verified(
        self,
        profile: Mapping[str, Any],
        slots: Sequence[Mapping[str, Any]],
        *,
        scratch_group: int,
        verified_at: str,
        nonempty_control: Mapping[str, Any],
        empty_control: Mapping[str, Any],
    ) -> dict[str, Any]:
        if isinstance(scratch_group, bool) or not isinstance(scratch_group, int) or scratch_group < 1:
            raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_SCRATCH_GROUP_INVALID")
        if not isinstance(verified_at, str) or not verified_at:
            raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_TIMESTAMP_INVALID")
        if not isinstance(profile.get("show_identity"), Mapping):
            raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_SHOW_IDENTITY_UNAVAILABLE")
        inventory = _inventory(profile)
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in slots:
            if not isinstance(item, Mapping):
                raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_SLOT_INVALID")
            ref, label = item.get("reference"), item.get("label")
            if not isinstance(ref, str) or not _POSITION_REF.fullmatch(ref) or ref in seen:
                raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_PRESET_REF_INVALID")
            candidates = inventory.get(ref, [])
            if len(candidates) != 1 or candidates[0].get("name") != label or str(candidates[0].get("preset_type") or "").upper() != "POSITION":
                raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_PRESET_IDENTITY_DRIFT")
            selected = item.get("selected_fixture_refs")
            if item.get("native_content_status") != "EMPTY" or selected != []:
                raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_SLOT_NOT_EMPTY")
            normalized.append({
                "reference": ref,
                "label": label,
                "preset_type": "POSITION",
                "native_content_status": "EMPTY",
                "selected_fixture_refs": [],
                "evidence": SOURCE,
            })
            seen.add(ref)
        if not normalized:
            raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_SLOTS_REQUIRED")
        nonempty_refs = nonempty_control.get("selected_fixture_refs") if isinstance(nonempty_control, Mapping) else None
        empty_refs = empty_control.get("selected_fixture_refs") if isinstance(empty_control, Mapping) else None
        if not isinstance(nonempty_refs, list) or not nonempty_refs or empty_refs != []:
            raise SpatialAnchorEmptyEvidenceError("EMPTY_EVIDENCE_AB_CONTROL_INVALID")
        value = {
            "schema": SCHEMA,
            "status": STATUS,
            "source": SOURCE,
            "method_validation": _METHOD,
            "verified_at": verified_at,
            "show_identity": deepcopy(dict(profile["show_identity"])),
            "scratch_group": scratch_group,
            "ab_controls": {
                "known_nonempty": deepcopy(dict(nonempty_control)),
                "known_empty": deepcopy(dict(empty_control)),
            },
            "slots": normalized,
            "safety_boundary": {
                "selection_probe_only_modified_isolated_scratch_group": True,
                "target_position_presets_were_not_modified": True,
                "fingerprint_drift_invalidates_evidence": True,
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return value
