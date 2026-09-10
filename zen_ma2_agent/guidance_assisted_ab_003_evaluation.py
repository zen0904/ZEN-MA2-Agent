"""Local, synthetic B2/B3 comparison helpers for design-intent review."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .design_guidance import build_design_guidance_context
from .guidance_assisted_designer import (
    REASONING_VERSION_B2,
    REASONING_VERSION_B3,
    GuidanceAssistedExperimentalDesigner,
)
from .song_analysis import SongAnalysisAdapter, validate_song_analysis


AB003_EVALUATION_SCHEMA = "zen.guidance_assisted_ab_003_evaluation.v0.1"
QUALITY_CRITERIA = (
    "DESIGN_INTENT_COHERENCE", "WHOLE_SONG_AWARENESS", "PREVIOUS_LOOK_AWARENESS",
    "FUTURE_HEADROOM_AWARENESS", "REPEATED_SECTION_REASONING", "INTENTIONAL_SIMILARITY",
    "TEXTURE_JUDGMENT", "VISUAL_DIMENSION_SELECTION", "COMPLETE_LOOK_REASONING",
    "RESOURCE_AWARENESS", "CONTEXT_AWARENESS", "NON_FORMULAIC_REASONING",
    "EVIDENCE_TRACEABILITY", "HUMAN_DESIGNER_READABILITY",
)


def cue_design_intent_trace(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    """Make B3 rationale inspectable without exposing a programming command."""
    traces = []
    for cue in candidate.get("cues", []):
        experimental = cue.get("experimental_design") or {}
        intent = experimental.get("design_intent") or {}
        basis = experimental.get("selection_basis") or {}
        traces.append({
            "SECTION": cue.get("source_section_id"),
            "KNOWN_SONG_CONTEXT": deepcopy(basis.get("known_song_context", {})),
            "PREVIOUS_VISUAL_STATE": list(basis.get("previous_look_roles", [])),
            "UPCOMING_CONTEXT": deepcopy(basis.get("upcoming_context", {})),
            "DESIGN_INTENT": deepcopy(intent),
            "KEEP": list(experimental.get("selected_roles", [])),
            "CHANGE": deepcopy(experimental.get("development", {})),
            "OMIT": list(experimental.get("omitted_roles", [])),
            "SUBSTITUTE": list(experimental.get("substitutions", [])),
            "INTENTIONALLY_UNCHANGED": experimental.get("development", {}).get("status") == "INTENTIONAL_SIMILARITY",
            "WHY": list(intent.get("rationale", [])),
            "UNKNOWN_UNAVAILABLE_INFORMATION": list(intent.get("unknown_context", [])),
            "TYPED_ACTION_DELTA": "EXPERIMENTAL_TYPED_ACTIONS_ONLY",
            "HUMAN_REVIEW": experimental.get("human_review", "UNSET"),
        })
    return traces


def _quality(candidate: dict[str, Any]) -> dict[str, str]:
    records = [cue.get("experimental_design") or {} for cue in candidate.get("cues", [])]
    intents = [item.get("design_intent") for item in records if item.get("design_intent")]
    repeated = [item.get("development", {}) for item in records if item.get("development", {}).get("previous_same_role_section_id")]
    all_have_context = bool(intents) and all(item.get("unknown_context") for item in intents)
    return {
        "DESIGN_INTENT_COHERENCE": "STRONG" if len(intents) == len(records) else "WEAK",
        "WHOLE_SONG_AWARENESS": "STRONG" if any(item.get("relationship_to_next", "").startswith("PREPARE_FOR_") for item in intents) else "ACCEPTABLE",
        "PREVIOUS_LOOK_AWARENESS": "STRONG" if any(item.get("relationship_to_previous") != "NO_PREVIOUS_LOOK" for item in intents) else "ACCEPTABLE",
        "FUTURE_HEADROOM_AWARENESS": "STRONG" if any(item.get("headroom_intent") == "PRESERVE_FOR_KNOWN_LATER_PEAK" for item in intents) else "ACCEPTABLE",
        "REPEATED_SECTION_REASONING": "STRONG" if repeated else "ACCEPTABLE",
        "INTENTIONAL_SIMILARITY": "STRONG" if any(item.get("status") == "INTENTIONAL_SIMILARITY" for item in repeated) else "ACCEPTABLE",
        "TEXTURE_JUDGMENT": "STRONG" if any((item.get("design_intent") or {}).get("design_dimensions", {}).get("texture") for item in records) else "WEAK",
        "VISUAL_DIMENSION_SELECTION": "STRONG" if all(item.get("selection_basis", {}).get("energy_is_not_a_layer_count") for item in records) else "WEAK",
        "COMPLETE_LOOK_REASONING": "STRONG" if any(item.get("omitted_roles") for item in records) else "ACCEPTABLE",
        "RESOURCE_AWARENESS": "STRONG" if all(item.get("selected_roles") for item in records) else "WEAK",
        "CONTEXT_AWARENESS": "STRONG" if all_have_context else "WEAK",
        "NON_FORMULAIC_REASONING": "STRONG" if all(item.get("selection_basis", {}).get("energy_is_not_a_layer_count") for item in records) else "WEAK",
        "EVIDENCE_TRACEABILITY": "STRONG" if all_have_context else "WEAK",
        "HUMAN_DESIGNER_READABILITY": "STRONG" if all(item.get("human_review") == "UNSET" and item.get("design_intent") for item in records) else "WEAK",
    }


def evaluate_ab003_case(analysis: dict[str, Any], *, profile: dict[str, Any], rig_context: dict[str, Any], industry_packs: Iterable[dict[str, Any]], user_evidence: Iterable[dict[str, Any]], user_reviews: Iterable[dict[str, Any]], baseline_designer: Any) -> dict[str, Any]:
    """Return A, frozen B2 reference and B3 candidate without any live path."""
    analysis = validate_song_analysis(analysis)
    song = SongAnalysisAdapter().to_designer_input(analysis)
    guidance = build_design_guidance_context(analysis, rig_context, industry_packs, user_evidence, user_reviews)
    baseline = baseline_designer.design(deepcopy(song), deepcopy(profile))
    b2 = GuidanceAssistedExperimentalDesigner(baseline_designer, reasoning_version=REASONING_VERSION_B2).design(song, profile, guidance)
    b3 = GuidanceAssistedExperimentalDesigner(baseline_designer, reasoning_version=REASONING_VERSION_B3).design(song, profile, guidance)
    return {
        "schema": AB003_EVALUATION_SCHEMA,
        "analysis": deepcopy(analysis),
        "baseline_plan": baseline, "b2_plan": b2, "b3_plan": b3,
        "b3_trace": cue_design_intent_trace(b3), "quality": _quality(b3),
        "production_default_unchanged": baseline == baseline_designer.design(deepcopy(song), deepcopy(profile)),
        "human_review": "UNSET",
    }
