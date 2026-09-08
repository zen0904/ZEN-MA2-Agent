"""Exact-label semantic Position Preset registry; deliberately no fuzzy match."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .portable import app_root


class SemanticPresetRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_root() / "semantic_presets" / "ZEN_SEMANTIC_PRESET_REGISTRY.json"
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if raw.get("schema") != "zen.semantic_preset_registry.v0.1" or not isinstance(raw.get("entries"), list):
            raise ValueError("Invalid semantic Preset registry.")
        self.raw = raw

    def resolve(self, presets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only explicit POSITION-label bindings discovered in state."""
        available = {(str(item.get("preset_type") or "").upper(), str(item.get("name") or "")): item for item in presets}
        bindings: list[dict[str, Any]] = []
        for entry in self.raw["entries"]:
            candidate = available.get((str(entry.get("preset_type") or "").upper(), str(entry.get("label") or "")))
            if candidate and entry.get("can_reference"):
                bindings.append({**entry, "preset_id": candidate.get("number"), "resolved": True, "source": "MA2_PRESET_INVENTORY_EXACT_LABEL"})
        return bindings
