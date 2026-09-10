"""Single-entry, command-free intake and bounded rig-context normalization.

This module deliberately sits *before* shadow guidance.  It never selects MA2
objects, estimates physical coordinates, or converts a visual observation into
a safety-critical fact.  Its job is to preserve what is known, expose what is
unknown, and bypass planning when a user has already confirmed a layout.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


SHOW_INTAKE_SCHEMA = "zen.show_intake.v0.1"
RIG_CONTEXT_SCHEMA = "zen.rig_context.v0.1"
RIG_PROPOSAL_SCHEMA = "zen.rig_proposal.v0.1"

ROUTING_MODES = {"USER_CONFIRMED_LAYOUT", "ASSISTED_RIG_PLANNING", "EXISTING_SHOW"}
FACT_STATES = {"CONFIRMED", "INFERRED", "UNKNOWN"}
MOUNTING = {"FLOOR", "RAISED_APPROVED", "FLOWN_APPROVED", "UNKNOWN"}
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}
_SAFETY_CRITICAL = {"SAFE_TO_HANG_FIXTURES", "RIGGING_CAPACITY", "STRUCTURAL_LOAD", "POWER_CAPACITY", "CERTIFIED_RIGGING_POINTS"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Intake, rig context, and proposals may not contain MA2 command fields.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe(nested)


def _fact(value: dict[str, Any], *, visual: bool = False) -> dict[str, Any]:
    required = {"fact_id", "value", "certainty", "source"}
    if not isinstance(value, dict) or required - set(value):
        raise ValueError("A fact needs fact_id, value, certainty, and source.")
    normalized = deepcopy(value)
    normalized["fact_id"] = str(normalized["fact_id"]).strip().upper()
    normalized["certainty"] = str(normalized["certainty"]).strip().upper()
    if not normalized["fact_id"] or normalized["certainty"] not in FACT_STATES:
        raise ValueError("Fact identity/certainty is invalid.")
    if not str(normalized["source"]).strip():
        raise ValueError("Fact source must be explicit.")
    if visual and normalized["certainty"] == "CONFIRMED":
        raise ValueError("Visual observations are observations, not automatically confirmed facts.")
    if normalized["fact_id"] in _SAFETY_CRITICAL and normalized["certainty"] != "CONFIRMED":
        if normalized["value"] not in {None, "UNKNOWN", False}:
            raise ValueError("Safety-critical capability must remain UNKNOWN/FALSE unless confirmed.")
    return normalized


def _fixture_family(value: dict[str, Any]) -> dict[str, Any]:
    required = {"family", "count", "certainty", "source"}
    if not isinstance(value, dict) or required - set(value):
        raise ValueError("Fixture inventory needs family/count/certainty/source.")
    normalized = deepcopy(value)
    normalized["family"] = str(normalized["family"]).strip().upper()
    if not normalized["family"] or not isinstance(normalized["count"], int) or normalized["count"] < 0:
        raise ValueError("Fixture family/count is invalid.")
    normalized["certainty"] = str(normalized["certainty"]).upper()
    if normalized["certainty"] not in FACT_STATES or not str(normalized["source"]).strip():
        raise ValueError("Fixture inventory provenance is invalid.")
    return normalized


def _placement(value: dict[str, Any], *, user_confirmed: bool) -> dict[str, Any]:
    required = {"fixture_family", "count", "zone", "mounting", "certainty", "source"}
    if not isinstance(value, dict) or required - set(value):
        raise ValueError("Placement needs family/count/zone/mounting/certainty/source.")
    normalized = deepcopy(value)
    normalized["fixture_family"] = str(normalized["fixture_family"]).strip().upper()
    normalized["zone"] = str(normalized["zone"]).strip().upper()
    normalized["mounting"] = str(normalized["mounting"]).strip().upper()
    normalized["certainty"] = str(normalized["certainty"]).strip().upper()
    if not normalized["fixture_family"] or not normalized["zone"] or not isinstance(normalized["count"], int) or normalized["count"] < 0:
        raise ValueError("Placement identity/count is invalid.")
    if normalized["mounting"] not in MOUNTING or normalized["certainty"] not in FACT_STATES:
        raise ValueError("Placement mounting/certainty is invalid.")
    if normalized["mounting"] == "FLOWN_APPROVED" and normalized["certainty"] != "CONFIRMED":
        raise ValueError("Flown placement requires confirmed approval.")
    if user_confirmed and (normalized["certainty"] != "CONFIRMED" or normalized["source"] != "USER_CONFIRMED"):
        raise ValueError("User-confirmed layout placement must remain USER_CONFIRMED/CONFIRMED.")
    return normalized


def validate_show_intake(value: dict[str, Any]) -> dict[str, Any]:
    """Validate one user-facing request without requiring a complete tech pack."""
    required = {"schema", "intake_id", "requested_task", "routing_mode", "fixture_inventory", "facts", "visual_observations", "constraints"}
    if not isinstance(value, dict) or value.get("schema") != SHOW_INTAKE_SCHEMA or required - set(value):
        raise ValueError(f"Intake schema must be {SHOW_INTAKE_SCHEMA} with required fields.")
    normalized = deepcopy(value)
    normalized["routing_mode"] = str(normalized["routing_mode"]).upper()
    if normalized["routing_mode"] not in ROUTING_MODES or not str(normalized["intake_id"]).strip() or not str(normalized["requested_task"]).strip():
        raise ValueError("Intake identity/routing mode is invalid.")
    if not isinstance(normalized["fixture_inventory"], list) or not normalized["fixture_inventory"]:
        raise ValueError("A bounded intake needs at least one declared fixture family.")
    normalized["fixture_inventory"] = [_fixture_family(item) for item in normalized["fixture_inventory"]]
    normalized["facts"] = [_fact(item) for item in normalized["facts"]]
    normalized["constraints"] = [_fact(item) for item in normalized["constraints"]]
    normalized["visual_observations"] = [_fact(item, visual=True) for item in normalized["visual_observations"]]
    layout = normalized.get("user_confirmed_layout") or []
    if not isinstance(layout, list):
        raise ValueError("user_confirmed_layout must be a list when supplied.")
    normalized["user_confirmed_layout"] = [_placement(item, user_confirmed=normalized["routing_mode"] == "USER_CONFIRMED_LAYOUT") for item in layout]
    if normalized["routing_mode"] == "USER_CONFIRMED_LAYOUT" and not normalized["user_confirmed_layout"]:
        raise ValueError("USER_CONFIRMED_LAYOUT requires explicit user-confirmed placement.")
    if normalized["routing_mode"] == "EXISTING_SHOW" and not isinstance(normalized.get("existing_show"), dict):
        raise ValueError("EXISTING_SHOW requires an explicit scanned-show reference.")
    _safe(normalized)
    return normalized


def _facts_by_id(intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["fact_id"]: item for item in [*intake["facts"], *intake["constraints"], *intake["visual_observations"]]}


def _roles(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bounded capability hypotheses; they remain inferred, never physical facts."""
    roles: list[dict[str, Any]] = []
    for item in inventory:
        family = item["family"]
        if "LED" in family:
            candidates = ("COLOR_FIELD", "DENSITY_LAYER", "TIMING_LAYER")
        elif any(token in family for token in ("MOVING", "MOVER", "HEAD")):
            candidates = ("PRIMARY_FOCUS", "MOVER_TEXTURE_LAYER")
        else:
            candidates = ("BROAD_ENVIRONMENT",)
        for role in candidates:
            roles.append({"role": role, "certainty": "INFERRED", "source": "FIXTURE_FAMILY_CAPABILITY", "fixture_family": family, "scope": "CONTEXT_DEPENDENT"})
    deduped: dict[str, dict[str, Any]] = {}
    for item in roles:
        deduped.setdefault(item["role"], item)
    return list(deduped.values())


