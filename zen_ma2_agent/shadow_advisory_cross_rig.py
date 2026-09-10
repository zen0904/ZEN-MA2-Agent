"""Evaluate same-song shadow advisories across explicit synthetic rig contexts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .shadow_advisory_evaluation import evaluate_shadow_case


CROSS_RIG_FIXTURE_SCHEMA = "zen.shadow_advisory_cross_rig_fixture.v0.1"
CROSS_RIG_EVALUATION_SCHEMA = "zen.shadow_advisory_cross_rig_evaluation.v0.1"
RUBRIC = (
    "RESOURCE_PRIORITIZATION", "ROLE_LAYER_SELECTION", "INTENTIONAL_OMISSION",
    "SUBSTITUTION_REASONING", "COMPLETE_LOOK_UNDER_CONSTRAINT", "SONG_INTENT_PRESERVATION",
    "CONTEXT_AWARENESS", "RESOURCE_AWARENESS", "EVIDENCE_TRACEABILITY",
    "NON_FORMULAIC_REASONING", "ACTIONABLE_DESIGN_VALUE",
)


def validate_cross_rig_fixture(value: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "label", "common_song_fixture", "common_song_case_id", "restrained_song_case_id", "rig_context_ids"}
    if not isinstance(value, dict) or value.get("schema") != CROSS_RIG_FIXTURE_SCHEMA or required - set(value):
        raise ValueError("Invalid cross-rig evaluation fixture.")
    if value["label"] != "SYNTHETIC_EVALUATION_ONLY" or len(value["rig_context_ids"]) != 4:
        raise ValueError("Cross-rig evaluation must be explicitly synthetic with four rigs.")
    return deepcopy(value)


def _resource_advisory(result: dict[str, Any]) -> dict[str, Any]:
    return next(item for item in result["advisories"] if item["advisory_id"] == "advisory-resource-adaptation")


def _choices(result: dict[str, Any]) -> list[dict[str, Any]]:
    return _resource_advisory(result).get("resource_choices", [])


def _state_choice(result: dict[str, Any], state: str) -> dict[str, Any]:
    return next(item for item in _choices(result) if item["energy_state"] == state)


def _complete_look(result: dict[str, Any]) -> bool:
    present = {item["energy_state"] for item in _choices(result)}
    if len(present) < 2:
        return False
    choices = {state: _state_choice(result, state) for state in present}
    signatures = {state: (tuple(value["KEEP"]), tuple(value["REDUCE"]), tuple(value["OMIT"]), tuple(item["REPLACEMENT"] for item in value["SUBSTITUTE"])) for state, value in choices.items()}
    return len(set(signatures.values())) == len(present)


def _fixture_language_failures(result: dict[str, Any]) -> list[str]:
    case = result["guidance_context"]["case_context"]
    failures: list[str] = []
    available = set(case.get("available_roles", []))
    for choice in _choices(result):
        for key in ("KEEP", "REDUCE", "OMIT"):
            if not set(choice[key]) <= available:
                failures.append(f"{choice['section_id']}: selected unavailable role in {key}.")
    if case["case_id"] == "RIG_C_LED_ONLY":
        selected = {item for choice in _choices(result) for key in ("KEEP", "REDUCE", "OMIT") for item in choice[key]}
        if any("BEAM" in item or "AERIAL" in item or "GOBO" in item or "MOVER" in item for item in selected):
            failures.append("LED-only rig selected unavailable mover/beam/gobo language.")
    if case["case_id"] == "RIG_D_IMPERFECT_ASYMMETRIC":
        selected = {item for choice in _choices(result) for key in ("KEEP", "REDUCE", "OMIT") for item in choice[key]}
        if any(item in {"MIRROR_PAIR", "SYMMETRIC_TEXTURE", "SYMMETRIC_FULL_RIG"} for item in selected):
            failures.append("Asymmetric rig forced a mirrored/symmetric role.")
    return failures


def _rubric(result: dict[str, Any]) -> dict[str, str]:
    choices = _choices(result)
    substitute = any(choice["SUBSTITUTE"] for choice in choices)
    constrained = result["guidance_context"]["case_context"]["resource_scale"] in {"LIMITED", "SMALL", "MEDIUM"}
    return {
        "RESOURCE_PRIORITIZATION": "STRONG" if all(choice["KEEP"] for choice in choices) else "WEAK",
        "ROLE_LAYER_SELECTION": "STRONG" if all(choice["KEEP"] or choice["SUBSTITUTE"] for choice in choices) else "WEAK",
        "INTENTIONAL_OMISSION": "STRONG" if any(choice["OMIT"] for choice in choices) else "WEAK",
        "SUBSTITUTION_REASONING": "STRONG" if substitute else "ACCEPTABLE" if not constrained else "WEAK",
        "COMPLETE_LOOK_UNDER_CONSTRAINT": "STRONG" if _complete_look(result) else "FAIL",
        "SONG_INTENT_PRESERVATION": "STRONG" if result["baseline_vs_shadow_plan"] == "IDENTICAL" else "FAIL",
        "CONTEXT_AWARENESS": "STRONG" if result["guidance_context"]["case_context"]["scope"] in {"SHADOW_EVALUATION_ONLY", "BOUNDED_CASE_CONTEXT"} else "WEAK",
        "RESOURCE_AWARENESS": "STRONG" if choices else "FAIL",
        "EVIDENCE_TRACEABILITY": "STRONG" if all(choice["REASON"] for choice in choices) else "WEAK",
        "NON_FORMULAIC_REASONING": "STRONG" if result["rubric"]["NON_FORMULAIC_REASONING"] == "STRONG" else "WEAK",
        "ACTIONABLE_DESIGN_VALUE": "STRONG" if any(choice["SUBSTITUTE"] for choice in choices) or any(choice["OMIT"] for choice in choices) else "ACCEPTABLE",
    }


def _evaluate_song_across_rigs(song_case: dict[str, Any], rigs: dict[str, dict[str, Any]], **kwargs: Any) -> list[dict[str, Any]]:
    results = []
    for rig_id, rig in rigs.items():
        item = evaluate_shadow_case(song_case, training_case=rig, **kwargs)
        item["resource_advisory"] = _resource_advisory(item)
        item["cross_rig_rubric"] = _rubric(item)
        item["fixture_language_failures"] = _fixture_language_failures(item)
        results.append(item)
    return results


def evaluate_cross_rig(common_song_case: dict[str, Any], restrained_song_case: dict[str, Any], rigs: dict[str, dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    """Keep song data fixed while changing only explicit case/resource context."""
    common = _evaluate_song_across_rigs(common_song_case, rigs, **kwargs)
    restrained = _evaluate_song_across_rigs(restrained_song_case, {key: rigs[key] for key in ("RIG_A_RESOURCE_RICH_CONTROL", "RIG_B_MEDIUM_LIVE", "RIG_C_LED_ONLY")}, **kwargs)
    maps = [item["energy_map"] for item in common]
    same_song = all(item == maps[0] for item in maps[1:])
    choice_signatures = {
        item["guidance_context"]["case_context"]["case_id"]: tuple((choice["energy_state"], tuple(choice["KEEP"]), tuple(choice["REDUCE"]), tuple(choice["OMIT"]), tuple(entry["REPLACEMENT"] for entry in choice["SUBSTITUTE"])) for choice in _choices(item))
        for item in common
    }
    all_results = common + restrained
    failures = [f"{item['guidance_context']['case_context']['case_id']}: {failure}" for item in all_results for failure in item["fixture_language_failures"] + item["negative_failures"]]
    return {
        "schema": CROSS_RIG_EVALUATION_SCHEMA, "common_song_results": common, "restrained_song_results": restrained,
        "same_song_intent_preserved": same_song, "cross_rig_choice_signatures": choice_signatures,
        "cross_rig_differences": len(set(choice_signatures.values())) > 1,
        "baseline_preservation": "IDENTICAL" if all(item["baseline_vs_shadow_plan"] == "IDENTICAL" for item in all_results) else "NOT_IDENTICAL",
        "failures": failures,
        "readiness": "READY_FOR_HUMAN_CROSS_RIG_REVIEW" if same_song and len(set(choice_signatures.values())) == 4 and not failures else "NEEDS_MORE_SHADOW_WORK",
        "limitation": "Rig contexts are explicit synthetic semantic constraints, not live MA2 inventories or physical geometry. Human review is required before any runtime A/B work.",
    }
