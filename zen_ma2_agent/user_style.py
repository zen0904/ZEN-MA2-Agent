"""Human-reviewed user style evidence, intentionally separate from Designer style."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

SCHEMA = "zen.user_style_evidence.v0.1"
CANDIDATE_SCHEMA = "zen.user_style_candidate.v0.1"
REVIEW_SCHEMA = "zen.user_style_review.v0.1"
REFERENCE_TYPES = {"POSITIVE_VISUAL_REFERENCE", "NEGATIVE_VISUAL_REFERENCE", "COMPARATIVE_PREFERENCE", "DIRECT_USER_STATEMENT", "A_B_C_ENERGY_REVIEW"}
STRENGTHS = {"STRONG_POSITIVE", "POSITIVE", "NEUTRAL", "NEGATIVE", "STRONG_NEGATIVE"}
SCOPES = {"CASE_LOCAL", "CROSS_CASE_CANDIDATE", "USER_STYLE_CANDIDATE"}
STATUSES = {"SUPPORTED", "PARTIAL", "UNKNOWN", "REJECTED_BY_EVIDENCE"}
REVIEW_DECISIONS = {"UNSET", "ACCEPT", "ACCEPT_WITH_LIMITATION", "NEEDS_MORE_EVIDENCE", "REJECT", "UNSURE"}
REVIEW_PRIORITIES = {"HIGH", "NORMAL", "LOW"}
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "script"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("User style evidence cannot contain MA2 commands.")
        for item in value.values():
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)


@dataclass(frozen=True)
class UserStyleEvidence:
    evidence_id: str
    source_reference: str
    reference_domain: str
    reference_type: str
    user_reaction: str
    normalized_traits: tuple[str, ...]
    strength: str
    scope: str
    confidence: str
    evidence_count: int
    contradictions: tuple[str, ...]
    provenance: str = "HUMAN_VISUAL_REVIEW"
    reviewed_at: str = ""
    raw_user_reaction: str = ""
    normalized_interpretation: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.source_reference.strip() or not self.user_reaction.strip():
            raise ValueError("Evidence identity, source and reaction are required.")
        if self.reference_type not in REFERENCE_TYPES or self.strength not in STRENGTHS or self.scope not in SCOPES:
            raise ValueError("Invalid user style evidence classification.")
        if self.provenance != "HUMAN_VISUAL_REVIEW":
            raise ValueError("User style evidence must retain human visual provenance.")
        if self.evidence_count < 1:
            raise ValueError("evidence_count must be positive")
        if not self.raw_user_reaction:
            object.__setattr__(self, "raw_user_reaction", self.user_reaction)
        _safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["normalized_traits"] = list(self.normalized_traits)
        data["contradictions"] = list(self.contradictions)
        return {"schema": SCHEMA, **data}


def validate_evidence(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        raise ValueError(f"Evidence schema must be {SCHEMA}.")
    _safe(value)
    fields = set(UserStyleEvidence.__dataclass_fields__)
    missing = fields - {"provenance", "reviewed_at", "raw_user_reaction", "normalized_interpretation"} - set(value)
    if missing:
        raise ValueError(f"Evidence is missing: {', '.join(sorted(missing))}")
    payload = {key: value[key] for key in fields if key in value}
    payload.setdefault("provenance", "HUMAN_VISUAL_REVIEW")
    payload.setdefault("reviewed_at", "")
    payload.setdefault("raw_user_reaction", payload.get("user_reaction", ""))
    payload.setdefault("normalized_interpretation", "")
    payload["normalized_traits"] = tuple(payload["normalized_traits"])
    payload["contradictions"] = tuple(payload["contradictions"])
    return UserStyleEvidence(**payload).to_dict()


@dataclass(frozen=True)
class StyleCandidate:
    candidate_id: str
    name: str
    meaning: str
    supporting_references: tuple[str, ...]
    contradicting_references: tuple[str, ...]
    evidence_strength: str
    confidence: str
    promotion_status: str = "HUMAN_REVIEWED_CANDIDATE"
    promoted: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.name.strip() or not self.meaning.strip():
            raise ValueError("Style candidate identity and meaning are required.")
        if self.promoted or self.promotion_status != "HUMAN_REVIEWED_CANDIDATE":
            raise ValueError("Permanent style promotion is disabled in this layer.")
        _safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["supporting_references"] = list(self.supporting_references)
        value["contradicting_references"] = list(self.contradicting_references)
        return {"schema": CANDIDATE_SCHEMA, **value}


@dataclass(frozen=True)
class UserStyleReview:
    candidate_id: str
    evidence_ids: tuple[str, ...]
    decision: str = "UNSET"
    scope: str = "USER_STYLE_CANDIDATE"
    rationale: str = ""
    limitations: str = ""
    reviewer: str = "UNASSIGNED"
    reviewed_at: str = ""
    version: str = "v0.1"
    ai_recommendation: str = "UNSURE"
    priority: str = "NORMAL"

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("Review must reference a candidate.")
        if self.decision not in REVIEW_DECISIONS or self.scope not in SCOPES:
            raise ValueError("Invalid user style review decision or scope.")
        if self.ai_recommendation not in REVIEW_DECISIONS - {"UNSET"}:
            raise ValueError("Invalid AI recommendation.")
        if self.priority not in REVIEW_PRIORITIES:
            raise ValueError("Invalid review priority.")
        _safe(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_ids"] = list(self.evidence_ids)
        return {"schema": REVIEW_SCHEMA, **value}


def validate_review(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != REVIEW_SCHEMA:
        raise ValueError(f"Review schema must be {REVIEW_SCHEMA}.")
    _safe(value)
    fields = set(UserStyleReview.__dataclass_fields__)
    missing = fields - {"decision", "scope", "rationale", "limitations", "reviewer", "reviewed_at", "version", "ai_recommendation", "priority"} - set(value)
    if missing:
        raise ValueError(f"Review is missing: {', '.join(sorted(missing))}")
    payload = {key: value[key] for key in fields if key in value}
    payload.setdefault("decision", "UNSET")
    payload.setdefault("scope", "USER_STYLE_CANDIDATE")
    payload.setdefault("rationale", "")
    payload.setdefault("limitations", "")
    payload.setdefault("reviewer", "UNASSIGNED")
    payload.setdefault("reviewed_at", "")
    payload.setdefault("version", "v0.1")
    payload.setdefault("ai_recommendation", "UNSURE")
    payload.setdefault("priority", "NORMAL")
    payload["evidence_ids"] = tuple(payload["evidence_ids"])
    return UserStyleReview(**payload).to_dict()


def _seed_recommendation(candidate: dict[str, Any]) -> str:
    status = candidate.get("status")
    if status == "SUPPORTED":
        return "ACCEPT_WITH_LIMITATION"
    if status == "PARTIAL":
        return "NEEDS_MORE_EVIDENCE"
    if status == "REJECTED_BY_EVIDENCE":
        return "REJECT"
    return "UNSURE"


def build_review_records(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create review-ready records; every human decision remains UNSET."""
    records = []
    for candidate in candidates:
        records.append(UserStyleReview(
            candidate_id=candidate["candidate_id"],
            evidence_ids=tuple(candidate.get("supporting_references", ())) + tuple(candidate.get("contradicting_references", ())),
            decision="UNSET",
            rationale="",
            limitations="Human review must confirm scope and context before future knowledge consideration.",
            ai_recommendation=_seed_recommendation(candidate),
        ).to_dict())
    return records


