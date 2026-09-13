"""Canonical, provenance-bearing knowledge and deterministic retrieval.

The store is an offline boundary: it validates source identity, keeps facts
separate from design knowledge, and returns compact projections for agents.
It never calls a model or a console.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .external_lighting_knowledge import build_pack, validate_source_registry

STORE_SCHEMA = "zen.knowledge_store.v0.1"
LEDGER_SCHEMA = "zen.evidence_ledger.v0.1"
FACT_SCHEMA = "zen.verified_fact.v0.1"
PROJECTION_SCHEMA = "zen.knowledge_projection.v0.1"
CATEGORIES = {
    "GLOBAL_LIGHTING_DESIGN_KNOWLEDGE", "MA2_TECHNICAL_KNOWLEDGE",
    "FIXTURE_TECHNICAL_KNOWLEDGE", "SHOW_FACTS", "ZEN_STYLE_AND_WORKFLOW_KNOWLEDGE",
}
PROMOTABLE_STATES = {"SHADOW_ONLY", "CASE_TRIAL", "CONTEXT_DEPENDENT", "PROMOTED"}
ROLE_TOPICS = {
    "RESEARCHER": {"VISUAL_HIERARCHY", "CONTRAST", "NEGATIVE_SPACE_RESTRAINT", "DENSITY", "COLOR_RELATIONSHIPS", "LAYERING_DEPTH", "ENERGY_PROGRESSION", "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_HEADROOM"},
    "LIGHTING_DESIGNER": {"VISUAL_HIERARCHY", "NEGATIVE_SPACE_RESTRAINT", "DENSITY", "CONTRAST", "COLOR_RELATIONSHIPS", "LAYERING_DEPTH", "MOVEMENT_COMPOSITION", "FOCUS_VISUAL_ATTENTION", "ENERGY_PROGRESSION", "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_HEADROOM"},
    "CRITIC": {"VISUAL_HIERARCHY", "NEGATIVE_SPACE_RESTRAINT", "DENSITY", "CONTRAST", "LAYERING_DEPTH", "ENERGY_PROGRESSION", "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_HEADROOM", "CONSOLE_MAINTAINABILITY"},
    "FINALIZER": {"VISUAL_HIERARCHY", "NEGATIVE_SPACE_RESTRAINT", "DENSITY", "CONTRAST", "COLOR_RELATIONSHIPS", "LAYERING_DEPTH", "MOVEMENT_COMPOSITION", "FOCUS_VISUAL_ATTENTION", "ENERGY_PROGRESSION", "REPEATED_SECTION_DEVELOPMENT", "RESOURCE_HEADROOM", "CONSOLE_MAINTAINABILITY"},
}


def _tokens(value: object) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9_]+", str(value).lower()) if len(token) > 2}


def topic_category(topic: str) -> str:
    if topic == "CONSOLE_MAINTAINABILITY":
        return "MA2_TECHNICAL_KNOWLEDGE"
    if topic == "FIXTURE_CAPABILITY_PROVENANCE":
        return "FIXTURE_TECHNICAL_KNOWLEDGE"
    return "GLOBAL_LIGHTING_DESIGN_KNOWLEDGE"


def normalize_records(pack: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records = []
    for raw in pack.get("records", []):
        record = dict(raw)
        record["category"] = topic_category(str(record["topic"]))
        records.append(record)
    return tuple(sorted(records, key=lambda item: str(item["record_id"])))


def load_canonical_store(registry_path: Path | str, pack_path: Path | str) -> dict[str, Any]:
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    pack = json.loads(Path(pack_path).read_text(encoding="utf-8"))
    validated_registry = validate_source_registry(registry)
    validated_pack = build_pack(validated_registry, pack)
    records = normalize_records(validated_pack)
    return {
        "schema": STORE_SCHEMA,
        "store_id": "ZEN_KNOWLEDGE_STORE_001",
        "source_registry_ref": validated_registry["registry_id"],
        "pack_ref": str(Path(pack_path).as_posix()),
        "records": list(records),
        "source_registry": validated_registry,
    }


def validate_store(store: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(store, dict) or store.get("schema") != STORE_SCHEMA:
        raise ValueError(f"Knowledge store schema must be {STORE_SCHEMA}.")
    if not store.get("store_id") or not store.get("source_registry_ref"):
        raise ValueError("Knowledge store identity and registry reference are required.")
    registry = validate_source_registry(store.get("source_registry", {}))
    source_ids = {item["source_id"] for item in registry["sources"]}
    record_ids: set[str] = set()
    for record in store.get("records", []):
        required = {"record_id", "source_id", "category", "topic", "normalized_claim", "applicability_scope", "exclusions", "confidence", "promotion_state", "summary"}
        if not required <= set(record):
            raise ValueError("Knowledge record is missing required canonical fields.")
        if record["record_id"] in record_ids or record["source_id"] not in source_ids:
            raise ValueError("Knowledge record identity or source reference is invalid.")
        if record["category"] not in CATEGORIES:
            raise ValueError("Unknown knowledge category.")
        record_ids.add(record["record_id"])
    return store


def retrieve_records(records: Iterable[dict[str, Any]], *, role: str, request: str = "", current_context: object | None = None, limit: int = 8, max_records_per_topic: int = 2) -> list[dict[str, Any]]:
    role = role.upper()
    topics = ROLE_TOPICS.get(role, set())
    query = _tokens(request)
    context_tokens = _tokens(current_context or "")
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for record in records:
        if record.get("promotion_state") not in PROMOTABLE_STATES:
            continue
        text = " ".join(str(record.get(key, "")) for key in ("topic", "normalized_claim", "claim", "summary", "applicability_scope", "scope", "related_design_concepts"))
        text_tokens = _tokens(text)
        score = (35 if record.get("topic") in topics else 0) + 4 * len(query & text_tokens) + 2 * len(context_tokens & text_tokens)
        scored.append((score, str(record.get("record_id", "")), record))
    scored.sort(key=lambda item: (-item[0], item[1]))
    selected: list[dict[str, Any]] = []
    topic_counts: dict[str, int] = {}
    for _, _, record in scored:
        topic = str(record.get("topic"))
        if topic_counts.get(topic, 0) >= max_records_per_topic:
            continue
        selected.append(record)
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        if len(selected) >= limit:
            break
    return selected


def project_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "schema": PROJECTION_SCHEMA,
        "record_id": record["record_id"],
        "topic": record["topic"],
        "claim": record.get("normalized_claim", record.get("claim", "")),
        "scope": record.get("applicability_scope", record.get("scope", "")),
        "exclusions": record["exclusions"],
        "confidence": record["confidence"],
        "promotion_state": record["promotion_state"],
        "summary": record["summary"],
    } for record in records]


def build_evidence_ledger(*, facts: Iterable[dict[str, Any]] = (), knowledge: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for fact in facts:
        validate_fact(fact)
        entries.append({"evidence_ref": fact["fact_id"], "kind": "VERIFIED_FACT", "source": fact["source"], "summary": fact["claim"]})
    for record in knowledge:
        if not isinstance(record, dict) or not record.get("record_id") or not record.get("source_id"):
            raise ValueError("DESIGN_KNOWLEDGE ledger entries require canonical record and source identity.")
        entries.append({"evidence_ref": record["record_id"], "kind": "DESIGN_KNOWLEDGE", "source_id": record["source_id"], "summary": record["normalized_claim"]})
    return {"schema": LEDGER_SCHEMA, "entries": sorted(entries, key=lambda item: item["evidence_ref"])}


def validate_evidence_refs(refs: Iterable[str], ledger: dict[str, Any]) -> list[str]:
    known = {entry.get("evidence_ref") for entry in ledger.get("entries", [])}
    refs = list(refs)
    if any(ref not in known for ref in refs):
        raise ValueError("Evidence reference is not present in the canonical ledger.")
    return refs


def verified_fact(*, fact_id: str, claim: str, source: str, evidence: object) -> dict[str, Any]:
    if not fact_id.strip() or not claim.strip() or not source.strip() or evidence in (None, "", [], {}):
        raise ValueError("A VERIFIED_FACT requires claim, source and evidence.")
    return {"schema": FACT_SCHEMA, "fact_id": fact_id, "kind": "VERIFIED_FACT", "claim": claim, "source": source, "evidence": evidence}


def validate_fact(fact: dict[str, Any]) -> dict[str, Any]:
    if fact.get("schema") != FACT_SCHEMA or fact.get("kind") != "VERIFIED_FACT":
        raise ValueError("Fact must be a verified fact record.")
    if not fact.get("source") or fact.get("evidence") in (None, "", [], {}):
        raise ValueError("VERIFIED_FACT cannot omit evidence.")
    return fact


def artistic_proposal(*, proposal_id: str, claim: str, evidence_refs: Iterable[str] = ()) -> dict[str, Any]:
    return {"schema": "zen.artistic_proposal.v0.1", "proposal_id": proposal_id, "kind": "ARTISTIC_PROPOSAL", "claim": claim, "evidence_refs": list(evidence_refs)}


def unknown(*, field: str, reason: str) -> dict[str, Any]:
    return {"schema": "zen.unknown.v0.1", "kind": "UNKNOWN", "field": field, "reason": reason}
