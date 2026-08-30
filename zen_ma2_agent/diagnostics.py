"""Deterministic, read-only Show Diagnostics v1."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .state.store import StateStore


@dataclass(frozen=True)
class DiagnosticFinding:
    id: str
    category: str
    severity: str
    title: str
    summary: str
    details: str
    object_type: str | None
    object_number: int | str | None
    source: str | None
    confidence: str
    suggested_action: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiagnosticReport:
    findings: tuple[DiagnosticFinding, ...]
    capabilities: tuple[dict[str, str], ...]

    @property
    def status(self) -> str:
        levels = {item.severity for item in self.findings}
        return "ERROR" if "ERROR" in levels else "WARNING" if "WARNING" in levels else "OK"

    @property
    def counts(self) -> dict[str, int]:
        return {level: sum(item.severity == level for item in self.findings) for level in ("ERROR", "WARNING", "INFO")}

    def as_dict(self) -> dict[str, Any]:
        return {"status": self.status, "counts": self.counts, "findings": [item.as_dict() for item in self.findings], "capabilities": list(self.capabilities)}


class ShowDiagnostics:
    """Conservative rules over verified StateStore snapshots only."""

    def evaluate(self, state: StateStore) -> DiagnosticReport:
        findings: list[DiagnosticFinding] = []
        for resource in ("groups", "fixtures", "layouts", "presets", "effects", "sequences", "cues", "pages", "executors"):
            findings.extend(self._snapshot_health(state, resource))
        for resource in ("group_membership", "layout_items"):
            if state.get(resource) is not None:
                findings.extend(self._snapshot_health(state, resource))

        groups = self._values(state, "groups")
        names: dict[str, list[dict[str, Any]]] = {}
        for group in groups:
            name = str(group.get("name") or "").strip()
            if not name:
                findings.append(self._finding("group.empty_name", "group", "WARNING", f"Group {group.get('number')} has no name.", object_type="group", object_number=group.get("number"), source=self._source(state, "groups"), suggested="Label the Group if it is intended for operator use."))
            else:
                names.setdefault(name.casefold(), []).append(group)
        for same_name in names.values():
            if len(same_name) > 1:
                numbers = ", ".join(str(item.get("number")) for item in same_name)
                findings.append(self._finding("group.duplicate_name", "group", "WARNING", f'Duplicate Group name "{same_name[0].get("name")}" on Groups {numbers}.', details="The inventory returned the same non-empty Group label more than once.", source=self._source(state, "groups"), suggested="Use distinct labels where Groups need to be addressed by name."))

        memberships = {item.get("group_no"): item for item in self._values(state, "group_membership")}
        for group in groups:
            membership = memberships.get(group.get("number"))
            if membership is not None and not membership.get("fixtures"):
                findings.append(self._finding("group.empty", "group", "WARNING", f'Group {group.get("number")} "{group.get("name", "")}" is empty.', object_type="group", object_number=group.get("number"), source=membership.get("source") or self._source(state, "group_membership"), suggested="Verify membership if this Group should contain fixtures."))

        fixtures = self._values(state, "fixtures")
        findings.extend(self._duplicates(fixtures, "fixture", "Fixture", self._source(state, "fixtures")))
        unlabeled_fixtures = sum(not str(item.get("name") or "").strip() for item in fixtures)
        if unlabeled_fixtures:
            findings.append(self._finding("fixture.unlabeled", "fixture", "INFO", f"{unlabeled_fixtures} Fixtures have no label.", source=self._source(state, "fixtures"), suggested="Fixture labels are optional, but improve Chat results."))

        geometry_reported = False
        for layout in self._values(state, "layout_items"):
            unknown = [item for item in layout.get("items", []) if item.get("type") == "unknown"]
            if unknown:
                details = "Raw tokens: " + ", ".join("[" + ", ".join(map(str, item.get("reference_tokens", []))) + "]" for item in unknown)
                findings.append(self._finding("layout.unresolved_cobjects", "layout", "WARNING", f"Layout {layout.get('layout')} contains {len(unknown)} unresolved CObjects.", details=details, object_type="layout", object_number=layout.get("layout"), source=layout.get("source") or self._source(state, "layout_items"), confidence="verified_export", suggested="Keep tokens for a future validated MA2 mapping probe."))
            geometry = layout.get("fixture_geometry") or {}
            if geometry.get("status") == "UNSUPPORTED" and not geometry_reported:
                geometry_reported = True
                findings.append(self._finding("layout.fixture_geometry_unavailable", "layout", "INFO", "Fixture-level Layout geometry is not currently available.", details=geometry.get("reason", "The current Layout Export provider exposes partial CObjects."), source=geometry.get("source"), confidence="verified_ma2_limit", suggested="Do not interpret this as an empty fixture Layout."))

        presets = self._values(state, "presets")
        unlabeled_presets = sum(self._unlabeled(item) for item in presets)
        if unlabeled_presets:
            findings.append(self._finding("preset.unlabeled", "preset", "INFO", f"{unlabeled_presets} Presets are unlabeled.", source=self._source(state, "presets"), suggested="An empty Preset Pool is valid."))

        effects = self._values(state, "effects")
        findings.extend(self._duplicates(effects, "effect", "Effect", self._source(state, "effects")))
        unlabeled_effects = sum(self._unlabeled(item) for item in effects)
        if unlabeled_effects:
            findings.append(self._finding("effect.unlabeled", "effect", "INFO", f"{unlabeled_effects} Effects are unlabeled.", source=self._source(state, "effects"), suggested="This aggregate does not make a large Effect Pool a warning."))

        sequences = self._values(state, "sequences")
        if self._available(state, "cues"):
            cue_sequences = {item.get("sequence") for item in self._values(state, "cues")}
            for sequence in sequences:
                if sequence.get("number") not in cue_sequences:
                    findings.append(self._finding("sequence.no_cues", "sequence", "INFO", f"Sequence {sequence.get('number')} has no cues.", object_type="sequence", object_number=sequence.get("number"), source=self._source(state, "cues"), suggested="This is valid for an empty or placeholder Sequence."))
        sequence_numbers = {item.get("number") for item in sequences}
        for executor in self._values(state, "executors"):
            if executor.get("assignment_type") == "sequence" and executor.get("assignment") not in sequence_numbers:
                findings.append(self._finding("executor.missing_sequence", "executor", "WARNING", f"Executor {executor.get('location')} references unavailable Sequence {executor.get('assignment')}.", object_type="executor", object_number=executor.get("location"), source=self._source(state, "executors"), suggested="Refresh Sequence and Executor inventories, then verify assignment."))
        return DiagnosticReport(tuple(findings), tuple(self._capabilities(state)))

    @staticmethod
    def _values(state: StateStore, resource: str) -> list[dict[str, Any]]:
        snapshot = state.get(resource)
        return list(snapshot.values) if snapshot else []

    @staticmethod
    def _source(state: StateStore, resource: str) -> str | None:
        snapshot = state.get(resource)
        return snapshot.source if snapshot else None

    @staticmethod
    def _unlabeled(item: dict[str, Any]) -> bool:
        name = str(item.get("name") or "").strip()
        return not name or name == str(item.get("number"))

    @staticmethod
    def _finding(identifier: str, category: str, severity: str, summary: str, *, details: str | None = None, object_type: str | None = None, object_number: int | str | None = None, source: str | None = None, confidence: str = "provider_verified", suggested: str | None = None) -> DiagnosticFinding:
        return DiagnosticFinding(identifier, category, severity, summary, summary, details or summary, object_type, object_number, source, confidence, suggested)

    def _snapshot_health(self, state: StateStore, resource: str) -> list[DiagnosticFinding]:
        snapshot = state.get(resource)
        label = resource.replace("_", " ").title()
        if snapshot is None:
            return [self._finding(f"state.{resource}.unavailable", resource, "WARNING", f"{label} diagnostics unavailable.", details="No snapshot was returned by the provider.", confidence="unavailable")]
        if snapshot.stale:
            detail = f"Using data from {snapshot.updated_at}."
            if snapshot.error:
                detail += f" {snapshot.error}"
            return [self._finding(f"state.{resource}.stale", resource, "WARNING", f"{label} state is stale.", details=detail, source=snapshot.source, confidence="stale")]
        if snapshot.error:
            severity = "INFO" if snapshot.error.startswith("UNSUPPORTED") else "WARNING" if snapshot.values else "ERROR"
            status = "Using stale data" if snapshot.values else "No data available"
            return [self._finding(f"state.{resource}.error", resource, severity, f"{label} state could not be refreshed.", details=f"{status}. {snapshot.error}", source=snapshot.source, confidence="provider_error")]
        return []

    @staticmethod
    def _available(state: StateStore, resource: str) -> bool:
        snapshot = state.get(resource)
        return bool(snapshot and not snapshot.error and not snapshot.stale)

    def _duplicates(self, values: Iterable[dict[str, Any]], category: str, label: str, source: str | None) -> list[DiagnosticFinding]:
        seen: set[Any] = set(); duplicate: set[Any] = set()
        for item in values:
            number = item.get("number")
            if number in seen: duplicate.add(number)
            seen.add(number)
        return [self._finding(f"{category}.duplicate_id", category, "ERROR", f"Duplicate {label} ID {number} returned by the provider.", object_type=category, object_number=number, source=source, confidence="provider_verified", suggested="Refresh the inventory and inspect source data.") for number in sorted(duplicate, key=str)]

    def _capabilities(self, state: StateStore) -> list[dict[str, str]]:
        layout_items = state.get("layout_items")
        geometry = "UNSUPPORTED"
        if layout_items:
            for value in layout_items.values:
                geometry = str((value.get("fixture_geometry") or {}).get("status") or (layout_items.capability or {}).get("layout_fixture_geometry", "UNSUPPORTED"))
                break
        return [
            {"name": "Groups", "status": self._capability(state, "groups")},
            {"name": "Group membership", "status": self._capability(state, "group_membership")},
            {"name": "Fixtures", "status": self._capability(state, "fixtures")},
            {"name": "Layout inventory", "status": self._capability(state, "layouts")},
            {"name": "Layout CObjects", "status": "SUPPORTED" if layout_items else "UNAVAILABLE"},
            {"name": "Layout fixture geometry", "status": geometry},
            {"name": "Presets", "status": self._capability(state, "presets")},
            {"name": "Effects", "status": self._capability(state, "effects")},
            {"name": "Sequences / Cues", "status": self._capability(state, "cues")},
            {"name": "Pages / Executors", "status": self._capability(state, "executors")},
        ]

    @staticmethod
    def _capability(state: StateStore, resource: str) -> str:
        snapshot = state.get(resource)
        if not snapshot: return "UNAVAILABLE"
        if snapshot.error and snapshot.error.startswith("UNSUPPORTED"): return "UNSUPPORTED"
        if snapshot.error: return "ERROR"
        return "STALE" if snapshot.stale else "SUPPORTED"
