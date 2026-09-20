"""Small, provenance-first training-data boundary.

This module stores reviewable examples; it does not train a model or decide
artistic ground truth.  Only explicitly approved samples may be exported.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .llm.autonomous_designer import DesignValidationError, validate_design_output

SCHEMA = "zen.training_sample.v0.1"
STATUSES = {"RAW", "AUTO_COLLECTED", "NEEDS_REVIEW", "APPROVED", "REJECTED", "SUPERSEDED"}
CATEGORIES = {"KNOWLEDGE_DATA", "REASONING_AND_CRITIQUE_DATA", "ZEN_STYLE_AND_WORKFLOW_DATA"}
ROLE_SEQUENCE = ("researcher", "lighting_designer", "critic", "finalizer")


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


def build_raw_sample_from_completed_run(
    run_path: Path | str,
    *,
    request_text: str | None = None,
    show_context_refs: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a reviewable RAW sample from one completed multi-agent run.

    This is intentionally a read-only collector: it validates the completed
    final artifact, copies bounded role artifacts/provenance, and never marks
    a sample approved or alters the canonical knowledge store.
    """
    root = Path(run_path)
    try:
        state = json.loads((root / "run.json").read_text(encoding="utf-8"))
        final = json.loads((root / "final_design.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Completed run evidence is missing or invalid.") from exc
    if not isinstance(state, dict) or state.get("status") != "COMPLETE":
        raise ValueError("Only a COMPLETE multi-agent run may become a training candidate.")
    try:
        final = validate_design_output(final)
    except (DesignValidationError, TypeError, ValueError) as exc:
        raise ValueError("Completed run final_design.json failed schema validation.") from exc
    if state.get("CODEX_ARTISTIC_INTERVENTION") not in (None, "NONE"):
        raise ValueError("Training candidates must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    if state.get("MA2_WRITES") not in (None, 0, "0", False):
        raise ValueError("A run with MA2 writes cannot become an automatic training candidate.")

    artifacts: dict[str, Any] = {}
    providers: dict[str, Any] = {}
    knowledge_refs: set[str] = set()
    for role in ROLE_SEQUENCE:
        try:
            envelope = json.loads((root / "steps" / f"{role}.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Completed run is missing the {role} artifact.") from exc
        if not isinstance(envelope, dict) or not isinstance(envelope.get("artifact"), dict):
            raise ValueError(f"Completed run has an invalid {role} artifact envelope.")
        artifacts[role] = {
            "artifact": envelope["artifact"],
            "candidate_artifacts": envelope.get("candidate_artifacts", []),
            "artifact_hash": envelope.get("artifact_hash"),
        }
        providers[role] = envelope.get("provider", {})
        refs = envelope["artifact"].get("evidence_refs", [])
        if isinstance(refs, list):
            knowledge_refs.update(ref for ref in refs if isinstance(ref, str))

    execution = state.get("role_execution", [])
    if isinstance(execution, list):
        for item in execution:
            if isinstance(item, dict):
                refs = item.get("knowledge_refs", [])
                if isinstance(refs, list):
                    knowledge_refs.update(ref for ref in refs if isinstance(ref, str))
    run_id = str(state.get("RUN_ID") or root.name)
    source_model = "MULTI_PROVIDER"
    source_provider = "MULTI_PROVIDER"
    request_value: Any = {"request_hash": state.get("REQUEST_HASH")}
    if request_text is not None:
        if not isinstance(request_text, str) or len(request_text) > 100000:
            raise ValueError("request_text is missing or exceeds the bounded collector limit.")
        request_value["request"] = request_text
    sample = make_training_sample(
        sample_id="run_" + run_id,
        category="REASONING_AND_CRITIQUE_DATA",
        input_data={
            "request": request_value,
            "show_context_refs": sorted(set(show_context_refs)),
            "knowledge_refs": sorted(knowledge_refs),
        },
        output_data={"roles": artifacts, "final_design": final},
        provenance={
            "source_run_id": run_id,
            "source_commit": state.get("GIT_HEAD", "UNKNOWN"),
            "source_model": source_model,
            "source_provider": source_provider,
            "providers_by_role": providers,
            "context_hash": state.get("CONTEXT_HASH", "UNKNOWN"),
            "knowledge_refs": sorted(knowledge_refs),
            "human_review_status": "UNSET",
            "approval_status": "NEEDS_REVIEW",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "CODEX_ARTISTIC_INTERVENTION": "NONE",
            "MA2_WRITES": 0,
        },
        status="RAW",
    )
    return sample


def write_raw_sample_from_completed_run(
    run_path: Path | str,
    destination_root: Path | str,
    *,
    request_text: str | None = None,
    show_context_refs: Iterable[str] = (),
) -> Path:
    sample = build_raw_sample_from_completed_run(
        run_path, request_text=request_text, show_context_refs=show_context_refs,
    )
    destination = Path(destination_root) / "training" / "raw" / (sample["sample_id"] + ".json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination
