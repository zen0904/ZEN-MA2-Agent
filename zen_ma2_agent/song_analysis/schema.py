"""Validation and normalization for command-free song analysis documents."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


SONG_ANALYSIS_SCHEMA = "zen.song_analysis.v0.1"
SECTION_ROLES = {
    "INTRO", "VERSE", "PRE_CHORUS", "CHORUS", "POST_CHORUS", "DROP",
    "BREAK", "BRIDGE", "SOLO", "INSTRUMENTAL", "BUILD", "OUTRO", "UNKNOWN",
}
_FORBIDDEN_KEYS = {"telnet", "command", "commands", "lua", "ma2_command", "raw_command"}


class SongAnalysisError(ValueError):
    pass


def _walk_forbidden(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = _FORBIDDEN_KEYS & set(value)
        if forbidden:
            raise SongAnalysisError("Song analysis may not contain transport or MA2 command fields.")
        for nested in value.values():
            _walk_forbidden(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_forbidden(nested)


def _number(value: object, field: str, *, minimum: float | None = None, maximum: float | None = None, nullable: bool = True) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SongAnalysisError(f"{field} must be a number or null.")
    result = float(value)
    if minimum is not None and result < minimum or maximum is not None and result > maximum:
        raise SongAnalysisError(f"{field} must be between {minimum} and {maximum}.")
    return result


def _provenance(value: object, *, default_source: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"source": default_source, "confidence": 1.0 if default_source == "MANUAL" else None}
    source = str(value.get("source") or default_source).strip().upper()
    confidence = _number(value.get("confidence"), "provenance confidence", minimum=0.0, maximum=1.0)
    return {"source": source, "confidence": confidence}


def _normal_section(section: object, index: int) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise SongAnalysisError(f"Section {index} must be an object.")
    section_id = str(section.get("id") or "").strip()
    name = str(section.get("name") or section.get("label") or "").strip()
    if not section_id or not name:
        raise SongAnalysisError(f"Section {index} requires id and name.")
    role = str(section.get("role") or "UNKNOWN").strip().upper()
    if role not in SECTION_ROLES:
        raise SongAnalysisError(f"Section {section_id} has unsupported role {role}.")
    start = _number(section.get("start"), f"Section {section_id} start", minimum=0.0)
    end = _number(section.get("end"), f"Section {section_id} end", minimum=0.0)
    if start is not None and end is not None and end < start:
        raise SongAnalysisError(f"Section {section_id} end must not be before start.")
    notes = section.get("notes", [])
    if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
        raise SongAnalysisError(f"Section {section_id} notes must be a string list.")
    return {
        "id": section_id,
        "name": name,
        "label": str(section.get("label") or name),
        "start": start,
        "end": end,
        "energy": _number(section.get("energy"), f"Section {section_id} energy", minimum=0.0, maximum=1.0),
        "density": _number(section.get("density"), f"Section {section_id} density", minimum=0.0, maximum=1.0),
        "accent_level": _number(section.get("accent_level"), f"Section {section_id} accent_level", minimum=0.0, maximum=1.0),
        "role": role,
        "notes": list(notes),
        "provenance": _provenance(section.get("provenance"), default_source="MANUAL"),
    }


def apply_manual_overrides(analysis: dict[str, Any], overrides: object) -> dict[str, Any]:
    """Apply explicit human decisions after parsing/derivation, never before."""
    result = deepcopy(analysis)
    if overrides in (None, []):
        return result
    if not isinstance(overrides, list):
        raise SongAnalysisError("manual_overrides must be a list.")
    by_id = {section["id"]: section for section in result.get("sections", [])}
    for override in overrides:
        if not isinstance(override, dict):
            raise SongAnalysisError("Each manual override must be an object.")
        section = by_id.get(str(override.get("section_id") or ""))
        if section is None:
            raise SongAnalysisError("Manual override references an unknown section_id.")
        if "force_role" in override:
            role = str(override["force_role"] or "").strip().upper()
            if role not in SECTION_ROLES:
                raise SongAnalysisError(f"Manual override has unsupported role {role}.")
            section["role"] = role
        if "force_energy" in override:
            section["energy"] = _number(override["force_energy"], "manual force_energy", minimum=0.0, maximum=1.0, nullable=False)
        if "lighting_note" in override and str(override["lighting_note"]).strip():
            section["notes"].append(str(override["lighting_note"]).strip())
        section["provenance"] = {"source": "MANUAL", "confidence": 1.0}
    result["manual_overrides"] = deepcopy(overrides)
    return result


def validate_song_analysis(document: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized analysis or reject unsafe/ambiguous input."""
    if not isinstance(document, dict) or document.get("schema") != SONG_ANALYSIS_SCHEMA:
        raise SongAnalysisError(f"Song analysis schema must be {SONG_ANALYSIS_SCHEMA}.")
    _walk_forbidden(document)
    song = document.get("song")
    if not isinstance(song, dict) or not str(song.get("title") or "").strip():
        raise SongAnalysisError("Song analysis requires song.title.")
    sections_input = document.get("sections")
    if not isinstance(sections_input, list) or not sections_input:
        raise SongAnalysisError("Song analysis requires at least one section.")
    sections = [_normal_section(item, index) for index, item in enumerate(sections_input, start=1)]
    ids = [section["id"] for section in sections]
    if len(ids) != len(set(ids)):
        raise SongAnalysisError("Song analysis contains duplicate section IDs.")
    timed = sorted((section for section in sections if section["start"] is not None), key=lambda section: section["start"])
    for previous, current in zip(timed, timed[1:]):
        if previous["end"] is not None and current["start"] < previous["end"]:
            raise SongAnalysisError(f"Sections {previous['id']} and {current['id']} overlap.")
    events: list[dict[str, Any]] = []
    for event in document.get("events", []):
        if not isinstance(event, dict):
            raise SongAnalysisError("Each event must be an object.")
        event_type = str(event.get("type") or "").strip().upper()
        if event_type not in {"ACCENT", "BREAK", "HIT"}:
            raise SongAnalysisError("Song event type must be ACCENT, BREAK, or HIT.")
        events.append({
            "time": _number(event.get("time"), "Event time", minimum=0.0, nullable=False),
            "type": event_type,
            "strength": _number(event.get("strength"), "Event strength", minimum=0.0, maximum=1.0),
            "section_id": str(event.get("section_id") or "").strip() or None,
            "provenance": _provenance(event.get("provenance"), default_source="MANUAL"),
        })
    performance = document.get("performance") or {}
    if not isinstance(performance, dict):
        raise SongAnalysisError("performance must be an object.")
    stage_roles = document.get("stage_roles") or []
    if not isinstance(stage_roles, list) or not all(isinstance(item, dict) for item in stage_roles):
        raise SongAnalysisError("stage_roles must be an object list.")
    build = document.get("build") or {}
    active_range = build.get("active_sequence_range")
    if active_range is not None and (not isinstance(active_range, list) or len(active_range) != 2 or not all(isinstance(value, int) and value > 0 for value in active_range) or active_range[0] > active_range[1]):
        raise SongAnalysisError("build.active_sequence_range must be an increasing two-number list.")
    effect_policy = str(build.get("effect_policy") or "").strip().upper()
    if effect_policy not in {"", "DIMMER_CHASE_V1", "DIMMER_CHASE_REUSE_SLOW_V1"}:
        raise SongAnalysisError("build.effect_policy is unsupported.")
    normalized = {
        "schema": SONG_ANALYSIS_SCHEMA,
        "song": {
            "title": str(song["title"]).strip(),
            "duration_seconds": _number(song.get("duration_seconds"), "song.duration_seconds", minimum=0.0),
            "bpm": _number(song.get("bpm"), "song.bpm", minimum=0.0),
        },
        "sections": sections,
        "events": events,
        "performance": {
            "live": bool(performance.get("live", False)),
            "fixed_timeline": bool(performance.get("fixed_timeline", False)),
            "may_extend_solo": bool(performance.get("may_extend_solo", False)),
            "may_repeat_chorus": bool(performance.get("may_repeat_chorus", False)),
        },
        "stage_roles": [{"role": str(item.get("role") or "").strip().upper(), "semantic_position": str(item.get("semantic_position") or "").strip() or None} for item in stage_roles],
        "build": {"active_sequence_range": list(active_range) if active_range is not None else None, "max_cues_per_section": int(build.get("max_cues_per_section", 2)), "effect_policy": effect_policy},
        "source": _provenance(document.get("source"), default_source="MANUAL"),
    }
    if not 1 <= normalized["build"]["max_cues_per_section"] <= 3:
        raise SongAnalysisError("build.max_cues_per_section must be from 1 to 3.")
    return apply_manual_overrides(normalized, document.get("manual_overrides"))
