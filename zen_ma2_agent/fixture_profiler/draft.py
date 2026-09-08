"""Build draft-only Fixture observations without range inference.

The current Agent has no verified provider for Preset raw values.  This module
therefore accepts only structured observations with declared evidence and keeps
all unobserved boundaries and fine-channel relationships unknown.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


FIXTURE_PROFILE_DRAFT_SCHEMA = "zen.fixture_profile_draft.v0.1"
EVIDENCE = {"VERIFIED_EXISTING_PROFILE", "VERIFIED_PRESET", "VERIFIED_MANUAL", "VERIFIED_HARDWARE_TEST", "INFERRED_HIGH_CONFIDENCE", "INFERRED_LOW_CONFIDENCE", "UNKNOWN"}


class ObservationError(ValueError):
    pass


class FixtureProfiler:
    def draft(self, observations: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(observations, list) or not observations:
            raise ObservationError("At least one verified Fixture observation is required.")
        normalized: list[dict[str, Any]] = []
        for index, raw in enumerate(observations, start=1):
            if not isinstance(raw, dict):
                raise ObservationError(f"Observation {index} must be an object.")
            fixture_id, preset_name, attribute = raw.get("fixture_id"), str(raw.get("preset_name") or "").strip(), str(raw.get("attribute") or "").strip()
            if isinstance(fixture_id, bool) or not isinstance(fixture_id, int) or fixture_id < 1 or not preset_name or not attribute:
                raise ObservationError(f"Observation {index} requires fixture_id, preset_name, and attribute.")
            dmx = raw.get("observed_dmx")
            if dmx is not None and (isinstance(dmx, bool) or not isinstance(dmx, int) or not 0 <= dmx <= 255):
                raise ObservationError(f"Observation {index} observed_dmx must be an 8-bit integer or null.")
            evidence = str(raw.get("evidence") or "VERIFIED_PRESET")
            if evidence not in EVIDENCE:
                raise ObservationError(f"Observation {index} has an unknown evidence value.")
            normalized.append({
                "fixture_id": fixture_id,
                "fixture_type": raw.get("fixture_type") or {"status": "UNKNOWN"},
                "preset_id": raw.get("preset_id"),
                "preset_name": preset_name,
                "attribute": attribute,
                "observed_dmx": dmx,
                "decimal16": raw.get("decimal16") if isinstance(raw.get("decimal16"), int) else None,
                "coarse_fine_relation": raw.get("coarse_fine_relation") or "UNVERIFIED_FINE_MAPPING",
                "evidence": evidence,
                "confidence": raw.get("confidence") or evidence,
                "range": "UNKNOWN",
            })
        by_attribute: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in normalized:
            by_attribute[item["attribute"]].append(item)
        return {
            "schema": FIXTURE_PROFILE_DRAFT_SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "draft_only": True,
            "observations": normalized,
            "channel_set_candidates": [
                {"attribute": attribute, "observed_points": values, "range": "UNKNOWN", "apply_status": "DRAFT_ONLY"}
                for attribute, values in sorted(by_attribute.items())
            ],
            "limits": {
                "automatic_preset_raw_capture": "NOT_IMPLEMENTED",
                "dmx_range_inference": "BLOCKED_BY_EVIDENCE_POLICY",
                "fixture_type_apply": "NOT_IMPLEMENTED",
                "fixture_type_export": "NOT_IMPLEMENTED",
            },
        }
