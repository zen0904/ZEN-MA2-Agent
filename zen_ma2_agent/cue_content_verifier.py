"""Deterministic comparison of approved ShowPlan actions with Sequence Export readback."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class CueContentVerificationError(ValueError):
    """The approved plan or readback evidence cannot be compared safely."""


def _strict_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _cue_number(value: object) -> int | None:
    if not isinstance(value, Mapping):
        return None
    number = _strict_positive_int(value.get("number"))
    sub_number = value.get("sub_number")
    if number is None:
        return None
    if sub_number not in (None, "", "0", 0):
        return None
    return number


def _fixture_id(row: Mapping[str, Any]) -> int | None:
    channel = row.get("channel")
    if not isinstance(channel, Mapping):
        return None
    return _strict_positive_int(channel.get("fixture_id"))


def _numeric_equal(raw: object, expected: int) -> bool:
    if raw is None:
        return False
    try:
        return Decimal(str(raw).strip()) == Decimal(expected)
    except (InvalidOperation, ValueError):
        return False


def _address_components(address: object) -> tuple[int, ...] | None:
    if not isinstance(address, Mapping):
        return None
    raw = address.get("no_components")
    if not isinstance(raw, list) or not raw:
        return None
    values: list[int] = []
    for item in raw:
        if isinstance(item, bool):
            return None
        text = str(item).strip()
        if not text.isdigit():
            return None
        values.append(int(text))
    return tuple(values)


def _preset_suffix_matches(address: object, reference: str) -> bool:
    parts = reference.split(".")
    if len(parts) != 2 or any(not item.isdigit() for item in parts):
        raise CueContentVerificationError(f"Invalid Preset reference: {reference}")
    expected = tuple(int(item) for item in parts)
    actual = _address_components(address)
    return bool(actual and len(actual) >= 2 and actual[-2:] == expected)


def _effect_matches(address: object, effect_id: int) -> bool:
    actual = _address_components(address)
    return bool(actual and actual[-1] == effect_id)


def _flatten_rows(cue: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    parts = cue.get("parts")
    for part in parts if isinstance(parts, list) else []:
        if not isinstance(part, Mapping):
            continue
        cue_data = part.get("cue_data")
        for row in cue_data if isinstance(cue_data, list) else []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def verify_cue_content(
    show_plan: Mapping[str, Any],
    sequence_discovery: Mapping[str, Any],
    group_memberships: Mapping[int, list[int] | tuple[int, ...]],
) -> dict[str, Any]:
    """Compare expected typed actions with raw Sequence Export evidence.

    Raw numeric Value equality is checked literally/numerically. No DMX,
    percentage, physical-unit, or normalization claim is made.
    """
    cues = show_plan.get("cues")
    if not isinstance(cues, list) or not cues:
        raise CueContentVerificationError("Approved ShowPlan has no Cue list.")
    exported = sequence_discovery.get("cues")
    if not isinstance(exported, list):
        raise CueContentVerificationError("Sequence export has no Cue list.")

    numbered: dict[int, dict[str, Any]] = {}
    duplicates: set[int] = set()
    unnumbered = 0
    for cue in exported:
        if not isinstance(cue, dict):
            continue
        number = _cue_number(cue.get("number"))
        if number is None:
            unnumbered += 1
            continue
        if number in numbered:
            duplicates.add(number)
        else:
            numbered[number] = cue

    source = sequence_discovery.get("xml_discovery")
    sha256 = source.get("sha256") if isinstance(source, Mapping) else None
    report_cues: list[dict[str, Any]] = []
    overall = "VERIFIED"

    for expected_cue in cues:
        if not isinstance(expected_cue, Mapping):
            raise CueContentVerificationError("Approved Cue is not an object.")
        cue_no = expected_cue.get("cue_number")
        if isinstance(cue_no, bool) or not isinstance(cue_no, int) or cue_no < 1:
            raise CueContentVerificationError("Approved Cue number is invalid.")

        actual = numbered.get(cue_no)
        cue_result: dict[str, Any] = {
            "cue_number": cue_no,
            "label": expected_cue.get("label"),
            "status": "VERIFIED",
            "actions": [],
        }
        if cue_no in duplicates:
            cue_result["status"] = "MISMATCH"
            cue_result["reason"] = "DUPLICATE_NUMBERED_CUE"
            report_cues.append(cue_result)
            overall = "MISMATCH"
            continue
        if actual is None:
            cue_result["status"] = "MISMATCH"
            cue_result["reason"] = "EXPECTED_CUE_ABSENT"
            report_cues.append(cue_result)
            overall = "MISMATCH"
            continue

        rows = _flatten_rows(actual)
        rows_by_fixture: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            fixture = _fixture_id(row)
            if fixture is not None:
                rows_by_fixture.setdefault(fixture, []).append(row)

        actions = expected_cue.get("actions")
        if not isinstance(actions, list):
            raise CueContentVerificationError(f"Cue {cue_no} has no typed action list.")

        for index, action in enumerate(actions, start=1):
            if not isinstance(action, Mapping):
                raise CueContentVerificationError(f"Cue {cue_no} action {index} is invalid.")
            operation = action.get("operation")
            target = action.get("target")
            group_no = target.get("ref") if isinstance(target, Mapping) else None
            if isinstance(group_no, bool) or not isinstance(group_no, int) or group_no < 1:
                raise CueContentVerificationError(f"Cue {cue_no} action {index} has invalid Group target.")
            members_raw = group_memberships.get(group_no)
            members = [
                member for member in (members_raw or [])
                if isinstance(member, int) and not isinstance(member, bool) and member > 0
            ]
            evidence: dict[str, Any] = {
                "action_index": index,
                "operation": operation,
                "group": group_no,
                "group_members": members,
                "status": "VERIFIED",
            }
            if not members:
                evidence.update(status="MISMATCH", reason="GROUP_MEMBERSHIP_UNAVAILABLE")
            elif operation == "SET_DIMMER":
                level = action.get("level")
                if isinstance(level, bool) or not isinstance(level, int):
                    raise CueContentVerificationError(
                        f"Cue {cue_no} action {index} has invalid Dimmer level."
                    )
                per_fixture: dict[str, list[object]] = {}
                missing: list[int] = []
                for fixture in members:
                    dim_rows = [
                        row for row in rows_by_fixture.get(fixture, [])
                        if isinstance(row.get("channel"), Mapping)
                        and row["channel"].get("attribute_name") == "DIM"
                    ]
                    values = [
                        (row.get("raw_values") or {}).get("Value")
                        for row in dim_rows
                        if isinstance(row.get("raw_values"), Mapping)
                    ]
                    per_fixture[str(fixture)] = values
                    if not any(_numeric_equal(value, level) for value in values):
                        missing.append(fixture)
                evidence.update(
                    expected_raw_numeric=level,
                    raw_values_by_fixture=per_fixture,
                    claim_scope="Raw exported DIM Value numerically equals the approved Builder level; no unit/scaling claim.",
                )
                if missing:
                    evidence.update(status="MISMATCH", reason="DIM_VALUE_MISMATCH_OR_ABSENT", missing_fixtures=missing)

            elif operation == "CALL_PRESET":
                reference = action.get("preset_ref")
                if not isinstance(reference, str):
                    raise CueContentVerificationError(
                        f"Cue {cue_no} action {index} has invalid Preset reference."
                    )
                per_fixture: dict[str, list[list[str]]] = {}
                missing: list[int] = []
                for fixture in members:
                    candidates: list[list[str]] = []
                    matched = False
                    for row in rows_by_fixture.get(fixture, []):
                        preset = row.get("preset")
                        if isinstance(preset, Mapping) and isinstance(preset.get("no_components"), list):
                            candidates.append([str(value) for value in preset["no_components"]])
                        if _preset_suffix_matches(preset, reference):
                            matched = True
                    per_fixture[str(fixture)] = candidates
                    if not matched:
                        missing.append(fixture)
                evidence.update(
                    expected_preset_ref=reference,
                    preset_no_components_by_fixture=per_fixture,
                    claim_scope="Preset identity matches trailing exported No components only; labels/display text are not identity evidence.",
                )
                if missing:
                    evidence.update(status="MISMATCH", reason="PRESET_IDENTITY_MISMATCH_OR_ABSENT", missing_fixtures=missing)

            elif operation == "CALL_EFFECT":
                effect_ref = action.get("effect_ref")
                effect_id = effect_ref.get("id") if isinstance(effect_ref, Mapping) else None
                if isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id < 1:
                    raise CueContentVerificationError(
                        f"Cue {cue_no} action {index} has invalid Effect reference."
                    )
                per_fixture: dict[str, list[list[str]]] = {}
                missing: list[int] = []
                for fixture in members:
                    candidates: list[list[str]] = []
                    matched = False
                    for row in rows_by_fixture.get(fixture, []):
                        effect = row.get("effect")
                        if isinstance(effect, Mapping) and isinstance(effect.get("no_components"), list):
                            candidates.append([str(value) for value in effect["no_components"]])
                        if _effect_matches(effect, effect_id):
                            matched = True
                    per_fixture[str(fixture)] = candidates
                    if not matched:
                        missing.append(fixture)
                evidence.update(
                    expected_effect_id=effect_id,
                    effect_no_components_by_fixture=per_fixture,
                    claim_scope="Effect identity matches the trailing exported Effect No component.",
                )
                if missing:
                    evidence.update(status="MISMATCH", reason="EFFECT_IDENTITY_MISMATCH_OR_ABSENT", missing_fixtures=missing)

            else:
                evidence.update(status="MISMATCH", reason="UNSUPPORTED_APPROVED_ACTION")

            if evidence["status"] != "VERIFIED":
                cue_result["status"] = "MISMATCH"
                overall = "MISMATCH"
            cue_result["actions"].append(evidence)

        report_cues.append(cue_result)

    return {
        "schema": "zen.cue_content_verification.v0.1",
        "status": overall,
        "sequence_no": sequence_discovery.get("sequence_no"),
        "source": sequence_discovery.get("source"),
        "source_discovery_status": sequence_discovery.get("status"),
        "source_xml_sha256": sha256,
        "unnumbered_system_cues": unnumbered,
        "duplicate_numbered_cues": sorted(duplicates),
        "cues": report_cues,
    }


__all__ = ["CueContentVerificationError", "verify_cue_content"]
