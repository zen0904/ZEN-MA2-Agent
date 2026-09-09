"""Human-review workflow for industry evidence.

Review records are separate, immutable decisions. They never edit an
IndustryReferenceSource or DerivedObservation and never connect to MA2 or the
Designer runtime.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .industry_references import EVIDENCE_TYPES, REVIEW_STATUSES


REVIEW_SCHEMA = "zen.industry_evidence_review.v0.1"
AI_RECOMMENDATION_SCHEMA = "zen.industry_evidence_ai_recommendation.v0.1"
REVIEWER_TYPES = {"HUMAN", "AI_ASSISTED_HUMAN"}
DECISIONS = {"ACCEPT", "ACCEPT_WITH_LIMITATION", "NEEDS_CONTEXT", "REJECT", "DUPLICATE", "UNSURE"}
REVIEW_CONFIDENCES = {"HIGH", "MEDIUM", "LOW"}
SCOPE_CONFIRMATIONS = {"GLOBAL_CANDIDATE", "DOMAIN_ONLY", "CASE_ONLY", "NOT_GENERALIZABLE", "UNKNOWN"}
ACTIVE_DECISIONS = {"ACCEPT", "ACCEPT_WITH_LIMITATION"}
PRIORITIES = {"HIGH", "MEDIUM", "LOW"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _no_commands(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = {"command", "commands", "raw_command", "telnet", "lua", "ma_command"} & set(value)
        if forbidden:
            raise ValueError("Evidence review records cannot contain MA2 command fields.")
        for nested in value.values():
            _no_commands(nested)
    elif isinstance(value, list):
        for nested in value:
            _no_commands(nested)


@dataclass(frozen=True)
class HumanReviewRecord:
    review_id: str
    evidence_id: str
    source_id: str
    reviewer_type: str
    decision: str
    confidence: str
    reason: str
    scope_confirmation: str
    notes: str
    reviewed_at: str

    def __post_init__(self) -> None:
        if not self.review_id.strip() or not self.evidence_id.strip() or not self.source_id.strip():
            raise ValueError("Review identity is required.")
        if self.reviewer_type not in REVIEWER_TYPES or self.decision not in DECISIONS:
            raise ValueError("Invalid reviewer type or decision.")
        if self.confidence not in REVIEW_CONFIDENCES or self.scope_confirmation not in SCOPE_CONFIRMATIONS:
            raise ValueError("Invalid review confidence or scope confirmation.")
        if not self.reason.strip() or not self.reviewed_at.strip():
            raise ValueError("Review reason and timestamp are required.")
        _no_commands(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": REVIEW_SCHEMA, **asdict(self)}


@dataclass(frozen=True)
class AIReviewRecommendation:
    recommendation_id: str
    evidence_id: str
    source_id: str
    recommended_decision: str
    recommended_scope: str
    recommended_reason: str
    confidence: str
    created_at: str

    def __post_init__(self) -> None:
        if self.recommended_decision not in DECISIONS or self.recommended_scope not in SCOPE_CONFIRMATIONS:
            raise ValueError("Invalid AI review recommendation.")
        if self.confidence not in REVIEW_CONFIDENCES:
            raise ValueError("Invalid AI recommendation confidence.")
        _no_commands(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {"schema": AI_RECOMMENDATION_SCHEMA, **asdict(self)}


def validate_review(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != REVIEW_SCHEMA:
        raise ValueError(f"Review schema must be {REVIEW_SCHEMA}.")
    fields = set(HumanReviewRecord.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Review is missing: {', '.join(sorted(missing))}")
    return HumanReviewRecord(**{key: value[key] for key in fields}).to_dict()


def validate_recommendation(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != AI_RECOMMENDATION_SCHEMA:
        raise ValueError(f"Recommendation schema must be {AI_RECOMMENDATION_SCHEMA}.")
    fields = set(AIReviewRecommendation.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Recommendation is missing: {', '.join(sorted(missing))}")
    return AIReviewRecommendation(**{key: value[key] for key in fields}).to_dict()


def review_observation(observation: dict[str, Any], *, decision: str, reason: str, scope_confirmation: str = "UNKNOWN", confidence: str = "MEDIUM", reviewer_type: str = "HUMAN", notes: str = "", review_id: str | None = None, reviewed_at: str | None = None) -> dict[str, Any]:
    """Create a review record without mutating ``observation``."""
    _no_commands(observation)
    if not observation.get("observation_id") or not observation.get("source_id"):
        raise ValueError("Observation must have identity before review.")
    record = HumanReviewRecord(review_id or f"review_{observation['observation_id']}", observation["observation_id"], observation["source_id"], reviewer_type, decision, confidence, reason, scope_confirmation, notes, reviewed_at or _utc_now())
    return record.to_dict()


def review_batch(observations: Iterable[dict[str, Any]], decisions: dict[str, dict[str, Any]], *, reviewer_type: str = "HUMAN", reviewed_at: str | None = None) -> list[dict[str, Any]]:
    """Create deterministic records for an observation-id keyed decision map."""
    records = []
    for observation in observations:
        spec = decisions.get(observation.get("observation_id"))
        if spec is None:
            continue
        records.append(review_observation(observation, reviewer_type=reviewer_type, reviewed_at=reviewed_at, **spec))
    return records


def ai_recommendation(observation: dict[str, Any]) -> dict[str, Any]:
    """Make a conservative suggestion; it is never a human decision."""
    evidence_type = observation.get("evidence_type")
    if evidence_type in {"VISUAL_INFERENCE", "MODEL_INTERPRETATION"}:
        decision, reason, confidence = "NEEDS_CONTEXT", "Interpretation needs human confirmation of intent and context.", "LOW"
    else:
        decision, reason, confidence = "ACCEPT_WITH_LIMITATION", "Source-linked direct statement appears usable within its documented domain; retain publisher and scope limits.", "MEDIUM"
    recommendation = AIReviewRecommendation(f"ai_review_{observation['observation_id']}", observation["observation_id"], observation["source_id"], decision, "DOMAIN_ONLY", reason, confidence, _utc_now())
    return recommendation.to_dict()


def active_knowledge_eligibility(review: dict[str, Any]) -> dict[str, Any]:
    normalized = validate_review(review)
    eligible = normalized["decision"] in ACTIVE_DECISIONS
    return {"eligible": eligible, "status": "ACTIVE_KNOWLEDGE_CANDIDATE" if eligible else "BLOCKED_PENDING_ACCEPTANCE", "decision": normalized["decision"], "scope": normalized["scope_confirmation"], "reason": "Human acceptance confirms interpretation only; cross-source and cross-domain promotion remains separate." if eligible else "Only ACCEPT or ACCEPT_WITH_LIMITATION may enter future knowledge candidates."}


def is_active_candidate(review: dict[str, Any]) -> bool:
    return bool(active_knowledge_eligibility(review)["eligible"])


def review_priority(observation: dict[str, Any]) -> str:
    if observation.get("evidence_type") in {"VISUAL_INFERENCE", "MODEL_INTERPRETATION"} or observation.get("scope") == "GLOBAL_CANDIDATE":
        return "HIGH"
    if observation.get("scope") == "DOMAIN":
        return "MEDIUM"
    return "LOW"


def source_bias_metadata(sources: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    result = []
    for source in sources:
        bias = "MANUFACTURER_CASE_STUDY_BIAS" if source.get("source_type") == "MANUFACTURER_CASE_STUDY" or source.get("publisher") in {"Ayrton", "ETC"} else "NONE_IDENTIFIED"
        result.append({"source_id": source["source_id"], "selection_bias": bias, "review_note": "Bias lowers confidence/context certainty; it does not automatically reject the source."})
    return result


def _matrix(pack: dict[str, Any], names: Iterable[str], field: str) -> list[dict[str, Any]]:
    result = []
    for name in names:
        linked = [item for item in pack.get("observations", []) if name in item.get(field, [])]
        supporting = [item["observation_id"] for item in linked if item.get("stance") == "SUPPORTS"]
        conflicting = [item["observation_id"] for item in linked if item.get("stance") in {"CONTRADICTS", "CONTEXT_DEPENDENT"}]
        result.append({"name": name, "supporting_observations": supporting, "conflicting_observations": conflicting, "human_accepted": [], "needs_context": [], "rejected": [], "current_status": "PENDING_HUMAN_REVIEW"})
    return result


def principle_review_matrix(pack: dict[str, Any], principles: Iterable[str]) -> list[dict[str, Any]]:
    return _matrix(pack, principles, "principle_refs")


def antipattern_review_matrix(pack: dict[str, Any], anti_patterns: Iterable[str]) -> list[dict[str, Any]]:
    return _matrix(pack, anti_patterns, "anti_pattern_refs")


def observation_priority_summary(observations: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    result = {priority: [] for priority in PRIORITIES}
    for item in observations:
        result[review_priority(item)].append(item["observation_id"])
    return result
