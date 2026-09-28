"""Verified semantic Position bindings for Spatial System vNext.

This module maps a human spatial target to an already content-verified native
Position Preset application. It owns no MA transport and never creates Position
values, Presets, Cues, Sequences, or console commands.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from .position_application_evidence import position_binding_matches_profile


SEMANTIC_POSITION_BINDING_SCHEMA = "zen.semantic_position_binding.v0.1"
SEMANTIC_POSITION_BINDING_STATUS = "VERIFIED"
SEMANTIC_POSITION_BINDING_SOURCE = "VERIFIED_POSITION_APPLICATION_BINDING"
_TARGET = re.compile(r"[A-Z][A-Z0-9_]*(?:\.[A-Z][A-Z0-9_]*)+\Z")


class SemanticPositionBindingError(ValueError):
    """A semantic target cannot be bound without changing or inventing truth."""


def normalize_semantic_position_target(value: object) -> str:
    if not isinstance(value, str):
        raise SemanticPositionBindingError("SEMANTIC_POSITION_TARGET_INVALID")
    target = value.strip().upper()
    if not _TARGET.fullmatch(target):
        raise SemanticPositionBindingError("SEMANTIC_POSITION_TARGET_INVALID")
    return target


def build_semantic_position_binding(
    profile: Mapping[str, Any],
    application_binding: Mapping[str, Any],
    *,
    semantic_target: str,
) -> dict[str, Any]:
    """Bind one semantic POINT target to one proven Position Preset application."""
    target = normalize_semantic_position_target(semantic_target)
    if not isinstance(application_binding, Mapping) or not position_binding_matches_profile(
        profile, application_binding
    ):
        raise SemanticPositionBindingError("POSITION_APPLICATION_BINDING_UNVERIFIED")

    return {
        "schema": SEMANTIC_POSITION_BINDING_SCHEMA,
        "status": SEMANTIC_POSITION_BINDING_STATUS,
        "show_identity": deepcopy(profile.get("show_identity")),
        "group_id": application_binding.get("group_id"),
        "group_name": application_binding.get("group_name"),
        "semantic_target": target,
        "target_kind": "POINT",
        "resolution_mode": "REUSE",
        "position_preset": {
            "reference": application_binding.get("reference"),
            "label": application_binding.get("preset_label"),
        },
        "application_binding": deepcopy(dict(application_binding)),
        "source": SEMANTIC_POSITION_BINDING_SOURCE,
    }


def semantic_position_binding_matches_profile(
    profile: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> bool:
    """Require both semantic identity and the underlying native proof to remain valid."""
    try:
        if (
            not isinstance(binding, Mapping)
            or binding.get("schema") != SEMANTIC_POSITION_BINDING_SCHEMA
            or binding.get("status") != SEMANTIC_POSITION_BINDING_STATUS
            or binding.get("source") != SEMANTIC_POSITION_BINDING_SOURCE
            or binding.get("target_kind") != "POINT"
            or binding.get("resolution_mode") != "REUSE"
            or binding.get("show_identity") != profile.get("show_identity")
            or normalize_semantic_position_target(binding.get("semantic_target"))
            != binding.get("semantic_target")
        ):
            return False
        application = binding.get("application_binding")
        preset = binding.get("position_preset")
        if not isinstance(application, Mapping) or not isinstance(preset, Mapping):
            return False
        if not position_binding_matches_profile(profile, application):
            return False
        return bool(
            binding.get("group_id") == application.get("group_id")
            and binding.get("group_name") == application.get("group_name")
            and preset.get("reference") == application.get("reference")
            and preset.get("label") == application.get("preset_label")
        )
    except (SemanticPositionBindingError, TypeError, ValueError):
        return False


def semantic_position_resources_for_profile(
    profile: Mapping[str, Any],
    bindings: Iterable[Mapping[str, Any]],
) -> dict[int, list[dict[str, Any]]]:
    """Return unambiguous current-Show semantic targets grouped by Group ID.

    Conflicting bindings for one Group/target are not exposed. Ambiguity is a
    fail-closed absence, never a "pick one" policy.
    """
    candidates: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for binding in bindings:
        if not isinstance(binding, Mapping) or not semantic_position_binding_matches_profile(
            profile, binding
        ):
            continue
        group_id = binding.get("group_id")
        target = binding.get("semantic_target")
        preset = binding.get("position_preset")
        if (
            isinstance(group_id, bool)
            or not isinstance(group_id, int)
            or group_id < 1
            or not isinstance(target, str)
            or not isinstance(preset, Mapping)
        ):
            continue
        row = {
            "semantic_target": target,
            "target_kind": "POINT",
            "resolution_mode": "REUSE",
            "reference": preset.get("reference"),
            "name": preset.get("label"),
            "verification": SEMANTIC_POSITION_BINDING_STATUS,
            "source": SEMANTIC_POSITION_BINDING_SOURCE,
        }
        candidates.setdefault((group_id, target), []).append(row)

    result: dict[int, list[dict[str, Any]]] = {}
    for (group_id, _target), rows in sorted(candidates.items()):
        identities = {(row.get("reference"), row.get("name")) for row in rows}
        if len(identities) != 1:
            continue
        result.setdefault(group_id, []).append(deepcopy(rows[0]))
    for rows in result.values():
        rows.sort(key=lambda item: item["semantic_target"])
    return result


class SemanticPositionBindingStore:
    """Durable operator-authored semantic mappings; current Show truth wins."""

    def __init__(self, root: Path):
        self.path = Path(root) / "data" / "ZEN_SEMANTIC_POSITION_BINDINGS.json"

    def has_candidates(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return bool(
            isinstance(data, dict)
            and data.get("schema") == "zen.semantic_position_binding_catalog.v0.1"
            and isinstance(data.get("bindings"), list)
            and data["bindings"]
        )

    def load_verified(self, profile: Mapping[str, Any]) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if (
            not isinstance(data, dict)
            or data.get("schema") != "zen.semantic_position_binding_catalog.v0.1"
            or not isinstance(data.get("bindings"), list)
        ):
            return []
        return [
            row for row in data["bindings"]
            if isinstance(row, dict)
            and semantic_position_binding_matches_profile(profile, row)
        ]

    def record_verified(
        self,
        profile: Mapping[str, Any],
        application_binding: Mapping[str, Any],
        *,
        semantic_target: str,
    ) -> dict[str, Any]:
        """Record only an explicit semantic label over an already verified native proof."""
        binding = build_semantic_position_binding(
            profile, application_binding, semantic_target=semantic_target
        )
        rows = self.load_verified(profile)
        rows = [
            row for row in rows
            if (row.get("group_id"), row.get("semantic_target"))
            != (binding["group_id"], binding["semantic_target"])
        ]
        rows.append(binding)
        rows.sort(key=lambda row: (row["group_id"], row["semantic_target"]))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "schema": "zen.semantic_position_binding_catalog.v0.1",
                    "bindings": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return binding