def _affordances(roles: list[str]) -> dict[str, dict[str, Any]]:
    """Shadow-only resource choices.  They do not choose Groups, presets, or levels."""
    color = "COLOR_FIELD" if "COLOR_FIELD" in roles else None
    focus = "PRIMARY_FOCUS" if "PRIMARY_FOCUS" in roles else None
    timing = "TIMING_LAYER" if "TIMING_LAYER" in roles else None
    texture = "MOVER_TEXTURE_LAYER" if "MOVER_TEXTURE_LAYER" in roles else None
    environment = "BROAD_ENVIRONMENT" if "BROAD_ENVIRONMENT" in roles else None
    low_keep = [item for item in (focus, color, environment) if item][:2] or roles[:1]
    medium_keep = list(dict.fromkeys(low_keep + [item for item in (texture, environment) if item]))
    high_keep = list(dict.fromkeys(medium_keep + [item for item in (timing, color) if item]))
    def choice(keep: list[str], *, reduce: list[str], omit: list[str], substitute: list[dict[str, str]], reason: str) -> dict[str, Any]:
        return {"KEEP": keep, "REDUCE": reduce, "OMIT": omit, "SUBSTITUTE": substitute, "REASON": [reason]}
    low_omit = [item for item in (timing, texture) if item and item not in low_keep]
    medium_reduce = [item for item in (timing, texture) if item and item not in medium_keep]
    substitutions: list[dict[str, str]] = []
    if not texture and color and timing:
        substitutions.append({"UNAVAILABLE": "INDEPENDENT_TEXTURE_LAYER", "REPLACEMENT": "COLOR_AND_TIMING_CONTRAST", "REASON": "Use declared LED-capable contrast rather than inventing mover texture."})
    return {
        "LOW": choice(low_keep, reduce=[item for item in roles if item not in low_keep and item not in low_omit], omit=low_omit, substitute=[], reason="Keep a complete quiet state with deliberate negative space."),
        "MEDIUM": choice(medium_keep, reduce=medium_reduce, omit=[], substitute=substitutions, reason="Develop section identity through available layers without treating every role as mandatory."),
        "HIGH": choice(high_keep, reduce=[], omit=[], substitute=substitutions, reason="Use available density and timing selectively for a context-appropriate peak."),
    }


