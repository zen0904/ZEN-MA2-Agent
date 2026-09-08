"""Portable, command-free song-analysis input layer.

The package deliberately stops at a normalized ``ZEN_SONG_ANALYSIS`` document.
It never talks to grandMA2 and never represents transport commands.
"""

from .adapter import SongAnalysisAdapter
from .schema import (
    SONG_ANALYSIS_SCHEMA,
    SongAnalysisError,
    apply_manual_overrides,
    validate_song_analysis,
)
from .script_parser import ScriptSongParser

__all__ = [
    "SONG_ANALYSIS_SCHEMA",
    "SongAnalysisAdapter",
    "SongAnalysisError",
    "ScriptSongParser",
    "apply_manual_overrides",
    "validate_song_analysis",
]
