"""Typed Effect resource resolution for Designer and Builder.

This module deliberately has no Telnet client and no MA2 command strings.
It can only choose a fresh, evidence-backed existing Effect or prepare an
``EffectSpec`` for the already-verified Effect Builder v1 boundary.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .effect_builder import EffectSpec, resolve_effect_spec
from .models import Intent


CATALOG_SCHEMA = "zen.effect_catalog.v0.1"
_SPEED_BPM = {"SLOW": 30, "MED": 60, "FAST": 120}


class EffectRequirementError(ValueError):
    pass


@dataclass(frozen=True)
class EffectRequirement:
    """The only v1 visual-effect request the Designer may express.

    The fields intentionally match only values the existing Dimmer Chase
    builder already knows how to create.  More expressive Effect schemas must
    wait for independent MA2 command and read-back evidence.
    """

    feature: str
    family: str
    waveform: str
    low: int
    high: int
    speed_class: str
    speed_bpm: int
    phase: str
    direction: str
    groups: int
    target_type: str
    target_ref: int
    target_name: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EffectRequirement":
        if not isinstance(raw, dict):
            raise EffectRequirementError("Effect requirement must be an object.")
        feature = str(raw.get("feature") or "").upper()
        family = str(raw.get("family") or "").upper()
        waveform = str(raw.get("waveform") or "").upper()
        speed_class = str(raw.get("speed_class") or "").upper()
        direction = str(raw.get("direction") or "").lower()
        phase = str(raw.get("phase") or "")
        target_type = str(raw.get("target_type") or "").lower()
        target_ref = raw.get("target_ref")
        low, high, groups = raw.get("low"), raw.get("high"), raw.get("groups")
        if (feature, family, waveform) != ("DIMMER", "CHASE", "PWM"):
            raise EffectRequirementError("Effect Resource Resolver v1 supports DIMMER_CHASE with PWM only.")
        if speed_class not in _SPEED_BPM:
            raise EffectRequirementError("DIMMER_CHASE speed_class must be SLOW, MED, or FAST.")
        speed_bpm = raw.get("speed_bpm", _SPEED_BPM[speed_class])
        if speed_bpm != _SPEED_BPM[speed_class]:
            raise EffectRequirementError("DIMMER_CHASE speed_bpm must match its verified speed_class.")
        if (low, high, phase, direction, groups) != (0, 100, "0..360", "forward", 1):
            raise EffectRequirementError("DIMMER_CHASE v1 supports only low=0, high=100, phase=0..360, forward, groups=1.")
        if target_type not in {"group", "fixture"} or isinstance(target_ref, bool) or not isinstance(target_ref, int) or target_ref < 1:
            raise EffectRequirementError("DIMMER_CHASE requires a positive Group or Fixture target reference.")
        name = raw.get("target_name")
        return cls(feature, family, waveform, low, high, speed_class, speed_bpm, phase, direction, groups, target_type, target_ref, str(name) if name else None)

    @property
    def kind(self) -> str:
        return "DIMMER_CHASE"

    @property
    def normalized_key(self) -> str:
        return "|".join((self.kind, str(self.low), str(self.high), str(self.speed_bpm), self.phase, self.direction, str(self.groups), self.target_type, str(self.target_ref)))

    @property
    def semantic_label(self) -> str:
        return f"ZEN_FX_DIM_CHASE_{self.speed_class}_{self.target_type.upper()}{self.target_ref}"

    def summary(self) -> dict[str, Any]:
        return asdict(self) | {"kind": self.kind, "normalized_key": self.normalized_key, "semantic_label": self.semantic_label}


@dataclass(frozen=True)
class EffectResolution:
    status: str
    requirement: EffectRequirement
    effect_ref: dict[str, Any] | None
    effect_spec: EffectSpec | None
    candidates: tuple[dict[str, Any], ...] = ()
    reason: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "requirement": self.requirement.summary(),
            "effect_ref": self.effect_ref,
            "effect_spec": self.effect_spec.summary() if self.effect_spec else None,
            "candidates": list(self.candidates),
            "reason": self.reason,
        }


def show_identity(profile: dict[str, Any]) -> dict[str, str]:
    """Produce a conservative scan identity when MA2 exposes no show UUID.

    The fingerprint intentionally excludes mutable Effect/Sequence inventories:
    an approved resource creation must not invalidate its own catalog entry.
    Group membership is part of identity because Group-bound Preset/Effect
    evidence must not survive an exact-subfixture membership drift.
    """
    token = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)

    def membership_identity(item: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
        exact = item.get("fixture_refs_in_selection_order")
        if isinstance(exact, list) and exact and all(isinstance(ref, str) and ref.strip() for ref in exact):
            # Applicability is a member-set fact; selection order may change
            # chase appearance without changing which exact instances exist.
            return "EXACT", tuple(sorted(ref.strip() for ref in exact))
        roots = item.get("fixture_ids_in_selection_order")
        if isinstance(roots, list):
            # Preserve duplicate roots. Multi-instance legacy profiles may
            # legitimately contain the same root more than once.
            return "ROOT", tuple(sorted((token(value) for value in roots)))
        return "UNKNOWN", ()

    stable = {
        # A provider refresh can legitimately repeat a pool row before its
        # compaction pass. Identity represents the observed Show, not refresh
        # count. Exact membership changes, however, invalidate bound evidence.
        "groups": sorted({
            (token(item.get("group_id")), token(item.get("name")), token(membership_identity(item)))
            for item in profile.get("groups", []) if isinstance(item, dict)
        }),
        "fixtures": sorted({(token(item.get("fixture_id")), token(item.get("fixture_type"))) for item in profile.get("fixtures", []) if isinstance(item, dict)}),
        "presets": sorted({(token(item.get("reference")), token(item.get("name"))) for item in profile.get("presets", []) if isinstance(item, dict)}),
    }
    digest = hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    return {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": digest, "confidence": "PARTIAL"}


class EffectCatalog:
    """Portable, Agent-owned metadata; never a substitute for fresh List Effect."""

    def __init__(self, root: Path):
        self.path = Path(root) / "data" / "ZEN_EFFECT_CATALOG.json"

    def load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"schema": CATALOG_SCHEMA, "entries": []}
        except (OSError, json.JSONDecodeError):
            return {"schema": CATALOG_SCHEMA, "entries": []}
        if not isinstance(raw, dict) or raw.get("schema") != CATALOG_SCHEMA or not isinstance(raw.get("entries"), list):
            return {"schema": CATALOG_SCHEMA, "entries": []}
        return raw

    def save(self, catalog: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def record(self, *, requirement: EffectRequirement, effect_id: int, label: str, identity: dict[str, str], verification: dict[str, str]) -> dict[str, Any]:
        catalog = self.load()
        entries = [item for item in catalog["entries"] if not (item.get("show_identity") == identity and item.get("effect_id") == effect_id)]
        entry = {
            "effect_id": effect_id,
            "label": label,
            "ownership": "ZEN_AGENT",
            "requirement": requirement.summary(),
            "show_identity": identity,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "verification": verification,
            "source": "EFFECT_BUILDER_V1",
        }
        catalog["entries"] = [*entries, entry]
        self.save(catalog)
        return entry


class EffectResourceResolver:
    """Resolve verified references or prepare exactly one existing builder spec."""

    def __init__(self, catalog: EffectCatalog):
        self.catalog = catalog

    def resolve(self, raw_requirement: EffectRequirement | dict[str, Any], *, profile: dict[str, Any]) -> EffectResolution:
        requirement = raw_requirement if isinstance(raw_requirement, EffectRequirement) else EffectRequirement.from_dict(raw_requirement)
        identity = show_identity(profile)
        effects = [item for item in profile.get("effects", []) if isinstance(item, dict) and isinstance(item.get("effect_id"), int)]
        by_id = {item["effect_id"]: item for item in effects}
        catalog_matches = []
        for entry in self.catalog.load()["entries"]:
            if entry.get("ownership") != "ZEN_AGENT" or entry.get("show_identity") != identity:
                continue
            if (entry.get("requirement") or {}).get("normalized_key") != requirement.normalized_key:
                continue
            effect = by_id.get(entry.get("effect_id"))
            if not effect or effect.get("name") != entry.get("label"):
                continue
            catalog_matches.append((entry, effect))
        if catalog_matches:
            entry, effect = min(catalog_matches, key=lambda pair: int(pair[1]["effect_id"]))
            return EffectResolution("EXISTING_MATCH", requirement, {
                "id": effect["effect_id"], "label": effect.get("name"), "source": "EFFECT_RESOURCE_RESOLVER", "ownership": "ZEN_AGENT",
                "verification": entry.get("verification"),
                "match": "VERIFIED_AGENT_CATALOG" if len(catalog_matches) == 1 else "VERIFIED_AGENT_CATALOG_LOWEST_ID",
            }, None)

        # Existing template labels have a deliberately small exact vocabulary;
        # a generic human label such as "Chase" never becomes an automatic match.
        expected_template = f"FX_DIM_CHASE_{requirement.speed_class}"
        template = [
            item
            for item in effects
            if str(item.get("name") or "").strip().upper() == expected_template
            and str(item.get("kind") or "").upper() == "TEMPLATE"
        ]
        if template:
            effect = min(template, key=lambda item: int(item["effect_id"]))
            return EffectResolution("EXISTING_MATCH", requirement, {
                "id": effect["effect_id"], "label": effect.get("name"), "source": "EFFECT_RESOURCE_RESOLVER", "ownership": "TEMPLATE",
                "verification": {"object": "FRESH_LIST_VERIFIED", "label": "STRICT_SEMANTIC_TEMPLATE", "parameters": "UNAVAILABLE"},
                "match": "STRICT_SEMANTIC_TEMPLATE" if len(template) == 1 else "STRICT_SEMANTIC_TEMPLATE_LOWEST_ID",
            }, None)

        candidates = tuple({"id": item["effect_id"], "label": item.get("name"), "reason": "Name-only candidate; not an exact verified specification."} for item in effects if "CHASE" in str(item.get("name") or "").upper())
        try:
            spec = self.to_effect_spec(requirement, profile)
        except EffectRequirementError as exc:
            return EffectResolution("UNSUPPORTED", requirement, None, None, candidates, str(exc))
        return EffectResolution("CREATE_REQUIRED", requirement, None, spec, candidates, "No verified compatible existing Effect is available.")

    @staticmethod
    def to_effect_spec(requirement: EffectRequirement, profile: dict[str, Any]) -> EffectSpec:
        groups = [{"number": item.get("group_id"), "name": item.get("name")} for item in profile.get("groups", []) if isinstance(item, dict)]
        fixtures = [{"number": item.get("fixture_id"), "name": item.get("name")} for item in profile.get("fixtures", []) if isinstance(item, dict)]
        effects = [{"number": item.get("effect_id"), "name": item.get("name")} for item in profile.get("effects", []) if isinstance(item, dict)]
        if requirement.target_type == "group":
            target_type, target = "group_number", requirement.target_ref
        else:
            target_type, target = "fixture_number", requirement.target_ref
        intent = Intent("build_dimmer_chase", {
            "target_type": target_type, "target": target, "speed_bpm": requirement.speed_bpm,
            "direction": requirement.direction, "effect_name": requirement.semantic_label,
        }, "EffectResourceResolver")
        try:
            return resolve_effect_spec(intent, groups=groups, fixtures=fixtures, effects=effects)
        except Exception as exc:
            raise EffectRequirementError(str(exc)) from exc


def apply_effect_references(plan: dict[str, Any], resolutions: dict[str, EffectResolution]) -> dict[str, Any]:
    """Replace only resolved typed requirement IDs; never add MA2 command text."""
    normalized = json.loads(json.dumps(plan))
    for cue in normalized.get("cues", []):
        for action in cue.get("actions", []):
            requirement_id = action.get("effect_requirement_id")
            if not requirement_id:
                continue
            resolution = resolutions.get(str(requirement_id))
            if not resolution or resolution.status != "EXISTING_MATCH" or not resolution.effect_ref:
                raise EffectRequirementError(f"Effect requirement {requirement_id!r} is not resolved.")
            action["operation"] = "CALL_EFFECT"
            action["effect_ref"] = resolution.effect_ref
            action.pop("effect_requirement_id", None)
    normalized["effect_resolutions"] = {key: value.summary() for key, value in resolutions.items()}
    return normalized
