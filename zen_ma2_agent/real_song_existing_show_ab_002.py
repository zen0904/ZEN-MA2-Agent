"""Case-scoped Existing Show density-cohort A/B experiment; no console path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .guidance_assisted_ab_003_evaluation import evaluate_ab003_case
from .human_design_review import extract_human_review_case
from .rig_intake import route_show_intake, validate_rig_context


REAL_SONG_EXISTING_SHOW_AB002_SCHEMA = "zen.real_song_existing_show_ab_002.v0.1"
CASE_ID = "REAL_SONG_EXISTING_SHOW_AB_002"
APPROVAL_SOURCE = "ZEN_HUMAN_CASE_SPECIFIC_DENSITY_ELIGIBILITY_AB002"


def _approved_density_context(base_fixture: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    if approval.get("schema") != "zen.real_song_existing_show_ab_002_fixture.v0.1":
        raise ValueError("Expected the bounded A/B 002 case approval fixture.")
    if approval.get("approval_scope") != "CASE_SPECIFIC_ELIGIBILITY_ONLY" or approval.get("case_id") != CASE_ID:
        raise ValueError("A/B 002 requires its exact human case-specific eligibility approval.")
    route = route_show_intake(deepcopy(base_fixture["existing_show_intake"]))
    if route.get("route") != "EXISTING_SHOW" or route.get("planner_status") != "BYPASSED_EXISTING_SHOW":
        raise ValueError("Existing Show A/B 002 must reuse the scanned Show and bypass rig planning.")
    profile_groups = {item.get("group_id") for item in base_fixture["show_snapshot"]["profile"].get("groups", [])}
    approved = list(approval.get("approved_density_group_ids") or [])
    if approved != sorted(set(approved)) or set(approved) != profile_groups or 9999 in approved:
        raise ValueError("A/B 002 density approval must contain each and only the scanned Groups 1–7.")
    context = deepcopy(route["rig_context"])
    context["available_roles"] = [
        *context["available_roles"],
        {"role": "DENSITY_LAYER", "certainty": "CONFIRMED", "source": APPROVAL_SOURCE,
         "scope": "CASE_SPECIFIC_ELIGIBILITY_ONLY"},
    ]
    context["role_bindings"] = [
        {
            "role": "DENSITY_LAYER", "target": {"type": "group", "ref": group_id},
            "certainty": "CONFIRMED", "source": APPROVAL_SOURCE,
            "approval_scope": "CASE_SPECIFIC_ELIGIBILITY_ONLY", "approval_case_id": CASE_ID,
            "resource_selection_mode": "CASE_SPECIFIC_DENSITY_COHORT",
        }
        for group_id in approved
    ]
    return validate_rig_context(context)


def _density_cue_cards(result: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for baseline, experimental in zip(result["baseline_plan"]["cues"], result["experimental_plan"]["cues"]):
        design = experimental.get("experimental_design") or {}
        selection = design.get("density_resource_selection") or {}
        selected = [item["target"]["ref"] for item in selection.get("selected", [])]
        unused = [item["target"]["ref"] for item in selection.get("unused", [])]
        dimmers = [
            {"group_id": action.get("target", {}).get("ref"), "level": action.get("level")}
            for action in experimental.get("actions", []) if action.get("operation") == "SET_DIMMER"
        ]
        cards.append({
            "cue_id": experimental.get("id"), "section_instance_id": experimental.get("section_instance_id"),
            "cue_occurrence_index": experimental.get("cue_occurrence_index"), "section_id": experimental.get("source_section_id"),
            "design_intent": deepcopy(design.get("design_intent")), "density_strategy": selection.get("density_strategy"),
            "selected_groups": selected, "intentionally_unused_groups": unused, "dimmer_actions": dimmers,
            "previous_look_comparison": deepcopy(design.get("development", {})),
            "desired_vs_realized_delta": deepcopy(design.get("intent_realizability", {})),
            "actual_action_delta": design.get("intent_realizability", {}).get("actual_action_delta"),
            "actual_plan_delta_vs_baseline": "CHANGED" if baseline.get("actions") != experimental.get("actions") else "UNCHANGED",
            "approval_provenance": APPROVAL_SOURCE, "human_review": design.get("human_review", "UNSET"),
            "baseline_actions": deepcopy(baseline.get("actions", [])), "experimental_actions": deepcopy(experimental.get("actions", [])),
        })
    return cards


def _quality_flags(cards: list[dict[str, Any]], analysis: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    approved = set(range(1, 8))
    if not cards or any(set(card["selected_groups"]) | set(card["intentionally_unused_groups"]) != approved for card in cards):
        flags.append("DENSITY_COHORT_ACCOUNTING_INVALID")
    if not any(card["intentionally_unused_groups"] for card in cards):
        flags.append("NO_INTENTIONAL_GROUP_OMISSION")
    if any(any(action.get("operation") != "SET_DIMMER" for action in card["experimental_actions"]) for card in cards):
        flags.append("UNAPPROVED_ACTION_TYPE_PRESENT")
    if not any(card["actual_action_delta"] == "CHANGED" for card in cards):
        flags.append("NO_EXPRESSIVE_ACTION_DELTA")
    base_cards = [card for card in cards if card["cue_occurrence_index"] == 0]
    group_counts = [len(card["selected_groups"]) for card in base_cards]
    if group_counts == sorted(group_counts) and len(set(group_counts)) > 1:
        flags.append("MONOTONIC_GROUP_COUNT_RISK")
    final = next((card for card in cards if card["section_id"] == "final_chorus" and card["cue_occurrence_index"] == 0), None)
    if final and len(final["selected_groups"]) == 7 and final["dimmer_actions"] and all(item["level"] == 100 for item in final["dimmer_actions"]):
        flags.append("FINAL_COHORT_SATURATION_RISK")
    if any(len(card["selected_groups"]) > 1 and len({item["level"] for item in card["dimmer_actions"]}) == 1 for card in cards):
        flags.append("GROUP_LEVEL_HOMOGENEITY_UNRESOLVED")
    sections = {item["id"]: item for item in analysis.get("sections", [])}
    for card in base_cards:
        development = card["previous_look_comparison"].get("status")
        if development == "MUSICALLY_JUSTIFIED_DELTA" and card["actual_action_delta"] == "UNCHANGED":
            flags.append("UNREALIZED_JUSTIFIED_REPEAT_DELTA")
        if card["section_id"] in sections and card["approval_provenance"] != APPROVAL_SOURCE:
            flags.append("UNTRACEABLE_DENSITY_ACTION")
    return sorted(set(flags))


def evaluate_real_song_existing_show_ab_002(
    base_fixture: dict[str, Any], approval: dict[str, Any], analysis: dict[str, Any], *,
    industry_packs: Iterable[dict[str, Any]], user_evidence: Iterable[dict[str, Any]],
    user_reviews: Iterable[dict[str, Any]], baseline_designer: Any,
) -> dict[str, Any]:
    """Run a deterministic, case-approved B3 candidate without any MA2 I/O."""
    if base_fixture.get("schema") != "zen.real_song_existing_show_ab_fixture.v0.1":
        raise ValueError("A/B 002 must reuse the exact A/B 001 Existing Show snapshot.")
    rig_context = _approved_density_context(base_fixture, approval)
    profile = deepcopy(base_fixture["show_snapshot"]["profile"])
    result = evaluate_ab003_case(
        deepcopy(analysis), profile=profile, rig_context=rig_context, industry_packs=industry_packs,
        user_evidence=user_evidence, user_reviews=user_reviews, baseline_designer=baseline_designer,
    )
    cards = _density_cue_cards({"baseline_plan": result["baseline_plan"], "experimental_plan": result["b3_plan"]})
    flags = _quality_flags(cards, result["analysis"])
    section_ids = [str(item["id"]) for item in result["analysis"]["sections"]]
    review = extract_human_review_case(result, case_id=CASE_ID, section_ids=section_ids)
    return {
        "schema": REAL_SONG_EXISTING_SHOW_AB002_SCHEMA, "case_id": CASE_ID,
        "song_analysis_ref": "examples/REALISTIC_SONG_ANALYSIS.json",
        "show_identity": deepcopy(base_fixture["show_snapshot"]["show_identity"]),
        "existing_show_route": {"route": "EXISTING_SHOW", "planner_status": "BYPASSED_EXISTING_SHOW"},
        "human_approval": deepcopy(approval), "resource_binding_policy": "CASE_SPECIFIC_DENSITY_LAYER_ONLY",
        "baseline_plan": result["baseline_plan"], "experimental_plan": result["b3_plan"],
        "cue_cards": cards, "review": review,
        "quality_flags": flags,
        "recommendation": "NEEDS_REVISION" if flags else "PROMISING",
        "production_default_unchanged": result["production_default_unchanged"],
        "ma2_write_audit": "ZERO_WRITES_BY_DESIGN", "human_review": "UNSET",
    }
