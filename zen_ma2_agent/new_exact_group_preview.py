"""Pure preview for a new Agent-owned exact-subfixture Test Show Group.

No transport, approval, or execution entry point is provided here. A later
write gate must re-scan occupancy and verify a native raw Group export.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from .allocation import first_free_from_front


class NewExactGroupPreviewError(ValueError):
    pass


_REF = re.compile(r"([1-9]\d*)\.([1-9]\d*)\Z")
_LABEL = re.compile(r"ZEN_[A-Z0-9_]{1,56}\Z")


def preview_new_exact_group(
    profile: Mapping[str, Any], *, label: str, fixture_refs: Sequence[str]
) -> dict[str, Any]:
    """Validate a fresh read-only inventory and describe, but never execute, a write."""
    resources = profile.get("resources")
    if not isinstance(resources, Mapping):
        raise NewExactGroupPreviewError("Fresh read-only Show resource metadata is required.")
    now = datetime.now(timezone.utc)
    for name in ("groups", "fixtures", "fixture_geometry"):
        meta = resources.get(name)
        if (not isinstance(meta, Mapping) or meta.get("status") != "SUPPORTED"
                or meta.get("stale") is not False or not meta.get("updated_at")):
            raise NewExactGroupPreviewError(f"Fresh read-only {name} inventory is required.")
        try:
            observed = datetime.fromisoformat(str(meta["updated_at"]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise NewExactGroupPreviewError(f"Fresh read-only {name} timestamp is invalid.") from exc
        if observed.tzinfo is None or not -timedelta(seconds=5) <= now - observed <= timedelta(seconds=60):
            raise NewExactGroupPreviewError(f"Fresh read-only {name} inventory is required.")
    if not isinstance(label, str) or not _LABEL.fullmatch(label):
        raise NewExactGroupPreviewError("An ASCII Agent-owned ZEN_ label is required.")
    if isinstance(fixture_refs, (str, bytes)) or not isinstance(fixture_refs, Sequence) or not fixture_refs:
        raise NewExactGroupPreviewError("At least one exact fixture.subfixture ref is required.")

    allowed: set[str] = set()
    fixtures = profile.get("fixtures")
    if not isinstance(fixtures, list):
        raise NewExactGroupPreviewError("Verified fixture inventory is required.")
    for fixture in fixtures:
        if not isinstance(fixture, Mapping):
            raise NewExactGroupPreviewError("Malformed fixture inventory.")
        fixture_id = fixture.get("fixture_id")
        geometry = fixture.get("stage_geometry")
        subfixtures = geometry.get("subfixtures") if isinstance(geometry, Mapping) else None
        if not isinstance(fixture_id, int) or isinstance(fixture_id, bool) or not isinstance(subfixtures, list):
            raise NewExactGroupPreviewError("Exact subfixture inventory is required.")
        for subfixture in subfixtures:
            sub_id = subfixture.get("subfixture_id") if isinstance(subfixture, Mapping) else None
            if isinstance(sub_id, int) and not isinstance(sub_id, bool) and sub_id > 0:
                allowed.add(f"{fixture_id}.{sub_id}")

    refs = tuple(fixture_refs)
    if not all(isinstance(ref, str) for ref in refs):
        raise NewExactGroupPreviewError("Exact fixture refs must be strings.")
    if len(set(refs)) != len(refs):
        raise NewExactGroupPreviewError("Duplicate exact fixture refs are forbidden.")
    for ref in refs:
        match = _REF.fullmatch(ref) if isinstance(ref, str) else None
        if match is None or int(match.group(1)) == 9999 or ref not in allowed:
            raise NewExactGroupPreviewError(f"Unverified or protected exact fixture ref: {ref!r}.")

    groups = profile.get("groups")
    if not isinstance(groups, list):
        raise NewExactGroupPreviewError("Fresh Group inventory is required.")
    occupied: list[int] = []
    for group in groups:
        group_id = group.get("group_id") if isinstance(group, Mapping) else None
        if not isinstance(group_id, int) or isinstance(group_id, bool) or group_id < 1:
            raise NewExactGroupPreviewError("Malformed Group inventory; allocation cannot be trusted.")
        occupied.append(group_id)
        if group.get("name") == label:
            raise NewExactGroupPreviewError("Agent-owned Group label is already occupied.")
    if len(set(occupied)) != len(occupied):
        raise NewExactGroupPreviewError("Duplicate Group IDs in inventory.")
    group_id = first_free_from_front(occupied)
    commands = ("ClearAll", *(f"Fixture {ref}" for ref in refs),
                f"Store Group {group_id} /nc", f'Label Group {group_id} "{label}"', "ClearAll")
    return {
        "schema": "zen.new_exact_group_preview.v0.1",
        "status": "PREVIEW_ONLY",
        "executable": False,
        "approval_required": True,
        "group_id": group_id,
        "label": label,
        "fixture_refs_in_selection_order": list(refs),
        "commands": list(commands),
        "future_readback_requirement": "EXACT_RAW_EXPORT_GROUP_MEMBER_AND_ORDER_COMPARE",
        "inventory_updated_at": {name: resources[name]["updated_at"] for name in ("groups", "fixtures", "fixture_geometry")},
    }
