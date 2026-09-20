"""Review-first knowledge ingestion for externally discovered sources.

A model may extract concise candidate knowledge, but source identity,
promotion state and canonical-store mutation remain backend-owned.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .external_lighting_knowledge import (
    CONFIDENCES,
    EVIDENCE_CLASSIFICATIONS,
    TOPICS,
    validate_record,
    validate_source,
)
from .knowledge_store import find_duplicate_candidates
from .portable import portable_state_path
from .llm.router import ProviderRouter, ProviderSlot

EXTRACTION_SCHEMA = "zen.knowledge_extraction.v0.1"
BATCH_SCHEMA = "zen.knowledge_ingestion_batch.v0.1"
MAX_SOURCE_CHARACTERS = 80000
MAX_RECORDS_PER_SOURCE = 8

EXTRACTABLE_FIELDS = {
    "topic", "normalized_claim", "evidence_classification",
    "applicability_scope", "exclusions", "confidence", "conflicts",
    "related_design_concepts", "related_console_capabilities",
    "source_provenance", "summary",
}

FORBIDDEN_EXTRACTION_KEYS = {
    "record_id", "source_id", "promotion_state", "knowledge_kind",
    "command", "commands", "ma_command", "ma2_command", "ma2_commands",
    "telnet", "lua", "shell", "script", "quote", "quotes", "full_text",
    "article_text", "transcript",
}

class KnowledgeIngestionError(ValueError):
    pass


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise KnowledgeIngestionError("Knowledge extractor response was not valid JSON.") from exc
    if not isinstance(value, dict):
        raise KnowledgeIngestionError("Knowledge extractor response must be a JSON object.")
    return value


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in FORBIDDEN_EXTRACTION_KEYS:
                return True
            if _contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _contains_secret(value: object, secret: str) -> bool:
    """Detect a configured provider secret before a candidate can be staged."""
    if not secret:
        return False
    if isinstance(value, str):
        return secret in value
    if isinstance(value, dict):
        return any(_contains_secret(key, secret) or _contains_secret(child, secret) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_secret(child, secret) for child in value)
    return False


def _record_id(source_id: str, topic: str, claim: str) -> str:
    digest = hashlib.sha256((source_id + "\n" + topic + "\n" + claim).encode("utf-8")).hexdigest()[:16]
    return "auto_" + digest


def _normalize_candidate(source_id: str, raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise KnowledgeIngestionError("Knowledge candidate must be an object.")
    if _contains_forbidden_key(raw):
        raise KnowledgeIngestionError("Knowledge candidate contains a forbidden field.")
    unknown_fields = set(raw) - EXTRACTABLE_FIELDS
    if unknown_fields:
        raise KnowledgeIngestionError("Knowledge candidate contains unsupported fields: " + ", ".join(sorted(unknown_fields)))
    missing = EXTRACTABLE_FIELDS - set(raw)
    if missing:
        raise KnowledgeIngestionError("Knowledge candidate is missing fields: " + ", ".join(sorted(missing)))

    topic = str(raw["topic"]).strip().upper()
    classification = str(raw["evidence_classification"]).strip().upper()
    confidence = str(raw["confidence"]).strip().upper()
    if topic not in TOPICS:
        raise KnowledgeIngestionError("Unknown knowledge topic: " + topic)
    if classification not in EVIDENCE_CLASSIFICATIONS:
        raise KnowledgeIngestionError("Unknown evidence classification: " + classification)
    if confidence not in CONFIDENCES:
        raise KnowledgeIngestionError("Unknown confidence: " + confidence)

    claim = " ".join(str(raw["normalized_claim"]).split())
    if not claim:
        raise KnowledgeIngestionError("Knowledge candidate claim is empty.")

    value = {
        "schema": "zen.external_lighting_knowledge_record.v0.1",
        "record_id": _record_id(source_id, topic, claim),
        "source_id": source_id,
        "topic": topic,
        "normalized_claim": claim,
        "evidence_classification": classification,
        "knowledge_kind": "DESCRIPTIVE",
        "applicability_scope": str(raw["applicability_scope"]).strip(),
        "exclusions": list(raw["exclusions"]),
        "confidence": confidence,
        "promotion_state": "INGESTED_UNREVIEWED",
        "conflicts": list(raw["conflicts"]),
        "related_design_concepts": list(raw["related_design_concepts"]),
        "related_console_capabilities": list(raw["related_console_capabilities"]),
        "source_provenance": str(raw["source_provenance"]).strip(),
        "summary": " ".join(str(raw["summary"]).split()),
    }
    try:
        return validate_record(value)
    except (TypeError, ValueError) as exc:
        raise KnowledgeIngestionError(str(exc)) from exc


def validate_extraction_payload(payload: object, *, source_id: str, max_records: int = MAX_RECORDS_PER_SOURCE) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or payload.get("schema") != EXTRACTION_SCHEMA:
        raise KnowledgeIngestionError("Knowledge extraction schema must be " + EXTRACTION_SCHEMA + ".")
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise KnowledgeIngestionError("Knowledge extraction records must be a list.")
    if len(raw_records) > max_records:
        raise KnowledgeIngestionError("Knowledge extraction returned too many records.")
    normalized = [_normalize_candidate(source_id, item) for item in raw_records]
    ids = [item["record_id"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise KnowledgeIngestionError("Knowledge extraction produced duplicate records.")
    return normalized


def _duplicate_review(canonical_records: list[dict[str, Any]], candidate_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidate_ids = {item["record_id"] for item in candidate_records}
    review = find_duplicate_candidates([*canonical_records, *candidate_records], similarity_threshold=0.78)
    return [item for item in review if item.get("record_id_a") in candidate_ids or item.get("record_id_b") in candidate_ids]


def extract_knowledge_candidates(
    router: ProviderRouter,
    *,
    source: dict[str, Any],
    source_text: str,
    canonical_records: list[dict[str, Any]] | None = None,
    max_records: int = MAX_RECORDS_PER_SOURCE,
) -> tuple[dict[str, Any], ProviderSlot]:
    """Extract candidate knowledge. Raw source text is transient and never stored."""
    canonical_source = validate_source(source)
    if not source_text.strip():
        raise KnowledgeIngestionError("Source text is empty.")
    if len(source_text) > MAX_SOURCE_CHARACTERS:
        raise KnowledgeIngestionError("Source text exceeds ingestion limit.")
    if not 1 <= max_records <= MAX_RECORDS_PER_SOURCE:
        raise KnowledgeIngestionError("max_records is outside the supported range.")

    system = (
        "ROLE: KNOWLEDGE_EXTRACTOR. Read only the supplied source text and extract concise, "
        "copyright-safe, descriptive lighting knowledge. Return one JSON object with schema "
        + EXTRACTION_SCHEMA + " and records. Maximum " + str(max_records) + " records. "
        "Each record must contain exactly: topic, normalized_claim, evidence_classification, "
        "applicability_scope, exclusions, confidence, conflicts, related_design_concepts, "
        "related_console_capabilities, source_provenance, summary. Never copy passages, "
        "quotations, transcripts, command text, Lua, Telnet, shell, MA commands, source URL, "
        "title, publisher, record IDs, source IDs, promotion states, or knowledge_kind. "
        "Do not turn one case into a universal rule. Preserve limitations and uncertainty. "
        "If there is no transferable knowledge, return an empty records array."
    )
    user = _canonical_json({
        "source_identity": {
            "source_id": canonical_source["source_id"],
            "source_type": canonical_source["source_type"],
            "authority": canonical_source["authority"],
            "source_bias": canonical_source["source_bias"],
        },
        "allowed_topics": sorted(TOPICS),
        "allowed_evidence_classifications": sorted(EVIDENCE_CLASSIFICATIONS),
        "allowed_confidence": sorted(CONFIDENCES),
        "source_text": source_text,
    })
    content, slot = router.complete(role="RESEARCHER", system=system, user=user)
    # The provider response is transient.  Reject a response containing the
    # configured credential before parsing or staging anything, so a secret
    # cannot enter a batch, diagnostic, or duplicate-review record.
    if slot.api_key and slot.api_key in content:
        raise KnowledgeIngestionError("Knowledge extractor response contained a provider secret.")
    payload = _parse_json_object(content)
    if _contains_secret(payload, slot.api_key):
        raise KnowledgeIngestionError("Knowledge extractor response contained a provider secret.")
    records = validate_extraction_payload(payload, source_id=canonical_source["source_id"], max_records=max_records)
    duplicates = _duplicate_review(canonical_records or [], records)
    content_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    batch_id = "kb-" + canonical_source["source_id"].lower() + "-" + content_hash[:12]
    batch = {
        "schema": BATCH_SCHEMA,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "review_status": "NEEDS_REVIEW",
        "source": canonical_source,
        "source_content_sha256": content_hash,
        "source_text_stored": False,
        "provider": slot.safe_identity(),
        "records": records,
        "duplicate_candidates": duplicates,
        "declared_conflicts": [
            {"record_id": record["record_id"], "conflicts": record["conflicts"]}
            for record in records if record["conflicts"]
        ],
        "canonical_write_performed": False,
        "ma2_write_performed": False,
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    return batch, slot


def validate_ingestion_batch(batch: object) -> dict[str, Any]:
    if not isinstance(batch, dict) or batch.get("schema") != BATCH_SCHEMA:
        raise KnowledgeIngestionError("Invalid knowledge ingestion batch schema.")
    if batch.get("review_status") != "NEEDS_REVIEW":
        raise KnowledgeIngestionError("New ingestion batches must remain NEEDS_REVIEW.")
    if batch.get("source_text_stored") is not False:
        raise KnowledgeIngestionError("Raw source text must not be stored.")
    if batch.get("canonical_write_performed") is not False:
        raise KnowledgeIngestionError("Ingestion staging cannot write the canonical store.")
    if batch.get("ma2_write_performed") is not False:
        raise KnowledgeIngestionError("Knowledge ingestion cannot write MA2.")
    if batch.get("CODEX_ARTISTIC_INTERVENTION") != "NONE":
        raise KnowledgeIngestionError("Knowledge ingestion must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")

    source = validate_source(batch.get("source", {}))
    records = batch.get("records")
    if not isinstance(records, list):
        raise KnowledgeIngestionError("Ingestion batch records must be a list.")
    for record in records:
        normalized = validate_record(record)
        if normalized["source_id"] != source["source_id"]:
            raise KnowledgeIngestionError("Ingestion record/source identity mismatch.")
        if normalized["promotion_state"] != "INGESTED_UNREVIEWED":
            raise KnowledgeIngestionError("Staged knowledge cannot be promoted automatically.")
        if normalized["knowledge_kind"] != "DESCRIPTIVE":
            raise KnowledgeIngestionError("Staged knowledge must remain descriptive.")
    return batch


def stage_ingestion_batch(batch: dict[str, Any], *, root: Path | None = None) -> Path:
    """Persist one validated batch to mutable pending knowledge storage."""
    validate_ingestion_batch(batch)
    pending = (root or portable_state_path("knowledge")) / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    path = pending / (str(batch["batch_id"]) + ".json")
    path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
