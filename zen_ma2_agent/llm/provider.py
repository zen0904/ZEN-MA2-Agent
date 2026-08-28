from __future__ import annotations

from typing import Protocol

from ..models import Intent


class LLMProvider(Protocol):
    """Reserved provider boundary. The deterministic parser remains the default."""

    def propose_intent(self, request: str) -> Intent | None: ...
