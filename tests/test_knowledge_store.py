from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.knowledge_store import (
    artistic_proposal,
    build_evidence_ledger,
    find_duplicate_candidates,
    load_canonical_store,
    project_records,
    resolve_research_sources,
    retrieve_records,
    unknown,
    validate_evidence_refs,
    verified_fact,
)

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeStoreTests(unittest.TestCase):
    def test_existing_pack_loads_losslessly_with_source_registry_integrity(self):
        store = load_canonical_store(ROOT / "data/external_lighting_knowledge_source_registry_001.json", ROOT / "data/external_lighting_knowledge_pack_001.json")
        self.assertGreaterEqual(len(store["records"]), 100)
        self.assertIn("ZEN_STYLE_AND_WORKFLOW_KNOWLEDGE", {record["category"] for record in store["records"]})

    def test_unknown_source_fails_closed(self):
        pack = json.loads((ROOT / "data/external_lighting_knowledge_pack_001.json").read_text(encoding="utf-8"))
        pack["records"][0]["source_id"] = "NOT_REGISTERED"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pack.json"
            path.write_text(json.dumps(pack), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_canonical_store(ROOT / "data/external_lighting_knowledge_source_registry_001.json", path)

    def test_retrieval_is_deterministic_role_specific_and_topic_diverse(self):
        store = load_canonical_store(ROOT / "data/external_lighting_knowledge_source_registry_001.json", ROOT / "data/external_lighting_knowledge_pack_001.json")
        first = retrieve_records(store["records"], role="LIGHTING_DESIGNER", request="quiet repeated section", limit=8, max_records_per_topic=1)
        second = retrieve_records(store["records"], role="LIGHTING_DESIGNER", request="quiet repeated section", limit=8, max_records_per_topic=1)
        self.assertEqual([item["record_id"] for item in first], [item["record_id"] for item in second])
        self.assertEqual(len({item["topic"] for item in first}), len(first))

    def test_human_review_required_records_are_retrievable_in_shadow(self):
        store = load_canonical_store(ROOT / "data/external_lighting_knowledge_source_registry_001.json", ROOT / "data/external_lighting_knowledge_pack_001.json")
        record = dict(next(item for item in store["records"] if item["topic"] == "VISUAL_HIERARCHY"))
        record["promotion_state"] = "HUMAN_REVIEW_REQUIRED"
        selected = retrieve_records([record], role="LIGHTING_DESIGNER", request="", limit=1)
        self.assertEqual(selected[0]["record_id"], record["record_id"])
        self.assertEqual(project_records(selected)[0]["promotion_state"], "HUMAN_REVIEW_REQUIRED")

    def test_projection_preserves_review_fields_without_raw_source_metadata(self):
        record = {"record_id": "K1", "topic": "DENSITY", "normalized_claim": "claim", "applicability_scope": "scope", "exclusions": ["x"], "confidence": "MEDIUM", "promotion_state": "SHADOW_ONLY", "summary": "summary", "source_id": "S1"}
        projection = project_records([record])[0]
        self.assertEqual(set(projection), {"schema", "record_id", "topic", "claim", "scope", "exclusions", "confidence", "promotion_state", "summary"})

    def test_evidence_ledger_rejects_unknown_refs_and_keeps_fact_knowledge_distinct(self):
        fact = verified_fact(fact_id="FACT_001", claim="verified", source="show-export", evidence={"id": 1})
        knowledge = {"record_id": "KNOW_001", "source_id": "S1", "normalized_claim": "descriptive"}
        ledger = build_evidence_ledger(facts=[fact], knowledge=[knowledge])
        validate_evidence_refs(["FACT_001", "KNOW_001"], ledger)
        with self.assertRaises(ValueError):
            validate_evidence_refs(["UNKNOWN"], ledger)

    def test_artistic_proposal_and_unknown_are_legal_without_fake_proof(self):
        self.assertEqual(artistic_proposal(proposal_id="P1", claim="contextual choice")["kind"], "ARTISTIC_PROPOSAL")
        self.assertEqual(unknown(field="harmony", reason="not available")["kind"], "UNKNOWN")

    def test_research_source_resolution_uses_registry_identity(self):
        registry = json.loads((ROOT / "data/external_lighting_knowledge_source_registry_001.json").read_text(encoding="utf-8"))
        pack = json.loads((ROOT / "data/external_lighting_knowledge_pack_001.json").read_text(encoding="utf-8"))
        record = pack["records"][0]
        resolved = resolve_research_sources(sources=[{"source_id": record["source_id"], "record_id": record["record_id"]}], source_registry=registry, records=pack["records"])
        self.assertEqual(resolved[0]["source_id"], record["source_id"])
        self.assertEqual(resolved[0]["canonical_source"]["title"], next(item["title"] for item in registry["sources"] if item["source_id"] == record["source_id"]))

    def test_research_source_identity_mismatch_and_fabricated_metadata_fail(self):
        registry = json.loads((ROOT / "data/external_lighting_knowledge_source_registry_001.json").read_text(encoding="utf-8"))
        pack = json.loads((ROOT / "data/external_lighting_knowledge_pack_001.json").read_text(encoding="utf-8"))
        first = pack["records"][0]
        second = next(item for item in pack["records"] if item["source_id"] != first["source_id"])
        with self.assertRaises(ValueError):
            resolve_research_sources(sources=[{"source_id": first["source_id"], "record_id": second["record_id"]}], source_registry=registry, records=pack["records"])
        with self.assertRaises(ValueError):
            resolve_research_sources(sources=[{"source_id": first["source_id"], "title": "Fabricated title"}], source_registry=registry, records=pack["records"])

    def test_duplicate_candidates_are_deterministic_and_non_mutating(self):
        records = [
            {"record_id": "B", "topic": "DENSITY", "normalized_claim": "Density can change through selective source use."},
            {"record_id": "A", "topic": "DENSITY", "normalized_claim": "Density can change through selective source use."},
            {"record_id": "C", "topic": "COLOR_RELATIONSHIPS", "normalized_claim": "Color supports palette relationships."},
        ]
        found = find_duplicate_candidates(records)
        self.assertEqual(found[0]["record_id_a"], "A")
        self.assertEqual(found[0]["record_id_b"], "B")
        self.assertEqual(found[0]["review_status"], "REVIEW_REQUIRED")
        self.assertEqual(records[0]["record_id"], "B")


if __name__ == "__main__":
    unittest.main()