def validate_candidate(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") != CANDIDATE_SCHEMA:
        raise ValueError(f"Candidate schema must be {CANDIDATE_SCHEMA}.")
    fields = set(StyleCandidate.__dataclass_fields__)
    missing = fields - set(value)
    if missing:
        raise ValueError(f"Candidate is missing: {', '.join(sorted(missing))}")
    payload = {key: value[key] for key in fields}
    payload["supporting_references"] = tuple(payload["supporting_references"])
    payload["contradicting_references"] = tuple(payload["contradicting_references"])
    return StyleCandidate(**payload).to_dict()


def synthesize_candidates(evidence: Iterable[dict[str, Any]], names: Iterable[str]) -> list[dict[str, Any]]:
    records = [validate_evidence(item) for item in evidence]
    result = []
    for name in names:
        support = [r["evidence_id"] for r in records if name in r["normalized_traits"] and r["strength"] in {"STRONG_POSITIVE", "POSITIVE"}]
        contradict = [r["evidence_id"] for r in records if name in r["contradictions"]]
        if name == "HIGH_IMPACT_ALWAYS":
            result.append(StyleCandidate(f"candidate_{name}", name, "High impact is required in every look.", tuple(support), tuple(contradict) or ["EVIDENCE_LOW_ENERGY_POSITIVE", "EVIDENCE_MINIMALISM_POSITIVE"], "REJECTED", "HIGH").to_dict() | {"status": "REJECTED_BY_EVIDENCE"})
            continue
        status = "SUPPORTED" if len(support) >= 2 and not contradict else "PARTIAL" if support else "UNKNOWN"
        strength = "STRONG" if len(support) >= 3 else "MODERATE" if support else "WEAK"
        confidence = "HIGH" if len(support) >= 3 and not contradict else "MEDIUM" if support else "LOW"
        meaning = {
            "IMPACT_WHEN_MUSICALLY_JUSTIFIED": "Use transient impact when section, rhythm and emotional contour justify it; restraint remains valid.",
            "MULTI_LEVEL_ENERGY_DESIGN": "Low, medium and high energy states are each complete looks and develop meaningfully.",
            "CONTROLLED_MAXIMALISM": "Dense layers are welcome when hierarchy, palette, timing and geometry remain organized.",
            "PALETTE_COHERENCE": "A dominant theme and coherent palette are preferred over random color mixing.",
        }.get(name, name.replace("_", " ").title())
        result.append(StyleCandidate(f"candidate_{name}", name, meaning, tuple(support), tuple(contradict), strength, confidence).to_dict() | {"status": status})
    return result


def compare_with_industry(candidates: Iterable[dict[str, Any]], pack002: dict[str, Any]) -> list[dict[str, Any]]:
    categories = {o.get("category") for o in pack002.get("observations", [])}
    result = []
    for candidate in candidates:
        name = candidate["name"]
        if name in {"CONTROLLED_MAXIMALISM", "PALETTE_COHERENCE", "MUSIC_STRUCTURE_ALIGNMENT", "CLEAN_VISUAL_HIERARCHY"}:
            status = "ALIGN" if name == "CONTROLLED_MAXIMALISM" and "CONTROLLED_MAXIMALISM" in categories else "PARTIAL_ALIGN"
        elif name in {"INTENTIONAL_RESTRAINT", "NEGATIVE_SPACE_ACCEPTANCE"}:
            status = "PARTIAL_ALIGN"
        else:
            status = "UNKNOWN"
        result.append({"candidate": name, "status": status, "time_window": "2022-2025", "promoted": False})
    return result
