"""Deterministic, local-only quality evaluation for shadow design advisories."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .design_guidance import build_design_guidance_context, run_shadow_designer
from .song_analysis import SongAnalysisAdapter, validate_song_analysis


EVALUATION_SCHEMA = "zen.shadow_advisory_evaluation.v0.1"
FIXTURE_SCHEMA = "zen.shadow_advisory_evaluation_fixture.v0.1"
RUBRIC_DIMENSIONS = (
    "MUSICAL_STRUCTURE_UNDERSTANDING", "ENERGY_ARC_COHERENCE", "COMPLETE_LOOK_REASONING",
    "VISUAL_HIERARCHY_REASONING", "PALETTE_REASONING", "RESTRAINT_AND_IMPACT_JUDGMENT",
    "REPEATED_SECTION_DEVELOPMENT", "CONTEXT_AWARENESS", "RESOURCE_AWARENESS",
    "EVIDENCE_TRACEABILITY", "CONFLICT_HANDLING", "NON_FORMULAIC_REASONING",
    "ACTIONABLE_DESIGN_VALUE",
)
FORBIDDEN_INTERPRETATIONS = (
    "HIGH_IMPACT_ALWAYS", "MAXIMALISM_EQUALS_CLUTTER", "MULTICOLOR_EQUALS_BAD",
    "MINIMALISM_EQUALS_LOW_PREFERENCE", "KPOP_YG_EQUALS_GLOBAL_STYLE_RULE",
)


def validate_evaluation_fixture(document: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("schema") != FIXTURE_SCHEMA:
        raise ValueError(f"Evaluation fixture schema must be {FIXTURE_SCHEMA}.")
    if document.get("label") != "SYNTHETIC_EVALUATION_ONLY" or not isinstance(document.get("cases"), list):
        raise ValueError("Evaluation fixtures must be explicitly synthetic and case-based.")
    result = deepcopy(document)
    ids: set[str] = set()
    for item in result["cases"]:
        if item.get("synthetic_label") != "SYNTHETIC_EVALUATION_ONLY" or not item.get("case_id") or item["case_id"] in ids:
            raise ValueError("Each synthetic evaluation case needs a unique explicit label.")
        ids.add(item["case_id"])
        item["analysis"] = validate_song_analysis(item["analysis"])
    return result


def _energy_map(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for section in analysis["sections"]:
        energy = section.get("energy")
        band = "UNKNOWN" if energy is None else "LOW" if energy <= 0.35 else "MEDIUM" if energy <= 0.70 else "HIGH"
        result.append({"section_id": section["id"], "role": section["role"], "energy": energy, "band": band})
    return result


def _references(advisories: Iterable[dict[str, Any]]) -> set[str]:
    return {reference for item in advisories for reference in item.get("evidence_references", [])}


def _relevant_style(context: dict[str, Any], advisories: Iterable[dict[str, Any]]) -> tuple[list[str], list[str]]:
    signals = {name for item in advisories for name in item.get("user_style_signal_names", [])}
    active = context["active_user_style"]
    relevant = [item["name"] for item in active if item["name"] in signals]
    unused = [item["name"] for item in active if item["name"] not in relevant]
    unused.extend(item["name"] for item in context["context_dependent_user_style"])
    return sorted(set(relevant)), sorted(set(unused))


def _specific_section_provenance(advisories: Iterable[dict[str, Any]], analysis: dict[str, Any]) -> bool:
    section_ids = {item["id"] for item in analysis["sections"]}
    for advisory in advisories:
        refs = advisory.get("song_signal_references", [])
        if refs and any(f"song:section:{section_id}" in refs for section_id in section_ids):
            return True
    return False


def _negative_failures(context: dict[str, Any], advisories: Iterable[dict[str, Any]], analysis: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    active = {item["name"] for item in context["active_user_style"]}
    rejected = {item["name"] for item in context["rejected_interpretations"]}
    contextual = {item["name"] for item in context["context_dependent_user_style"]}
    if active & set(FORBIDDEN_INTERPRETATIONS):
        failures.append("Rejected interpretation entered active shadow guidance.")
    if not set(FORBIDDEN_INTERPRETATIONS) <= rejected:
        failures.append("A rejected/non-global interpretation was not preserved.")
    if {"DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "CONTROLLED_BUILDUP", "GEOMETRIC_COMPOSITION"} & active:
        failures.append("A context-dependent candidate entered active shadow guidance.")
    if not {"DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "CONTROLLED_BUILDUP", "GEOMETRIC_COMPOSITION"} <= contextual:
        failures.append("A context-dependent candidate was not retained as context-dependent.")
    recommendation_text = " ".join(item["recommendation"] for item in advisories).casefold()
    prohibited_phrases = (
        "always use maximum impact", "every event is a mandatory maximum-impact moment",
        "every chorus must be larger", "every buildup must add", "every drop must use maximum impact",
        "dominant theme color is required", "geometry is required",
    )
    if any(phrase in recommendation_text for phrase in prohibited_phrases):
        failures.append("Advisory used a prohibited universal/maximum formulation.")
    if not _specific_section_provenance(advisories, analysis):
        failures.append("Generic prose failure: advisory lacks section-specific provenance.")
    return failures


def _rubric(context: dict[str, Any], advisories: list[dict[str, Any]], analysis: dict[str, Any], failures: list[str]) -> dict[str, str]:
    ids = {item["advisory_id"] for item in advisories}
    kinds = {item["kind"] for item in context["song_signals"]}
    has_repeated = "REPEATED_SECTION_DEVELOPMENT" in kinds
    has_events = "RHYTHMIC_ACCENT" in kinds
    generic = any("Generic prose" in item for item in failures)
    return {
        "MUSICAL_STRUCTURE_UNDERSTANDING": "STRONG" if "advisory-complete-energy-states" in ids and "SECTION_STRUCTURE" in kinds else "FAIL",
        "ENERGY_ARC_COHERENCE": "STRONG" if "advisory-whole-song-arc" in ids and "DYNAMIC_CONTOUR" in kinds else "WEAK",
        "COMPLETE_LOOK_REASONING": "STRONG" if "advisory-complete-energy-states" in ids else "FAIL",
        "VISUAL_HIERARCHY_REASONING": "STRONG" if "advisory-section-identity-and-hierarchy" in ids else "WEAK",
        "PALETTE_REASONING": "STRONG" if "advisory-section-identity-and-hierarchy" in ids else "WEAK",
        "RESTRAINT_AND_IMPACT_JUDGMENT": "STRONG" if not has_events or "advisory-rhythmic-punctuation" in ids else "WEAK",
        "REPEATED_SECTION_DEVELOPMENT": "STRONG" if not has_repeated or "advisory-repeated-section-development" in ids else "WEAK",
        "CONTEXT_AWARENESS": "STRONG" if context["case_context"].get("case_id") else "FAIL",
        "RESOURCE_AWARENESS": "ACCEPTABLE" if context["case_context"].get("geometry_status") else "WEAK",
        "EVIDENCE_TRACEABILITY": "STRONG" if all(item.get("evidence_references") is not None for item in advisories) else "FAIL",
        "CONFLICT_HANDLING": "STRONG" if any(item.get("conflicts") for item in advisories) else "WEAK",
        "NON_FORMULAIC_REASONING": "STRONG" if "advisory-whole-song-arc" in ids else "WEAK",
        "ACTIONABLE_DESIGN_VALUE": "WEAK" if generic else "ACCEPTABLE",
    }


def evaluate_shadow_case(case: dict[str, Any], *, designer: Any, profile: dict[str, Any], training_case: dict[str, Any], industry_packs: Iterable[dict[str, Any]], user_evidence: Iterable[dict[str, Any]], user_reviews: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Run baseline + shadow without mutating the Designer, plan, or external state."""
    analysis = validate_song_analysis(case["analysis"])
    designer_input = SongAnalysisAdapter().to_designer_input(analysis)
    baseline = designer.design(deepcopy(designer_input), deepcopy(profile))
    context = build_design_guidance_context(analysis, training_case, industry_packs, user_evidence, user_reviews)
    shadow = run_shadow_designer(designer, designer_input, profile, context)
    advisories = shadow["advisories"]
    failures = _negative_failures(context, advisories, analysis)
    relevant, unused = _relevant_style(context, advisories)
    return {
        "case_id": case["case_id"], "name": case["name"], "synthetic_label": case.get("synthetic_label"),
        "energy_map": _energy_map(analysis), "advisories": advisories, "guidance_context": context,
        "relevant_user_style": relevant, "intentionally_unused_or_contextual_style": unused,
        "baseline_vs_shadow_plan": "IDENTICAL" if baseline == shadow["actual_show_plan"] else "NOT_IDENTICAL",
        "negative_failures": failures, "rubric": _rubric(context, advisories, analysis, failures),
        "resource_constraints": [item for advisory in advisories for item in advisory.get("conflicts", []) if item.get("outcome") in {"RESOURCE_LIMITATION", "CONTEXT_OVERRIDES_STYLE"}],
    }


def evaluate_fixture(document: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    fixture = validate_evaluation_fixture(document)
    results = [evaluate_shadow_case(item, **kwargs) for item in fixture["cases"]]
    return {
        "schema": EVALUATION_SCHEMA, "label": fixture["label"], "cases": results,
        "baseline_preservation": "IDENTICAL" if all(item["baseline_vs_shadow_plan"] == "IDENTICAL" for item in results) else "NOT_IDENTICAL",
        "negative_failures": [f"{item['case_id']}: {failure}" for item in results for failure in item["negative_failures"]],
        "readiness": "NEEDS_MORE_SHADOW_WORK",
        "limitation": "Advisories are deterministic, traceable review material but remain broad design intentions; human comparison across real show/rig contexts is still required before any A/B runtime experiment.",
    }
