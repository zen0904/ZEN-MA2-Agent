"""Shadow-only design guidance composed around the deterministic Designer.

This module is deliberately outside the Designer/Builder execution path.  It
collects typed, attributable evidence and emits advisory records only; the
actual ``ZEN_SHOW_PLAN`` returned by a Designer is preserved verbatim.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Callable, Iterable

from .training_case import validate_training_case
from .user_style import validate_evidence, validate_review
from .song_analysis import validate_song_analysis


GUIDANCE_CONTEXT_SCHEMA = "zen.design_guidance_context.v0.1"
ADVISORY_SCHEMA = "zen.design_advisory.v0.1"
SHADOW_RESULT_SCHEMA = "zen.design_guidance_shadow_result.v0.1"

SOURCE_CATEGORIES = {"SONG", "CASE", "INDUSTRY", "USER_STYLE", "MULTI_SOURCE"}
CONFLICT_OUTCOMES = {
    "ALIGN", "PARTIAL_ALIGN", "PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE",
    "CONTEXT_OVERRIDES_STYLE", "RESOURCE_LIMITATION", "UNRESOLVED",
}
_FORBIDDEN_KEYS = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}

# These statements remain explicit *non-rules*.  They are retained separately
# from reviewed candidates so a consumer cannot reinterpret absence as approval.
NON_GLOBAL_INTERPRETATIONS = (
    "MINIMALISM_EQUALS_LOW_PREFERENCE",
    "KPOP_YG_EQUALS_GLOBAL_STYLE_RULE",
)


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN_KEYS & set(value):
            raise ValueError("Design guidance may not contain MA2 command fields.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _safe(nested)


def _candidate_name(review: dict[str, Any]) -> str:
    identifier = str(review.get("candidate_id") or "")
    return identifier.removeprefix("candidate_")


@dataclass(frozen=True)
class DesignGuidanceContext:
    """Typed, provenance-preserving advisory input; never a style profile."""

    song_signals: tuple[dict[str, Any], ...]
    case_context: dict[str, Any]
    industry_evidence: tuple[dict[str, Any], ...]
    active_user_style: tuple[dict[str, Any], ...]
    context_dependent_user_style: tuple[dict[str, Any], ...]
    rejected_interpretations: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]
    schema: str = GUIDANCE_CONTEXT_SCHEMA
    runtime_mode: str = "SHADOW_ONLY"

    def __post_init__(self) -> None:
        if self.schema != GUIDANCE_CONTEXT_SCHEMA or self.runtime_mode != "SHADOW_ONLY":
            raise ValueError("Guidance context is shadow-only and schema-bound.")
        _safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("song_signals", "industry_evidence", "active_user_style", "context_dependent_user_style", "rejected_interpretations", "limitations"):
            value[key] = list(value[key])
        return value


@dataclass(frozen=True)
class DesignAdvisory:
    advisory_id: str
    recommendation: str
    rationale: str
    source_categories: tuple[str, ...]
    evidence_references: tuple[str, ...]
    human_review_status: str
    industry_review_status: str
    song_signal_references: tuple[str, ...]
    case_references: tuple[str, ...]
    confidence: str
    scope: str
    limitations: tuple[str, ...]
    conflicts: tuple[dict[str, Any], ...]
    unresolved_conditions: tuple[str, ...]
    future_actionability_status: str = "SHADOW_ONLY_REVIEW_REQUIRED"
    schema: str = ADVISORY_SCHEMA
    user_style_signal_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.advisory_id or not self.recommendation:
            raise ValueError("An advisory requires identity and recommendation.")
        if self.schema != ADVISORY_SCHEMA or not set(self.source_categories) <= SOURCE_CATEGORIES:
            raise ValueError("Invalid advisory schema or source category.")
        if any(item.get("outcome") not in CONFLICT_OUTCOMES for item in self.conflicts):
            raise ValueError("Invalid structured conflict outcome.")
        _safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("source_categories", "evidence_references", "song_signal_references", "case_references", "limitations", "conflicts", "unresolved_conditions", "user_style_signal_names"):
            value[key] = list(value[key])
        return value


def _song_signals(song_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep structural, rhythmic and dynamic facts distinct rather than MUSIC_SYNC."""
    signals: list[dict[str, Any]] = []
    sections = list(song_analysis.get("sections") or [])
    occurrences: dict[str, int] = {}
    previous_energy: float | None = None
    for index, section in enumerate(sections, start=1):
        section_id = str(section.get("id") or f"section_{index}")
        role = str(section.get("role") or "UNKNOWN").upper()
        occurrences[role] = occurrences.get(role, 0) + 1
        signals.append({"signal_id": f"song:section:{section_id}", "kind": "SECTION_STRUCTURE", "section_id": section_id, "role": role, "index": index, "energy": section.get("energy"), "density": section.get("density"), "source": "SONG_ANALYSIS"})
        energy = section.get("energy")
        if isinstance(energy, (int, float)) and previous_energy is not None and energy != previous_energy:
            signals.append({"signal_id": f"song:dynamic:{section_id}", "kind": "DYNAMIC_CONTOUR", "section_id": section_id, "direction": "RISE" if energy > previous_energy else "FALL", "from_energy": previous_energy, "to_energy": energy, "source": "SONG_ANALYSIS"})
        if isinstance(energy, (int, float)):
            previous_energy = float(energy)
        if role in {"BUILD", "PRE_CHORUS", "BREAK", "OUTRO", "DROP"}:
            signals.append({"signal_id": f"song:transition:{section_id}", "kind": "BUILDUP_RELEASE", "section_id": section_id, "role": role, "source": "SONG_ANALYSIS"})
    for role, count in sorted(occurrences.items()):
        if count > 1:
            signals.append({"signal_id": f"song:repeat:{role}", "kind": "REPEATED_SECTION_DEVELOPMENT", "role": role, "occurrences": count, "source": "SONG_ANALYSIS"})
    for index, event in enumerate(song_analysis.get("events") or [], start=1):
        event_type = str(event.get("type") or "").upper()
        signals.append({"signal_id": f"song:event:{index}", "kind": "RHYTHMIC_ACCENT" if event_type in {"ACCENT", "HIT"} else "BUILDUP_RELEASE", "event_type": event_type, "section_id": event.get("section_id"), "strength": event.get("strength"), "source": "SONG_ANALYSIS"})
    return signals


