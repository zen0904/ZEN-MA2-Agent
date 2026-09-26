"""Deterministic Position-only merge into existing grandMA2 Cues.

This capability exists for one narrow operation:

    verified existing Sequence + verified existing Cues
    + verified Position calibration baseline
    + bounded relative PAN/TILT offsets
    -> Store Cue ... /merge /cueonly

It never creates a Sequence, Executor, Group, Preset, or Effect.  It never
changes Patch/Address/Fixture identity/type.  Visual/physical targeting is not
claimed from relative offsets alone.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .position_application_evidence import (
    PositionEvidenceError,
    _exact_refs,
    _group,
    _identity,
    _position_capability,
    _canonical_position_row_ref,
)
from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


PREVIEW_SCHEMA = "zen.position_existing_cue_merge_preview.v0.1"
VERIFY_SCHEMA = "zen.position_existing_cue_merge_verification.v0.1"
_PRIMARY_POSITION_ATTRS = {"PAN", "TILT"}
_POSITION_FAMILY_ATTRS = _PRIMARY_POSITION_ATTRS | {
    "VIRTUAL_POSITION_MODE", "MARK", "STAGEX", "STAGEY", "STAGEZ", "FLIP", "DIST",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class ExistingPositionMergeError(ValueError):
    pass


def _number(value: object) -> float:
    try:
        result = float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ExistingPositionMergeError("POSITION_NUMERIC_VALUE_INVALID") from exc
    if not math.isfinite(result):
        raise ExistingPositionMergeError("POSITION_NUMERIC_VALUE_INVALID")
    return result


def _fmt(value: float) -> str:
    if abs(value) < 0.0000001:
        value = 0.0
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def _cue_number(cue: Mapping[str, Any]) -> int:
    info = cue.get("number")
    raw = info.get("number") if isinstance(info, Mapping) else None
    if not isinstance(raw, str) or not raw.isdecimal() or int(raw) < 1:
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_NUMBER_INVALID")
    sub = info.get("sub_number")
    if sub not in (None, "", "0"):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_SUBCUE_UNSUPPORTED")
    return int(raw)


def _cue_label(cue: Mapping[str, Any]) -> str:
    parts = cue.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_PARTS_UNAVAILABLE")
    part0 = next((part for part in parts if isinstance(part, Mapping) and str(part.get("index")) == "0"), None)
    if not isinstance(part0, Mapping):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_PART0_UNAVAILABLE")
    label = part0.get("name")
    if not isinstance(label, str):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_LABEL_UNAVAILABLE")
    return label


def _cue_rows(cue: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for part in cue.get("parts", []):
        if not isinstance(part, Mapping):
            continue
        for row in part.get("cue_data", []):
            if isinstance(row, Mapping):
                rows.append(row)
    return rows


def _selection_channel_ref(profile: Mapping[str, Any], selection_ref: str) -> str:
    """Map an exact Group selection ref to its canonical Sequence CueData ref.

    A root-only Group member is accepted only when fresh geometry proves that
    body has exactly one subfixture. Dotted refs remain exact as-is.
    """
    if "." in selection_ref:
        return selection_ref
    fixtures = {
        str(item.get("fixture_id")): item
        for item in profile.get("fixtures", [])
        if isinstance(item, Mapping)
        and isinstance(item.get("fixture_id"), int)
        and not isinstance(item.get("fixture_id"), bool)
    }
    fixture = fixtures.get(selection_ref)
    if not isinstance(fixture, Mapping):
        raise ExistingPositionMergeError("POSITION_FIXTURE_IDENTITY_UNAVAILABLE")
    geometry = fixture.get("stage_geometry")
    subfixtures = geometry.get("subfixtures") if isinstance(geometry, Mapping) else None
    if not isinstance(subfixtures, list) or len(subfixtures) != 1:
        raise ExistingPositionMergeError("POSITION_MULTI_INSTANCE_PARENT_SELECTION_AMBIGUOUS")
    row = subfixtures[0]
    sub_id = row.get("subfixture_id") if isinstance(row, Mapping) else None
    if isinstance(sub_id, bool) or not isinstance(sub_id, int) or sub_id < 1:
        raise ExistingPositionMergeError("POSITION_SUBFIXTURE_IDENTITY_UNAVAILABLE")
    return f"{selection_ref}.{sub_id}"


def _row_attribute(row: Mapping[str, Any]) -> str:
    channel = row.get("channel")
    return str(channel.get("attribute_name") or "").upper() if isinstance(channel, Mapping) else ""


def derive_calibrated_baseline(
    profile: Mapping[str, Any],
    binding: Mapping[str, Any],
    calibration_discovery: Mapping[str, Any],
    exact_refs: Sequence[str],
) -> dict[str, dict[str, float]]:
    """Recover raw PAN/TILT baseline keyed by exact Group selection refs."""
    evidence = binding.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ExistingPositionMergeError("POSITION_BASELINE_BINDING_EVIDENCE_MISSING")
    if calibration_discovery.get("schema") != "zen.sequence_export_discovery.v0.1":
        raise ExistingPositionMergeError("POSITION_BASELINE_SEQUENCE_SCHEMA_INVALID")
    if calibration_discovery.get("status") != "VERIFIED":
        raise ExistingPositionMergeError("POSITION_BASELINE_SEQUENCE_NOT_VERIFIED")
    if calibration_discovery.get("sequence_no") != evidence.get("sequence"):
        raise ExistingPositionMergeError("POSITION_BASELINE_SEQUENCE_ID_MISMATCH")
    expected_sha = evidence.get("sequence_export_sha256")
    current_sha = (calibration_discovery.get("xml_discovery") or {}).get("sha256")
    if not isinstance(expected_sha, str) or not _SHA256.fullmatch(expected_sha):
        raise ExistingPositionMergeError("POSITION_BASELINE_ORIGINAL_SHA_INVALID")
    if not isinstance(current_sha, str) or not _SHA256.fullmatch(current_sha):
        raise ExistingPositionMergeError("POSITION_BASELINE_CURRENT_SHA_INVALID")

    preset_cue = evidence.get("cue")
    if isinstance(preset_cue, bool) or not isinstance(preset_cue, int) or preset_cue <= 1:
        raise ExistingPositionMergeError("POSITION_BASELINE_RAW_CUE_UNAVAILABLE")
    raw_cue_number = preset_cue - 1
    cues = {
        _cue_number(cue): cue
        for cue in calibration_discovery.get("cues", [])
        if isinstance(cue, Mapping)
    }
    raw_cue = cues.get(raw_cue_number)
    linked_cue = cues.get(preset_cue)
    if not isinstance(raw_cue, Mapping) or not isinstance(linked_cue, Mapping):
        raise ExistingPositionMergeError("POSITION_BASELINE_CALIBRATION_CUES_MISSING")

    selection_to_channel = {
        ref: _selection_channel_ref(profile, ref) for ref in exact_refs
    }
    if len(set(selection_to_channel.values())) != len(selection_to_channel):
        raise ExistingPositionMergeError("POSITION_BASELINE_CHANNEL_IDENTITY_AMBIGUOUS")
    channel_to_selection = {channel: ref for ref, channel in selection_to_channel.items()}
    result: dict[str, dict[str, float]] = {ref: {} for ref in exact_refs}
    for row in _cue_rows(raw_cue):
        attr = _row_attribute(row)
        if attr not in _PRIMARY_POSITION_ATTRS:
            continue
        channel = row.get("channel")
        if not isinstance(channel, Mapping):
            continue
        try:
            channel_ref = _canonical_position_row_ref(profile, channel)
        except PositionEvidenceError as exc:
            raise ExistingPositionMergeError(str(exc)) from exc
        selection_ref = channel_to_selection.get(channel_ref or "")
        if selection_ref is None:
            continue
        raw_values = row.get("raw_values")
        value = raw_values.get("Value") if isinstance(raw_values, Mapping) else None
        if value is None:
            raise ExistingPositionMergeError("POSITION_BASELINE_RAW_VALUE_MISSING")
        key = attr.lower()
        if key in result[selection_ref]:
            raise ExistingPositionMergeError("POSITION_BASELINE_DUPLICATE_ATTRIBUTE")
        result[selection_ref][key] = _number(value)
    if any(set(values) != {"pan", "tilt"} for values in result.values()):
        raise ExistingPositionMergeError("POSITION_BASELINE_INCOMPLETE")

    preset_ref = binding.get("reference")
    linked_hits: dict[str, set[str]] = {ref: set() for ref in exact_refs}
    for row in _cue_rows(linked_cue):
        attr = _row_attribute(row)
        if attr not in _PRIMARY_POSITION_ATTRS:
            continue
        channel = row.get("channel")
        if not isinstance(channel, Mapping):
            continue
        try:
            channel_ref = _canonical_position_row_ref(profile, channel)
        except PositionEvidenceError as exc:
            raise ExistingPositionMergeError(str(exc)) from exc
        selection_ref = channel_to_selection.get(channel_ref or "")
        if selection_ref is None:
            continue
        preset = row.get("preset")
        parts = preset.get("no_components") if isinstance(preset, Mapping) else None
        if not (
            isinstance(parts, list)
            and len(parts) >= 2
            and all(isinstance(item, str) and item.isdigit() for item in parts[-2:])
            and ".".join(str(int(item)) for item in parts[-2:]) == preset_ref
        ):
            raise ExistingPositionMergeError("POSITION_BASELINE_PRESET_LINK_MISMATCH")
        linked_hits[selection_ref].add(attr)
    if any(attrs != _PRIMARY_POSITION_ATTRS for attrs in linked_hits.values()):
        raise ExistingPositionMergeError("POSITION_BASELINE_PRESET_LINK_INCOMPLETE")
    return result


def _function_range(profile: Mapping[str, Any], fixture_type_label: str, attribute: str) -> tuple[float, float]:
    matches = [
        row for row in profile.get("fixture_type_profiles", [])
        if isinstance(row, Mapping)
        and row.get("status") == "SHOW_BOUND_VERIFIED"
        and isinstance(row.get("fixture_type"), Mapping)
        and row["fixture_type"].get("list_label") == fixture_type_label
    ]
    if len(matches) != 1:
        raise ExistingPositionMergeError("POSITION_FIXTURE_TYPE_PROFILE_UNAVAILABLE")
    channels = [
        row for row in matches[0].get("channels", [])
        if isinstance(row, Mapping) and str(row.get("attribute") or "").upper() == attribute
    ]
    if len(channels) != 1:
        raise ExistingPositionMergeError(f"POSITION_{attribute}_CHANNEL_AMBIGUOUS")
    functions = channels[0].get("functions")
    if not isinstance(functions, list) or not functions:
        raise ExistingPositionMergeError(f"POSITION_{attribute}_NATURAL_RANGE_UNAVAILABLE")
    ranges: list[tuple[float, float]] = []
    for function in functions:
        if not isinstance(function, Mapping):
            continue
        if function.get("from") is None or function.get("to") is None:
            continue
        a, b = _number(function["from"]), _number(function["to"])
        ranges.append((min(a, b), max(a, b)))
    if not ranges:
        raise ExistingPositionMergeError(f"POSITION_{attribute}_NATURAL_RANGE_UNAVAILABLE")
    return min(a for a, _ in ranges), max(b for _, b in ranges)


def fixture_limits(
    profile: Mapping[str, Any],
    exact_refs: Sequence[str],
) -> dict[str, dict[str, tuple[float, float]]]:
    fixtures = {
        str(item.get("fixture_id")): item
        for item in profile.get("fixtures", [])
        if isinstance(item, Mapping) and isinstance(item.get("fixture_id"), int)
    }
    result: dict[str, dict[str, tuple[float, float]]] = {}
    for exact_ref in exact_refs:
        root = exact_ref.split(".", 1)[0]
        fixture = fixtures.get(root)
        if not isinstance(fixture, Mapping):
            raise ExistingPositionMergeError("POSITION_FIXTURE_IDENTITY_UNAVAILABLE")
        label = fixture.get("fixture_type")
        if not isinstance(label, str) or not label:
            raise ExistingPositionMergeError("POSITION_FIXTURE_TYPE_IDENTITY_UNAVAILABLE")
        result[exact_ref] = {
            "pan": _function_range(profile, label, "PAN"),
            "tilt": _function_range(profile, label, "TILT"),
        }
    return result


def _symmetric(count: int, maximum: float) -> list[float]:
    if count < 1:
        raise ExistingPositionMergeError("POSITION_PATTERN_MEMBER_COUNT_INVALID")
    if count == 1:
        return [0.0]
    midpoint = (count - 1) / 2
    denom = midpoint or 1
    return [((index - midpoint) / denom) * maximum for index in range(count)]


def _pattern_offsets(pattern: str, count: int) -> list[tuple[float, float]]:
    spread6 = _symmetric(count, 6.0)
    spread12 = _symmetric(count, 12.0)
    reverse8 = list(reversed(_symmetric(count, 8.0)))
    if pattern == "CENTER":
        return [(0.0, 0.0)] * count
    if pattern == "LEFT":
        return [(6.0, 0.0)] * count
    if pattern == "RIGHT":
        return [(-6.0, 0.0)] * count
    if pattern == "FRONT":
        return [(0.0, -5.0)] * count
    if pattern == "UPSTAGE":
        return [(0.0, 5.0)] * count
    if pattern == "NARROW_FAN":
        return [(pan, 0.0) for pan in spread6]
    if pattern == "WIDE_FAN":
        return [(pan, 0.0) for pan in spread12]
    if pattern == "CROSS":
        return [(pan, 0.0) for pan in reverse8]
    if pattern == "ALTERNATE":
        return [((-8.0 if index % 2 == 0 else 8.0), (-2.0 if index % 2 == 0 else 2.0))
                for index in range(count)]
    if pattern == "EXPLODE":
        return [(pan, (-4.0 if index % 2 == 0 else 4.0)) for index, pan in enumerate(spread12)]
    if pattern == "COLLAPSE":
        return [(-pan, 2.0) for pan in spread6]
    raise ExistingPositionMergeError("POSITION_PATTERN_UNKNOWN")


def pattern_for_label(label: str, cue_number: int) -> str:
    text = label.upper()
    rules = (
        (("BLACKOUT", "RESET"), "CENTER"),
        (("FULL WHITE EXPLOSION", "WHITE IMPACT"), "EXPLODE"),
        (("FINAL HIT", "WHITE HIT", "STRIKE", "PUNCH"), "ALTERNATE"),
        (("ASCENT", "RISE"), "UPSTAGE"),
        (("REVEAL", "HALO", "AFTERGLOW", "DREAM"), "NARROW_FAN"),
        (("TENSION", "RELEASE", "DECAY"), "COLLAPSE"),
        (("POWER", "PEAK"), "WIDE_FAN"),
        (("SNAPBACK",), "RIGHT"),
        (("DEEP BLUE CUT", "CRIMSON LUXE"), "LEFT"),
        (("AMBER ACCENT", "RED DROP"), "RIGHT"),
        (("BUILD",), "NARROW_FAN"),
    )
    for tokens, pattern in rules:
        if any(token in text for token in tokens):
            return pattern
    cycle = ("CENTER", "NARROW_FAN", "CROSS", "FRONT", "WIDE_FAN", "UPSTAGE", "ALTERNATE")
    return cycle[(cue_number - 1) % len(cycle)]


def _bounded_value(base: float, offset: float, bounds: tuple[float, float]) -> float:
    low, high = bounds
    if not (low <= base <= high):
        raise ExistingPositionMergeError("POSITION_BASELINE_OUTSIDE_FIXTURE_RANGE")
    value = base + offset
    if value < low or value > high:
        raise ExistingPositionMergeError("POSITION_OFFSET_EXCEEDS_FIXTURE_RANGE")
    return value


def non_position_snapshot(discovery: Mapping[str, Any], cue_numbers: Sequence[int]) -> dict[str, Any]:
    wanted = set(cue_numbers)
    rows = []
    for cue in discovery.get("cues", []):
        if not isinstance(cue, Mapping):
            continue
        number = _cue_number(cue)
        if number not in wanted:
            continue
        kept_parts = []
        for part in cue.get("parts", []):
            if not isinstance(part, Mapping):
                continue
            kept = [
                row for row in part.get("cue_data", [])
                if isinstance(row, Mapping) and _row_attribute(row) not in _POSITION_FAMILY_ATTRS
            ]
            kept_parts.append({
                "index": part.get("index"),
                "name": part.get("name"),
                "cue_data": kept,
            })
        rows.append({"cue_number": number, "parts": kept_parts})
    rows.sort(key=lambda item: item["cue_number"])
    canonical = json.dumps(rows, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return {"rows": rows, "sha256": hashlib.sha256(canonical).hexdigest()}


def _commands_for_cue(
    sequence: int,
    cue_number: int,
    fixtures: Sequence[Mapping[str, Any]],
) -> list[str]:
    commands = ["ClearAll"]
    # Group identical values to reduce Telnet chatter while retaining exact
    # per-fixture values in the approved Preview.
    grouped: dict[tuple[str, str], list[str]] = {}
    for item in fixtures:
        ref = str(item["fixture_ref"])
        key = (_fmt(float(item["pan"])), _fmt(float(item["tilt"])))
        grouped.setdefault(key, []).append(ref)
    for (pan, tilt), refs in grouped.items():
        commands.append("Fixture " + " + ".join(refs))
        commands.append(f'Attribute "Pan" At {pan}')
        commands.append(f'Attribute "Tilt" At {tilt}')
    commands.append(f"Store Cue {cue_number} Sequence {sequence} /merge /cueonly /nc")
    return commands


def commands_from_preview(preview: Mapping[str, Any]) -> tuple[str, ...]:
    sequence = preview.get("target_sequence", {}).get("id")
    cue_updates = preview.get("cue_updates")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ExistingPositionMergeError("POSITION_MERGE_SEQUENCE_INVALID")
    if not isinstance(cue_updates, list) or not cue_updates:
        raise ExistingPositionMergeError("POSITION_MERGE_CUES_INVALID")
    commands: list[str] = []
    for cue in cue_updates:
        if not isinstance(cue, Mapping):
            raise ExistingPositionMergeError("POSITION_MERGE_CUE_INVALID")
        number = cue.get("cue_number")
        fixtures = cue.get("fixtures")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1 or not isinstance(fixtures, list):
            raise ExistingPositionMergeError("POSITION_MERGE_CUE_INVALID")
        commands.extend(_commands_for_cue(sequence, number, fixtures))
    commands.append("ClearAll")
    if any(not command.isascii() for command in commands):
        raise ExistingPositionMergeError("NON_ASCII_MA_TEXT")
    return tuple(commands)


def build_existing_position_merge_preview(
    profile: Mapping[str, Any],
    *,
    target_discovery: Mapping[str, Any],
    calibration_discovery: Mapping[str, Any],
    binding: Mapping[str, Any],
    sequence_no: int,
    group_id: int,
    cue_start: int,
    cue_end: int,
    executor_assignments: Sequence[Mapping[str, Any]] = (),
    cue_metadata: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    identity = _identity(profile)
    group = _group(profile, group_id)
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    if (
        binding.get("status") != "REAL_MACHINE_CONTENT_VERIFIED"
        or binding.get("show_identity") != identity
    ):
        raise ExistingPositionMergeError("POSITION_BASELINE_BINDING_NOT_VERIFIED")
    if binding.get("group_id") != group_id or binding.get("fixture_refs") != sorted(refs):
        raise ExistingPositionMergeError("POSITION_BASELINE_BINDING_GROUP_MISMATCH")
    if target_discovery.get("schema") != "zen.sequence_export_discovery.v0.1":
        raise ExistingPositionMergeError("TARGET_SEQUENCE_EXPORT_SCHEMA_INVALID")
    if target_discovery.get("status") != "VERIFIED" or target_discovery.get("sequence_no") != sequence_no:
        raise ExistingPositionMergeError("TARGET_SEQUENCE_EXPORT_NOT_VERIFIED")
    sequences = [
        item for item in profile.get("sequences", [])
        if isinstance(item, Mapping) and item.get("number") == sequence_no
    ]
    if len(sequences) != 1:
        raise ExistingPositionMergeError("TARGET_SEQUENCE_IDENTITY_UNAVAILABLE")
    sequence_label = sequences[0].get("name")
    if not isinstance(sequence_label, str) or not sequence_label.startswith("ZEN_"):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_NOT_AGENT_OWNED")

    cues = {
        _cue_number(cue): cue
        for cue in target_discovery.get("cues", [])
        if isinstance(cue, Mapping)
    }
    wanted = list(range(cue_start, cue_end + 1))
    if not wanted or any(number not in cues for number in wanted):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_RANGE_INCOMPLETE")
    metadata_by_number = {
        int(row["number"]): {
            "number": int(row["number"]),
            "name": row.get("name"),
            "fade": row.get("fade"),
            "delay": row.get("delay"),
        }
        for row in cue_metadata
        if isinstance(row, Mapping)
        and isinstance(row.get("number"), int)
        and not isinstance(row.get("number"), bool)
    }
    if any(number not in metadata_by_number for number in wanted):
        raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_METADATA_INCOMPLETE")
    for number in wanted:
        metadata = metadata_by_number[number]
        if metadata.get("name") != _cue_label(cues[number]):
            raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_METADATA_LABEL_MISMATCH")
        if metadata.get("fade") is None:
            raise ExistingPositionMergeError("TARGET_SEQUENCE_CUE_FADE_UNAVAILABLE")

    baseline = derive_calibrated_baseline(profile, binding, calibration_discovery, refs)
    limits = fixture_limits(profile, refs)
    ordered_refs = list(refs)
    updates = []
    for number in wanted:
        label = _cue_label(cues[number])
        pattern = pattern_for_label(label, number)
        offsets = _pattern_offsets(pattern, len(ordered_refs))
        fixture_rows = []
        for ref, (dpan, dtilt) in zip(ordered_refs, offsets):
            base = baseline[ref]
            pan = _bounded_value(base["pan"], dpan, limits[ref]["pan"])
            tilt = _bounded_value(base["tilt"], dtilt, limits[ref]["tilt"])
            fixture_rows.append({
                "fixture_ref": ref,
                "baseline_pan": base["pan"],
                "baseline_tilt": base["tilt"],
                "delta_pan": dpan,
                "delta_tilt": dtilt,
                "pan": pan,
                "tilt": tilt,
            })
        updates.append({
            "cue_number": number,
            "cue_label": label,
            "pattern": pattern,
            "fixtures": fixture_rows,
        })

    pre = non_position_snapshot(target_discovery, wanted)
    proposal: dict[str, Any] = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY",
        "show_identity": identity,
        "target_sequence": {
            "id": sequence_no,
            "label": sequence_label,
            "cue_start": cue_start,
            "cue_end": cue_end,
            "pre_export_sha256": (target_discovery.get("xml_discovery") or {}).get("sha256"),
            "pre_non_position_sha256": pre["sha256"],
            "cue_metadata": [metadata_by_number[number] for number in wanted],
            "executor_assignments": [
                {
                    "page": item.get("page"),
                    "executor": item.get("executor"),
                    "location": item.get("location"),
                    "label": item.get("label"),
                }
                for item in executor_assignments
                if isinstance(item, Mapping)
            ],
        },
        "group": {
            "id": group_id,
            "name": group.get("name"),
            "exact_refs": refs,
            "cue_channel_refs": {
                ref: _selection_channel_ref(profile, ref) for ref in refs
            },
        },
        "baseline": {
            "preset_reference": binding.get("reference"),
            "preset_label": binding.get("preset_label"),
            "calibration_sequence": (binding.get("evidence") or {}).get("sequence"),
            "calibration_export_sha256": (calibration_discovery.get("xml_discovery") or {}).get("sha256"),
            "values_by_fixture": baseline,
        },
        "direction_semantics": {
            "scope": "CURRENT_TEST_SHOW_OPERATOR_VERIFIED",
            "pan_negative": "STAGE_RIGHT",
            "pan_positive": "STAGE_LEFT",
            "tilt_negative": "AUDIENCE_FRONT",
            "tilt_positive": "UPSTAGE_INWARD",
            "xyz_sign_mapping_claimed": False,
            "high_low_claimed": False,
        },
        "pattern_semantics": {
            "kind": "RELATIVE_POSITION_SHAPES",
            "member_order": "VERIFIED_GROUP_SELECTION_ORDER",
            "physical_targeting_claimed": False,
        },
        "fixture_limits": {
            ref: {
                "pan": list(limits[ref]["pan"]),
                "tilt": list(limits[ref]["tilt"]),
            }
            for ref in ordered_refs
        },
        "cue_updates": updates,
        "write_scope": {
            "position_only": True,
            "store_mode": "MERGE_CUEONLY",
            "create_sequence": False,
            "create_executor": False,
            "modify_label": False,
            "modify_fade": False,
            "modify_dimmer": False,
            "modify_color": False,
            "modify_patch": False,
            "modify_address": False,
            "modify_fixture_identity_or_type": False,
        },
        "approval": "EXPLICIT_OWNER_APPROVAL_REQUIRED",
        "ma2_writes": 0,
    }
    commands = commands_from_preview(proposal)
    proposal["command_count"] = len(commands)
    proposal["command_plan_sha256"] = hashlib.sha256(
        "\n".join(commands).encode("ascii")
    ).hexdigest()
    canonical = json.dumps(proposal, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    proposal["preview_id"] = hashlib.sha256(canonical).hexdigest()[:16]
    return proposal


def verify_existing_position_merge(
    preview: Mapping[str, Any],
    post_discovery: Mapping[str, Any],
) -> dict[str, Any]:
    if preview.get("schema") != PREVIEW_SCHEMA:
        raise ExistingPositionMergeError("POSITION_MERGE_PREVIEW_SCHEMA_INVALID")
    sequence = preview.get("target_sequence", {}).get("id")
    if post_discovery.get("status") != "VERIFIED" or post_discovery.get("sequence_no") != sequence:
        raise ExistingPositionMergeError("POSITION_MERGE_POST_EXPORT_NOT_VERIFIED")
    updates = preview.get("cue_updates")
    if not isinstance(updates, list) or not updates:
        raise ExistingPositionMergeError("POSITION_MERGE_PREVIEW_CUES_INVALID")
    wanted = [int(cue["cue_number"]) for cue in updates]
    post_non_position = non_position_snapshot(post_discovery, wanted)
    if post_non_position["sha256"] != preview["target_sequence"]["pre_non_position_sha256"]:
        raise ExistingPositionMergeError("POSITION_MERGE_NON_POSITION_CONTENT_CHANGED")

    cues = {
        _cue_number(cue): cue
        for cue in post_discovery.get("cues", [])
        if isinstance(cue, Mapping)
    }
    matched = 0
    for update in updates:
        cue = cues.get(update["cue_number"])
        if not isinstance(cue, Mapping) or _cue_label(cue) != update["cue_label"]:
            raise ExistingPositionMergeError("POSITION_MERGE_CUE_LABEL_CHANGED")
        observed: dict[tuple[str, str], float] = {}
        channel_refs = preview.get("group", {}).get("cue_channel_refs")
        if not isinstance(channel_refs, Mapping):
            raise ExistingPositionMergeError("POSITION_MERGE_CHANNEL_IDENTITY_MISSING")
        reverse_refs = {str(value): str(key) for key, value in channel_refs.items()}
        if len(reverse_refs) != len(channel_refs):
            raise ExistingPositionMergeError("POSITION_MERGE_CHANNEL_IDENTITY_AMBIGUOUS")
        for row in _cue_rows(cue):
            attr = _row_attribute(row)
            channel = row.get("channel")
            if attr not in _PRIMARY_POSITION_ATTRS or not isinstance(channel, Mapping):
                continue
            raw_ref = channel.get("fixture_id")
            sub_ref = channel.get("subfixture_id")
            if not str(raw_ref).isdigit():
                continue
            channel_ref = str(int(raw_ref))
            if sub_ref not in (None, ""):
                if not str(sub_ref).isdigit():
                    continue
                channel_ref += f".{int(sub_ref)}"
            selection_ref = reverse_refs.get(channel_ref)
            if selection_ref is None and "." not in channel_ref:
                candidates = [
                    selection
                    for canonical, selection in reverse_refs.items()
                    if canonical.startswith(channel_ref + ".")
                ]
                if len(candidates) == 1:
                    selection_ref = candidates[0]
                elif len(candidates) > 1:
                    raise ExistingPositionMergeError(
                        "POSITION_MERGE_POST_PARENT_ROW_AMBIGUOUS"
                    )
            if selection_ref is None:
                continue
            raw_values = row.get("raw_values")
            value = raw_values.get("Value") if isinstance(raw_values, Mapping) else None
            if value is None:
                continue
            key = (selection_ref, attr)
            if key in observed:
                raise ExistingPositionMergeError("POSITION_MERGE_POST_DUPLICATE_POSITION_ROW")
            observed[key] = _number(value)
        for fixture in update["fixtures"]:
            ref = str(fixture["fixture_ref"])
            for attr, key in (("PAN", "pan"), ("TILT", "tilt")):
                value = observed.get((ref, attr))
                if value is None or not math.isclose(value, float(fixture[key]), rel_tol=0, abs_tol=0.001):
                    raise ExistingPositionMergeError(
                        f"POSITION_MERGE_POST_VALUE_MISMATCH_CUE_{update['cue_number']}_{ref}_{attr}"
                    )
                matched += 1
    return {
        "schema": VERIFY_SCHEMA,
        "status": "VERIFIED",
        "sequence": sequence,
        "cue_count": len(updates),
        "position_value_matches": matched,
        "non_position_content": "UNCHANGED",
        "cue_labels": "UNCHANGED",
        "post_export_sha256": (post_discovery.get("xml_discovery") or {}).get("sha256"),
    }


def preview_text(preview: Mapping[str, Any]) -> str:
    lines = [
        "POSITION-ONLY EXISTING CUE MERGE - PREVIEW",
        "",
        f"Sequence: {preview['target_sequence']['id']} {preview['target_sequence']['label']}",
        f"Cues: {preview['target_sequence']['cue_start']}-{preview['target_sequence']['cue_end']}",
        f"Group: {preview['group']['id']} {preview['group']['name']}",
        f"Baseline: Position Preset {preview['baseline']['preset_reference']} ({preview['baseline']['preset_label']})",
        "Store mode: /merge /cueonly",
        f"Generated MA2 commands: {preview['command_count']}",
        "",
        "Relative Position plan:",
    ]
    for cue in preview["cue_updates"]:
        offsets = ", ".join(
            (
                f"{row['fixture_ref']} "
                f"dP={_fmt(float(row['delta_pan']))} dT={_fmt(float(row['delta_tilt']))} "
                f"P={_fmt(float(row['pan']))} T={_fmt(float(row['tilt']))}"
            )
            for row in cue["fixtures"]
        )
        lines.append(f"- Cue {cue['cue_number']} {cue['cue_label']} | {cue['pattern']} | {offsets}")
    lines += [
        "",
        "Preserved by contract: Dimmer, Color, Cue label, Fade, Executor assignment, all non-PAN/TILT CueData.",
        "No Sequence/Executor/Preset/Group is created. No Patch/Address/Fixture identity/type write.",
        "Physical target/high-low semantics are NOT claimed from these relative offsets.",
        "Explicit approval required before any MA2 write.",
    ]
    return "\n".join(lines)


class ExistingPositionMergeSkill:
    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return (
            self.manifest.enabled
            and intent.kind == "merge_existing_cue_position"
            and state.has(self.manifest.required_state)
        )

    def create_task(self, intent: Intent) -> Task:
        return Task(
            "position-existing-cue-merge",
            "Existing Cue Position Merge",
            intent,
            self.manifest.id,
            self.manifest.required_state,
        )

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("position_merge_preview")
        if not isinstance(preview, Mapping) or preview.get("schema") != PREVIEW_SCHEMA:
            raise ExistingPositionMergeError("POSITION_MERGE_PREVIEW_INVALID")
        commands = commands_from_preview(preview)
        steps = tuple(
            ActionStep(
                f"position-merge-{index}",
                "Deterministic Position-only merge command",
                "command",
                command,
                "MODIFY",
                depends_on=(f"position-merge-{index - 1}",) if index > 1 else (),
            )
            for index, command in enumerate(commands, 1)
        )
        return WorkflowPlan(
            task,
            (
                Subtask("fresh-export", "Fresh native Sequence + calibration evidence", "Planning"),
                Subtask("preview", "Review exact relative Position offsets", "Planning"),
                Subtask("execute", "Merge PAN/TILT only into existing Cues", "Execution"),
                Subtask("verify", "Native Sequence Export + non-Position immutability check", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Existing Cue Position Merge"),),
            steps,
            "MODIFY",
            preview_text(preview),
            ("PREVIEW",),
            "Native Sequence Export must match every approved PAN/TILT value and preserve all non-Position CueData and Cue labels.",
            "No automatic rollback: existing Cue content is modified only by approved /merge writes; retain post-write native export for recovery evidence.",
            True,
            "PREVIEW",
            "READY",
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("position_merge_preview")
        if (
            plan.task.skill_id != self.manifest.id
            or plan.safety != "MODIFY"
            or not isinstance(preview, Mapping)
            or preview.get("schema") != PREVIEW_SCHEMA
            or plan.commands != commands_from_preview(preview)
        ):
            raise ExistingPositionMergeError("POSITION_MERGE_WORKFLOW_INVALID")
        for command in plan.commands:
            if not command.isascii():
                raise ExistingPositionMergeError("NON_ASCII_MA_TEXT")
            if command == "ClearAll":
                continue
            if re.fullmatch(r"Fixture [1-9]\d*(?:\.[1-9]\d*)?(?: \+ [1-9]\d*(?:\.[1-9]\d*)?)*", command):
                continue
            if re.fullmatch(r'Attribute "(?:Pan|Tilt)" At -?\d+(?:\.\d+)?', command):
                continue
            if re.fullmatch(r"Store Cue [1-9]\d* Sequence [1-9]\d* /merge /cueonly /nc", command):
                continue
            raise ExistingPositionMergeError("POSITION_MERGE_COMMAND_NOT_ALLOWLISTED")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        self.validate(approved_plan, None)
        return approved_plan.commands
