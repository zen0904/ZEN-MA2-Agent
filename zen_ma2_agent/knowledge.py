"""Evidence-bound lighting design knowledge models.

This module is deliberately local and inert: it stores claims, context and
provenance for future Designer use, but it does not call MA2 or promote a
single case or user reaction into a global rule.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Iterable


EVIDENCE_SCHEMA = "zen.lighting_design_evidence.v0.1"
SOURCE_TYPES = {"INDUSTRY_REFERENCE", "GENERAL_PRINCIPLE", "TRAINING_CASE", "USER_FEEDBACK", "REAL_SHOW_REVIEW", "MODEL_INFERENCE"}
DOMAINS = {"CONCERT", "KPOP", "BAND", "THEATRE", "SMALL_VENUE", "LIMITED_RIG", "GENERAL", "OTHER"}
SCOPES = {"GLOBAL", "DOMAIN", "CASE", "USER"}
FEEDBACK_TYPES = {"USER_LIKED", "USER_DISLIKED", "USER_PREFERRED_A_OVER_B", "USER_NEUTRAL", "USER_UNCERTAIN"}
AB_RESPONSES = {"A_PREFERRED", "B_PREFERRED", "BOTH_ACCEPTABLE", "BOTH_REJECTED", "NO_PREFERENCE"}


def _id(prefix: str, *parts: Any) -> str:
    digest = sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _walk_no_commands(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = {"command", "commands", "raw_command", "telnet", "lua", "ma_command"} & set(value)
        if forbidden:
            raise ValueError("Design evidence cannot contain MA2 command fields.")
        for nested in value.values():
            _walk_no_commands(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk_no_commands(nested)


@dataclass(frozen=True)
class DesignEvidence:
    evidence_id: str
    source_type: str
    domain: str
    claim: str
    context: dict[str, Any]
    support_count: int = 1
    contradiction_count: int = 0
    confidence: str = "UNKNOWN"
    scope: str = "CASE"
    provenance: str = "UNSPECIFIED"
    review_status: str = "UNREVIEWED"
    def __post_init__(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            raise ValueError("Invalid evidence source_type.")
        if self.domain not in DOMAINS:
            raise ValueError("Invalid evidence domain.")
        if self.scope not in SCOPES:
            raise ValueError("Invalid evidence scope.")
        if not self.claim.strip() or self.support_count < 0 or self.contradiction_count < 0:
            raise ValueError("Evidence claim/counts are invalid.")
        _walk_no_commands(self.context)
    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["schema"] = EVIDENCE_SCHEMA
        return value


def validate_evidence(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != EVIDENCE_SCHEMA:
        raise ValueError(f"Evidence schema must be {EVIDENCE_SCHEMA}.")
    required = {"evidence_id", "source_type", "domain", "claim", "context", "support_count", "contradiction_count", "confidence", "scope", "provenance", "review_status"}
    if not required <= set(value):
        raise ValueError("Evidence record is incomplete.")
    DesignEvidence(**{key: value[key] for key in required - {"schema"}})
    return dict(value)


def industry_reference(*, evidence_id: str, domain: str, claim: str, context: dict[str, Any], provenance: str, support_count: int = 1, contradiction_count: int = 0, confidence: str = "MEDIUM") -> dict[str, Any]:
    return DesignEvidence(evidence_id, "INDUSTRY_REFERENCE", domain, claim, context, support_count, contradiction_count, confidence, "DOMAIN", provenance, "UNREVIEWED").to_dict()


def general_principle_evidence(*, principle: str, claim: str, provenance: str = "CURRENT_INTERNAL_GENERAL_PRINCIPLE", support_count: int = 1) -> dict[str, Any]:
    return DesignEvidence(_id("principle", principle), "GENERAL_PRINCIPLE", "GENERAL", claim, {"principle": principle}, support_count, 0, "MEDIUM" if support_count > 1 else "LOW", "GLOBAL", provenance, "CANDIDATE").to_dict()


def training_case_evidence(*, case_id: str, claim: str, context: dict[str, Any], provenance: str = "TRAINING_CASE_CONTEXT") -> dict[str, Any]:
    return DesignEvidence(_id("case", case_id, claim), "TRAINING_CASE", "GENERAL", claim, {"case_id": case_id, **context}, 1, 0, "CASE_LOCAL", "CASE", provenance, "UNREVIEWED").to_dict()


def real_show_review(*, evidence_id: str, domain: str, claim: str, context: dict[str, Any], provenance: str) -> dict[str, Any]:
    return DesignEvidence(evidence_id, "REAL_SHOW_REVIEW", domain, claim, context, 1, 0, "MEDIUM", "CASE", provenance, "UNREVIEWED").to_dict()


def user_feedback(*, feedback_type: str, claim: str, case_id: str, song_id: str, rig_id: str, context: dict[str, Any] | None = None, evidence_id: str | None = None) -> dict[str, Any]:
    if feedback_type not in FEEDBACK_TYPES:
        raise ValueError("Unsupported normalized feedback type.")
    return DesignEvidence(
        evidence_id or _id("feedback", feedback_type, claim, case_id, song_id, rig_id),
        "USER_FEEDBACK", "GENERAL", claim,
        {"feedback_type": feedback_type, "case_id": case_id, "song_id": song_id, "rig_id": rig_id, **(context or {})},
        1, 0, "LOW", "CASE", "USER_FEEDBACK_SINGLE_OBSERVATION", "UNREVIEWED",
    ).to_dict()


def case_context(*, case_id: str, domain: str, claim: str, context: dict[str, Any]) -> dict[str, Any]:
    return DesignEvidence(_id("context", case_id, claim), "TRAINING_CASE", domain, claim, {"case_id": case_id, **context}, 1, 0, "CASE_LOCAL", "CASE", "CURRENT_CASE_CONTEXT", "UNREVIEWED").to_dict()


def evaluate_user_promotion(records: Iterable[dict[str, Any]], claim: str, *, min_feedback: int = 3, min_cases: int = 2, min_rigs: int = 2) -> dict[str, Any]:
    matches = [item for item in records if item.get("source_type") == "USER_FEEDBACK" and item.get("claim") == claim]
    cases = {item.get("context", {}).get("case_id") for item in matches if item.get("context", {}).get("case_id")}
    rigs = {item.get("context", {}).get("rig_id") for item in matches if item.get("context", {}).get("rig_id")}
    eligible = len(matches) >= min_feedback and len(cases) >= min_cases and len(rigs) >= min_rigs
    if not eligible:
        return {"status": "CASE_FEEDBACK_ONLY", "promoted": False, "reason": "Single or insufficiently repeated feedback cannot become a global or style rule.", "support_count": len(matches), "case_count": len(cases), "rig_count": len(rigs)}
    candidate = user_preference_candidate(claim=claim, support_count=len(matches), case_count=len(cases), rig_count=len(rigs))
    return {"status": "USER_PREFERENCE_CANDIDATE", "promoted": True, "candidate": candidate, "support_count": len(matches), "case_count": len(cases), "rig_count": len(rigs)}


def user_preference_candidate(*, claim: str, support_count: int, case_count: int, rig_count: int) -> dict[str, Any]:
    if support_count < 1 or case_count < 1 or rig_count < 1:
        raise ValueError("Preference candidate evidence is insufficient.")
    return DesignEvidence(_id("preference", claim), "USER_FEEDBACK", "GENERAL", claim, {"supporting_cases": case_count, "supporting_rigs": rig_count}, support_count, 0, "CANDIDATE", "USER", "REPEATED_CROSS_CASE_FEEDBACK", "CANDIDATE").to_dict()


def evaluate_general_promotion(records: Iterable[dict[str, Any]], claim: str, *, min_sources: int = 2, min_domains: int = 2) -> dict[str, Any]:
    matches = [item for item in records if item.get("claim") == claim and item.get("source_type") in {"INDUSTRY_REFERENCE", "GENERAL_PRINCIPLE", "REAL_SHOW_REVIEW", "TRAINING_CASE"}]
    domains = {item.get("domain") for item in matches}
    if len(matches) < min_sources or len(domains) < min_domains:
        return {"status": "CANDIDATE_ONLY", "promoted": False, "support_count": len(matches), "domain_count": len(domains), "reason": "A single case or domain cannot overwrite general knowledge."}
    return {"status": "GENERAL_CANDIDATE", "promoted": True, "support_count": len(matches), "domain_count": len(domains), "evidence_ids": [item.get("evidence_id") for item in matches]}


def ab_review(*, variant_a: str, variant_b: str, response: str, context: dict[str, Any], evidence_id: str | None = None) -> dict[str, Any]:
    if response not in AB_RESPONSES:
        raise ValueError("Invalid A/B response.")
    return DesignEvidence(evidence_id or _id("ab", variant_a, variant_b, response), "USER_FEEDBACK", "GENERAL", response, {"variant_a": variant_a, "variant_b": variant_b, **context}, 1, 0, "LOW", "CASE", "AB_REVIEW_SINGLE_OBSERVATION", "UNREVIEWED").to_dict()


@dataclass(frozen=True)
class DesignDecisionScores:
    professional_design_score: float | None
    context_fit_score: float | None
    user_preference_score: float | None
    evidence_confidence: str
    def __post_init__(self) -> None:
        for value in (self.professional_design_score, self.context_fit_score, self.user_preference_score):
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError("Design scores must be between 0 and 1 or None.")
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_conflict(*, industry_support: int, user_disliked: int, claim: str) -> dict[str, Any]:
    if industry_support > 0 and user_disliked > 0:
        return {"status": "PROFESSIONALLY_VALID_USER_STYLE_DIVERGENCE", "claim": claim, "preserve_industry_knowledge": True, "create_user_variant": True}
    return {"status": "NO_CONFLICT_EVIDENCE", "claim": claim, "preserve_industry_knowledge": True, "create_user_variant": False}

