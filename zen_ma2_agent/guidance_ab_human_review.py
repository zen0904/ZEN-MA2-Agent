"""Immutable human-review records for Guidance-Assisted Designer A/B tests.

These records are evidence about an experimental candidate.  They never alter
the original A/B fixture, the production Designer, or a live MA2 show.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


GUIDANCE_AB_HUMAN_REVIEW_SCHEMA = "zen.guidance_ab_human_review.v0.1"
REVIEW_DECISIONS = {
    "DIRECTION_ACCEPTED_WITH_REQUIRED_IMPROVEMENT",
    "CONTEXT_DEPENDENT",
    "NEEDS_GUIDANCE_REWORK",
    "ACCEPT_WITH_CONTEXT_LIMITATION",
}
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Human A/B review records may not contain MA2 command fields.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe(nested)


def validate_guidance_ab_human_review(value: dict[str, Any]) -> dict[str, Any]:
    """Validate a separately-stored, bounded human A/B review decision."""
    required = {
        "schema", "review_id", "experiment_id", "case_id", "baseline_reference",
        "guidance_assisted_reference", "human_decision", "human_feedback",
        "accepted_aspects", "rejected_aspects", "required_improvements",
        "context_limitations", "evidence_provenance", "review_status", "reviewer",
        "recorded_at",
    }
    if not isinstance(value, dict) or value.get("schema") != GUIDANCE_AB_HUMAN_REVIEW_SCHEMA or required - set(value):
        raise ValueError(f"Human A/B review schema must be {GUIDANCE_AB_HUMAN_REVIEW_SCHEMA} with all required fields.")
    normalized = deepcopy(value)
    if normalized["human_decision"] not in REVIEW_DECISIONS:
        raise ValueError("Unsupported human A/B review decision.")
    if normalized["review_status"] != "RECORDED" or not normalized["reviewer"]:
        raise ValueError("Human A/B review must be explicitly recorded with a reviewer.")
    if not all(isinstance(normalized[key], list) for key in ("accepted_aspects", "rejected_aspects", "required_improvements", "context_limitations", "evidence_provenance")):
        raise ValueError("Human A/B review collections must be lists.")
    if not all(isinstance(normalized[key], str) and normalized[key] for key in ("review_id", "experiment_id", "case_id", "baseline_reference", "guidance_assisted_reference", "human_feedback", "recorded_at")):
        raise ValueError("Human A/B review identifiers, feedback and metadata must be non-empty strings.")
    _safe(normalized)
    return normalized
