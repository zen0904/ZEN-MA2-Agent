"""Translate verified StateStore snapshots into a machine-readable show model.

The scanner deliberately serializes only evidence already held by read-only
providers.  Missing MA2 accessors stay explicit; it never fills a fixture type,
DMX value, position, or Effect parameter from a label or a guess.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..state.store import StateStore


SHOW_PROFILE_SCHEMA = "zen.show_profile.v0.1"


def _snapshot_metadata(state: StateStore, resource: str) -> dict[str, Any]:
    snapshot = state.get(resource)
    if not snapshot:
        return {"status": "UNAVAILABLE", "source": None, "updated_at": None, "stale": False, "error": "No snapshot collected.", "capability": None}
    status = "UNSUPPORTED" if snapshot.error and snapshot.error.startswith("UNSUPPORTED") else "ERROR" if snapshot.error else "STALE" if snapshot.stale else "SUPPORTED"
    return {"status": status, "source": snapshot.source, "updated_at": snapshot.updated_at, "stale": snapshot.stale, "error": snapshot.error, "capability": snapshot.capability}


def _unknown(reason: str) -> dict[str, str]:
    return {"status": "UNAVAILABLE", "reason": reason}


class ShowScanner:
    """Create a portable profile from the current shared read-only cache."""

    def scan(self, state: StateStore) -> dict[str, Any]:
        metadata = {resource: _snapshot_metadata(state, resource) for resource in state.RESOURCES}
        values = lambda resource: list(state.get(resource).values) if state.get(resource) else []
        memberships = {item.get("group_no"): item for item in values("group_membership")}
        fixtures = [
            {
                "fixture_id": item.get("number"),
                "name": item.get("name"),
                "fixture_type": item.get("fixture_type") if item.get("fixture_type") else _unknown("List Fixture did not return a verified fixture-type record."),
                "stage_position": _unknown("No verified read-only MA2 Stage XYZ provider."),
                "rotation": _unknown("No verified read-only MA2 fixture rotation provider."),
                "pan_tilt_capability": _unknown("No verified read-only MA2 fixture attribute/provider."),
                "dmx_mapping": _unknown("No verified Fixture Type or DMX channel provider."),
            }
            for item in values("fixtures")
        ]
        groups = []
        for group in values("groups"):
            membership = memberships.get(group.get("number"))
            groups.append({
                "group_id": group.get("number"),
                "name": group.get("name"),
                # Native Group Export preserves this order.  Never sort it.
                "fixture_ids_in_selection_order": list(membership.get("fixtures") or []) if membership else [],
                "membership": {"status": "SUPPORTED" if membership else metadata["group_membership"]["status"], "source": membership.get("source") if membership else metadata["group_membership"]["source"]},
            })
        presets = [
            {
                "preset_type": item.get("preset_type"),
                "pool_id": item.get("number"),
                "name": item.get("name"),
                "fixture_applicability": _unknown("Preset membership has no verified provider."),
                "stored_attributes": _unknown("Preset contents have no verified provider."),
                "stored_values": _unknown("Raw/decimal/physical Preset values have no verified provider."),
            }
            for item in values("presets")
        ]
        effects = [
            {
                "effect_id": item.get("number"),
                "name": item.get("name"),
                "kind": item.get("kind"),
                "line_count": item.get("line_count"),
                "attributes": list(item.get("attributes") or []),
                "effect_lines": _unknown("List Effect does not expose verified line parameters."),
            }
            for item in values("effects")
        ]
        return {
            "schema": SHOW_PROFILE_SCHEMA,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "resources": metadata,
            "fixtures": fixtures,
            "groups": groups,
            "presets": presets,
            "effects": effects,
            "sequences": values("sequences"),
            "cues": values("cues"),
            "pages": values("pages"),
            "executors": values("executors"),
            "layouts": values("layouts"),
            "layout_cobjects": values("layout_items"),
            "known_limits": {
                "layout_fixture_geometry": "UNSUPPORTED",
                "fixture_type_structure": "UNAVAILABLE",
                "preset_raw_values": "UNAVAILABLE",
                "effect_line_parameters": "UNAVAILABLE",
                "sequence_cue_values": "UNAVAILABLE",
            },
        }

    def write(self, state: StateStore, path: Path) -> dict[str, Any]:
        """Write a local JSON artifact only; no MA2 transport is invoked."""
        profile = self.scan(state)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return profile
