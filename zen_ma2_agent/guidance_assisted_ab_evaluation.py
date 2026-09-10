"""Local evaluation helpers for the opt-in Guidance-Assisted Designer A/B path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .design_guidance import build_design_guidance_context
from .guidance_assisted_designer import GuidanceAssistedExperimentalDesigner, GUIDANCE_ASSISTED_MODE, REASONING_VERSION_B2
from .song_analysis import SongAnalysisAdapter, validate_song_analysis


AB_EVALUATION_SCHEMA = "zen.guidance_assisted_ab_evaluation.v0.1"
AB_FIXTURE_SCHEMA = "zen.guidance_assisted_ab_fixture.v0.1"
RUBRIC = (
    "MUSICAL_STRUCTURE_ALIGNMENT", "ENERGY_ARC_COHERENCE", "COMPLETE_LOOK_QUALITY",
    "VISUAL_HIERARCHY", "PALETTE_COHERENCE", "RESTRAINT_IMPACT_JUDGMENT",
    "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_USAGE", "CONTEXT_FIT",
    "NON_FORMULAIC_DESIGN", "DESIGN_SPECIFICITY", "LIVE_USABILITY",
)


def validate_ab_fixture(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "label", "cases"}
    if not isinstance(value, dict) or value.get("schema") != AB_FIXTURE_SCHEMA or required - set(value):
        raise ValueError("Invalid A/B evaluation fixture.")
    if value["label"] != "SYNTHETIC_EVALUATION_ONLY" or not isinstance(value["cases"], list) or len(value["cases"]) < 4:
        raise ValueError("A/B evaluation fixture needs at least four synthetic cases.")
    return deepcopy(value)


def _actions(cue: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple((item.get("operation"), item.get("target", {}).get("type"), item.get("target", {}).get("ref"), item.get("preset_ref"), item.get("level"), item.get("effect_requirement_id")) for item in cue.get("actions", []))


def _cue_review(baseline: dict[str, Any], assisted: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    by_id = {item["id"]: item for item in assisted["cues"]}
    for cue in baseline["cues"]:
        other = by_id[cue["id"]]
        experimental = other.get("experimental_design") or {}
        changed = _actions(cue) != _actions(other)
        result.append({
            "cue_id": cue["id"], "section": cue.get("label"), "source_section_id": cue.get("source_section_id"), "role": cue.get("role"),
            "baseline_actions": _actions(cue), "assisted_actions": _actions(other), "delta": "CHANGED" if changed else "UNCHANGED",
            "selected_roles": list(experimental.get("selected_roles", [])), "omitted_roles": list(experimental.get("omitted_roles", [])),
            "reduced_roles": list(experimental.get("reduced_roles", [])), "substitutions": list(experimental.get("substitutions", [])),
            "why": list(experimental.get("evidence_references", [])), "human_review": "UNSET",
        })
    return result


def _energy_states(analysis: dict[str, Any], plan: dict[str, Any]) -> dict[str, set[tuple[Any, ...]]]:
    section_energy = {item["id"]: item.get("energy") for item in analysis["sections"]}
    result = {"LOW": set(), "MEDIUM": set(), "HIGH": set()}
    for cue in plan["cues"]:
        energy = section_energy.get(cue.get("source_section_id"))
        state = "LOW" if not isinstance(energy, (int, float)) or energy <= 0.35 else "MEDIUM" if energy <= 0.70 else "HIGH"
        experimental = cue.get("experimental_design") or {}
        signature = (tuple(experimental.get("selected_roles", [])), tuple(experimental.get("omitted_roles", [])), tuple(experimental.get("reduced_roles", [])), _actions(cue))
        result[state].add(signature)
    return result


def _rubric(plan: dict[str, Any], analysis: dict[str, Any], *, experimental: bool) -> dict[str, str]:
    states = _energy_states(analysis, plan)
    active = [state for state, signatures in states.items() if signatures]
    complete = len(active) >= 2 and len({signature for state in active for signature in states[state]}) > 1
    records = [cue.get("experimental_design") for cue in plan["cues"] if cue.get("experimental_design")]
    roles = {role for item in records for role in item.get("selected_roles", [])}
    omissions = any(item.get("omitted_roles") for item in records)
    substitutions = any(item.get("substitutions") for item in records)
    repeats = len({cue.get("role") for cue in plan["cues"]}) < len(plan["cues"])
    return {
        "MUSICAL_STRUCTURE_ALIGNMENT": "STRONG" if all(cue.get("source_section_id") for cue in plan["cues"]) else "WEAK",
        "ENERGY_ARC_COHERENCE": "STRONG" if len(active) >= 2 else "ACCEPTABLE",
        "COMPLETE_LOOK_QUALITY": "STRONG" if experimental and complete else "ACCEPTABLE" if complete else "WEAK",
        "VISUAL_HIERARCHY": "STRONG" if experimental and roles else "ACCEPTABLE",
        "PALETTE_COHERENCE": "STRONG" if experimental and any("COLOR" in role for role in roles) else "ACCEPTABLE",
        "RESTRAINT_IMPACT_JUDGMENT": "STRONG" if experimental and omissions else "ACCEPTABLE",
        "REPEATED_SECTION_DEVELOPMENT": "STRONG" if repeats and experimental else "ACCEPTABLE" if repeats else "WEAK",
        "RESOURCE_USAGE": "STRONG" if experimental and roles else "WEAK",
        "CONTEXT_FIT": "STRONG" if experimental and records else "ACCEPTABLE",
        "NON_FORMULAIC_DESIGN": "STRONG" if experimental and omissions and len(roles) > 1 else "ACCEPTABLE",
        "DESIGN_SPECIFICITY": "STRONG" if experimental and records else "WEAK",
        "LIVE_USABILITY": "ACCEPTABLE",  # action syntax is still canonical typed intent, never a live build claim.
    }


def _result_state(baseline: dict[str, Any], assisted: dict[str, Any], rig_context: dict[str, Any], baseline_rubric: dict[str, str], assisted_rubric: dict[str, str]) -> str:
    changed = bool(assisted.get("designer", {}).get("changed_typed_actions"))
    if not changed:
        return "NO_MEANINGFUL_DIFFERENCE"
    if rig_context.get("asymmetry", {}).get("detected"):
        return "MIXED"  # Intent is preserved, but no physical/aesthetic asymmetry judgement exists yet.
    gains = sum(assisted_rubric[key] == "STRONG" and baseline_rubric[key] != "STRONG" for key in RUBRIC)
    return "B_BETTER" if gains >= 3 else "MIXED"


def evaluate_ab_case(case: dict[str, Any], *, profile: dict[str, Any], rig_context: dict[str, Any], industry_packs: Iterable[dict[str, Any]], user_evidence: Iterable[dict[str, Any]], user_reviews: Iterable[dict[str, Any]], baseline_designer: Any, experimental_designer: GuidanceAssistedExperimentalDesigner | None = None) -> dict[str, Any]:
    analysis = validate_song_analysis(case["analysis"])
    song_input = SongAnalysisAdapter().to_designer_input(analysis)
    baseline = baseline_designer.design(deepcopy(song_input), deepcopy(profile))
    guidance = build_design_guidance_context(analysis, rig_context, industry_packs, user_evidence, user_reviews)
    assisted = (experimental_designer or GuidanceAssistedExperimentalDesigner(baseline_designer, reasoning_version=REASONING_VERSION_B2)).design(song_input, profile, guidance)
    baseline_rubric, assisted_rubric = _rubric(baseline, analysis, experimental=False), _rubric(assisted, analysis, experimental=True)
    return {
        "case_id": case["case_id"], "name": case["name"], "schema": AB_EVALUATION_SCHEMA,
        "baseline_plan": baseline, "guidance_assisted_plan": assisted, "guidance_context": guidance,
        "cue_by_cue_review": _cue_review(baseline, assisted), "baseline_rubric": baseline_rubric, "assisted_rubric": assisted_rubric,
        "result": _result_state(baseline, assisted, rig_context, baseline_rubric, assisted_rubric),
        "production_default_unchanged": baseline == baseline_designer.design(deepcopy(song_input), deepcopy(profile)),
        "experimental_mode": assisted["designer"].get("mode"), "context_dependent_active": [item["name"] for item in guidance["active_user_style"] if item["name"] in {"DOMINANT_THEME_COLOR", "STRONG_TRANSIENT_IMPACT", "HIGH_SECTION_DELTA", "RESTRAINT_BETWEEN_PEAKS", "CONTROLLED_BUILDUP", "GEOMETRIC_COMPOSITION"}],
        "rejected_active": [item["name"] for item in guidance["active_user_style"] if item["name"] in {"HIGH_IMPACT_ALWAYS", "MAXIMALISM_EQUALS_CLUTTER", "MULTICOLOR_EQUALS_BAD", "MINIMALISM_EQUALS_LOW_PREFERENCE", "KPOP_YG_EQUALS_GLOBAL_STYLE_RULE"}],
    }
