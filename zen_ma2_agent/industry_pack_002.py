"""Evidence-bound contemporary mainstream reference pack (Pack 002).

This module is deliberately inert.  It extends the Pack 001 evidence model
with visual-language and time-window metadata while keeping every inference
reviewable and outside the Designer runtime.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from .industry_references import (
    DOMAINS,
    EVIDENCE_TYPES,
    RELIABILITY,
    SCOPES,
    SOURCE_SCHEMA,
    SOURCE_TYPES,
    validate_source,
)

PACK002_SCHEMA = "zen.industry_reference_pack.v0.2"
PRIOR_SCHEMA = "zen.contemporary_mainstream_prior.v0.1"
VISUAL_LANGUAGES = {
    "CLEAN_MINIMAL", "CONTROLLED_MAXIMAL", "HIGH_IMPACT", "CAMERA_FIRST",
    "GEOMETRIC", "TEXTURAL", "COLOR_DRIVEN", "AERIAL_DRIVEN", "HYBRID", "UNKNOWN",
}
PACK002_CATEGORIES = {
    "SECTION_CONTRAST", "LAYER_ESCALATION", "FOCUS_HIERARCHY", "IMPACT_RESERVATION",
    "COLOR_DEVELOPMENT", "MOVEMENT_USAGE", "EFFECT_DENSITY", "REPEATED_SECTION_VARIATION",
    "VISUAL_REST", "FINAL_RELEASE", "SPATIAL_DEPTH", "RESOURCE_LIMITATION", "ASYMMETRY_HANDLING",
    "TRANSIENT_IMPACT", "BUILDUP_RESTRAINT", "IMPACT_RELEASE", "POST_IMPACT_RESET",
    "CONTROLLED_MAXIMALISM", "VISUAL_CLUTTER", "PALETTE_DISCIPLINE", "CAMERA_READABILITY",
}
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "script", "quote", "transcript"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Industry packs contain observations, not commands or copied source text.")
        for item in value.values():
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)


def _time_window(value: str) -> tuple[int, int]:
    try:
        start, end = (int(part.strip()) for part in value.split("-", 1))
    except Exception as exc:
        raise ValueError("time_window must be YYYY-YYYY") from exc
    if start < 2000 or end < start or end > 2100:
        raise ValueError("invalid time_window")
    return start, end


def normalize_visual_languages(values: Iterable[str]) -> list[str]:
    result = []
    for value in values:
        token = str(value).strip().upper()
        if token not in VISUAL_LANGUAGES:
            raise ValueError(f"Unknown visual language: {value}")
        if token not in result:
            result.append(token)
    return result or ["UNKNOWN"]


def classify_visual_language(values: Iterable[str]) -> list[str]:
    """Normalize an explicit, evidence-bound classification; never infer from a title."""
    return normalize_visual_languages(values)


def validate_source_002(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Pack 002 source must be an object")
    base = dict(value)
    base["schema"] = SOURCE_SCHEMA
    normalized = validate_source(base)
    required = {"time_window", "visual_language", "visual_reference", "selection_bias"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"Pack 002 source is missing: {', '.join(sorted(missing))}")
    _time_window(str(value["time_window"]))
    normalized.update({
        "time_window": str(value["time_window"]),
        "visual_language": normalize_visual_languages(value["visual_language"]),
        "visual_reference": str(value["visual_reference"]),
        "selection_bias": str(value["selection_bias"]),
    })
    if normalized["visual_reference"] not in {"OFFICIAL_PHOTO", "OFFICIAL_VIDEO", "TRADE_PHOTO", "NONE"}:
        raise ValueError("invalid visual_reference")
    _safe(normalized)
    return normalized


def validate_observation_002(value: dict[str, Any]) -> dict[str, Any]:
    required = {"observation_id", "source_id", "domain", "category", "observation", "evidence_type", "confidence", "scope", "applicability", "limitations", "teaching_note"}
    missing = required - set(value)
    if missing:
        raise ValueError(f"Pack 002 observation is missing: {', '.join(sorted(missing))}")
    if value["domain"] not in DOMAINS or value["category"] not in PACK002_CATEGORIES:
        raise ValueError("invalid Pack 002 observation domain/category")
    if value["evidence_type"] not in EVIDENCE_TYPES or value["confidence"] not in RELIABILITY:
        raise ValueError("invalid Pack 002 evidence type/confidence")
    if value["scope"] not in SCOPES:
        raise ValueError("invalid Pack 002 scope")
    if not str(value["observation"]).strip() or len(str(value["observation"])) > 600:
        raise ValueError("observation must be concise")
    result = dict(value)
    result["visual_language"] = normalize_visual_languages(value.get("visual_language", ["UNKNOWN"]))
    result.setdefault("stance", "SUPPORTS")
    result.setdefault("review_status", "HUMAN_REVIEW_REQUIRED")
    _safe(result)
    return result


@dataclass(frozen=True)
class ContemporaryMainstreamPrior:
    domain: str
    time_window: str
    evidence_count: int
    visual_language: tuple[str, ...]
    confidence: str
    source_diversity: int

    def __post_init__(self) -> None:
        if self.domain not in DOMAINS or self.confidence not in RELIABILITY:
            raise ValueError("invalid contemporary prior")
        _time_window(self.time_window)
        if self.evidence_count < 0 or self.source_diversity < 0:
            raise ValueError("prior counts cannot be negative")
        normalize_visual_languages(self.visual_language)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["visual_language"] = list(self.visual_language)
        return {"schema": PRIOR_SCHEMA, **data}


def build_prior(sources: Iterable[dict[str, Any]], observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    source_list = list(sources)
    obs_list = list(observations)
    years = [_time_window(s["time_window"]) for s in source_list]
    start, end = min(item[0] for item in years), max(item[1] for item in years)
    language_counts = Counter(lang for item in source_list for lang in item["visual_language"] if lang != "UNKNOWN")
    languages = tuple(sorted(language_counts)) or ("UNKNOWN",)
    confidence = "MEDIUM" if len(source_list) >= 6 and len({s["publisher"] for s in source_list}) >= 3 else "LOW"
    return ContemporaryMainstreamPrior("LARGE_CONCERT", f"{start}-{end}", len(obs_list), languages, confidence, len({s["publisher"] for s in source_list})).to_dict()


def build_pack_002(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("pack_id") != "INDUSTRY_REFERENCE_PACK_002":
        raise ValueError("Pack 002 id required")
    sources = [validate_source_002(item) for item in raw.get("sources", [])]
    observations = [validate_observation_002(item) for item in raw.get("observations", [])]
    ids = {s["source_id"] for s in sources}
    if len(ids) != len(sources) or any(o["source_id"] not in ids for o in observations):
        raise ValueError("Pack 002 source references must be unique and resolvable")
    prior = raw.get("contemporary_prior") or build_prior(sources, observations)
    if prior.get("schema") != PRIOR_SCHEMA:
        raise ValueError("invalid contemporary prior schema")
    candidate = raw.get("style_candidate", {})
    if candidate.get("promoted", False):
        raise ValueError("Pack 002 cannot promote a ZEN style profile")
    _safe(raw)
    return {
        "schema": PACK002_SCHEMA,
        "pack_id": "INDUSTRY_REFERENCE_PACK_002",
        "theme": "CONTEMPORARY_MAINSTREAM_POP_KPOP",
        "sources": sources,
        "observations": observations,
        "contemporary_prior": prior,
        "style_candidate": candidate,
        "runtime_wiring": "NOT_RUN",
        "global_promotions": [],
    }


def style_alignment(pack: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Compare a candidate preference without creating or mutating a style profile."""
    linked = [o for o in pack.get("observations", []) if o.get("teaching_note") and candidate.get("theme", "").lower() in o.get("teaching_note", "").lower()]
    requested = candidate.get("signals", [])
    alignments = []
    for signal in requested:
        matches = [o for o in pack.get("observations", []) if signal in o.get("principle_refs", []) or signal in o.get("anti_pattern_refs", [])]
        status = "ALIGN" if len({o["source_id"] for o in matches}) >= 2 else "PARTIALLY_ALIGN" if matches else "UNKNOWN"
        alignments.append({"signal": signal, "status": status, "source_ids": sorted({o["source_id"] for o in matches})})
    return {"candidate": candidate.get("name", "unnamed"), "alignments": alignments, "promoted": False, "linked_context_count": len(linked), "review_required": True}


def compare_packs(pack001: dict[str, Any], pack002: dict[str, Any]) -> dict[str, Any]:
    categories_1 = Counter(o.get("category") for o in pack001.get("observations", []))
    categories_2 = Counter(o.get("category") for o in pack002.get("observations", []))
    return {"pack001_sources": len(pack001.get("sources", [])), "pack002_sources": len(pack002.get("sources", [])), "pack001_categories": dict(categories_1), "pack002_categories": dict(categories_2), "new_categories": sorted(set(categories_2) - set(categories_1)), "global_promotions": []}
