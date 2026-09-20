from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.training_dataset import (
    build_raw_sample_from_completed_run,
    export_approved_jsonl,
    make_training_sample,
    validate_training_sample,
    write_raw_sample_from_completed_run,
)


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

    def test_completed_run_becomes_raw_needs_review_with_provenance(self):
        final = {
            "schema": "zen.autonomous_design.v0.1", "design_intent": {}, "visual_strategy": {},
            "virtual_rig": {}, "position_vocabulary": {}, "main_sequence": {},
            "free_cue_layer": {}, "evidence_trace": {}, "codex_artistic_intervention": "NONE",
        }
        research = {"schema": "zen.multi_agent_research.v0.1", "research_status": "OFFLINE_CACHED_CONTEXT", "subject": "s", "sources": [], "transferable_design_observations": [], "constraints": [], "uncertainties": [], "codex_artistic_intervention": "NONE"}
        designer = {"schema": "zen.multi_agent_designer_draft.v0.1", "design_intent": {}, "visual_strategy": {}, "resource_considerations": [], "uncertainties": [], "codex_artistic_intervention": "NONE"}
        critic = {"schema": "zen.multi_agent_critic.v0.1", "strengths": [], "problems": [], "severity": "NONE", "revision_requests": [], "codex_artistic_intervention": "NONE"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            (root / "steps").mkdir(parents=True)
            (root / "run.json").write_text(json.dumps({"status": "COMPLETE", "RUN_ID": "run-1", "GIT_HEAD": "abc", "CONTEXT_HASH": "ctx", "REQUEST_HASH": "req", "CODEX_ARTISTIC_INTERVENTION": "NONE", "MA2_WRITES": 0}), encoding="utf-8")
            for role, artifact in (("researcher", research), ("lighting_designer", designer), ("critic", critic), ("finalizer", final)):
                (root / "steps" / f"{role}.json").write_text(json.dumps({"artifact": artifact, "provider": {"slot": 1, "model": "local", "type": "OPENAI_COMPATIBLE_LOCAL"}, "candidate_artifacts": []}), encoding="utf-8")
            (root / "final_design.json").write_text(json.dumps(final), encoding="utf-8")
            sample = build_raw_sample_from_completed_run(root, request_text="request")
            self.assertEqual(sample["status"], "RAW")
            self.assertEqual(sample["provenance"]["approval_status"], "NEEDS_REVIEW")
            self.assertEqual(sample["provenance"]["CODEX_ARTISTIC_INTERVENTION"], "NONE")
            output = write_raw_sample_from_completed_run(root, Path(temp))
            self.assertTrue(output.as_posix().endswith("training/raw/run_run-1.json"))

    def test_invalid_or_unapproved_run_cannot_be_collected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            root.mkdir()
            (root / "run.json").write_text(json.dumps({"status": "FAILED"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_raw_sample_from_completed_run(root)


if __name__ == "__main__":
    unittest.main()
