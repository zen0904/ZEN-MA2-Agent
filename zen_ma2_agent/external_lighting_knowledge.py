"""Copyright-safe, provenance-bearing external lighting knowledge.

This module is deliberately inert.  It normalizes small, derived principles
from external sources for review and shadow critique; it does not alter either
Designer path, emit console commands, or promote a source into production
truth.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


SOURCE_SCHEMA = "zen.external_lighting_knowledge_source.v0.1"
SOURCE_REGISTRY_SCHEMA = "zen.external_lighting_knowledge_source_registry.v0.1"
RECORD_SCHEMA = "zen.external_lighting_knowledge_record.v0.1"
PACK_SCHEMA = "zen.external_lighting_knowledge_pack.v0.1"
CONTEXT_SCHEMA = "zen.external_lighting_knowledge_context.v0.1"
CRITIQUE_SCHEMA = "zen.external_lighting_knowledge_shadow_critique.v0.1"

EVIDENCE_CLASSIFICATIONS = {
    "OFFICIAL_DOCUMENTED", "GENERAL_DESIGN_KNOWLEDGE", "INDUSTRY_REFERENCE",
    "PROFESSIONAL_PRACTICE", "COMMUNITY_PRACTICE", "CASE_CONTEXT",
    "USER_PREFERENCE", "EXPERIMENTAL", "REAL_CONSOLE_VERIFIED",
}
SOURCE_TYPES = {
    "CONSOLE_DOCUMENTATION", "FIXTURE_STANDARD_DOCUMENTATION",
    "MANUFACTURER_EDUCATION", "PROFESSIONAL_TRADE_PRESS", "CASE_REFERENCE",
    "COMMUNITY_DISCUSSION", "USER_WORKFLOW_EVIDENCE",
}
TOPICS = {
    "VISUAL_HIERARCHY", "NEGATIVE_SPACE_RESTRAINT", "DENSITY", "CONTRAST",
    "COLOR_RELATIONSHIPS", "LAYERING_DEPTH", "MOVEMENT_COMPOSITION",
    "FOCUS_VISUAL_ATTENTION", "RHYTHMIC_PUNCTUATION", "ENERGY_PROGRESSION",
    "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_HEADROOM", "CONSOLE_MAINTAINABILITY",
    "FIXTURE_CAPABILITY_PROVENANCE",
}
KNOWLEDGE_KINDS = {"DESCRIPTIVE", "PRESCRIPTIVE_REQUIREMENT"}
PROMOTION_STATES = {
    "INGESTED_UNREVIEWED", "SHADOW_ONLY", "HUMAN_REVIEW_REQUIRED",
    "CASE_TRIAL", "PROMOTED", "CONTEXT_DEPENDENT", "REJECTED",
}
CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}
_FORBIDDEN_KEYS = {
    "command", "commands", "raw_command", "ma_command", "telnet", "lua",
    "script", "transcript", "quote", "full_text", "article_text",
}


def _walk_safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN_KEYS & set(value):
            raise ValueError("External knowledge contains derived notes only, never commands or copied source text.")
        for nested in value.values():
            _walk_safe(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _walk_safe(nested)


@dataclass(frozen=True)
class ExternalKnowledgeSource:
    source_id: str
    source_type: str
    publisher: str
    title: str
    url: str
    publication_date: str | None
    version: str | None
    retrieved_at: str
    authority: str
    copyright_policy: str
    source_bias: str
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.publisher.strip() or not self.title.strip():
            raise ValueError("External source identity, publisher and title are required.")
        if self.source_type not in SOURCE_TYPES or not self.url.startswith(("https://", "http://")):
            raise ValueError("External source type and URL are required.")
        if self.copyright_policy != "METADATA_AND_DERIVED_EXTRACTS_ONLY":
            raise ValueError("External sources must use derived-extract storage only.")
        _walk_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SOURCE_SCHEMA, **asdict(self)}


@dataclass(frozen=True)
class LightingKnowledgeRecord:
    record_id: str
    source_id: str
    topic: str
    normalized_claim: str
    evidence_classification: str
    knowledge_kind: str
    applicability_scope: str
    exclusions: tuple[str, ...]
    confidence: str
    promotion_state: str
    conflicts: tuple[str, ...]
    related_design_concepts: tuple[str, ...]
    related_console_capabilities: tuple[str, ...]
    source_provenance: str
    summary: str

    def __post_init__(self) -> None:
        if not self.record_id.strip() or not self.source_id.strip() or not self.normalized_claim.strip():
            raise ValueError("Knowledge record identity, source and claim are required.")
        if self.topic not in TOPICS or self.evidence_classification not in EVIDENCE_CLASSIFICATIONS:
            raise ValueError("Invalid knowledge topic or evidence classification.")
        if self.knowledge_kind not in KNOWLEDGE_KINDS or self.confidence not in CONFIDENCES:
            raise ValueError("Invalid knowledge kind or confidence.")
        if self.promotion_state not in PROMOTION_STATES:
            raise ValueError("Invalid promotion state.")
        if len(self.normalized_claim) > 500 or len(self.summary) > 600:
            raise ValueError("Knowledge records must remain concise derived extracts.")
        _walk_safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for field in ("exclusions", "conflicts", "related_design_concepts", "related_console_capabilities"):
            value[field] = list(value[field])
        return {"schema": RECORD_SCHEMA, **value}


def validate_source(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"Source schema must be {SOURCE_SCHEMA}.")
    _walk_safe(value)
    fields = set(ExternalKnowledgeSource.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Source is missing: {', '.join(sorted(missing))}")
    return ExternalKnowledgeSource(**{field: value[field] for field in fields}).to_dict()


def validate_source_registry(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SOURCE_REGISTRY_SCHEMA:
        raise ValueError(f"Source registry schema must be {SOURCE_REGISTRY_SCHEMA}.")
    sources = [validate_source(item) for item in value.get("sources", [])]
    ids = [item["source_id"] for item in sources]
    registry_id = str(value.get("registry_id") or "")
    if not registry_id or not sources or len(ids) != len(set(ids)):
        raise ValueError("Source registry needs unique, non-empty source identities.")
    return {"schema": SOURCE_REGISTRY_SCHEMA, "registry_id": registry_id, "sources": sources}


def validate_record(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != RECORD_SCHEMA:
        raise ValueError(f"Knowledge record schema must be {RECORD_SCHEMA}.")
    _walk_safe(value)
    fields = set(LightingKnowledgeRecord.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Knowledge record is missing: {', '.join(sorted(missing))}")
    payload = {field: value[field] for field in fields}
    for field in ("exclusions", "conflicts", "related_design_concepts", "related_console_capabilities"):
        payload[field] = tuple(payload[field])
    return LightingKnowledgeRecord(**payload).to_dict()


def build_pack(registry: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    normalized_registry = validate_source_registry(registry)
    if not isinstance(raw, dict) or raw.get("schema") != PACK_SCHEMA:
        raise ValueError(f"Knowledge pack schema must be {PACK_SCHEMA}.")
    if raw.get("source_registry_ref") != normalized_registry["registry_id"]:
        raise ValueError("Knowledge pack must reference the exact source registry.")
    records = [validate_record(item) for item in raw.get("records", [])]
    record_ids = [item["record_id"] for item in records]
    sources_by_id = {item["source_id"]: item for item in normalized_registry["sources"]}
    source_ids = set(sources_by_id)
    if not records or len(record_ids) != len(set(record_ids)):
        raise ValueError("Knowledge pack requires unique records.")
    if any(item["source_id"] not in source_ids for item in records):
        raise ValueError("Every knowledge record must reference a registered source.")
    if any(item["promotion_state"] == "PROMOTED" for item in records):
        raise ValueError("External ingestion cannot promote knowledge into production truth.")
    if any(item["knowledge_kind"] == "PRESCRIPTIVE_REQUIREMENT" for item in records):
        raise ValueError("External ingestion records must remain descriptive until separate review and case trial.")
    for item in records:
        source_type = sources_by_id[item["source_id"]]["source_type"]
        if source_type == "COMMUNITY_DISCUSSION" and item["evidence_classification"] != "COMMUNITY_PRACTICE":
            raise ValueError("Community material cannot be silently classified as authoritative knowledge.")
        if source_type == "CASE_REFERENCE" and item["evidence_classification"] == "GENERAL_DESIGN_KNOWLEDGE":
            raise ValueError("A case reference cannot silently become general design knowledge.")
    _walk_safe(raw)
    return {
        "schema": PACK_SCHEMA,
        "pack_id": str(raw.get("pack_id") or ""),
        "registry_id": normalized_registry["registry_id"],
        "purpose": str(raw.get("purpose") or ""),
        "runtime_wiring": "NOT_RUN",
        "global_promotions": [],
        "sources": normalized_registry["sources"],
        "records": records,
    }


def load_pack(registry_path: Path | str, pack_path: Path | str) -> dict[str, Any]:
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    raw_pack = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    return build_pack(registry, raw_pack)


def build_shadow_knowledge_context(pack: dict[str, Any], *, topics: Iterable[str] | None = None) -> dict[str, Any]:
    """Expose only reviewable, non-promoted records to an experimental consumer."""
    allowed_topics = set(topics or TOPICS)
    if not allowed_topics <= TOPICS:
        raise ValueError("Unknown knowledge topic requested.")
    records = [record for record in pack.get("records", []) if record["topic"] in allowed_topics and record["promotion_state"] in {"INGESTED_UNREVIEWED", "SHADOW_ONLY", "HUMAN_REVIEW_REQUIRED", "CONTEXT_DEPENDENT"}]
    return {
        "schema": CONTEXT_SCHEMA,
        "pack_id": pack.get("pack_id"),
        "runtime_mode": "SHADOW_ONLY",
        "records": sorted(records, key=lambda item: item["record_id"]),
        "actionability": "REASONING_AND_REVIEW_ONLY",
        "production_designer_modified": False,
        "global_promotions": [],
    }


def critique_ab002_density_limits(context: dict[str, Any], *, observed_findings: Iterable[str]) -> dict[str, Any]:
    """Make a source-linked critique without selecting resources or actions.

    This deliberately consumes already observed A/B-002 limitations.  It cannot
    infer a better Group distribution without Show-specific visual evidence.
    """
    if context.get("schema") != CONTEXT_SCHEMA or context.get("runtime_mode") != "SHADOW_ONLY":
        raise ValueError("External knowledge critique requires a shadow-only context.")
    known = set(observed_findings)
    topics_by_finding = {
        "FINAL_COHORT_SATURATION_RISK": {"VISUAL_HIERARCHY", "NEGATIVE_SPACE_RESTRAINT", "RESOURCE_HEADROOM"},
        "GROUP_LEVEL_HOMOGENEITY_UNRESOLVED": {"VISUAL_HIERARCHY", "CONTRAST", "LAYERING_DEPTH"},
    }
    advisories = []
    for finding in sorted(known & set(topics_by_finding)):
        topics = topics_by_finding[finding]
        refs = [record["record_id"] for record in context["records"] if record["topic"] in topics]
        advisories.append({
            "finding": finding,
            "knowledge_record_ids": refs,
            "review_question": "Does the realized density composition preserve an intentional hierarchy and usable headroom in the actual visual relationship?",
            "scope": "REVIEW_REQUIRED_SHOW_SPECIFIC_EVIDENCE",
            "limitation": "External general knowledge cannot establish current Group position, coverage, audience dominance, or a justified per-Group dimmer hierarchy.",
        })
    return {
        "schema": CRITIQUE_SCHEMA,
        "mode": "SHADOW_ONLY",
        "advisories": advisories,
        "action_changes": [],
        "production_designer_modified": False,
        "requires_show_specific_visual_evidence": True,
    }
