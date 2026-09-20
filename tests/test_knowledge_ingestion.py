from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.knowledge_ingestion import (
    EXTRACTION_SCHEMA,
    KnowledgeIngestionError,
    extract_knowledge_candidates,
    stage_ingestion_batch,
    validate_extraction_payload,
    validate_ingestion_batch,
)
from zen_ma2_agent.llm.router import ProviderSlot


def source() -> dict[str, object]:
    return {
        "schema": "zen.external_lighting_knowledge_source.v0.1",
        "source_id": "TEST_SOURCE",
        "source_type": "MANUFACTURER_EDUCATION",
        "publisher": "Test Publisher",
        "title": "Test source",
        "url": "https://example.test/source",
        "publication_date": None,
        "version": None,
        "retrieved_at": "2026-09-20",
        "authority": "TEST",
        "copyright_policy": "METADATA_AND_DERIVED_EXTRACTS_ONLY",
        "source_bias": "TEST_SCOPE",
        "notes": "",
    }


def record(*, claim: str = "Layer contrast can clarify visual hierarchy.", conflicts: list[str] | None = None) -> dict[str, object]:
    return {
        "topic": "VISUAL_HIERARCHY",
        "normalized_claim": claim,
        "evidence_classification": "GENERAL_DESIGN_KNOWLEDGE",
        "applicability_scope": "Context-dependent design reasoning.",
        "exclusions": ["Not a fixed song recipe."],
        "confidence": "MEDIUM",
        "conflicts": conflicts or [],
        "related_design_concepts": ["hierarchy"],
        "related_console_capabilities": [],
        "source_provenance": "TEST_SOURCE",
        "summary": "A concise derived principle.",
    }


class _ExtractorRouter:
    def __init__(self, payload: dict[str, object], *, api_key: str = ""):
        self.payload = payload
        self.slot = ProviderSlot(1, "OPENAI_COMPATIBLE", "test", "https://example.test/v1", api_key, ("RESEARCHER",), 5)

    def complete(self, *, role: str, system: str, user: str):
        return json.dumps(self.payload, ensure_ascii=False), self.slot


class KnowledgeIngestionTests(unittest.TestCase):
    def payload(self, records: list[dict[str, object]]) -> dict[str, object]:
        return {"schema": EXTRACTION_SCHEMA, "records": records}

    def test_valid_extraction_empty_result_and_backend_owned_fields(self):
        empty = validate_extraction_payload(self.payload([]), source_id="TEST_SOURCE")
        self.assertEqual(empty, [])
        batch, slot = extract_knowledge_candidates(
            _ExtractorRouter(self.payload([record()])), source=source(), source_text="derived source text",
        )
        self.assertEqual(batch["records"][0]["source_id"], "TEST_SOURCE")
        self.assertTrue(batch["records"][0]["record_id"].startswith("auto_"))
        self.assertEqual(batch["records"][0]["promotion_state"], "INGESTED_UNREVIEWED")
        self.assertEqual(batch["records"][0]["knowledge_kind"], "DESCRIPTIVE")
        self.assertEqual(batch["source_text_stored"], False)
        self.assertEqual(batch["canonical_write_performed"], False)
        self.assertEqual(batch["ma2_write_performed"], False)
        self.assertEqual(slot.number, 1)

    def test_unknown_topic_and_too_many_records_rejected(self):
        with self.assertRaises(KnowledgeIngestionError):
            validate_extraction_payload(self.payload([record() | {"topic": "UNKNOWN_TOPIC"}]), source_id="TEST_SOURCE")
        with self.assertRaises(KnowledgeIngestionError):
            validate_extraction_payload(self.payload([record() for _ in range(9)]), source_id="TEST_SOURCE")

    def test_forbidden_content_and_model_owned_identity_fields_rejected(self):
        for key, value in {
            "quote": "copied text", "transcript": "all text", "full_text": "article", "lua": "print(1)",
            "telnet": "Store Cue 1", "record_id": "model-id", "source_id": "wrong", "promotion_state": "PROMOTED",
        }.items():
            with self.subTest(key=key), self.assertRaises(KnowledgeIngestionError):
                validate_extraction_payload(self.payload([record() | {key: value}]), source_id="TEST_SOURCE")

    def test_hash_conflicts_duplicates_and_secret_safety(self):
        candidate = record(conflicts=["Alternative approach may apply in theatre context."])
        canonical = [{"record_id": "existing", "topic": candidate["topic"], "normalized_claim": candidate["normalized_claim"]}]
        batch, _ = extract_knowledge_candidates(
            _ExtractorRouter(self.payload([candidate])), source=source(), source_text="transient source", canonical_records=canonical,
        )
        self.assertTrue(batch["source_content_sha256"])
        self.assertNotIn("transient source", json.dumps(batch))
        self.assertTrue(batch["duplicate_candidates"])
        self.assertEqual(batch["declared_conflicts"][0]["conflicts"], candidate["conflicts"])
        self.assertEqual(validate_ingestion_batch(batch)["review_status"], "NEEDS_REVIEW")

        secret = "super-secret-key"
        with self.assertRaises(KnowledgeIngestionError):
            extract_knowledge_candidates(
                _ExtractorRouter(self.payload([record() | {"summary": secret}]), api_key=secret),
                source=source(), source_text="safe text",
            )

    def test_stage_writes_only_validated_pending_batch(self):
        batch, _ = extract_knowledge_candidates(_ExtractorRouter(self.payload([])), source=source(), source_text="text")
        with tempfile.TemporaryDirectory() as temp:
            path = stage_ingestion_batch(batch, root=Path(temp))
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["review_status"], "NEEDS_REVIEW")


if __name__ == "__main__":
    unittest.main()
