"""Evidence-bound industry reference pack models.

The pack is intentionally inert: it stores short, source-linked observations
for human review and never emits MA2 commands or changes Designer behaviour.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


SOURCE_SCHEMA = "zen.industry_reference_source.v0.1"
PACK_SCHEMA = "zen.industry_reference_pack.v0.1"
OBSERVATION_SCHEMA = "zen.industry_reference_observation.v0.1"

SOURCE_TYPES = {
    "DESIGNER_INTERVIEW", "PRODUCTION_BREAKDOWN", "MANUFACTURER_CASE_STUDY",
    "CONFERENCE_PRESENTATION", "TRADE_PRESS_INTERVIEW", "TECHNICAL_ARTICLE",
}
DOMAINS = {"LARGE_CONCERT", "BAND_LIVE", "THEATRE_NARRATIVE", "SMALL_PRODUCTION", "GENERAL"}
RIG_SCALES = {"LIMITED", "SMALL", "MEDIUM", "LARGE", "RESOURCE_RICH", "UNKNOWN"}
RELIABILITY = {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
EVIDENCE_TYPES = {"DIRECT_SOURCE_STATEMENT", "VISUAL_INFERENCE", "MODEL_INTERPRETATION"}
REVIEW_STATUSES = {"UNREVIEWED", "AI_EXTRACTED", "HUMAN_REVIEW_REQUIRED", "ACCEPTED", "REJECTED", "NEEDS_CONTEXT"}
SCOPES = {"GLOBAL_CANDIDATE", "DOMAIN", "CASE", "SOURCE_CONTEXT"}
OBSERVATION_CATEGORIES = {
    "SECTION_CONTRAST", "LAYER_ESCALATION", "FOCUS_HIERARCHY", "IMPACT_RESERVATION",
    "COLOR_DEVELOPMENT", "MOVEMENT_USAGE", "EFFECT_DENSITY", "REPEATED_SECTION_VARIATION",
    "VISUAL_REST", "FINAL_RELEASE", "SPATIAL_DEPTH", "RESOURCE_LIMITATION", "ASYMMETRY_HANDLING",
}
_FORBIDDEN_KEYS = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "script", "cue_sheet", "plot", "transcript", "quote"}


def _walk_safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN_KEYS & set(value):
            raise ValueError("Industry references may contain derived observations only.")
        for nested in value.values():
            _walk_safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_safe(nested)


@dataclass(frozen=True)
class IndustryReferenceSource:
    source_id: str
    title: str
    url: str
    publisher: str
    publication_date: str | None
    designer: str | None
    production: str
    domain: str
    rig_scale: str
    source_type: str
    reliability: str
    copyright_policy: str = "DERIVED_OBSERVATIONS_ONLY"
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.title.strip() or not self.url.startswith(("https://", "http://")):
            raise ValueError("Source identity, title and URL are required.")
        if self.domain not in DOMAINS or self.rig_scale not in RIG_SCALES:
            raise ValueError("Invalid source domain or rig scale.")
        if self.source_type not in SOURCE_TYPES or self.reliability not in RELIABILITY:
            raise ValueError("Invalid source type or reliability.")
        if self.copyright_policy != "DERIVED_OBSERVATIONS_ONLY":
            raise ValueError("Only derived-observation copyright policy is supported.")
        _walk_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SOURCE_SCHEMA, **asdict(self)}


@dataclass(frozen=True)
class DerivedObservation:
    observation_id: str
    source_id: str
    domain: str
    category: str
    observation: str
    evidence_type: str
    confidence: str
    scope: str
    applicability: str
    limitations: str
    context: Any = ""
    teaching_note: str = ""
    principle_refs: tuple[str, ...] = ()
    anti_pattern_refs: tuple[str, ...] = ()
    stance: str = "SUPPORTS"
    review_status: str = "HUMAN_REVIEW_REQUIRED"

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.source_id.strip() or not self.observation.strip():
            raise ValueError("Observation identity and text are required.")
        if self.domain not in DOMAINS or self.category not in OBSERVATION_CATEGORIES:
            raise ValueError("Invalid observation domain or category.")
        if self.evidence_type not in EVIDENCE_TYPES or self.confidence not in RELIABILITY:
            raise ValueError("Invalid observation evidence type or confidence.")
        if self.scope not in SCOPES or self.review_status not in REVIEW_STATUSES:
            raise ValueError("Invalid observation scope or review status.")
        if self.stance not in {"SUPPORTS", "CAUTIONS", "CONTRADICTS", "CONTEXT_DEPENDENT"}:
            raise ValueError("Invalid observation stance.")
        if len(self.observation) > 600 or len(self.teaching_note) > 600:
            raise ValueError("Observations must be short derived notes, not copied source text.")
        _walk_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["principle_refs"] = list(self.principle_refs)
        value["anti_pattern_refs"] = list(self.anti_pattern_refs)
        return {"schema": OBSERVATION_SCHEMA, **value}


def validate_source(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"Source schema must be {SOURCE_SCHEMA}.")
    fields = set(IndustryReferenceSource.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Source is missing: {', '.join(sorted(missing))}")
    return IndustryReferenceSource(**{key: value[key] for key in fields}).to_dict()


def validate_observation(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != OBSERVATION_SCHEMA:
        raise ValueError(f"Observation schema must be {OBSERVATION_SCHEMA}.")
    fields = set(DerivedObservation.__dataclass_fields__)
    optional = {"context", "teaching_note", "principle_refs", "anti_pattern_refs", "stance", "review_status"}
    missing = fields - optional - set(value)
    if missing:
        raise ValueError(f"Observation is missing: {', '.join(sorted(missing))}")
    payload = {key: value[key] for key in fields if key in value}
    payload.setdefault("context", "")
    payload.setdefault("teaching_note", "")
    payload.setdefault("principle_refs", ())
    payload.setdefault("anti_pattern_refs", ())
    payload.setdefault("stance", "SUPPORTS")
    payload.setdefault("review_status", "HUMAN_REVIEW_REQUIRED")
    payload["principle_refs"] = tuple(payload["principle_refs"])
    payload["anti_pattern_refs"] = tuple(payload["anti_pattern_refs"])
    return DerivedObservation(**payload).to_dict()


def build_pack(sources: Iterable[dict[str, Any]], observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    source_list = [validate_source(item) for item in sources]
    observation_list = [validate_observation(item) for item in observations]
    ids = {item["source_id"] for item in source_list}
    if len(ids) != len(source_list):
        raise ValueError("Source IDs must be unique.")
    if any(item["source_id"] not in ids for item in observation_list):
        raise ValueError("Every observation must reference a known source.")
    return {"schema": PACK_SCHEMA, "pack_id": "INDUSTRY_REFERENCE_PACK_001", "sources": source_list, "observations": observation_list}


def cross_analyze(pack: dict[str, Any], principles: Iterable[str] = (), anti_patterns: Iterable[str] = ()) -> dict[str, Any]:
    """Return deterministic counts while preserving contradictory stances."""
    observations = pack.get("observations", [])
    categories: dict[str, list[dict[str, Any]]] = {}
    for item in observations:
        categories.setdefault(item["category"], []).append(item)
    repeated = []
    domain_specific = []
    for category, records in sorted(categories.items()):
        domains = sorted({record["domain"] for record in records})
        sources = sorted({record["source_id"] for record in records})
        entry = {"category": category, "source_count": len(sources), "domains": domains, "observation_count": len(records)}
        (repeated if len(domains) >= 2 else domain_specific).append(entry)
    conflicts = []
    for category, records in sorted(categories.items()):
        stances = {record["stance"] for record in records}
        if "SUPPORTS" in stances and ("CONTRADICTS" in stances or "CONTEXT_DEPENDENT" in stances):
            conflicts.append({"category": category, "stances": sorted(stances), "source_ids": sorted({r["source_id"] for r in records})})

    def validate_claims(names: Iterable[str], field: str, *, anti_pattern: bool = False) -> list[dict[str, Any]]:
        result = []
        for name in names:
            records = [r for r in observations if name in r.get(field, [])]
            domains = {r["domain"] for r in records}
            support = [r for r in records if r["stance"] == "SUPPORTS"]
            contradiction = [r for r in records if r["stance"] == "CONTRADICTS"]
            contextual = [r for r in records if r["stance"] == "CONTEXT_DEPENDENT"]
            if contradiction and support:
                status = "MIXED"
            elif contradiction:
                status = "CONTRADICTED_IN_CONTEXT"
            elif contextual and not support:
                status = "CONTEXT_DEPENDENT"
            elif len({r["source_id"] for r in support}) >= 2 and len(domains) >= 2:
                status = "EXTERNALLY_SUPPORTED"
            elif support:
                status = "PARTIALLY_SUPPORTED"
            else:
                status = "NO_EVIDENCE_YET"
            if anti_pattern:
                status = {"EXTERNALLY_SUPPORTED": "SUPPORTED", "PARTIALLY_SUPPORTED": "PARTIAL", "MIXED": "CONTEXT_DEPENDENT", "CONTRADICTED_IN_CONTEXT": "CONTEXT_DEPENDENT", "CONTEXT_DEPENDENT": "CONTEXT_DEPENDENT", "NO_EVIDENCE_YET": "NO_EVIDENCE"}[status]
            result.append({"name": name, "status": status, "source_ids": sorted({r["source_id"] for r in records}), "domains": sorted(domains)})
        return result

    return {"repeated_cross_domain": repeated, "domain_specific": domain_specific, "conflicts": conflicts, "principles": validate_claims(principles, "principle_refs"), "anti_patterns": validate_claims(anti_patterns, "anti_pattern_refs", anti_pattern=True), "global_promotions": []}
