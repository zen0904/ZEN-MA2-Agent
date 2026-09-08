"""Deterministic text/Markdown cue-script parser; it does not infer audio roles."""
from __future__ import annotations

import re
from typing import Any

from .schema import SONG_ANALYSIS_SCHEMA, validate_song_analysis


_TIMED = re.compile(r"^\s*(?:(\d{1,2}):(\d{2})(?:\.(\d+))?\s+)?(?:[-*#]\s*)?(.*?)\s*$")
_ROLE_TERMS = (
    ("PRE_CHORUS", ("pre chorus", "pre-chorus", "前副歌", "預副歌")),
    ("POST_CHORUS", ("post chorus", "post-chorus", "後副歌")),
    ("CHORUS", ("chorus", "副歌")),
    ("INTRO", ("intro", "前奏", "開場")),
    ("VERSE", ("verse", "主歌")),
    ("BRIDGE", ("bridge", "橋段")),
    ("SOLO", ("solo", "獨奏", "薩克斯", "sax")),
    ("DROP", ("drop", "掉拍")),
    ("BREAK", ("break", "間奏", "breakdown")),
    ("BUILD", ("build", "堆疊")),
    ("OUTRO", ("outro", "尾奏", "結尾")),
    ("INSTRUMENTAL", ("instrumental", "演奏")),
)


def _role(text: str) -> str:
    folded = text.casefold()
    for role, terms in _ROLE_TERMS:
        if any(term.casefold() in folded for term in terms):
            return role
    return "UNKNOWN"


class ScriptSongParser:
    """Convert an operator-authored structure script into transparent data."""

    def parse(self, text: str, *, title: str, active_sequence_range: list[int] | None = None, performance: dict[str, Any] | None = None) -> dict[str, Any]:
        lines = [line for line in str(text).splitlines() if line.strip() and not line.lstrip().startswith("#")]
        sections = []
        for ordinal, line in enumerate(lines, start=1):
            matched = _TIMED.match(line)
            if not matched:
                continue
            minute, second, fractional, label = matched.groups()
            label = label.strip()
            if not label:
                continue
            start = None
            if minute is not None:
                start = int(minute) * 60 + int(second) + float("0." + fractional) if fractional else int(minute) * 60 + int(second)
            role = _role(label)
            sections.append({
                "id": f"{role.casefold()}_{ordinal}", "name": label, "label": label, "start": start,
                "end": None, "energy": None, "density": None, "accent_level": None, "role": role,
                "notes": [], "provenance": {"source": "SCRIPT_PARSED", "confidence": 1.0},
            })
        for current, following in zip(sections, sections[1:]):
            if current["start"] is not None and following["start"] is not None:
                current["end"] = following["start"]
        return validate_song_analysis({
            "schema": SONG_ANALYSIS_SCHEMA,
            "song": {"title": title, "duration_seconds": None, "bpm": None},
            "sections": sections,
            "performance": performance or {},
            "build": {"active_sequence_range": active_sequence_range, "max_cues_per_section": 2},
            "source": {"source": "SCRIPT_PARSED", "confidence": 1.0},
        })
