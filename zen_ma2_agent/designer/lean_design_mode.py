"""Deterministic compact context and delta planning for ordinary Design Mode.

This module deliberately stops at model-facing context assembly.  It does not
call a provider, inspect MA2, allocate Sequences, or construct MA2 commands.
The caller owns the one primary design call and the optional one delta call;
the compiler/Builder remains the only execution boundary.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from ..portable import portable_state_path


COMPACT_CONTEXT_SCHEMA = "zen.compact_design_context.v0.1"
DELTA_CONTEXT_SCHEMA = "zen.delta_design_context.v0.1"
DEFAULT_PRIMARY_DESIGN_CALL_BUDGET = 1
DEFAULT_DELTA_REVISION_CALL_BUDGET = 1
MULTI_AGENT_DEFAULT = False

_MAX_TEXT = 4000
_MAX_LIST = 128
_CUE_KEYS = ("id", "cue_number", "label", "fade", "actions", "intent")
_GROUP_KEYS = ("group_id", "name")
_PRESET_KEYS = ("reference", "preset_type", "name")
_EFFECT_KEYS = ("effect_id", "name")
_CAPABILITY_KEYS = (
    "fixture_type_identity",
    "show_fingerprint",
    "capabilities",
    "observed_attributes",
    "confidence",
    "source",
)
_SPATIAL_KEYS = (
    "show_fingerprint",
    "spatial_bootstrap_mode",
    "stage_frame",
    "coordinate_system",
    "spatial_strategy",
    "spatial_relationships",
    "resource_assignments",
    "position_summary",
    "geometry_summary",
    "negative_space",
    "height_layers",
    "depth_layers",
)
_SONG_KEYS = (
    "song",
    "song_name",
    "title",
    "artist",
    "performance_summary",
    "arrangement_summary",
    "brief",
    "style_direction",
)
_FORBIDDEN_TRANSPORT_KEYS = {
    "command",
    "commands",
    "console_command",
    "raw_command",
    "ma_command",
    "telnet",
    "lua",
}


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_context_hash(value: object) -> str:
    """Hash exactly the deterministic JSON representation sent to a model."""
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _bounded_text(value: object, *, limit: int = _MAX_TEXT) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    return value[:limit] if value else None


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _pick_mapping(value: object, keys: Sequence[str]) -> dict[str, Any]:
    source = _mapping(value)
    return {key: deepcopy(source[key]) for key in keys if key in source and source[key] is not None}


def _bounded_list(value: object) -> list[Any]:
    return deepcopy(list(value)[:_MAX_LIST]) if isinstance(value, list) else []


def _reject_forbidden_transport(value: object, *, path: str = "root") -> None:
    """Keep model context from becoming a covert MA2 command channel."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in _FORBIDDEN_TRANSPORT_KEYS:
                raise ValueError(f"forbidden transport field in design context: {path}.{key}")
            _reject_forbidden_transport(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_transport(child, path=f"{path}[{index}]")


def _compact_song(value: object) -> dict[str, Any]:
    return _pick_mapping(value, _SONG_KEYS)


def _compact_spatial(value: object) -> dict[str, Any]:
    source = _mapping(value)
    compact = _pick_mapping(source, _SPATIAL_KEYS)
    # Keep provider-relevant summaries bounded while excluding raw Show dumps.
    for key in ("resource_assignments", "spatial_relationships", "height_layers", "depth_layers"):
        if isinstance(compact.get(key), list):
            compact[key] = _bounded_list(compact[key])
    return compact


def _compact_groups(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        compact = _pick_mapping(item, _GROUP_KEYS)
        group_id = compact.get("group_id")
        if isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1:
            continue
        rows.append(compact)
    return sorted(rows, key=lambda item: (item["group_id"], str(item.get("name") or "")))[:_MAX_LIST]


def _compact_presets(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        compact = _pick_mapping(item, _PRESET_KEYS)
        reference = compact.get("reference")
        if not isinstance(reference, str) or not reference.strip():
            continue
        rows.append(compact)
    return sorted(rows, key=lambda item: (str(item["reference"]), str(item.get("name") or "")))[:_MAX_LIST]


def _compact_effects(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        compact = _pick_mapping(item, _EFFECT_KEYS)
        effect_id = compact.get("effect_id")
        if isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id < 1:
            continue
        rows.append(compact)
    return sorted(rows, key=lambda item: (item["effect_id"], str(item.get("name") or "")))[:_MAX_LIST]


def _compact_capabilities(value: object) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        compact = _pick_mapping(item, _CAPABILITY_KEYS)
        if compact:
            for key in ("capabilities", "observed_attributes"):
                if isinstance(compact.get(key), list):
                    compact[key] = sorted(str(entry) for entry in compact[key])[:_MAX_LIST]
            rows.append(compact)
    return sorted(rows, key=lambda item: (str(item.get("fixture_type_identity") or ""), str(item.get("source") or "")))[:_MAX_LIST]


def _compact_plan(value: object, *, cue_numbers: set[int] | None = None) -> dict[str, Any] | None:
    source = _mapping(value)
    cues = source.get("cues")
    if not isinstance(cues, list):
        return None
    selected: list[dict[str, Any]] = []
    for cue in cues:
        if not isinstance(cue, Mapping):
            continue
        number = cue.get("cue_number")
        if cue_numbers is not None and number not in cue_numbers:
            continue
        compact = {key: deepcopy(cue[key]) for key in _CUE_KEYS if key in cue}
        if isinstance(compact.get("actions"), list):
            compact["actions"] = _bounded_list(compact["actions"])
        selected.append(compact)
    return {"cues": selected}


def assemble_compact_design_context(
    *,
    song_context: Mapping[str, Any] | None = None,
    spatial_context: Mapping[str, Any] | None = None,
    groups: Sequence[Mapping[str, Any]] | None = None,
    presets: Sequence[Mapping[str, Any]] | None = None,
    effects: Sequence[Mapping[str, Any]] | None = None,
    capability_profiles: Sequence[Mapping[str, Any]] | None = None,
    prior_artistic_plan: Mapping[str, Any] | None = None,
    owner_revision_text: str | None = None,
) -> dict[str, Any]:
    """Build a stable, bounded context without copying a raw Show dump."""
    _reject_forbidden_transport(prior_artistic_plan, path="prior_artistic_plan")
    context: dict[str, Any] = {
        "schema": COMPACT_CONTEXT_SCHEMA,
        "song": _compact_song(song_context),
        "spatial": _compact_spatial(spatial_context),
        "verified_groups": _compact_groups(groups),
        "verified_presets": _compact_presets(presets),
        "verified_effects": _compact_effects(effects),
        "capability_summary": _compact_capabilities(capability_profiles),
    }
    plan = _compact_plan(prior_artistic_plan)
    if plan is not None:
        context["prior_artistic_plan"] = plan
    text = _bounded_text(owner_revision_text)
    if text is not None:
        context["owner_revision_text"] = text
    return {
        "schema": COMPACT_CONTEXT_SCHEMA,
        "context": context,
        "context_hash": stable_context_hash(context),
        "primary_design_call_budget": DEFAULT_PRIMARY_DESIGN_CALL_BUDGET,
        "delta_revision_call_budget": DEFAULT_DELTA_REVISION_CALL_BUDGET,
        "multi_agent_default": MULTI_AGENT_DEFAULT,
    }


def write_compact_context_cache(context_artifact: Mapping[str, Any], path: Path | None = None) -> Path:
    """Persist one portable JSON artifact; no database or provider is involved."""
    target = path or (portable_state_path("cache") / "lean_design_context.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(context_artifact), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def load_or_build_compact_context(*, cache_path: Path, **kwargs: Any) -> dict[str, Any]:
    """Reuse a cache only when its deterministic context hash still matches."""
    fresh = assemble_compact_design_context(**kwargs)
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cached = None
        if isinstance(cached, dict) and cached.get("context_hash") == fresh["context_hash"] and cached.get("context") == fresh["context"]:
            reused = deepcopy(cached)
            reused["cache_reused"] = True
            return reused
    write_compact_context_cache(fresh, cache_path)
    fresh["cache_reused"] = False
    return fresh


def _cue_numbers_from_request(owner_revision_text: str, count: int) -> set[int]:
    values = {int(match) for match in re.findall(r"\b(?:cue|cues)\s*([0-9]+)", owner_revision_text, flags=re.IGNORECASE)}
    return {value for value in values if 1 <= value <= count}


def _cue_numbers_from_labels(owner_revision_text: str, cues: object) -> set[int]:
    """Match explicit cue/section labels without inventing a default cue."""
    if not isinstance(cues, list):
        return set()
    normalized_request = re.sub(r"[^a-z0-9]+", " ", owner_revision_text.casefold()).strip()
    if not normalized_request:
        return set()
    selected: set[int] = set()
    for cue in cues:
        if not isinstance(cue, Mapping):
            continue
        number = cue.get("cue_number")
        label = str(cue.get("label") or "").strip()
        if not isinstance(number, int) or number < 1 or not label:
            continue
        normalized_label = re.sub(r"[^a-z0-9]+", " ", label.casefold()).strip()
        tokens = [token for token in normalized_label.split() if len(token) >= 3]
        if normalized_label and normalized_label in normalized_request:
            selected.add(number)
            continue
        if tokens and all(token in normalized_request for token in tokens):
            selected.add(number)
    return selected


def build_delta_revision_context(
    *,
    accepted_artistic_plan: Mapping[str, Any],
    owner_revision_text: str,
    groups: Sequence[Mapping[str, Any]] | None = None,
    presets: Sequence[Mapping[str, Any]] | None = None,
    effects: Sequence[Mapping[str, Any]] | None = None,
    capability_profiles: Sequence[Mapping[str, Any]] | None = None,
    song_context: Mapping[str, Any] | None = None,
    spatial_context: Mapping[str, Any] | None = None,
    affected_cue_numbers: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Build one bounded local revision context around affected cues."""
    _reject_forbidden_transport(accepted_artistic_plan, path="accepted_artistic_plan")
    cues = _mapping(accepted_artistic_plan).get("cues")
    cue_count = len(cues) if isinstance(cues, list) else 0
    explicit = {int(value) for value in (affected_cue_numbers or ()) if isinstance(value, int) and 1 <= value <= cue_count}
    selected = explicit or _cue_numbers_from_request(owner_revision_text, cue_count)
    if not selected:
        selected = _cue_numbers_from_labels(owner_revision_text, cues)
    # Never guess Cue 1. If the request cannot be localized deterministically,
    # send the bounded accepted plan so the single revision model call can
    # identify the affected region from real context.
    neighborhood = (
        {number for number in selected for number in (number - 1, number, number + 1) if 1 <= number <= cue_count}
        if selected
        else set(range(1, cue_count + 1))
    )
    compact_plan = _compact_plan(accepted_artistic_plan, cue_numbers=neighborhood) or {"cues": []}

    group_refs: set[int] = set()
    preset_refs: set[str] = set()
    effect_refs: set[int] = set()
    for cue in compact_plan["cues"]:
        for action in cue.get("actions", []) if isinstance(cue.get("actions"), list) else []:
            if not isinstance(action, Mapping):
                continue
            target = action.get("target")
            if isinstance(target, Mapping) and isinstance(target.get("ref"), int):
                group_refs.add(target["ref"])
            if isinstance(action.get("group"), int):
                group_refs.add(action["group"])
            for key in ("preset_ref", "preset", "color_preset", "position_preset", "focus_preset", "beam_preset", "gobo_preset"):
                if isinstance(action.get(key), str):
                    preset_refs.add(action[key])
            effect = action.get("effect_ref", action.get("effect"))
            if isinstance(effect, Mapping):
                effect = effect.get("id")
            if isinstance(effect, int) and not isinstance(effect, bool):
                effect_refs.add(effect)

    all_groups = _compact_groups(groups)
    all_presets = _compact_presets(presets)
    all_effects = _compact_effects(effects)
    context = {
        "schema": DELTA_CONTEXT_SCHEMA,
        "owner_revision_text": _bounded_text(owner_revision_text) or "",
        "affected_cue_numbers": sorted(selected),
        "cue_neighborhood": sorted(neighborhood),
        "selection_mode": "DETERMINISTIC_LOCAL" if selected else "UNRESOLVED_USE_FULL_BOUNDED_PLAN",
        "accepted_artistic_plan": compact_plan,
        "relevant_groups": [item for item in all_groups if item["group_id"] in group_refs] if selected else all_groups,
        "relevant_presets": [item for item in all_presets if item["reference"] in preset_refs] if selected else all_presets,
        "relevant_effects": [item for item in all_effects if item["effect_id"] in effect_refs] if selected else all_effects,
        "capability_summary": _compact_capabilities(capability_profiles),
        "song": _compact_song(song_context),
        "spatial": _compact_spatial(spatial_context),
    }
    return {
        "schema": DELTA_CONTEXT_SCHEMA,
        "context": context,
        "context_hash": stable_context_hash(context),
        "delta_revision_call_budget": DEFAULT_DELTA_REVISION_CALL_BUDGET,
        "multi_agent_default": MULTI_AGENT_DEFAULT,
    }


# Short aliases keep the boundary easy to discover for callers and tests.
build_compact_design_context = assemble_compact_design_context
assemble_delta_revision_context = build_delta_revision_context
