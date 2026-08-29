from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from .models import Intent
from .parser import ParseError, parse
from .skill_system import SkillManifest, SkillRegistry


class ResponseType(str, Enum):
    ANSWER = "ANSWER"
    ACTION_PLAN = "ACTION_PLAN"
    SKILL_PROPOSAL = "SKILL_PROPOSAL"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class RequestRoute:
    response_type: ResponseType
    normalized_text: str
    intent: Intent | None = None
    capability: SkillManifest | None = None


class IntentRouter:
    """General request entrypoint; deterministic parsing is one provider only."""

    _clone = re.compile(
        r"(?:複製|clone)\s*(?:群組|group)\s*(\d+)\s*(?:變|到|to)\s*(?:群組|group)?\s*(\d+)",
        re.I,
    )

    def normalize(self, text: str) -> str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).strip())

    def route(self, text: str, registry: SkillRegistry) -> RequestRoute:
        normalized = self.normalize(text)
        if not normalized:
            return RequestRoute(ResponseType.NEEDS_CLARIFICATION, normalized)
        clone = self._clone.fullmatch(normalized)
        if clone:
            intent = Intent("group_clone", {"source_group": int(clone.group(1)), "destination_group": int(clone.group(2))}, normalized)
            return self._capability_route(normalized, intent, registry)
        try:
            intent = parse(normalized)
        except ParseError:
            return RequestRoute(ResponseType.NEEDS_CLARIFICATION, normalized)
        if intent.kind.startswith("state_") or intent.kind in {"preset_list", "effect_list", "effect_lookup", "sequence_executor_lookup", "page_executor_list"}:
            return RequestRoute(ResponseType.ANSWER, normalized, intent)
        return self._capability_route(normalized, intent, registry)

    @staticmethod
    def _capability_route(normalized: str, intent: Intent, registry: SkillRegistry) -> RequestRoute:
        capability = registry.capability_for_intent(intent.kind)
        if not capability:
            return RequestRoute(ResponseType.NEEDS_CLARIFICATION, normalized, intent)
        if not capability.enabled or not capability.executable:
            return RequestRoute(ResponseType.NOT_IMPLEMENTED, normalized, intent, capability)
        return RequestRoute(ResponseType.ACTION_PLAN, normalized, intent, capability)
