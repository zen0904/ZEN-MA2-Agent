from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Group:
    number: int
    name: str


@dataclass(frozen=True)
class Fixture:
    number: int
    name: str
    fixture_type: str | None = None


@dataclass(frozen=True)
class Sequence:
    number: int
    name: str


@dataclass(frozen=True)
class Cue:
    sequence: int
    number: float
    name: str
    trigger: str | None = None
    fade: float | None = None
    delay: float | None = None


@dataclass(frozen=True)
class StateSnapshot:
    resource: str
    values: list[dict[str, Any]]
    updated_at: str
    source: str
    stale: bool = False
    error: str | None = None

    @classmethod
    def create(cls, resource: str, values: list[Any], *, source: str) -> "StateSnapshot":
        normalized = [asdict(value) if is_dataclass(value) else dict(value) for value in values]
        return cls(resource, normalized, datetime.now(timezone.utc).isoformat(), source)
