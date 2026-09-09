"""Training-case knowledge for the general lighting designer boundary.

Training cases describe design knowledge and resource context only.  They do
not emit MA2 commands and are deliberately not part of the Builder execution
path yet.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


TRAINING_CASE_SCHEMA = "zen.lighting_training_case.v0.1"
TRAINING_CASE_001 = "TRAINING_CASE_001"
ROLE_VOCABULARY = (
    "AERIAL", "KEY_LAYER", "WASH_LAYER", "TEXTURE", "BEAM_LAYER", "COLOR_LAYER",
    "IMPACT", "ACCENT", "FLOOR", "SIDE", "BACKLIGHT", "SILHOUETTE",
    "EYE_CANDY", "PERFORMER_FOCUS", "ENVIRONMENT", "UTILITY",
)
ZONE_VOCABULARY = (
    "UPSTAGE", "MIDSTAGE", "DOWNSTAGE", "HIGH", "MID", "LOW", "FLOOR",
    "CENTER", "INNER", "OUTER", "SIDE", "EDGE",
)
LAYER_VOCABULARY = (
    "BASE_LAYER", "SUBJECT_LAYER", "AERIAL_LAYER", "TEXTURE_LAYER",
    "COLOR_LAYER", "IMPACT_LAYER", "ACCENT_LAYER",
)
_FORBIDDEN_KEYS = {"command", "commands", "raw_command", "telnet", "lua", "ma_command"}


def _walk_no_commands(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN_KEYS & set(value):
            raise ValueError("Training cases may not contain MA2 command fields.")
        for nested in value.values():
            _walk_no_commands(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_no_commands(nested)


def validate_training_case(case: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(case, dict) or case.get("schema") != TRAINING_CASE_SCHEMA:
        raise ValueError(f"Training case schema must be {TRAINING_CASE_SCHEMA}.")
    required = ("case_id", "case_name", "case_type", "show_profile_ref", "resource_scale", "style_orientation", "fixture_groups", "rig_roles", "visual_layers", "design_principles", "constraints", "verified_resources", "assumptions", "confidence", "designer_lessons", "anti_patterns")
    missing = [key for key in required if key not in case]
    if missing:
        raise ValueError(f"Training case is missing: {', '.join(missing)}")
    if case["resource_scale"] not in {"LIMITED", "SMALL", "MEDIUM", "LARGE", "RESOURCE_RICH"}:
        raise ValueError("Training case resource_scale is invalid.")
    if case["style_orientation"] not in {"GENERAL", "KPOP", "BAND", "THEATRE", "CORPORATE", "OTHER"}:
        raise ValueError("Training case style_orientation is invalid.")
    if not isinstance(case["fixture_groups"], list) or not isinstance(case["design_principles"], list) or not isinstance(case["anti_patterns"], list):
        raise ValueError("Training case collections must be lists.")
    for group in case["fixture_groups"]:
        assignment = group.get("role_assignment") if isinstance(group, dict) else None
        if not isinstance(assignment, dict) or assignment.get("confidence") != "INFERRED_FROM_GROUP_IDENTITY":
            raise ValueError("Case fixture roles must retain inference provenance.")
        roles = [assignment.get("primary_role"), *(assignment.get("secondary_roles") or []), *(assignment.get("contextual_roles") or [])]
        if any(role not in ROLE_VOCABULARY for role in roles):
            raise ValueError("Case fixture role is outside the role vocabulary.")
        if any(zone not in ZONE_VOCABULARY for zone in assignment.get("possible_rig_zones", [])):
            raise ValueError("Case rig zone is outside the proposed zone vocabulary.")
    if any(layer.get("name") not in LAYER_VOCABULARY for layer in case["visual_layers"]):
        raise ValueError("Case visual layer is outside the layer vocabulary.")
    _walk_no_commands(case)
    return deepcopy(case)


_ROLE_MAP = {
    "HYBRID": ("AERIAL", ["KEY_LAYER", "TEXTURE"], ["IMPACT"], ["HIGH", "MID", "CENTER"], "A versatile case-specific moving layer that can bridge aerial and subject looks."),
    "SPOT": ("KEY_LAYER", ["PERFORMER_FOCUS", "ACCENT"], ["BACKLIGHT"], ["MID", "CENTER", "SIDE"], "A focused source for subject separation; actual use depends on fixture capability and plot."),
    "BEAM": ("BEAM_LAYER", ["AERIAL", "SILHOUETTE"], ["ACCENT"], ["HIGH", "UPSTAGE", "EDGE"], "A narrow-beam family can provide contrast and aerial punctuation in this case."),
    "WASH": ("WASH_LAYER", ["COLOR_LAYER", "ENVIRONMENT"], ["KEY_LAYER"], ["MID", "DOWNSTAGE", "CENTER"], "A broad source can establish coverage and color context without fixing a venue position."),
    "B-EYE": ("TEXTURE", ["COLOR_LAYER", "EYE_CANDY"], ["IMPACT"], ["MID", "HIGH", "OUTER"], "Pixel/shape capability is a case hypothesis, not a global Fixture Type rule."),
    "LED PAR": ("COLOR_LAYER", ["WASH_LAYER", "UTILITY"], ["BACKLIGHT"], ["LOW", "MID", "FLOOR"], "A compact color layer can support large looks or remain a restrained base."),
    "STROBE": ("IMPACT", ["ACCENT", "EYE_CANDY"], ["AERIAL"], ["HIGH", "EDGE", "OUTER"], "Reserved impact capacity preserves contrast for high-energy sections."),
}


def analyze_current_groups(profile: dict[str, Any]) -> list[dict[str, Any]]:
    fixture_types = {item.get("fixture_id"): item.get("fixture_type") for item in profile.get("fixtures", []) if isinstance(item, dict)}
    result = []
    for group in sorted((item for item in profile.get("groups", []) if isinstance(item, dict)), key=lambda item: int(item.get("group_id", 0))):
        name = str(group.get("name") or "").strip()
        primary, secondary, contextual, zones, rationale = _ROLE_MAP.get(name.upper(), ("UTILITY", [], ["ENVIRONMENT"], ["MID"], "Unknown Group identity; retained as a flexible utility role."))
        fixture_ids = list(group.get("fixture_ids_in_selection_order") or [])
        types = sorted({str(fixture_types.get(fixture_id) or "UNAVAILABLE") for fixture_id in fixture_ids})
        result.append({
            "group_id": group.get("group_id"),
            "name": name,
            "fixture_ids_in_selection_order": fixture_ids,
            "fixture_types": types,
            "role_assignment": {
                "primary_role": primary,
                "secondary_roles": secondary,
                "contextual_roles": contextual,
                "possible_rig_zones": zones,
                "rationale": rationale,
                "confidence": "INFERRED_FROM_GROUP_IDENTITY",
                "evidence": "Current Show Group name plus verified Fixture Type inventory; no physical placement claim.",
                "scope": "CASE_SPECIFIC",
            },
        })
    return result


def build_training_case_001(profile: dict[str, Any], *, show_profile_ref: str = "data/ZEN_CURRENT_SHOW_PROFILE.json") -> dict[str, Any]:
    groups = analyze_current_groups(profile)
    fixture_count = len([item for item in profile.get("fixtures", []) if isinstance(item, dict)])
    preset_count = len([item for item in profile.get("presets", []) if isinstance(item, dict)])
    effects = [item for item in profile.get("effects", []) if isinstance(item, dict)]
    case = {
        "schema": TRAINING_CASE_SCHEMA,
        "case_id": TRAINING_CASE_001,
        "case_name": "Resource-rich training rig — K-pop-oriented design study",
        "case_type": "RESOURCE_RICH_KPOP_ORIENTED",
        "show_profile_ref": show_profile_ref,
        "resource_scale": "RESOURCE_RICH",
        "style_orientation": "KPOP",
        "fixture_groups": groups,
        "rig_roles": list(ROLE_VOCABULARY),
        "visual_layers": [
            {"name": "BASE_LAYER", "purpose": "Maintain a readable minimum look and headroom."},
            {"name": "SUBJECT_LAYER", "purpose": "Separate performers or the focal subject."},
            {"name": "AERIAL_LAYER", "purpose": "Add beams, silhouettes, or vertical scale when available."},
            {"name": "TEXTURE_LAYER", "purpose": "Add movement, pixel texture, or visual detail."},
            {"name": "COLOR_LAYER", "purpose": "Shape palette and environment without relying on intensity alone."},
            {"name": "IMPACT_LAYER", "purpose": "Reserve high-contrast accents for meaningful musical moments."},
            {"name": "ACCENT_LAYER", "purpose": "Deliver short hits or sectional punctuation."},
        ],
        "design_principles": [
            {"principle": "RESERVE_HEADROOM", "why": "A look needs room to grow later.", "when_useful": "Openings, verses, and any long-form build.", "when_not_applicable": "A deliberately maximal one-shot cue.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "SECTION_CONTRAST", "why": "Section changes should be legible as changes in visual structure, not only level.", "when_useful": "Verse/chorus and pre/final transitions.", "when_not_applicable": "A deliberately static ambient passage.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "REPEATED_SECTION_DEVELOPMENT", "why": "Later occurrences should have a reason to feel related but not copied.", "when_useful": "Repeated verses, choruses, or hooks.", "when_not_applicable": "A conscious exact reprise.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "EFFECT_FATIGUE_AVOIDANCE", "why": "A motion effect loses impact when it is always present.", "when_useful": "Chorus/impact planning.", "when_not_applicable": "A continuous texture brief that explicitly demands it.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "LAYER_ESCALATION", "why": "Energy can rise through coverage, contrast, motion, focus, or added layers.", "when_useful": "Builds and finales.", "when_not_applicable": "When resources or song structure require restraint.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "FOCUS_HIERARCHY", "why": "The audience needs a readable subject even in a rich rig.", "when_useful": "Solos, verses, and dense choruses.", "when_not_applicable": "An intentionally environmental interlude.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "RESOURCE_AWARENESS", "why": "The same intent must degrade gracefully on limited or asymmetric rigs.", "when_useful": "Every design decision.", "when_not_applicable": "Never; the implementation may vary.", "scope": "GENERALIZABLE_LESSON"},
            {"principle": "ASYMMETRY_TOLERANCE", "why": "A designer should work with imperfect rigs instead of inventing symmetry.", "when_useful": "Medium, small, and production shows.", "when_not_applicable": "Only when symmetry is actually evidenced.", "scope": "GENERALIZABLE_LESSON"},
        ],
        "constraints": {
            "read_only": True,
            "no_ma2_commands": True,
            "no_geometry_write": True,
            "case_specific_decisions_are_not_global_rules": True,
            "spatial_zones_status": "PROPOSED_RIG_ZONE_NOT_VERIFIED_GEOMETRY",
        },
        "verified_resources": {
            "group_count": len(groups),
            "fixture_count": fixture_count,
            "preset_count": preset_count,
            "effect_count": len(effects),
            "groups_membership": "VERIFIED_FRESH_READ_ONLY",
            "fixture_identity_and_types": "VERIFIED_FRESH_READ_ONLY",
            "geometry": "GEOMETRY_UNINITIALIZED",
            "semantic_positions": "NONE",
            "effect_parameters": "PARTIAL",
        },
        "assumptions": [
            {"text": "Role assignments derive from Group identity and current Fixture inventory, not physical plot evidence.", "scope": "CASE_SPECIFIC", "confidence": "INFERRED_FROM_GROUP_IDENTITY"},
            {"text": "Each Group is modeled as a design layer candidate; Group names do not constrain future roles.", "scope": "CASE_SPECIFIC", "confidence": "INFERRED_FROM_GROUP_IDENTITY"},
            {"text": "No final XYZ, Stage Left/Right, Front/Back, or real hanging position is asserted.", "scope": "CASE_SPECIFIC", "confidence": "UNKNOWN"},
        ],
        "confidence": "PARTIAL_CASE_CONTEXT",
        "designer_lessons": [
            {"lesson": "CHORUS should increase visual layers, contrast, coverage, or movement where available.", "scope": "GENERALIZABLE_LESSON", "evidence": "V1 creative review"},
            {"lesson": "Impact resources should be reserved so high-energy sections retain contrast.", "scope": "GENERALIZABLE_LESSON", "evidence": "V1 effect-fatigue review"},
            {"lesson": "A resource-rich rig is a training context, not a requirement for a valid design.", "scope": "GENERALIZABLE_LESSON", "evidence": "Framework requirement"},
        ],
        "anti_patterns": [
            {"id": "INTENSITY_ONLY_PROGRESSION", "description": "Raising Dimmer while keeping every other layer identical.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "SAME_GROUP_EVERY_CUE", "description": "Using one Group for all sections despite available alternatives.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "SAME_PRESET_EVERY_CUE", "description": "Missing palette/focus development when verified resources exist.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "EFFECT_FATIGUE", "description": "Repeating one Effect until it no longer marks a meaningful section.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "EFFECT_TOO_EARLY", "description": "Spending a signature motion resource before the first major opening.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "FINAL_EQUALS_ONE_HUNDRED", "description": "Treating Final Chorus escalation as Dimmer 100% only.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
            {"id": "GEOMETRY_IGNORED", "description": "Failing to use verified numeric geometry when it is available.", "evidence": "Current V1 creative review", "scope": "GENERALIZABLE_LESSON"},
        ],
        "future_cases": [
            {"case_id": "CASE_002_MEDIUM_LIVE", "resource_scale": "MEDIUM", "style_orientation": "BAND", "status": "SCHEMA_STUB_ONLY"},
            {"case_id": "CASE_003_SMALL_VENUE", "resource_scale": "SMALL", "style_orientation": "GENERAL", "status": "SCHEMA_STUB_ONLY"},
            {"case_id": "CASE_004_LED_ONLY", "resource_scale": "LIMITED", "style_orientation": "GENERAL", "status": "SCHEMA_STUB_ONLY"},
            {"case_id": "CASE_005_IMPERFECT_RIG", "resource_scale": "MEDIUM", "style_orientation": "GENERAL", "status": "SCHEMA_STUB_ONLY"},
        ],
        "designer_integration": {
            "input": ["ZEN_SHOW_PROFILE", "Training Case design knowledge", "ZEN_SONG_ANALYSIS"],
            "output": "ZEN_SHOW_PLAN",
            "boundary": "Training Case supplies roles, layers, principles, and lessons; Designer emits typed intent; Builder remains the only MA2 command boundary.",
            "status": "INTERFACE_PLANNED_NOT_RUNTIME_WIRED",
        },
        "rig_architecture": [
            {"role": "AERIAL", "purpose": "Create vertical scale and silhouette moments.", "why_this_fixture": "Hybrid/Beam families are plausible case resources, subject to capability evidence.", "expected_looks": ["controlled beam punctuation", "silhouette layer", "reserved chorus lift"], "scope": "CASE_SPECIFIC"},
            {"role": "KEY_LAYER", "purpose": "Keep the performer readable.", "why_this_fixture": "Spot/Hybrid identity suggests a candidate subject layer; exact focus remains a design choice.", "expected_looks": ["restrained verse focus", "solo focus", "chorus subject separation"], "scope": "CASE_SPECIFIC"},
            {"role": "WASH_LAYER", "purpose": "Provide broad environmental coverage.", "why_this_fixture": "Wash/LED PAR Groups are useful candidates, not exclusive roles.", "expected_looks": ["base wash", "color field", "release into outro"], "scope": "CASE_SPECIFIC"},
            {"role": "TEXTURE", "purpose": "Add detail and visual density without consuming every impact resource.", "why_this_fixture": "B-EYE/Hybrid are plausible contextual sources in this training case.", "expected_looks": ["chorus texture", "repeated-section variation", "controlled eye-candy"], "scope": "CASE_SPECIFIC"},
            {"role": "IMPACT", "purpose": "Mark high-value musical accents.", "why_this_fixture": "Strobe is an inferred impact candidate in this case.", "expected_looks": ["chorus punctuation", "final accent", "short hit"], "scope": "CASE_SPECIFIC"},
            {"role": "COLOR_LAYER", "purpose": "Develop palette and contrast.", "why_this_fixture": "LED PAR/Wash/B-EYE can provide candidate color context where verified resources permit.", "expected_looks": ["pre-chorus build", "chorus palette change", "outro release"], "scope": "CASE_SPECIFIC"},
        ],
    }
    return validate_training_case(case)


def designer_context(case: dict[str, Any]) -> dict[str, Any]:
    """Return the command-free subset intended for a future Designer adapter."""
    validated = validate_training_case(case)
    return {"case_id": validated["case_id"], "roles": validated["rig_roles"], "layers": validated["visual_layers"], "principles": validated["design_principles"], "lessons": validated["designer_lessons"], "anti_patterns": validated["anti_patterns"], "status": "KNOWLEDGE_ONLY"}