def _rig_context(*, intake: dict[str, Any], source_mode: str, placement: list[dict[str, Any]], planning_status: str, proposal_ref: str | None, assumptions: list[str], clarification_requirements: list[dict[str, Any]]) -> dict[str, Any]:
    facts = [*intake["facts"], *intake["constraints"], *intake["visual_observations"]]
    roles = _roles(intake["fixture_inventory"])
    available_roles = [item["role"] for item in roles]
    if not available_roles:
        available_roles = ["BROAD_ENVIRONMENT"]
    asymmetry = any(item.get("fact_id") == "ASYMMETRIC_LAYOUT" and item.get("value") is True for item in facts)
    return validate_rig_context({
        "schema": RIG_CONTEXT_SCHEMA, "context_id": f"RIG_CONTEXT_{intake['intake_id']}", "requested_task": intake["requested_task"],
        "source_mode": source_mode, "layout_source": "USER_CONFIRMED" if source_mode == "USER_CONFIRMED_LAYOUT" else "ASSISTED_PROPOSAL" if source_mode == "ASSISTED_RIG_PLANNING" else "EXISTING_SHOW_SCAN",
        "planning_status": planning_status, "fixture_families": intake["fixture_inventory"], "available_roles": roles,
        "placement_semantics": placement, "facts": facts, "assumptions": assumptions, "unknowns": [item for item in facts if item["certainty"] == "UNKNOWN"],
        "constraints": intake["constraints"], "geometry_status": "USER_SEMANTIC_ONLY" if placement else "UNKNOWN", "asymmetry": {"detected": asymmetry, "source": "USER_CONFIRMED" if asymmetry else "NOT_ASSERTED"},
        "design_affordances": _affordances(available_roles), "proposal_ref": proposal_ref,
        "clarification_requirements": clarification_requirements, "scope": "BOUNDED_RIG_CONTEXT", "runtime_mode": "SHADOW_ONLY",
    })


