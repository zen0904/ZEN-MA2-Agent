"""Synthetic, bounded rig contexts used only for shadow advisory evaluation."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .training_case import TRAINING_CASE_001, validate_training_case


SHADOW_RIG_CONTEXT_SCHEMA = "zen.shadow_rig_context.v0.1"
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}
_STATES = {"LOW", "MEDIUM", "HIGH"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Shadow rig contexts may not contain MA2 command fields.")
        for item in value.values():
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)


def validate_shadow_rig_context(context: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "case_id", "case_name", "label", "resource_scale", "available_roles", "semantic_relationships", "geometry_status", "design_affordances", "constraints"}
    if not isinstance(context, dict) or context.get("schema") != SHADOW_RIG_CONTEXT_SCHEMA or required - set(context):
        raise ValueError("Invalid shadow rig context.")
    if context["label"] != "SHADOW_EVALUATION_ONLY":
        raise ValueError("Shadow rig context must remain evaluation-only.")
    if context["resource_scale"] not in {"LIMITED", "SMALL", "MEDIUM", "LARGE", "RESOURCE_RICH"}:
        raise ValueError("Invalid shadow rig resource scale.")
    if not isinstance(context["available_roles"], list) or not all(isinstance(item, str) and item for item in context["available_roles"]):
        raise ValueError("Shadow rig roles must be explicit strings.")
    affordances = context["design_affordances"]
    if set(affordances) != _STATES:
        raise ValueError("Shadow rig needs LOW, MEDIUM and HIGH affordances.")
    for state, choices in affordances.items():
        if not isinstance(choices, dict) or not {"KEEP", "REDUCE", "OMIT", "SUBSTITUTE", "REASON"} <= set(choices):
            raise ValueError(f"Shadow rig {state} affordance is incomplete.")
        if not all(isinstance(choices[key], list) for key in ("KEEP", "REDUCE", "OMIT", "SUBSTITUTE", "REASON")):
            raise ValueError("Shadow rig affordance values must be lists.")
        for key in ("KEEP", "REDUCE", "OMIT"):
            if not set(choices[key]) <= set(context["available_roles"]):
                raise ValueError("Shadow rig affordance can only select explicitly available roles.")
        if not all(isinstance(item, dict) and {"UNAVAILABLE", "REPLACEMENT", "REASON"} <= set(item) for item in choices["SUBSTITUTE"]):
            raise ValueError("Shadow rig substitutions must preserve unavailable/replacement/reason fields.")
    _safe(context)
    return deepcopy(context)


def _affordances(low: tuple[list[str], list[str], list[str], list[dict[str, str]], list[str]], medium: tuple[list[str], list[str], list[str], list[dict[str, str]], list[str]], high: tuple[list[str], list[str], list[str], list[dict[str, str]], list[str]]) -> dict[str, dict[str, Any]]:
    def as_choice(value: tuple[list[str], list[str], list[str], list[dict[str, str]], list[str]]) -> dict[str, Any]:
        keep, reduce, omit, substitute, reason = value
        return {"KEEP": keep, "REDUCE": reduce, "OMIT": omit, "SUBSTITUTE": substitute, "REASON": reason}
    return {"LOW": as_choice(low), "MEDIUM": as_choice(medium), "HIGH": as_choice(high)}


def build_resource_rich_control(training_case: dict[str, Any]) -> dict[str, Any]:
    """A shadow wrapper that grounds Rig A in Training Case 001 without writing it."""
    case = validate_training_case(training_case)
    if case["case_id"] != TRAINING_CASE_001:
        raise ValueError("Resource-rich control must reference Training Case 001.")
    roles = sorted({role for group in case["fixture_groups"] for role in [group["role_assignment"]["primary_role"], *group["role_assignment"].get("secondary_roles", [])]})
    return validate_shadow_rig_context({
        "schema": SHADOW_RIG_CONTEXT_SCHEMA, "case_id": "RIG_A_RESOURCE_RICH_CONTROL", "case_name": "Training Case 001 resource-rich control",
        "label": "SHADOW_EVALUATION_ONLY", "resource_scale": "RESOURCE_RICH", "available_roles": roles,
        "semantic_relationships": [{"type": "CASE_BOUND", "reference": TRAINING_CASE_001, "evidence": "Training Case 001 role hypotheses only."}],
        "geometry_status": case["verified_resources"].get("geometry", "UNKNOWN"),
        "constraints": {"base_training_case": TRAINING_CASE_001, "no_ma2_commands": True, "no_geometry_inference": True, "scope": "SHADOW_EVALUATION_ONLY"},
        "design_affordances": _affordances(
            (["KEY_LAYER", "COLOR_LAYER"], ["AERIAL", "TEXTURE"], ["IMPACT", "EYE_CANDY"], [], ["Preserve headroom and a clear focal hierarchy."]),
            (["KEY_LAYER", "COLOR_LAYER", "WASH_LAYER"], ["AERIAL"], ["IMPACT"], [], ["Develop contrast without activating every available layer."]),
            (["KEY_LAYER", "COLOR_LAYER", "AERIAL", "TEXTURE", "IMPACT"], ["EYE_CANDY"], [], [], ["Use high-value layers selectively; resource-rich does not mean every role is active."]),
        ),
    })


def build_cross_rig_evaluation_contexts(training_case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Four explicit semantic contexts; no fixture ID or MA2 geometry is implied."""
    rich = build_resource_rich_control(training_case)
    medium = validate_shadow_rig_context({
        "schema": SHADOW_RIG_CONTEXT_SCHEMA, "case_id": "RIG_B_MEDIUM_LIVE", "case_name": "Medium live rig", "label": "SHADOW_EVALUATION_ONLY",
        "resource_scale": "MEDIUM", "available_roles": ["PRIMARY_FOCUS", "COLOR_LAYER", "COMBINED_TEXTURE_IMPACT", "BROAD_ENVIRONMENT"],
        "semantic_relationships": [{"type": "CASE_BOUND", "reference": "MEDIUM_LIVE", "evidence": "Synthetic bounded resource context."}],
        "geometry_status": "SYNTHETIC_SEMANTIC_ONLY", "constraints": {"no_ma2_commands": True, "no_geometry_inference": True, "scope": "SHADOW_EVALUATION_ONLY"},
        "design_affordances": _affordances(
            (["PRIMARY_FOCUS", "COLOR_LAYER"], ["BROAD_ENVIRONMENT"], ["COMBINED_TEXTURE_IMPACT"], [], ["Protect focus and palette; leave the combined accent source inactive for negative space."]),
            (["PRIMARY_FOCUS", "COLOR_LAYER", "BROAD_ENVIRONMENT"], ["COMBINED_TEXTURE_IMPACT"], [], [{"UNAVAILABLE": "INDEPENDENT_AERIAL_LAYER", "REPLACEMENT": "BROAD_ENVIRONMENT_DEPTH_CHANGE", "REASON": "Use the available environment layer for contrast rather than inventing an aerial source."}], ["Prioritize section identity before independent texture."]),
            (["PRIMARY_FOCUS", "COLOR_LAYER", "COMBINED_TEXTURE_IMPACT"], ["BROAD_ENVIRONMENT"], [], [{"UNAVAILABLE": "SEPARATE_TEXTURE_AND_IMPACT", "REPLACEMENT": "COMBINED_TEXTURE_IMPACT_TIMED_ACCENT", "REASON": "One flexible source performs a bounded accent role."}], ["Use the combined source only for meaningful high-energy punctuation."]),
        ),
    })
    led = validate_shadow_rig_context({
        "schema": SHADOW_RIG_CONTEXT_SCHEMA, "case_id": "RIG_C_LED_ONLY", "case_name": "LED-only rig", "label": "SHADOW_EVALUATION_ONLY",
        "resource_scale": "LIMITED", "available_roles": ["COLOR_FIELD", "DENSITY_LAYER", "TIMING_LAYER", "LEFT_RIGHT_RELATIONSHIP"],
        "semantic_relationships": [{"type": "EXPLICIT_SYNTHETIC", "reference": "LEFT_RIGHT_RELATIONSHIP", "evidence": "Synthetic case explicitly supplies this semantic relationship."}],
        "geometry_status": "SYNTHETIC_SEMANTIC_ONLY", "constraints": {"no_mover_position": True, "no_beam_aerial": True, "no_gobo_texture": True, "no_geometry_inference": True, "scope": "SHADOW_EVALUATION_ONLY"},
        "design_affordances": _affordances(
            (["COLOR_FIELD"], ["DENSITY_LAYER"], ["TIMING_LAYER", "LEFT_RIGHT_RELATIONSHIP"], [], ["Use color field and deliberate inactive space to establish a complete quiet state."]),
            (["COLOR_FIELD", "DENSITY_LAYER"], ["TIMING_LAYER"], [], [{"UNAVAILABLE": "MOVER_AERIAL_MOVEMENT", "REPLACEMENT": "COLOR_FIELD_DENSITY_CHANGE", "REASON": "Section contrast comes from available color and density, not invented motion."}], ["Make the medium state distinct through density and palette behavior."]),
            (["COLOR_FIELD", "DENSITY_LAYER", "TIMING_LAYER", "LEFT_RIGHT_RELATIONSHIP"], [], [], [{"UNAVAILABLE": "BEAM_TRANSIENT_IMPACT", "REPLACEMENT": "LEFT_RIGHT_TIMING_CONTRAST_PLUS_DENSITY_PUNCTUATION", "REASON": "Explicit left/right relation and timing provide a credible LED-only accent mechanism."}], ["Use timing/density punctuation without claiming mover or beam language."]),
        ),
    })
    imperfect = validate_shadow_rig_context({
        "schema": SHADOW_RIG_CONTEXT_SCHEMA, "case_id": "RIG_D_IMPERFECT_ASYMMETRIC", "case_name": "Imperfect asymmetric rig", "label": "SHADOW_EVALUATION_ONLY",
        "resource_scale": "MEDIUM", "available_roles": ["PRIMARY_FOCUS", "COLOR_LAYER", "ASYMMETRIC_TEXTURE", "IMPACT_ACCENT"],
        "semantic_relationships": [{"type": "EXPLICIT_SYNTHETIC", "reference": "UNEQUAL_COUNTS", "evidence": "Synthetic case explicitly declares unequal capability."}, {"type": "EXPLICIT_SYNTHETIC", "reference": "CENTER_CAPABLE", "evidence": "Synthetic case explicitly declares an available focal relation."}],
        "geometry_status": "SYNTHETIC_SEMANTIC_ONLY", "constraints": {"no_symmetry_assumption": True, "no_ma2_geometry_inference": True, "scope": "SHADOW_EVALUATION_ONLY"},
        "design_affordances": _affordances(
            (["PRIMARY_FOCUS", "COLOR_LAYER"], ["ASYMMETRIC_TEXTURE"], ["IMPACT_ACCENT"], [], ["Keep the center-capable focus legible and leave imbalance quiet when the music is restrained."]),
            (["PRIMARY_FOCUS", "COLOR_LAYER", "ASYMMETRIC_TEXTURE"], [], ["IMPACT_ACCENT"], [{"UNAVAILABLE": "MIRRORED_TEXTURE_PATTERN", "REPLACEMENT": "INTENTIONAL_ASYMMETRIC_TEXTURE", "REASON": "Use the declared unequal capability as an intentional directional texture, not a failed mirror."}], ["Preserve hierarchy without forcing symmetry."]),
            (["PRIMARY_FOCUS", "COLOR_LAYER", "ASYMMETRIC_TEXTURE", "IMPACT_ACCENT"], [], [], [{"UNAVAILABLE": "SYMMETRIC_FULL_RIG_IMPACT", "REPLACEMENT": "CENTER_FOCUS_PLUS_ASYMMETRIC_ACCENT", "REASON": "Retain focal clarity and use the imbalance purposefully."}], ["High energy does not require a symmetrical visual composition."]),
        ),
    })
    return {item["case_id"]: item for item in (rich, medium, led, imperfect)}