def _case_context(case: dict[str, Any]) -> dict[str, Any]:
    case = validate_training_case(case)
    return {
        "case_id": case["case_id"], "case_type": case["case_type"], "resource_scale": case["resource_scale"],
        "style_orientation": case["style_orientation"], "fixture_group_roles": [
            {"group_id": item.get("group_id"), "name": item.get("name"), "role_assignment": deepcopy(item.get("role_assignment", {}))}
            for item in case["fixture_groups"]
        ],
        "visual_layers": deepcopy(case["visual_layers"]), "constraints": deepcopy(case["constraints"]),
        "verified_resources": deepcopy(case["verified_resources"]), "assumptions": deepcopy(case["assumptions"]),
        "confidence": case["confidence"], "geometry_status": case["verified_resources"].get("geometry"),
        "source": "TRAINING_CASE", "scope": "BOUNDED_CASE_CONTEXT",
    }


def _industry_records(packs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for pack in packs:
        for item in pack.get("observations", []):
            review = str(item.get("review_status") or "HUMAN_REVIEW_REQUIRED")
            records.append({
                "evidence_id": item.get("observation_id"), "pack_id": pack.get("pack_id"), "source_id": item.get("source_id"),
                "category": item.get("category"), "observation": item.get("observation"), "scope": item.get("scope"),
                "confidence": item.get("confidence"), "reliability": item.get("confidence"), "stance": item.get("stance", "SUPPORTS"),
                "review_status": review, "eligible_for_shadow_advisory": review == "ACCEPTED", "limitations": item.get("limitations", ""),
                "source_bias": next((source.get("selection_bias", source.get("notes", "")) for source in pack.get("sources", []) if source.get("source_id") == item.get("source_id")), ""),
            })
    return records


def build_design_guidance_context(song_analysis: dict[str, Any], training_case: dict[str, Any], industry_packs: Iterable[dict[str, Any]], user_evidence: Iterable[dict[str, Any]], user_reviews: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Build a read-only context.  Review decisions, not AI candidates, gate style."""
    song_analysis = validate_song_analysis(song_analysis)
    evidence_by_id = {item["evidence_id"]: validate_evidence(item) for item in user_evidence}
    reviews = [validate_review(item) for item in user_reviews]
    active, contextual, rejected = [], [], []
    for review in reviews:
        unknown_evidence = sorted(set(review["evidence_ids"]) - set(evidence_by_id))
        if unknown_evidence:
            raise ValueError(f"Human style review references unknown evidence: {', '.join(unknown_evidence)}")
        name = _candidate_name(review)
        record = {
            "candidate_id": review["candidate_id"], "name": name, "decision": review["decision"], "priority": review["priority"],
            "evidence_ids": list(review["evidence_ids"]), "evidence_provenance": [evidence_by_id[item]["provenance"] for item in review["evidence_ids"] if item in evidence_by_id],
            "scope": review["scope"], "rationale": review["rationale"], "limitations": review["limitations"], "reviewer": review["reviewer"], "reviewed_at": review["reviewed_at"],
        }
        if review["decision"] in {"ACCEPT", "ACCEPT_WITH_LIMITATION"}:
            record["active_in_shadow_guidance"] = True
            active.append(record)
        elif review["decision"] in {"NEEDS_MORE_EVIDENCE", "UNSET", "UNSURE"}:
            record["active_in_shadow_guidance"] = False
            contextual.append(record)
        elif review["decision"] == "REJECT":
            rejected.append(record)
    rejected.extend({"name": name, "decision": "NON_GLOBAL_CONCLUSION", "active_in_shadow_guidance": False, "scope": "STYLE_DIRECTION_LABEL_ONLY"} for name in NON_GLOBAL_INTERPRETATIONS)
    context = DesignGuidanceContext(
        song_signals=tuple(_song_signals(song_analysis)), case_context=_case_context(training_case),
        industry_evidence=tuple(_industry_records(industry_packs)), active_user_style=tuple(active),
        context_dependent_user_style=tuple(contextual), rejected_interpretations=tuple(rejected),
        limitations=(
            "Guidance is advisory only and does not alter Designer output.",
            "Human acceptance is eligible for future consideration, not a runtime rule or ZEN_STYLE_PROFILE trait.",
            "Industry observations retain review state and source limitations.",
        ),
    )
    return context.to_dict()


def _style(context: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in context["active_user_style"] if item["name"] == name), None)


def _energy_bands(context: dict[str, Any]) -> dict[str, list[str]]:
    bands = {"LOW": [], "MEDIUM": [], "HIGH": []}
    for item in context["song_signals"]:
        if item["kind"] != "SECTION_STRUCTURE" or not isinstance(item.get("energy"), (int, float)):
            continue
        label = f"{item['section_id']} ({item['role']})"
        bands["LOW" if item["energy"] <= 0.35 else "MEDIUM" if item["energy"] <= 0.70 else "HIGH"].append(label)
    return bands


def _signal_ids(context: dict[str, Any], *kinds: str) -> tuple[str, ...]:
    return tuple(item["signal_id"] for item in context["song_signals"] if item["kind"] in set(kinds))


def _conflicts(context: dict[str, Any]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    if context["case_context"]["resource_scale"] in {"LIMITED", "SMALL"}:
        conflicts.append({"outcome": "RESOURCE_LIMITATION", "between": ["CASE", "USER_STYLE"], "detail": "Available visual layers may constrain a preferred complete-look distinction."})
    if context["case_context"].get("geometry_status") not in {"SUPPORTED", "REAL_MACHINE_VERIFIED"}:
        conflicts.append({"outcome": "CONTEXT_OVERRIDES_STYLE", "between": ["CASE", "USER_STYLE"], "detail": "Geometry-specific choices remain unavailable or unverified for this case."})
    if any(item["review_status"] != "ACCEPTED" for item in context["industry_evidence"]):
        conflicts.append({"outcome": "PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE", "between": ["INDUSTRY", "USER_STYLE"], "detail": "Industry observations remain valid evidence with independent human-review status."})
    return conflicts or [{"outcome": "ALIGN", "between": ["SONG", "CASE", "USER_STYLE"], "detail": "No conflict detected in the bounded advisory context."}]


def generate_shadow_advisories(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate abstract recommendations; no cue/action/resource mutation exists here."""
    _safe(context)
    if context.get("schema") != GUIDANCE_CONTEXT_SCHEMA or context.get("runtime_mode") != "SHADOW_ONLY":
        raise ValueError("Only a shadow guidance context can produce advisory output.")
    conflicts = tuple(_conflicts(context))
    advisories: list[DesignAdvisory] = []
    bands = _energy_bands(context)
    structure_ids = _signal_ids(context, "SECTION_STRUCTURE")
    dynamic_ids = _signal_ids(context, "DYNAMIC_CONTOUR")
    rhythm_ids = _signal_ids(context, "RHYTHMIC_ACCENT")
    transition_ids = _signal_ids(context, "BUILDUP_RELEASE")
    repeated_ids = _signal_ids(context, "REPEATED_SECTION_DEVELOPMENT")
    complete = _style(context, "EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK")
    if complete:
        low = ", ".join(bands["LOW"]) or "no measured low-energy section"
        high = ", ".join(bands["HIGH"]) or "no measured high-energy section"
        advisories.append(DesignAdvisory(
            "advisory-complete-energy-states",
            f"Treat low-energy sections [{low}] and high-energy sections [{high}] as distinct complete visual states, not one look at different Dimmer levels.",
            "The human-confirmed high-priority preference calls for distinct complete visual states; the specific section and dynamic evidence identifies where those states are needed.",
            ("SONG", "CASE", "USER_STYLE"), tuple(complete["evidence_ids"]), "ACCEPT", "HUMAN_REVIEW_REQUIRED",
            structure_ids + dynamic_ids,
            (context["case_context"]["case_id"],), "HIGH", "CONTEXT_AWARE_ADVISORY", tuple([complete["limitations"]] if complete["limitations"] else []), conflicts,
            ("No typed action, fixture selection, preset, effect, level, fade, or timing is generated.",),
            user_style_signal_names=("EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK", "MULTI_LEVEL_ENERGY_DESIGN", "INTENTIONAL_RESTRAINT"),
        ))
    arc = _style(context, "PROGRESSIVE_ENERGY_ARC")
    if arc:
        advisories.append(DesignAdvisory(
            "advisory-whole-song-arc",
            "Review the whole-song energy journey for coherent development, while allowing rise, reset, plateau, delayed peak, or multiple peaks.",
            "Human review confirms a coherent arc but explicitly rejects a fixed A-to-B-to-C formula.",
            ("SONG", "USER_STYLE"), tuple(arc["evidence_ids"]), "ACCEPT", "NOT_APPLICABLE",
            dynamic_ids + repeated_ids + transition_ids, (), "HIGH", "CONTEXT_AWARE_ADVISORY", tuple([arc["limitations"]] if arc["limitations"] else []), (),
            ("This is not a prescribed energy curve.",),
            user_style_signal_names=("PROGRESSIVE_ENERGY_ARC", "MUSIC_STRUCTURE_ALIGNMENT", "DYNAMIC_CONTOUR_TRACKING"),
        ))
    hierarchy = _style(context, "CLEAN_VISUAL_HIERARCHY")
    palette = _style(context, "PALETTE_COHERENCE")
    if hierarchy and palette:
        advisories.append(DesignAdvisory(
            "advisory-section-identity-and-hierarchy",
            "For the identified section map, preserve a readable focal hierarchy and coherent palette logic while varying the visual composition only where song and case context justify it.",
            "Human-confirmed hierarchy and palette preferences apply across the song, but neither requires monochrome-only color nor a forced large section delta.",
            ("SONG", "CASE", "USER_STYLE"), tuple(hierarchy["evidence_ids"] + palette["evidence_ids"]), "ACCEPT", "HUMAN_REVIEW_REQUIRED",
            structure_ids, (context["case_context"]["case_id"],), "HIGH", "CONTEXT_AWARE_ADVISORY",
            tuple(filter(None, (palette["limitations"], "Dominant-theme color remains context-dependent and is not a requirement."))), (),
            ("No palette values or fixture resources are selected by this advisory.",),
            user_style_signal_names=("CLEAN_VISUAL_HIERARCHY", "PALETTE_COHERENCE", "MUSIC_STRUCTURE_ALIGNMENT"),
        ))
    if rhythm_ids:
        impact = _style(context, "CONTROLLED_HIGH_IMPACT")
        if impact:
            advisories.append(DesignAdvisory(
                "advisory-rhythmic-punctuation",
                "Use the identified accent/hit events as candidates for intentional punctuation; do not treat every event as a mandatory maximum-impact moment.",
                "Rhythmic alignment is human-confirmed, while high impact remains explicitly bounded by musical and resource context.",
                ("SONG", "USER_STYLE"), tuple(impact["evidence_ids"]), "ACCEPT_WITH_LIMITATION", "NOT_APPLICABLE",
                rhythm_ids, (), "MEDIUM", "EVENT_CONTEXT_ADVISORY", tuple([impact["limitations"]]), (),
                ("STRONG_TRANSIENT_IMPACT remains context-dependent and is not promoted.",),
                user_style_signal_names=("RHYTHMIC_ACCENT_SYNC", "CONTROLLED_HIGH_IMPACT"),
            ))
    if repeated_ids:
        advisories.append(DesignAdvisory(
            "advisory-repeated-section-development",
            "Develop repeated sections through an intentional relationship to their earlier occurrence; do not assume either an exact copy or automatic escalation.",
            "Repeated-section identity is preserved as a song fact, while the accepted whole-song arc remains non-formulaic.",
            ("SONG", "USER_STYLE"), tuple(arc["evidence_ids"] if arc else ()), "ACCEPT" if arc else "NOT_APPLICABLE", "NOT_APPLICABLE",
            repeated_ids, (), "MEDIUM", "CONTEXT_AWARE_ADVISORY", (), (),
            ("HIGH_SECTION_DELTA remains context-dependent and is not required.",),
            user_style_signal_names=("PROGRESSIVE_ENERGY_ARC", "MUSIC_STRUCTURE_ALIGNMENT"),
        ))
    advisories.append(DesignAdvisory(
        "advisory-professional-evidence-boundary",
        "Treat professional observations as context-bounded alternatives, not as automatic global rules or a replacement for human style review.",
        "Industry evidence retains source bias, scope, reliability, and independent review state.",
        ("INDUSTRY", "USER_STYLE"), tuple(item["evidence_id"] for item in context["industry_evidence"]), "MIXED", "HUMAN_REVIEW_REQUIRED", (), (context["case_context"]["case_id"],), "MEDIUM", "EVIDENCE_TRACE", (),
        tuple(item for item in conflicts if item["outcome"] == "PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE"),
        ("Professional validity and user preference remain independently represented.",),
        user_style_signal_names=(),
    ))
    return [item.to_dict() for item in advisories]


def run_shadow_designer(designer: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | Any, song_input: dict[str, Any], profile: dict[str, Any], guidance_context: dict[str, Any]) -> dict[str, Any]:
    """Run the unchanged Designer and return a separate shadow advisory envelope."""
    callable_design = designer.design if hasattr(designer, "design") else designer
    plan = callable_design(deepcopy(song_input), deepcopy(profile))
    return {
        "schema": SHADOW_RESULT_SCHEMA,
        "runtime_mode": "SHADOW_ONLY",
        "actual_show_plan": plan,
        "advisories": generate_shadow_advisories(guidance_context),
        "guidance_context_schema": guidance_context["schema"],
        "designer_runtime_guidance_activation": "NOT_RUN",
    }
