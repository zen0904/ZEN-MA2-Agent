"""Verified grammar capability for hydrating an existing empty Position Preset.

The grammar capability is deliberately separate from per-slot emptiness proof.
A verified grammar does not authorize ZEN to overwrite an arbitrary existing
Preset.  The exact target slot must still be a current-Show POSITION Preset
whose native content has separately been proven empty before first hydration.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping


CAPABILITY_SCHEMA = "zen.spatial_anchor_hydration_capability.v0.1"
GRAMMAR_ID = "STORE_PRESET_MERGE_SELECTIVE"
MA2_VERSION_FAMILY = "grandMA2_3.9"
STATUS = "REAL_MACHINE_CONTENT_VERIFIED"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_POSITION_REF = re.compile(r"2\.[1-9]\d*\Z")
_FIXTURE_REF = re.compile(r"[1-9]\d*(?:\.[1-9]\d*)?\Z")


class SpatialAnchorHydrationError(ValueError):
    """Hydration grammar evidence is missing, malformed, or over-claimed."""


def spatial_anchor_hydration_capability_is_verified(value: object) -> bool:
    """Single source of truth for the existing-Preset hydration grammar."""
    if not isinstance(value, Mapping):
        return False
    verification = value.get("verification")
    evidence = value.get("evidence")
    return bool(
        value.get("schema") == CAPABILITY_SCHEMA
        and value.get("status") == STATUS
        and value.get("grammar") == GRAMMAR_ID
        and value.get("ma2_version_family") == MA2_VERSION_FAMILY
        and isinstance(verification, Mapping)
        and verification.get("existing_empty_preset_identity") == "VERIFIED"
        and verification.get("merge_selective_application") == STATUS
        and verification.get("cue_content_readback") == "VERIFIED"
        and isinstance(evidence, Mapping)
        and isinstance(evidence.get("sequence_export_sha256"), str)
        and bool(_SHA256.fullmatch(evidence["sequence_export_sha256"]))
    )


class SpatialAnchorHydrationCapability:
    """Persist only content-verified real-machine hydration grammar evidence."""

    def __init__(self, root: Path):
        self.path = Path(root) / "data" / "ZEN_SPATIAL_ANCHOR_HYDRATION_CAPABILITY.json"

    def load_verified(self) -> dict[str, Any] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        return value if spatial_anchor_hydration_capability_is_verified(value) else None

    def record_content_verified(
        self,
        *,
        preset_ref: str,
        preset_label: str,
        group_id: int,
        group_name: str,
        group_refs: Iterable[str],
        matched_channel_refs: Iterable[str],
        sequence: int,
        cue: int,
        sequence_export_sha256: str,
    ) -> dict[str, Any]:
        """Record capability only after native Sequence content proves the link."""
        if not isinstance(preset_ref, str) or not _POSITION_REF.fullmatch(preset_ref):
            raise SpatialAnchorHydrationError("HYDRATION_PRESET_REF_INVALID")
        if not isinstance(preset_label, str) or not preset_label.strip():
            raise SpatialAnchorHydrationError("HYDRATION_PRESET_LABEL_INVALID")
        if isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1:
            raise SpatialAnchorHydrationError("HYDRATION_GROUP_ID_INVALID")
        if not isinstance(group_name, str) or not group_name.strip():
            raise SpatialAnchorHydrationError("HYDRATION_GROUP_NAME_INVALID")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise SpatialAnchorHydrationError("HYDRATION_SEQUENCE_INVALID")
        if isinstance(cue, bool) or not isinstance(cue, int) or cue < 1:
            raise SpatialAnchorHydrationError("HYDRATION_CUE_INVALID")
        if not isinstance(sequence_export_sha256, str) or not _SHA256.fullmatch(sequence_export_sha256):
            raise SpatialAnchorHydrationError("HYDRATION_SEQUENCE_EXPORT_SHA_INVALID")

        groups = tuple(str(ref).strip() for ref in group_refs)
        matched = tuple(str(ref).strip() for ref in matched_channel_refs)
        if not groups or not matched or any(not _FIXTURE_REF.fullmatch(ref) for ref in (*groups, *matched)):
            raise SpatialAnchorHydrationError("HYDRATION_FIXTURE_REFS_INVALID")

        value = {
            "schema": CAPABILITY_SCHEMA,
            "status": STATUS,
            "grammar": GRAMMAR_ID,
            "ma2_version_family": MA2_VERSION_FAMILY,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "evidence": {
                "preset_ref": preset_ref,
                "preset_label": preset_label,
                "target_group": group_id,
                "target_group_name": group_name,
                "group_refs": list(groups),
                "matched_channel_refs": sorted(set(matched)),
                "sequence": sequence,
                "cue": cue,
                "sequence_export_sha256": sequence_export_sha256,
            },
            "verification": {
                "existing_empty_preset_identity": "VERIFIED",
                "merge_selective_application": STATUS,
                "native_position_attributes": ["PAN", "TILT"],
                "preset_reference_suffix_match": "VERIFIED",
                "single_instance_parent_row_canonicalization": "VERIFIED",
                "cue_content_readback": "VERIFIED",
            },
            "safety_boundary": {
                "slot_emptiness_is_per_target_evidence": True,
                "capability_does_not_authorize_nonempty_preset_overwrite": True,
                "preview_and_explicit_approval_still_required": True,
            },
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return value