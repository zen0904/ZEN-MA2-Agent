"""Metadata-only visual reference records for review and shadow reasoning."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

SCHEMA = "zen.visual_reference.v0.1"
REVIEW_STATUSES = {"NEEDS_REVIEW", "HUMAN_CONFIRMED", "REJECTED"}
REFERENCE_KINDS = {"POSITIVE", "NEGATIVE", "MIXED"}
MEDIA_ORIGINS = {"EXTERNAL_WEB", "USER_PROVIDED_MEDIA", "LOCAL_REFERENCE"}


@dataclass(frozen=True)
class VisualReference:
    reference_id: str
    title: str
    source_url: str | None
    publisher: str
    retrieved_at: str
    reference_kind: str
    observations: tuple[str, ...]
    transferable_concepts: tuple[str, ...]
    non_transferable_specifics: tuple[str, ...]
    related_topics: tuple[str, ...]
    confidence: str
    review_status: str
    media_origin: str = "EXTERNAL_WEB"
    media_ref: str | None = None
    media_policy: str = "METADATA_ONLY_NO_BINARY_MEDIA"

    def __post_init__(self) -> None:
        if not self.reference_id.strip() or not self.title.strip():
            raise ValueError("Visual reference identity and title are required.")
        if self.media_origin not in MEDIA_ORIGINS:
            raise ValueError("Invalid visual reference media origin.")
        if self.source_url is not None and not self.source_url.startswith(("https://", "http://")):
            raise ValueError("Visual reference source_url must be an HTTP(S) URL when supplied.")
        if self.source_url is None and not (self.media_origin == "USER_PROVIDED_MEDIA" and self.media_ref):
            raise ValueError("A reference without source_url requires USER_PROVIDED_MEDIA and media_ref.")
        if self.reference_kind not in REFERENCE_KINDS or self.review_status not in REVIEW_STATUSES:
            raise ValueError("Invalid visual reference kind or review status.")
        if self.media_policy != "METADATA_ONLY_NO_BINARY_MEDIA":
            raise ValueError("Visual references must remain metadata-only.")
        if not self.observations or not self.transferable_concepts:
            raise ValueError("Visual references require bounded observations and concepts.")

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, **asdict(self), "observations": list(self.observations), "transferable_concepts": list(self.transferable_concepts), "non_transferable_specifics": list(self.non_transferable_specifics), "related_topics": list(self.related_topics)}


def validate_visual_reference(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") != SCHEMA:
        raise ValueError(f"Visual reference schema must be {SCHEMA}.")
    defaults = {"media_origin": "EXTERNAL_WEB", "media_ref": None, "media_policy": "METADATA_ONLY_NO_BINARY_MEDIA"}
    fields = {field: value[field] if field in value else defaults[field] for field in VisualReference.__dataclass_fields__}
    for name in ("observations", "transferable_concepts", "non_transferable_specifics", "related_topics"):
        fields[name] = tuple(fields[name])
    return VisualReference(**fields).to_dict()
