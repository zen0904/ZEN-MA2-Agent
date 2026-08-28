from __future__ import annotations

from dataclasses import asdict, dataclass
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
class StateSnapshot:
    resource: str
    values: list[dict[str, Any]]
    updated_at: str

    @classmethod
    def create(cls, resource: str, values: list[Group | Fixture]) -> "StateSnapshot":
        return cls(resource, [asdict(value) for value in values], datetime.now(timezone.utc).isoformat())
