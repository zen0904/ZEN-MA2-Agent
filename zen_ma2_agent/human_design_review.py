"""Presentation-only extraction for human review of actual B3 candidates."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


HUMAN_DESIGN_REVIEW_SCHEMA = "zen.human_design_review.v0.1"
AUDIENCE_PERCEPTION_CLASSES = {"SUPPORTED_BY_INPUT", "BOUNDED_INFERENCE", "TOO_SPECULATIVE"}


def _action_summary(cue: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "operation": action.get("operation"), "target": deepcopy(action.get("target")),
        "preset_ref": action.get("preset_ref"), "preset_type": action.get("preset_type"),
        "effect_requirement_id": action.get("effect_requirement_id"), "level": action.get("level"),
    } for action in cue.get("actions", [])]


def _card_for_trace(trace: dict[str, Any], *, baseline: dict[str, Any], b2: dict[str, Any], b3: dict[str, Any], audience_class: str, energy: Any = "NOT_AVAILABLE") -> dict[str, Any]:
    section_id = trace["SECTION"]
    def cue(plan: dict[str, Any]) -> dict[str, Any]:
        cue_id = trace.get("CUE_ID")
        if cue_id:
            match = next((item for item in plan.get("cues", []) if item.get("id") == cue_id), None)
            if match is not None:
                return match
        instance_id = trace.get("SECTION_INSTANCE_ID")
        if instance_id:
            match = next((item for item in plan.get("cues", []) if item.get("section_instance_id") == instance_id and item.get("cue_occurrence_index", 0) == trace.get("CUE_OCCURRENCE_INDEX", 0)), None)
            if match is not None:
                return match
        return next(item for item in plan.get("cues", []) if item.get("source_section_id") == section_id)
    if audience_class not in AUDIENCE_PERCEPTION_CLASSES:
        raise ValueError("Unknown audience-perception review class.")
    card = deepcopy(trace)
    card.update({
        "schema": HUMAN_DESIGN_REVIEW_SCHEMA,
        "CASE": None,
        "ENERGY": energy,
        "AUDIENCE_PERCEPTION_CLASS": audience_class,
        "A_PRODUCTION_BASELINE": _action_summary(cue(baseline)),
        "B2_AB002": _action_summary(cue(b2)),
        "B3_AB003": _action_summary(cue(b3)),
        "HUMAN_REVIEW_QUESTIONS": [
            "Does the WHY make sense?",
            "Would a real lighting designer plausibly make this KEEP/CHANGE/OMIT choice?",
            "Does the relationship with the previous look make sense?",
            "Should repeated material stay similar, develop, change differently, or remain unknown?",
            "Are the selected/omitted roles reasonable?",
            "Does this feel HUMAN_LIKE, ACCEPTABLE_BUT_MECHANICAL, TOO_FORMULAIC, WRONG, or NEED_REAL_SONG_CONTEXT?",
        ],
        "HUMAN_REVIEW": "UNSET",
    })
    return card


def extract_human_review_case(result: dict[str, Any], *, case_id: str, section_ids: list[str], audience_classes: dict[str, str] | None = None) -> dict[str, Any]:
    """Extract cards from evaluator output; never synthesize a design result."""
    if result.get("schema") != "zen.guidance_assisted_ab_003_evaluation.v0.1":
        raise ValueError("Expected an actual A/B-003 evaluation result.")
    traces = list(result.get("b3_trace", []))
    analysis_sections = {item["id"]: item for item in result.get("analysis", {}).get("sections", [])}
    audience_classes = audience_classes or {}
    cards = []
    for section_id in section_ids:
        matching = [item for item in traces if item["SECTION"] == section_id]
        if not matching:
            raise ValueError(f"B3 trace does not contain requested section {section_id}.")
        for trace in matching:
            card = _card_for_trace(trace, baseline=result["baseline_plan"], b2=result["b2_plan"], b3=result["b3_plan"], audience_class=audience_classes.get(section_id, "BOUNDED_INFERENCE"), energy=analysis_sections.get(section_id, {}).get("energy", "NOT_AVAILABLE"))
            known_context = card.get("KNOWN_SONG_CONTEXT") or {}
            known_context["energy"] = card["ENERGY"]
            card["KNOWN_SONG_CONTEXT"] = known_context
            card["CASE"] = case_id
            cards.append(card)
    return {
        "schema": HUMAN_DESIGN_REVIEW_SCHEMA, "case_id": case_id, "cards": cards,
        "production_default_unchanged": result.get("production_default_unchanged") is True,
        "human_review": "UNSET",
    }
