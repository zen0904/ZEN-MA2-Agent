from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class SafetyLevel(str, Enum):
    SAFE = "SAFE"
    MODIFY = "MODIFY"
    DANGEROUS = "DANGEROUS"


@dataclass(frozen=True)
class Intent:
    kind: str
    parameters: dict[str, Any]
    source_text: str


@dataclass(frozen=True)
class CommandPlan:
    intent: Intent
    command: str | None
    safety: SafetyLevel
    preview_note: str
    executable: bool

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["safety"] = self.safety.value
        return result
