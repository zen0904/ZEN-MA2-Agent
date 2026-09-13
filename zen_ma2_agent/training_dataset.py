"""Small, provenance-first training-data boundary.

This module stores reviewable examples; it does not train a model or decide
artistic ground truth.  Only explicitly approved samples may be exported.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "zen.training_sample.v0.1"
STATUSES = {"RAW", "AUTO_COLLECTED", "NEEDS_REVIEW", "APPROVED", "REJECTED", "SUPERSEDED"}
CATEGORIES = {"KNOWLEDGE_DATA", "REASONING_AND_CRITIQUE_DATA", "ZEN_STYLE_AND_WORKFLOW_DATA"}


def validate_training_sample(sample: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "sample_id", "category", "status", "input", "output", "provenance"}
    if not isinstance(sample, dict) or sample.get("schema") != SCHEMA or not required <= set(sample):
        raise ValueError("Training sample schema or required fields are invalid.")
    if sample["category"] not in CATEGORIES or sample["status"] not in STATUSES:
        raise ValueError("Training sample category or status is invalid.")
    provenance = sample["provenance"]
    provenance_required = {"source_run_id", "source_commit", "source_model", "source_provider", "context_hash", "knowledge_refs", "human_review_status", "approval_status", "created_at", "CODEX_ARTISTIC_INTERVENTION"}
    if not isinstance(provenance, dict) or not provenance_required <= set(provenance):
        raise ValueError("Training sample provenance is incomplete.")
    if provenance["CODEX_ARTISTIC_INTERVENTION"] != "NONE":
        raise ValueError("Training data must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    if sample["status"] == "APPROVED":
        approver = provenance.get("approved_by") or sample.get("approved_by")
        if not approver or str(approver).upper() == "CODEX":
            raise ValueError("Artistic training data cannot be approved by Codex or without an approver.")
    return sample


def make_training_sample(*, sample_id: str, category: str, input_data: Any, output_data: Any, provenance: dict[str, Any], status: str = "NEEDS_REVIEW") -> dict[str, Any]:
    sample = {"schema": SCHEMA, "sample_id": sample_id, "category": category, "status": status, "input": input_data, "output": output_data, "provenance": dict(provenance)}
    return validate_training_sample(sample)


def export_approved_jsonl(samples: Iterable[dict[str, Any]], path: Path | str) -> Path:
    validated = [validate_training_sample(sample) for sample in samples]
    approved = [sample for sample in validated if sample["status"] == "APPROVED"]
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(sample, ensure_ascii=False, sort_keys=True) + "\n" for sample in approved), encoding="utf-8")
    return destination