def validate_rig_context(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "context_id", "requested_task", "source_mode", "layout_source", "planning_status", "fixture_families", "available_roles", "placement_semantics", "facts", "assumptions", "unknowns", "constraints", "geometry_status", "asymmetry", "design_affordances", "scope", "runtime_mode"}
    if not isinstance(value, dict) or value.get("schema") != RIG_CONTEXT_SCHEMA or required - set(value):
        raise ValueError(f"Rig context schema must be {RIG_CONTEXT_SCHEMA} with required fields.")
    normalized = deepcopy(value)
    if normalized["source_mode"] not in ROUTING_MODES or normalized["runtime_mode"] != "SHADOW_ONLY":
        raise ValueError("Rig context must retain a valid routing source and shadow-only runtime mode.")
    normalized["fixture_families"] = [_fixture_family(item) for item in normalized["fixture_families"]]
    normalized["placement_semantics"] = [_placement(item, user_confirmed=normalized["source_mode"] == "USER_CONFIRMED_LAYOUT") for item in normalized["placement_semantics"]]
    normalized["facts"] = [_fact(item) for item in normalized["facts"]]
    normalized["constraints"] = [_fact(item) for item in normalized["constraints"]]
    normalized["unknowns"] = [_fact(item) for item in normalized["unknowns"]]
    if any(item["certainty"] != "UNKNOWN" for item in normalized["unknowns"]):
        raise ValueError("Rig-context unknowns must remain explicit UNKNOWN facts.")
    if not isinstance(normalized["available_roles"], list) or not all(isinstance(item, dict) and item.get("certainty") in FACT_STATES for item in normalized["available_roles"]):
        raise ValueError("Rig roles must carry certainty.")
    if not isinstance(normalized["design_affordances"], dict) or set(normalized["design_affordances"]) != {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Rig context needs bounded LOW/MEDIUM/HIGH shadow affordances.")
    declared = {item["role"] for item in normalized["available_roles"]}
    for choice in normalized["design_affordances"].values():
        if not {"KEEP", "REDUCE", "OMIT", "SUBSTITUTE", "REASON"} <= set(choice):
            raise ValueError("Rig affordances need keep/reduce/omit/substitute/reason.")
        if not set(choice["KEEP"] + choice["REDUCE"] + choice["OMIT"]) <= declared:
            raise ValueError("Rig affordances may only use declared roles.")
    _safe(normalized)
    return normalized


def validate_rig_proposal(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "proposal_id", "source_intake_id", "status", "placements", "constraints", "assumptions", "unknowns", "fallback", "confidence", "scope"}
    if not isinstance(value, dict) or value.get("schema") != RIG_PROPOSAL_SCHEMA or required - set(value):
        raise ValueError(f"Rig proposal schema must be {RIG_PROPOSAL_SCHEMA} with required fields.")
    normalized = deepcopy(value)
    normalized["placements"] = [_placement(item, user_confirmed=False) for item in normalized["placements"]]
    normalized["constraints"] = [_fact(item) for item in normalized["constraints"]]
    normalized["unknowns"] = [_fact(item) for item in normalized["unknowns"]]
    if any(item["certainty"] != "UNKNOWN" for item in normalized["unknowns"]):
        raise ValueError("Proposal unknowns must remain UNKNOWN.")
    if any(item["mounting"] == "FLOWN_APPROVED" for item in normalized["placements"]):
        hanging = next((item for item in normalized["constraints"] if item["fact_id"] == "SAFE_TO_HANG_FIXTURES"), None)
        if not hanging or hanging["certainty"] != "CONFIRMED" or hanging["value"] is not True:
            raise ValueError("A rig proposal cannot rely on flown placement without confirmed hanging approval.")
    _safe(normalized)
    return normalized


def _floor_only(intake: dict[str, Any]) -> bool:
    return any(item["fact_id"] == "FLOOR_ONLY" and item["certainty"] == "CONFIRMED" and item["value"] is True for item in intake["constraints"])


def _hanging_confirmed(intake: dict[str, Any]) -> bool:
    return any(item["fact_id"] == "SAFE_TO_HANG_FIXTURES" and item["certainty"] == "CONFIRMED" and item["value"] is True for item in intake["facts"] + intake["constraints"])


def _safe_floor_zone(intake: dict[str, Any]) -> bool:
    facts = _facts_by_id(intake)
    return any(item["fact_id"] in {"FLOOR_ZONE_AVAILABLE", "REAR_FLOOR_ZONE_USABLE", "SIDE_FLOOR_ZONE_USABLE"} and item["value"] is True and item["certainty"] in {"CONFIRMED", "INFERRED"} for item in facts.values())


def _plan_floor_only(intake: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not _floor_only(intake) or not _safe_floor_zone(intake):
        return None, [{"question_id": "CONFIRM_SAFE_FLOOR_ZONE", "question": "Is at least one usable floor zone available for the proposed fixtures?", "reason": "No safe bounded placement fallback exists without a usable floor zone.", "material_impact": "PHYSICAL_FEASIBILITY"}]
    placements = []
    for item in intake["fixture_inventory"]:
        family, count = item["family"], item["count"]
        zone = "FLOOR_REAR_LINE" if "LED" in family else "FLOOR_REAR_CLUSTER"
        placements.append({"fixture_family": family, "count": count, "zone": zone, "mounting": "FLOOR", "certainty": "INFERRED", "source": "ASSISTED_RIG_PLANNING"})
    unknowns = [item for item in [*intake["facts"], *intake["constraints"], *intake["visual_observations"]] if item["certainty"] == "UNKNOWN"]
    proposal = validate_rig_proposal({
        "schema": RIG_PROPOSAL_SCHEMA, "proposal_id": f"RIG_PROPOSAL_{intake['intake_id']}_FLOOR", "source_intake_id": intake["intake_id"], "status": "BOUNDED_PROPOSAL",
        "placements": placements, "constraints": intake["constraints"], "assumptions": ["Floor zones are used only because the intake confirms FLOOR_ONLY and supplies a usable floor-zone observation.", "No flown, raised, electrical, or structural capacity is assumed."],
        "unknowns": unknowns, "fallback": {"name": "REAR_LINE_COMPACT", "description": "If side zones are unavailable, keep every fixture in a compact rear floor line/cluster rather than relying on unconfirmed placement.", "status": "SAFE_BOUNDED_FALLBACK"},
        "confidence": "PARTIAL", "scope": "PROPOSAL_REQUIRES_HUMAN_REVIEW",
    })
    return proposal, []


def route_show_intake(value: dict[str, Any]) -> dict[str, Any]:
    """Route one primary-agent request; returns context/proposal, never commands."""
    intake = validate_show_intake(value)
    if intake["routing_mode"] == "USER_CONFIRMED_LAYOUT":
        needs_hanging_confirmation = any(item["mounting"] == "FLOWN_APPROVED" for item in intake["user_confirmed_layout"]) and not _hanging_confirmed(intake)
        questions = ([{"question_id": "CONFIRM_HANGING_CAPABILITY", "question": "Are the proposed flown fixtures approved for this venue's rigging and load limits?", "reason": "User placement is preserved, but a visible/user-described position is not a safety certification.", "material_impact": "PHYSICAL_FEASIBILITY"}] if needs_hanging_confirmation else [])
        status = "BYPASSED_USER_LAYOUT_SAFETY_CLARIFICATION" if questions else "BYPASSED"
        context = _rig_context(intake=intake, source_mode="USER_CONFIRMED_LAYOUT", placement=intake["user_confirmed_layout"], planning_status=status, proposal_ref=None, assumptions=[], clarification_requirements=questions)
        return {"schema": "zen.show_intake_route.v0.1", "route": "USER_CONFIRMED_LAYOUT", "planner_status": status, "rig_context": context, "rig_proposal": None, "clarification_requirements": questions}
    if intake["routing_mode"] == "EXISTING_SHOW":
        show = intake["existing_show"]
        placement = [_placement(item, user_confirmed=False) for item in show.get("placement_semantics", [])]
        context = _rig_context(intake=intake, source_mode="EXISTING_SHOW", placement=placement, planning_status="BYPASSED_EXISTING_SHOW", proposal_ref=show.get("show_profile_ref"), assumptions=["Existing scanned rig/show context is reused; no physical redesign is performed."], clarification_requirements=[])
        return {"schema": "zen.show_intake_route.v0.1", "route": "EXISTING_SHOW", "planner_status": "BYPASSED_EXISTING_SHOW", "rig_context": context, "rig_proposal": None, "clarification_requirements": []}
    proposal, questions = _plan_floor_only(intake)
    if proposal is None:
        context = _rig_context(intake=intake, source_mode="ASSISTED_RIG_PLANNING", placement=[], planning_status="BLOCKED_TARGETED_CLARIFICATION", proposal_ref=None, assumptions=[], clarification_requirements=questions)
        return {"schema": "zen.show_intake_route.v0.1", "route": "ASSISTED_RIG_PLANNING", "planner_status": "BLOCKED_TARGETED_CLARIFICATION", "rig_context": context, "rig_proposal": None, "clarification_requirements": questions}
    context = _rig_context(intake=intake, source_mode="ASSISTED_RIG_PLANNING", placement=proposal["placements"], planning_status="PROPOSAL_READY", proposal_ref=proposal["proposal_id"], assumptions=proposal["assumptions"], clarification_requirements=[])
    return {"schema": "zen.show_intake_route.v0.1", "route": "ASSISTED_RIG_PLANNING", "planner_status": "PROPOSAL_READY", "rig_context": context, "rig_proposal": proposal, "clarification_requirements": []}
