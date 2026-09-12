"""Human-confirmed visual relationship intake for one scanned Existing Show.

This is deliberately separated from technical capability, B3 roles, geometry
writing, and Designer selection.  It records only what a human confirms about
the current rig's visible relationships, while preserving unknowns.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable


VISUAL_RELATIONSHIP_SCHEMA = "zen.current_show_visual_relationships.v0.1"
GROUP_VISUAL_SCHEMA = "zen.current_show_group_visual_evidence.v0.1"

PHYSICAL_PRESENCE = {
    "CENTER_BIASED", "SIDE_BIASED", "WIDE_STAGE", "NARROW_AREA", "OVERHEAD",
    "FLOOR_LEVEL", "REAR_STAGE", "FRONT_STAGE", "MIXED", "UNKNOWN",
}
COVERAGE_SCOPE = {"LOCAL", "MEDIUM", "BROAD", "UNKNOWN"}
VISUAL_WEIGHT = {"LIGHT", "MEDIUM", "HEAVY", "CONTEXT_DEPENDENT", "UNKNOWN"}
SYMMETRY = {"SYMMETRIC", "ASYMMETRIC", "MIXED", "UNKNOWN"}
VISUAL_DOMAIN = {
    "STAGE_SURFACE", "PERFORMER_AREA", "AUDIENCE_FACING", "AERIAL_SPACE",
    "BACKGROUND_FRAME", "MIXED", "UNKNOWN",
}
CONFIRMATION_STATES = {"HUMAN_CONFIRMED", "UNKNOWN"}
RELATIONSHIP_TYPES = {
    "VISUALLY_OVERLAPS_WITH", "VISUALLY_COMPLEMENTS", "VISUALLY_COMPETES_WITH",
    "SPATIALLY_SEPARATE_FROM", "VISUALLY_DOMINATES", "VISUALLY_SUBORDINATE_TO",
    "UNKNOWN",
}
_FORBIDDEN = {
    "command", "commands", "raw_command", "ma_command", "telnet", "lua",
    "role", "roles", "candidate_role", "case_role_assignment", "fixture_priority",
    "preset", "effect", "sequence", "cue",
}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Visual relationship intake cannot contain commands, roles, or programming resources.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe(nested)


def _field(value: dict[str, Any], *, allowed: set[str], multiple: bool = False) -> dict[str, Any]:
    required = {"value", "confirmation_state", "provenance"}
    if not isinstance(value, dict) or required - set(value):
        raise ValueError("Visual field needs value, confirmation_state, and provenance.")
    result = deepcopy(value)
    result["confirmation_state"] = str(result["confirmation_state"]).upper()
    if result["confirmation_state"] not in CONFIRMATION_STATES or not str(result["provenance"]).strip():
        raise ValueError("Visual-field confirmation/provenance is invalid.")
    values = result["value"] if multiple else [result["value"]]
    if not isinstance(values, list) or not values:
        raise ValueError("Visual field value is invalid.")
    normalized = [str(item).upper() for item in values]
    if not set(normalized) <= allowed or len(normalized) != len(set(normalized)):
        raise ValueError("Visual field uses an unsupported or duplicate value.")
    if "UNKNOWN" in normalized and len(normalized) != 1:
        raise ValueError("UNKNOWN cannot be combined with asserted visual values.")
    if result["confirmation_state"] == "UNKNOWN" and normalized != ["UNKNOWN"]:
        raise ValueError("Only HUMAN_CONFIRMED fields may carry asserted visual values.")
    if result["confirmation_state"] == "HUMAN_CONFIRMED" and "UNKNOWN" in normalized:
        raise ValueError("A human-confirmed field cannot retain UNKNOWN.")
    result["value"] = normalized if multiple else normalized[0]
    return result


def _group(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema", "group_id", "group_label", "fixture_count", "physical_presence",
        "coverage_scope", "visual_weight_relative", "symmetry", "primary_visual_domain",
        "human_review",
    }
    if not isinstance(value, dict) or value.get("schema") != GROUP_VISUAL_SCHEMA or required - set(value):
        raise ValueError(f"Group visual schema must be {GROUP_VISUAL_SCHEMA} with required fields.")
    result = deepcopy(value)
    if not isinstance(result["group_id"], int) or result["group_id"] < 1 or not str(result["group_label"]).strip():
        raise ValueError("Group visual identity is invalid.")
    if not isinstance(result["fixture_count"], int) or result["fixture_count"] < 0:
        raise ValueError("Group fixture_count is invalid.")
    result["physical_presence"] = _field(result["physical_presence"], allowed=PHYSICAL_PRESENCE, multiple=True)
    result["coverage_scope"] = _field(result["coverage_scope"], allowed=COVERAGE_SCOPE)
    result["visual_weight_relative"] = _field(result["visual_weight_relative"], allowed=VISUAL_WEIGHT)
    result["symmetry"] = _field(result["symmetry"], allowed=SYMMETRY)
    result["primary_visual_domain"] = _field(result["primary_visual_domain"], allowed=VISUAL_DOMAIN)
    if result["human_review"] != "UNSET":
        raise ValueError("This intake creates review prompts; it cannot pre-fill human review.")
    _safe(result)
    return result


def _relationship(value: dict[str, Any], group_ids: set[int]) -> dict[str, Any]:
    required = {"relationship_id", "from_group_id", "to_group_id", "relationship_type", "confirmation_state", "provenance"}
    if not isinstance(value, dict) or required - set(value):
        raise ValueError("Relationship needs identity, two Groups, type, confirmation state, and provenance.")
    result = deepcopy(value)
    if not str(result["relationship_id"]).strip() or result["from_group_id"] not in group_ids or result["to_group_id"] not in group_ids:
        raise ValueError("Relationship must reference existing Groups.")
    if result["from_group_id"] == result["to_group_id"]:
        raise ValueError("A relationship cannot self-reference.")
    result["relationship_type"] = str(result["relationship_type"]).upper()
    result["confirmation_state"] = str(result["confirmation_state"]).upper()
    if result["relationship_type"] not in RELATIONSHIP_TYPES or result["confirmation_state"] not in CONFIRMATION_STATES:
        raise ValueError("Relationship type/state is invalid.")
    if result["confirmation_state"] == "UNKNOWN" and result["relationship_type"] != "UNKNOWN":
        raise ValueError("An unconfirmed relationship must remain UNKNOWN.")
    if result["confirmation_state"] == "HUMAN_CONFIRMED" and result["relationship_type"] == "UNKNOWN":
        raise ValueError("A confirmed relationship needs an observed relationship type.")
    if not str(result["provenance"]).strip():
        raise ValueError("Relationship provenance is required.")
    _safe(result)
    return result


def validate_visual_relationship_intake(value: dict[str, Any]) -> dict[str, Any]:
    """Validate a show-bound, role-free human visual relationship intake."""
    required = {
        "schema", "intake_id", "show_identity", "groups", "relationships",
        "preexisting_evidence", "scope", "runtime_wiring", "human_review_status",
    }
    if not isinstance(value, dict) or value.get("schema") != VISUAL_RELATIONSHIP_SCHEMA or required - set(value):
        raise ValueError(f"Visual relationship intake schema must be {VISUAL_RELATIONSHIP_SCHEMA}.")
    result = deepcopy(value)
    identity = result["show_identity"]
    if not isinstance(identity, dict) or not str(identity.get("value") or "").strip():
        raise ValueError("A show-bound visual intake requires an explicit Show identity.")
    result["groups"] = [_group(item) for item in result["groups"]]
    ids = [item["group_id"] for item in result["groups"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("Visual-intake Group identities must be sorted and unique.")
    result["relationships"] = [_relationship(item, set(ids)) for item in result["relationships"]]
    rel_ids = [item["relationship_id"] for item in result["relationships"]]
    if len(rel_ids) != len(set(rel_ids)):
        raise ValueError("Relationship identities must be unique.")
    if not isinstance(result["preexisting_evidence"], list) or not result["preexisting_evidence"]:
        raise ValueError("Preexisting evidence must be retained separately from human confirmation.")
    for evidence in result["preexisting_evidence"]:
        if not isinstance(evidence, dict) or {"evidence_id", "state", "source", "limitations"} - set(evidence):
            raise ValueError("Preexisting evidence needs identity, state, source, and limitations.")
        if evidence["state"] != "PREEXISTING_EVIDENCE":
            raise ValueError("Preexisting evidence cannot be represented as human confirmation.")
    if result["scope"] != "CURRENT_SHOW_VISUAL_RELATIONSHIPS_ONLY" or result["runtime_wiring"] != "NOT_RUN":
        raise ValueError("Visual relationship intake must remain current-show scoped and unwired.")
    if result["human_review_status"] != "READY_FOR_HUMAN_INPUT":
        raise ValueError("Visual relationship intake must remain ready for human input.")
    _safe(result)
    return result


def load_visual_relationship_intake(path: Path | str) -> dict[str, Any]:
    return validate_visual_relationship_intake(json.loads(Path(path).read_text(encoding="utf-8")))


def human_confirm_group_fields(intake: dict[str, Any], *, group_id: int, fields: dict[str, Any], reviewer: str) -> dict[str, Any]:
    """Return a revised intake with explicit human-confirmed observation fields.

    This helper is a data preparation boundary only. It does not select a role,
    mutate a Show, generate a plan, or infer values not supplied by the reviewer.
    """
    if not str(reviewer).strip():
        raise ValueError("A human reviewer identity is required.")
    result = validate_visual_relationship_intake(intake)
    group = next((item for item in result["groups"] if item["group_id"] == group_id), None)
    if group is None:
        raise ValueError("Unknown Group.")
    allowed_fields = {"physical_presence", "coverage_scope", "visual_weight_relative", "symmetry", "primary_visual_domain"}
    if not fields or not set(fields) <= allowed_fields:
        raise ValueError("Only bounded visual observation fields may be confirmed.")
    for name, supplied in fields.items():
        group[name] = {
            "value": supplied,
            "confirmation_state": "HUMAN_CONFIRMED",
            "provenance": f"HUMAN_CONFIRMED:{reviewer}",
        }
    return validate_visual_relationship_intake(result)


def describe_shadow_use(intake: dict[str, Any]) -> dict[str, Any]:
    """Expose only a conceptual review boundary; never action recommendations."""
    normalized = validate_visual_relationship_intake(intake)
    confirmed = [group["group_id"] for group in normalized["groups"] if any(group[field]["confirmation_state"] == "HUMAN_CONFIRMED" for field in ("physical_presence", "coverage_scope", "visual_weight_relative", "symmetry", "primary_visual_domain"))]
    return {
        "mode": "CONCEPTUAL_ONLY_NOT_WIRED",
        "confirmed_group_ids": confirmed,
        "could_inform": ["GROUP_LEVEL_HOMOGENEITY_UNRESOLVED", "FINAL_COHORT_SATURATION_RISK"],
        "cannot_do": ["change_ab002_actions", "select_b3_roles", "infer_missing_relationships", "write_ma2"],
    }
