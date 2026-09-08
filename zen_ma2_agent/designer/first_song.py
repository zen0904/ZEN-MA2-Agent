"""Deterministic first-song design using only scanned references."""
from __future__ import annotations

from typing import Any

from .schema import SHOW_PLAN_SCHEMA, validate_show_plan


class FirstSongDesignError(ValueError):
    pass


class FirstSongDesigner:
    """Translate manually supplied song sections into typed, command-free cues."""

    def design(self, song_input: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        song = str(song_input.get("song_name") or "").strip()
        sections = song_input.get("sections")
        active_range = song_input.get("active_sequence_range")
        if not song or not isinstance(sections, list) or len(sections) < 5:
            raise FirstSongDesignError("First Song input requires a song_name and at least five sections.")
        if not isinstance(active_range, list) or len(active_range) != 2 or not all(isinstance(value, int) for value in active_range) or active_range[0] < 1 or active_range[0] > active_range[1]:
            raise FirstSongDesignError("First Song input requires an explicit active_sequence_range.")
        groups = [item for item in profile.get("groups", []) if isinstance(item.get("group_id"), int)]
        presets = [item for item in profile.get("presets", []) if item.get("reference")]
        if not groups:
            raise FirstSongDesignError("MISSING_RESOURCE: no scanned Group is available.")
        if not presets:
            raise FirstSongDesignError("MISSING_RESOURCE: no scanned Preset reference is available.")
        group = groups[0]
        # Current production evidence contains Focus 6.1–6.5. Prefer a
        # stable normal/default-style Focus preset but never manufacture one.
        preset = next((item for item in presets if item.get("preset_type") == "FOCUS" and "normal" in str(item.get("name", "")).casefold()), presets[0])
        warnings = []
        if not profile.get("semantic_presets"):
            warnings.append("No exact POS_STAGE_* preset found; position actions were skipped.")
        if not profile.get("effects"):
            warnings.append("No Effect inventory entry found; effect actions were skipped.")
        else:
            warnings.append("Effect call was skipped: no production Effect-call command grammar is verified for this builder.")
        cues = []
        for number, section in enumerate(sections, start=1):
            label = str(section.get("name") or f"SECTION_{number}").strip()
            energy = float(section.get("energy", 0.5))
            if not 0.0 <= energy <= 1.0:
                raise FirstSongDesignError(f"Section {label} energy must be between 0 and 1.")
            level = max(1, min(100, round(15 + energy * 80)))
            fade = 2.0 if energy <= 0.3 else 1.2 if energy <= 0.6 else 0.5
            cues.append({
                "id": f"cue-{number}", "cue_number": number, "label": label, "fade": fade,
                "actions": [
                    {"target": {"type": "group", "ref": group["group_id"]}, "operation": "CALL_PRESET", "preset_ref": preset["reference"], "preset_type": preset.get("preset_type")},
                    {"target": {"type": "group", "ref": group["group_id"]}, "operation": "SET_DIMMER", "level": level},
                ],
            })
        return validate_show_plan({
            "schema": SHOW_PLAN_SCHEMA, "song": song, "target_sequence": None,
            "active_sequence_range": active_range, "cues": cues, "warnings": warnings,
            "designer": {"kind": "DETERMINISTIC_FIRST_SONG", "uses_neutral_geometry": bool(profile.get("geometry_analysis"))},
        })
