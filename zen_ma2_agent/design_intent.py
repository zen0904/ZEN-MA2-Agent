"""Typed, command-free design intent for the experimental A/B Designer only."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


DESIGN_INTENT_SCHEMA = "zen.design_intent.v0.1"
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Design intent may not contain MA2 command fields.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe(nested)


def validate_design_intent(value: dict[str, Any]) -> dict[str, Any]:
    """Validate a reviewable artistic rationale without prescribing MA2 syntax."""
    required = {
        "schema", "intent_id", "section_id", "section_role", "audience_perception_goal",
        "relationship_to_previous", "relationship_to_next", "continuity_vs_change",
        "design_dimensions", "headroom_intent", "resource_strategy",
        "intentional_omissions", "rationale", "evidence_provenance", "unknown_context", "scope",
    }
    if not isinstance(value, dict) or value.get("schema") != DESIGN_INTENT_SCHEMA or required - set(value):
        raise ValueError(f"Design intent schema must be {DESIGN_INTENT_SCHEMA} with required fields.")
    normalized = deepcopy(value)
    if not all(isinstance(normalized[key], str) and normalized[key] for key in (
        "intent_id", "section_id", "section_role", "audience_perception_goal",
        "relationship_to_previous", "relationship_to_next", "continuity_vs_change",
        "headroom_intent", "resource_strategy", "scope",
    )):
        raise ValueError("Design intent identity and relationship fields must be non-empty strings.")
    if not isinstance(normalized["design_dimensions"], dict):
        raise ValueError("Design intent dimensions must remain a typed mapping.")
    if not all(isinstance(normalized[key], list) for key in ("intentional_omissions", "rationale", "evidence_provenance", "unknown_context")):
        raise ValueError("Design intent rationale/provenance collections must be lists.")
    _safe(normalized)
    return normalized
