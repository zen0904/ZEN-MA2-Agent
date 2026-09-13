from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.training_dataset import export_approved_jsonl, make_training_sample, validate_training_sample


def provenance(**extra):
    value = {
        "source_run_id": "run-1", "source_commit": "abc", "source_model": "none", "source_provider": "offline",
        "context_hash": "ctx", "knowledge_refs": ["KNOW_1"], "human_review_status": "UNSET",
        "approval_status": "NEEDS_REVIEW", "created_at": "2026-09-13T00:00:00Z", "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    value.update(extra)
    return value


class TrainingDatasetTests(unittest.TestCase):
    def test_provenance_and_categories_are_required(self):
        sample = make_training_sample(sample_id="S1", category="KNOWLEDGE_DATA", input_data={"x": 1}, output_data={"y": 2}, provenance=provenance())
        self.assertEqual(sample["status"], "NEEDS_REVIEW")
        with self.assertRaises(ValueError):
            make_training_sample(sample_id="S2", category="BAD", input_data={}, output_data={}, provenance=provenance())

    def test_only_approved_samples_export(self):
        samples = [
            make_training_sample(sample_id="RAW", category="KNOWLEDGE_DATA", input_data={}, output_data={}, provenance=provenance()),
            make_training_sample(sample_id="APP", category="REASONING_AND_CRITIQUE_DATA", input_data={}, output_data={}, provenance=provenance(approved_by="ZEN_HUMAN_REVIEW"), status="APPROVED"),
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = export_approved_jsonl(samples, Path(temp) / "approved.jsonl")
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["sample_id"] for row in rows], ["APP"])

    def test_codex_cannot_self_approve(self):
        with self.assertRaises(ValueError):
            make_training_sample(sample_id="S1", category="ZEN_STYLE_AND_WORKFLOW_DATA", input_data={}, output_data={}, provenance=provenance(approved_by="CODEX"), status="APPROVED")


if __name__ == "__main__":
    unittest.main()
