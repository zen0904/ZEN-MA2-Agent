"""Load the explicit MA2 Stage-axis evidence record shipped with the Agent."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..portable import app_root


AXIS_PROFILE_FILENAME = "ZEN_STAGE_AXIS_PROFILE.json"


class StageAxisProfile:
    """A small read-only record; it never upgrades missing visual evidence."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_root() / "geometry" / AXIS_PROFILE_FILENAME

    def read(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "status": "UNAVAILABLE",
                "reason": "Stage axis profile is not available in the portable root.",
                "confidence": "UNKNOWN",
            }
        if not isinstance(raw, dict):
            return {"status": "ERROR", "reason": "Stage axis profile must be a JSON object.", "confidence": "UNKNOWN"}
        return {"status": "SUPPORTED", **raw}
