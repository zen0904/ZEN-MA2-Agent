from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import Fixture, Group, StateSnapshot


class StateStore:
    """Shared read-only show-state cache. Providers are the only writers."""

    def __init__(self) -> None:
        self._snapshots: dict[str, StateSnapshot] = {}

    def put_groups(self, values: Iterable[Group]) -> StateSnapshot:
        snapshot = StateSnapshot.create("groups", list(values))
        self._snapshots["groups"] = snapshot
        return snapshot

    def put_fixtures(self, values: Iterable[Fixture]) -> StateSnapshot:
        snapshot = StateSnapshot.create("fixtures", list(values))
        self._snapshots["fixtures"] = snapshot
        return snapshot

    def get(self, resource: str) -> StateSnapshot | None:
        return self._snapshots.get(resource)

    def has(self, resources: Iterable[str]) -> bool:
        return all(resource in self._snapshots for resource in resources)

    def summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in ("groups", "fixtures", "presets", "sequences", "cues", "executors", "effects", "layouts", "timecodes", "programmer", "selection", "patch"):
            snapshot = self.get(name)
            result[name] = {"status": "available", "count": len(snapshot.values), "updated_at": snapshot.updated_at, "values": snapshot.values} if snapshot else {"status": "Not available yet", "values": []}
        return result
