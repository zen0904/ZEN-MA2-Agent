from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import Fixture, Group, StateSnapshot


class StateStore:
    """Shared read-only show-state cache. Providers are the only writers."""

    def __init__(self) -> None:
        self._snapshots: dict[str, StateSnapshot] = {}

    RESOURCES = ("groups", "fixtures", "fixture_geometry", "fixture_type_profiles", "group_membership", "layouts", "layout_items", "selection", "programmer", "sequences", "cues", "presets", "effects", "pages", "executors", "timecodes")

    def put(self, resource: str, values: Iterable[Any], *, source: str, capability: dict[str, Any] | None = None) -> StateSnapshot:
        if resource not in self.RESOURCES:
            raise ValueError(f"Unknown state resource: {resource}")
        snapshot = StateSnapshot.create(resource, list(values), source=source, capability=capability)
        self._snapshots[resource] = snapshot
        return snapshot

    def put_groups(self, values: Iterable[Group]) -> StateSnapshot:
        return self.put("groups", values, source="ma2_telnet_list")

    def put_fixtures(self, values: Iterable[Fixture]) -> StateSnapshot:
        return self.put("fixtures", values, source="ma2_telnet_list")

    def upsert(self, resource: str, key: str, value: dict[str, Any], *, source: str, capability: dict[str, Any] | None = None) -> StateSnapshot:
        existing = self.get(resource)
        values = list(existing.values) if existing else []
        values = [item for item in values if item.get(key) != value.get(key)]
        values.append(value)
        return self.put(resource, values, source=source, capability=capability)

    def record_error(self, resource: str, error: str, *, source: str, capability: dict[str, Any] | None = None) -> StateSnapshot:
        existing = self.get(resource)
        values = list(existing.values) if existing else []
        snapshot = StateSnapshot.create(resource, values, source=source, capability=capability if capability is not None else existing.capability if existing else None)
        snapshot = StateSnapshot(snapshot.resource, snapshot.values, snapshot.updated_at, snapshot.source, bool(existing), error, snapshot.capability)
        self._snapshots[resource] = snapshot
        return snapshot

    def mark_stale(self, resource: str, reason: str = "Connection changed; refresh required.") -> None:
        snapshot = self.get(resource)
        if snapshot:
            self._snapshots[resource] = StateSnapshot(snapshot.resource, snapshot.values, snapshot.updated_at, snapshot.source, True, reason, snapshot.capability)

    def get(self, resource: str) -> StateSnapshot | None:
        return self._snapshots.get(resource)

    def has(self, resources: Iterable[str]) -> bool:
        return all((snapshot := self.get(resource)) is not None and not snapshot.stale and not snapshot.error for resource in resources)

    def summary(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name in self.RESOURCES:
            snapshot = self.get(name)
            if not snapshot:
                result[name] = {"status": "Not available yet", "count": 0, "updated_at": None, "source": None, "stale": False, "error": None, "capability": None, "values": []}
            else:
                status = "UNSUPPORTED" if snapshot.error and snapshot.error.startswith("UNSUPPORTED") else "ERROR" if snapshot.error else "available"
                result[name] = {"status": status, "count": len(snapshot.values), "updated_at": snapshot.updated_at, "source": snapshot.source, "stale": snapshot.stale, "error": snapshot.error, "capability": snapshot.capability, "values": snapshot.values}
        return result
