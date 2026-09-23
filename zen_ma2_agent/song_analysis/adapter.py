"""Adapt normalized song analysis to the proven first-song Designer contract."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .schema import SongAnalysisError, validate_song_analysis


class SongAnalysisAdapter:
    """Keep all audio/script semantics upstream of the command-free Designer."""

    def to_designer_input(self, analysis: dict[str, Any]) -> dict[str, Any]:
        analysis = validate_song_analysis(analysis)
        active_range = analysis["build"].get("active_sequence_range") or [1, 9999]
        sections = []
        for section in analysis["sections"]:
            sections.append({
                "id": section["id"], "name": section["name"], "label": section["label"], "role": section["role"],
                "start": section["start"], "end": section["end"], "energy": section["energy"], "density": section["density"],
                "accent_level": section["accent_level"], "notes": list(section["notes"]), "provenance": deepcopy(section["provenance"]),
            })
        return {
            "song_name": analysis["song"]["title"], "active_sequence_range": list(active_range), "sections": sections,
            "events": deepcopy(analysis["events"]), "performance": deepcopy(analysis["performance"]),
            "stage_roles": deepcopy(analysis["stage_roles"]), "max_cues_per_section": analysis["build"]["max_cues_per_section"],
            "effect_policy": analysis["build"].get("effect_policy", ""),
            "analysis_schema": analysis["schema"],
        }
