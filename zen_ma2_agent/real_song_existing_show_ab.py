"""Read-only A/B evaluation using one real song-analysis fixture and a scanned Show snapshot."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .guidance_assisted_ab_003_evaluation import evaluate_ab003_case
from .human_design_review import extract_human_review_case
from .rig_intake import route_show_intake


REAL_SONG_EXISTING_SHOW_AB_SCHEMA = "zen.real_song_existing_show_ab.v0.1"


def evaluate_real_song_existing_show_ab(
    fixture: dict[str, Any], analysis: dict[str, Any], *, industry_packs: Iterable[dict[str, Any]],
    user_evidence: Iterable[dict[str, Any]], user_reviews: Iterable[dict[str, Any]], baseline_designer: Any,
) -> dict[str, Any]:
    """Run A/B-003 with existing Show provenance; never calls a console path."""
    if fixture.get("schema") != "zen.real_song_existing_show_ab_fixture.v0.1":
        raise ValueError("Expected the Real Song + Existing Show A/B 001 fixture.")
    route = route_show_intake(deepcopy(fixture["existing_show_intake"]))
    if route.get("route") != "EXISTING_SHOW" or route.get("planner_status") != "BYPASSED_EXISTING_SHOW":
        raise ValueError("Real Existing Show A/B must reuse the existing Show without rig planning.")
    profile = deepcopy(fixture["show_snapshot"]["profile"])
    result = evaluate_ab003_case(
        deepcopy(analysis), profile=profile, rig_context=route["rig_context"], industry_packs=industry_packs,
        user_evidence=user_evidence, user_reviews=user_reviews, baseline_designer=baseline_designer,
    )
    section_ids = [str(item["id"]) for item in result["analysis"]["sections"]]
    review = extract_human_review_case(result, case_id="REAL_SONG_EXISTING_SHOW_AB_001", section_ids=section_ids)
    unrealized = [
        {"cue_id": cue["id"], "section_instance_id": cue.get("section_instance_id"), "status": design["intent_realizability"]["status"], "reason": design["intent_realizability"]["reason"]}
        for cue in result["b3_plan"]["cues"]
        if (design := cue.get("experimental_design")) and design.get("intent_realizability", {}).get("status") != "REALIZED"
    ]
    return {
        "schema": REAL_SONG_EXISTING_SHOW_AB_SCHEMA,
        "fixture_label": fixture["label"], "song_analysis_ref": fixture["song_analysis_ref"],
        "show_identity": deepcopy(fixture["show_snapshot"]["show_identity"]),
        "existing_show_route": route, "resource_binding_policy": deepcopy(fixture["resource_binding_policy"]),
        "baseline_plan": result["baseline_plan"], "experimental_plan": result["b3_plan"],
        "review": review, "unrealized_intents": unrealized,
        "production_default_unchanged": result["production_default_unchanged"],
        "ma2_write_audit": "ZERO_WRITES_BY_DESIGN",
        "human_review": "UNSET",
    }
