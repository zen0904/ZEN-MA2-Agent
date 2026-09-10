"""Deterministic first-song design using only scanned references."""
from __future__ import annotations

from typing import Any

from .schema import SHOW_PLAN_SCHEMA, validate_show_plan


class FirstSongDesignError(ValueError):
    pass


class FirstSongDesigner:
    """Translate structured song sections into typed, command-free cues.

    This deliberately chooses *lighting* defaults only when an analysis leaves
    energy unknown.  It never writes that default back as measured song data.
    """

    _ROLE_ENERGY = {
        "INTRO": 0.25, "VERSE": 0.42, "PRE_CHORUS": 0.62,
        "CHORUS": 0.88, "POST_CHORUS": 0.78, "DROP": 0.92,
        "BREAK": 0.22, "BRIDGE": 0.55, "SOLO": 0.70,
        "INSTRUMENTAL": 0.50, "BUILD": 0.72, "OUTRO": 0.30,
        "UNKNOWN": 0.50,
    }

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
        effect_policy = str(song_input.get("effect_policy") or "").upper()
        if effect_policy not in {"", "DIMMER_CHASE_V1", "DIMMER_CHASE_REUSE_SLOW_V1"}:
            raise FirstSongDesignError("Only explicit verified DIMMER_CHASE effect policies are supported.")
        if not profile.get("effects"):
            warnings.append("No Effect inventory entry found; effect actions were skipped.")
        elif effect_policy:
            warnings.append("Effect requirements are typed and will be resolved through the verified Effect Resource Resolver.")
        effect_requirements: dict[str, dict[str, Any]] = {}
        cues = []
        occurrences: dict[str, int] = {}
        max_cues = int(song_input.get("max_cues_per_section", 1))
        max_cues = max(1, min(3, max_cues))
        for section_index, section in enumerate(sections, start=1):
            label = str(section.get("name") or f"SECTION_{section_index}").strip()
            role = str(section.get("role") or "UNKNOWN").strip().upper()
            occurrence = occurrences.get(role, 0) + 1
            occurrences[role] = occurrence
            # A role occurrence is the stable identity for repeated material;
            # cue labels/source section ids alone are not sufficient because
            # one section may intentionally produce a base cue plus accents.
            section_instance_id = f"{role.lower()}_{occurrence}"
            raw_energy = section.get("energy")
            energy = self._ROLE_ENERGY.get(role, 0.50) if raw_energy is None else float(raw_energy)
            if not 0.0 <= energy <= 1.0:
                raise FirstSongDesignError(f"Section {label} energy must be between 0 and 1.")
            # Repeated roles are intentionally not a copied visual state. The
            # occurrence uplift is deterministic, bounded, and only affects
            # typed intensity intent; it never selects unscanned resources.
            level = max(1, min(100, round(15 + energy * 80) + min(occurrence - 1, 3) * 4))
            fade = self._fade_for(role, energy)
            cue_number = len(cues) + 1
            actions = [
                {"target": {"type": "group", "ref": group["group_id"]}, "operation": "CALL_PRESET", "preset_ref": preset["reference"], "preset_type": preset.get("preset_type")},
                {"target": {"type": "group", "ref": group["group_id"]}, "operation": "SET_DIMMER", "level": level},
            ]
            effect_requirement_id = self._effect_requirement_id(role, occurrence, effect_policy)
            if effect_requirement_id:
                requirement = self._effect_requirement(effect_requirement_id, group, role, occurrence)
                effect_requirements[effect_requirement_id] = requirement
                actions.append({"target": {"type": "group", "ref": group["group_id"]}, "operation": "CALL_EFFECT", "effect_requirement_id": effect_requirement_id})
            cues.append({
                "id": f"cue-{cue_number}", "cue_number": cue_number, "label": label, "fade": fade,
                "source_section_id": section.get("id"), "section_instance_id": section_instance_id,
                "section_role": role, "role": role, "occurrence_index": occurrence, "cue_occurrence_index": 0,
                "design_energy": energy, "design_energy_source": "ANALYSIS" if raw_energy is not None else "DESIGN_ROLE_DEFAULT",
                "actions": actions,
            })
            # Events remain a deliberately limited density mechanism.  An
            # ACCENT becomes one extra cue only when it is explicitly bound to
            # this section; untimed or unbound events are retained upstream.
            matching = [event for event in song_input.get("events", []) if event.get("section_id") == section.get("id") and event.get("type") in {"ACCENT", "HIT"}]
            for accent_index, event in enumerate(matching[: max(0, max_cues - 1)], start=1):
                strength = float(event.get("strength") if event.get("strength") is not None else 0.5)
                accent_level = max(level, min(100, round(20 + max(energy, strength) * 80)))
                cue_number = len(cues) + 1
                accent_actions = [
                    {"target": {"type": "group", "ref": group["group_id"]}, "operation": "CALL_PRESET", "preset_ref": preset["reference"], "preset_type": preset.get("preset_type")},
                    {"target": {"type": "group", "ref": group["group_id"]}, "operation": "SET_DIMMER", "level": accent_level},
                ]
                if effect_requirement_id:
                    accent_actions.append({"target": {"type": "group", "ref": group["group_id"]}, "operation": "CALL_EFFECT", "effect_requirement_id": effect_requirement_id})
                cues.append({
                    "id": f"cue-{cue_number}", "cue_number": cue_number, "label": f"{label}_ACCENT_{accent_index}",
                    "fade": 0.2 if strength >= 0.7 else 0.5, "source_section_id": section.get("id"),
                    "section_instance_id": section_instance_id, "section_role": role, "role": role,
                    "event_type": event.get("type"), "occurrence_index": occurrence, "cue_occurrence_index": accent_index,
                    "actions": accent_actions,
                })
        return validate_show_plan({
            "schema": SHOW_PLAN_SCHEMA, "song": song, "target_sequence": None,
            "active_sequence_range": active_range, "cues": cues, "effect_requirements": effect_requirements, "warnings": warnings,
            "designer": {
                "kind": "DETERMINISTIC_FIRST_SONG",
                "input_kind": "SONG_ANALYSIS" if song_input.get("analysis_schema") else "MANUAL_FIRST_SONG",
                "uses_neutral_geometry": bool(profile.get("geometry_analysis")),
                "repeated_section_variation": "OCCURRENCE_UPLIFT_V1",
            },
        })

    @staticmethod
    def _fade_for(role: str, energy: float) -> float:
        if role in {"BREAK", "DROP"}:
            return 0.2
        if role in {"INTRO", "OUTRO"}:
            return 2.0
        return 2.0 if energy <= 0.3 else 1.2 if energy <= 0.6 else 0.5

    @staticmethod
    def _effect_requirement_id(role: str, occurrence: int, policy: str) -> str | None:
        if policy == "DIMMER_CHASE_REUSE_SLOW_V1":
            return "fx-dim-chase-slow" if role in {"PRE_CHORUS", "CHORUS"} else None
        if policy != "DIMMER_CHASE_V1":
            return None
        if role == "CHORUS":
            return "fx-dim-chase-fast" if occurrence >= 2 else "fx-dim-chase-med"
        if role in {"PRE_CHORUS", "BUILD"}:
            return "fx-dim-chase-slow"
        return None

    @staticmethod
    def _effect_requirement(identifier: str, group: dict[str, Any], role: str, occurrence: int) -> dict[str, Any]:
        speed = identifier.rsplit("-", 1)[-1].upper()
        return {
            "id": identifier, "feature": "DIMMER", "family": "CHASE", "waveform": "PWM", "low": 0, "high": 100,
            "speed_class": speed, "speed_bpm": {"SLOW": 30, "MED": 60, "FAST": 120}[speed], "phase": "0..360", "direction": "forward", "groups": 1,
            "target_type": "group", "target_ref": group["group_id"], "target_name": group.get("name"),
            "designer_reason": f"{role} occurrence {occurrence} deterministic DIMMER_CHASE_V1 variation",
        }
