"""Recover bounded current-Show resource evidence from the proven SHEESH Test Show build.

This adapter is intentionally test-show-specific.  It never infers general
Preset applicability from a Preset type or fixture capability.  It only
re-exposes Group/Preset pairs that were actually programmed in the committed
real-MA2 SHEESH Build 001 plan, and only while the current Show still presents
the exact Sequence and Preset identities from that successful build.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .effect_resources import show_identity


SHEESH_TEST_SEQUENCE = 901
SHEESH_TEST_SEQUENCE_LABEL = "ZEN_SHEESH_TEST"
SOURCE = "SHEESH_REAL_MA2_TEST_SHOW_BUILD_001"


class TestShowEvidenceError(ValueError):
    pass


def _current_sequence_matches(profile: Mapping[str, Any]) -> bool:
    for item in profile.get("sequences", []) if isinstance(profile.get("sequences"), list) else []:
        if not isinstance(item, Mapping):
            continue
        if item.get("number") == SHEESH_TEST_SEQUENCE and str(item.get("name") or "") == SHEESH_TEST_SEQUENCE_LABEL:
            return True
    return False


def _palette_from_plan(plan: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in plan.get("test_palette", []) if isinstance(plan.get("test_palette"), list) else []:
        if not isinstance(item, Mapping):
            continue
        number = item.get("preset")
        label = str(item.get("label") or "").strip()
        if isinstance(number, int) and not isinstance(number, bool) and number > 0 and label:
            result[f"4.{number}"] = label
    return result


def derive_sheesh_test_preset_bindings(
    profile: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Derive only historically observed Group/Preset pairs for this Test Show.

    The committed build report states that Build 001 completed on real MA2 and
    that its native Color preset labels plus Sequence/Cue objects read back.
    This function still refuses reuse unless those exact Test Show object
    identities are present in the *current* scanned Show.
    """
    identity = show_identity(dict(profile))
    result: dict[str, Any] = {
        "schema": "zen.test_show_preset_binding_recovery.v0.1",
        "source": SOURCE,
        "show_identity": identity,
        "sequence": {
            "number": SHEESH_TEST_SEQUENCE,
            "label": SHEESH_TEST_SEQUENCE_LABEL,
            "current_match": False,
        },
        "status": "UNAVAILABLE",
        "bindings": [],
        "reason": None,
    }

    if str(plan.get("schema") or "") != "zen.show_plan.v0.1" or plan.get("sequence") != SHEESH_TEST_SEQUENCE:
        result["reason"] = "COMMITTED_TEST_PLAN_IDENTITY_MISMATCH"
        return result
    if str(plan.get("sequence_label") or "") != SHEESH_TEST_SEQUENCE_LABEL:
        result["reason"] = "COMMITTED_TEST_SEQUENCE_LABEL_MISMATCH"
        return result
    if not _current_sequence_matches(profile):
        result["reason"] = "CURRENT_TEST_SEQUENCE_IDENTITY_NOT_PRESENT"
        return result
    result["sequence"]["current_match"] = True

    groups = {
        item.get("group_id"): item
        for item in profile.get("groups", [])
        if isinstance(item, Mapping) and isinstance(item.get("group_id"), int)
    }
    presets = {
        str(item.get("reference") or ""): item
        for item in profile.get("presets", [])
        if isinstance(item, Mapping) and item.get("reference")
    }
    palette = _palette_from_plan(plan)
    if not palette:
        result["reason"] = "COMMITTED_TEST_PALETTE_EMPTY"
        return result

    used_refs: set[str] = set()
    observed: dict[tuple[int, str], set[int]] = {}
    for cue in plan.get("cues", []) if isinstance(plan.get("cues"), list) else []:
        if not isinstance(cue, Mapping):
            continue
        cue_number = cue.get("cue_number")
        for action in cue.get("actions", []) if isinstance(cue.get("actions"), list) else []:
            if not isinstance(action, Mapping) or action.get("operation") != "CALL_PRESET":
                continue
            target = action.get("target")
            group_id = target.get("ref") if isinstance(target, Mapping) and target.get("type") == "group" else None
            reference = str(action.get("preset_ref") or "")
            if reference not in palette:
                # Build 001 also contains no non-palette CALL_PRESET action today;
                # if that changes, do not silently promote it as Color evidence.
                continue
            if not isinstance(group_id, int) or group_id not in groups:
                result["reason"] = f"CURRENT_GROUP_{group_id}_NOT_PRESENT"
                return result
            current = presets.get(reference)
            if not current:
                result["reason"] = f"CURRENT_PRESET_{reference}_NOT_PRESENT"
                return result
            if str(current.get("preset_type") or "").upper() != "COLOR":
                result["reason"] = f"CURRENT_PRESET_{reference}_TYPE_MISMATCH"
                return result
            if str(current.get("name") or "") != palette[reference]:
                result["reason"] = f"CURRENT_PRESET_{reference}_LABEL_MISMATCH"
                return result
            used_refs.add(reference)
            if isinstance(cue_number, int):
                observed.setdefault((group_id, reference), set()).add(cue_number)

    if not observed:
        result["reason"] = "NO_OBSERVED_TEST_SHOW_COLOR_APPLICATIONS"
        return result
    if not used_refs.issubset(palette):
        result["reason"] = "OBSERVED_PRESET_OUTSIDE_TEST_PALETTE"
        return result

    bindings = []
    for (group_id, reference), cue_numbers in sorted(observed.items()):
        bindings.append({
            "status": "SHOW_BOUND_VERIFIED",
            "show_identity": deepcopy(identity),
            "group_id": group_id,
            "reference": reference,
            "preset_type": "COLOR",
            "source": SOURCE,
            "evidence": {
                "kind": "OBSERVED_REAL_MA2_TEST_BUILD_APPLICATION",
                "sequence": SHEESH_TEST_SEQUENCE,
                "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
                "cue_numbers": sorted(cue_numbers),
                "current_preset_label": palette[reference],
                "reuse_scope": "CURRENT_MATCHING_TEST_SHOW_ONLY",
            },
        })

    result["status"] = "SHOW_BOUND_VERIFIED"
    result["bindings"] = bindings
    result["reason"] = None
    return result


SHEESH_TEST_GROUP_FIXTURES: dict[int, tuple[int, ...]] = {
    1: tuple(range(101, 109)),
    2: tuple(range(301, 309)),
    3: tuple(range(201, 209)),
    4: tuple(range(501, 509)),
    5: tuple(range(401, 409)),
    6: tuple(range(601, 609)),
    7: tuple(range(701, 709)),
}


def derive_sheesh_test_rgb_palette_bindings(
    profile: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover full owned RGB palette applicability only from exact RGB evidence.

    This deliberately does not infer applicability from Preset type or Group
    name. It requires:
    - current Sequence 901 Test Show identity;
    - exact current Group member set for the known Test Show Group;
    - every current FixtureType used by that Group to have SHOW_BOUND_VERIFIED
      RGB_COLOR (COLORRGB1/2/3) channel evidence;
    - exact current owned 4.101-4.113 palette refs/types/labels.

    When all conditions hold, every owned RGB palette preset is applicable to
    that Group because the palette itself was authored through the same
    COLORRGB1/2/3 attribute family.
    """
    identity = show_identity(dict(profile))
    result: dict[str, Any] = {
        "schema": "zen.test_show_rgb_palette_binding_recovery.v0.1",
        "source": "SHEESH_TEST_SHOW_OWNED_RGB_PALETTE",
        "show_identity": identity,
        "status": "UNAVAILABLE",
        "bindings": [],
        "verified_groups": [],
        "rejected_groups": [],
        "reason": None,
    }

    if str(plan.get("schema") or "") != "zen.show_plan.v0.1" or plan.get("sequence") != SHEESH_TEST_SEQUENCE:
        result["reason"] = "COMMITTED_TEST_PLAN_IDENTITY_MISMATCH"
        return result
    if str(plan.get("sequence_label") or "") != SHEESH_TEST_SEQUENCE_LABEL:
        result["reason"] = "COMMITTED_TEST_SEQUENCE_LABEL_MISMATCH"
        return result
    if not _current_sequence_matches(profile):
        result["reason"] = "CURRENT_TEST_SEQUENCE_IDENTITY_NOT_PRESENT"
        return result

    palette = _palette_from_plan(plan)
    presets = {
        str(item.get("reference") or ""): item
        for item in profile.get("presets", [])
        if isinstance(item, Mapping) and item.get("reference")
    }
    if set(palette) != {f"4.{number}" for number in range(101, 114)}:
        result["reason"] = "OWNED_RGB_PALETTE_MANIFEST_INCOMPLETE"
        return result
    for reference, expected_label in palette.items():
        current = presets.get(reference)
        if not current:
            result["reason"] = f"CURRENT_PRESET_{reference}_NOT_PRESENT"
            return result
        if str(current.get("preset_type") or "").upper() != "COLOR":
            result["reason"] = f"CURRENT_PRESET_{reference}_TYPE_MISMATCH"
            return result
        if str(current.get("name") or "") != expected_label:
            result["reason"] = f"CURRENT_PRESET_{reference}_LABEL_MISMATCH"
            return result

    fixtures = {
        item.get("fixture_id"): item
        for item in profile.get("fixtures", [])
        if isinstance(item, Mapping) and isinstance(item.get("fixture_id"), int)
    }
    profiles = {}
    for item in profile.get("fixture_type_profiles", []) if isinstance(profile.get("fixture_type_profiles"), list) else []:
        if not isinstance(item, Mapping) or item.get("status") != "SHOW_BOUND_VERIFIED":
            continue
        fixture_type = item.get("fixture_type")
        label = str((fixture_type or {}).get("list_label") or "").strip() if isinstance(fixture_type, Mapping) else ""
        if label:
            profiles[label] = item

    groups = {
        item.get("group_id"): item
        for item in profile.get("groups", [])
        if isinstance(item, Mapping) and isinstance(item.get("group_id"), int)
    }

    bindings: list[dict[str, Any]] = []
    verified_groups: list[int] = []
    rejected_groups: list[dict[str, Any]] = []
    for group_id, expected_members in sorted(SHEESH_TEST_GROUP_FIXTURES.items()):
        group = groups.get(group_id)
        current_members = tuple(
            value
            for value in (group.get("fixture_ids_in_selection_order") or [])
            if isinstance(value, int) and not isinstance(value, bool)
        ) if isinstance(group, Mapping) else ()
        if len(current_members) != len(expected_members) or set(current_members) != set(expected_members):
            rejected_groups.append({"group_id": group_id, "reason": "GROUP_MEMBER_SET_MISMATCH"})
            continue

        type_labels = {
            str((fixtures.get(fixture_id) or {}).get("fixture_type") or "").strip()
            for fixture_id in current_members
        }
        type_labels.discard("")
        if not type_labels:
            rejected_groups.append({"group_id": group_id, "reason": "FIXTURE_TYPE_IDENTITY_UNAVAILABLE"})
            continue

        rgb_profiles = []
        unsupported = False
        for label in sorted(type_labels):
            fixture_profile = profiles.get(label)
            capability = (fixture_profile.get("capabilities") or {}).get("RGB_COLOR") if fixture_profile else None
            status = str((capability or {}).get("status") or "UNKNOWN") if isinstance(capability, Mapping) else "UNKNOWN"
            rgb_profiles.append({"fixture_type": label, "status": status})
            if status != "SHOW_BOUND_VERIFIED":
                unsupported = True
        if unsupported:
            rejected_groups.append({
                "group_id": group_id,
                "reason": "RGB_COLOR_NOT_SHOW_BOUND_VERIFIED",
                "fixture_types": rgb_profiles,
            })
            continue

        verified_groups.append(group_id)
        for reference, label in sorted(palette.items()):
            bindings.append({
                "status": "SHOW_BOUND_VERIFIED",
                "show_identity": deepcopy(identity),
                "group_id": group_id,
                "reference": reference,
                "preset_type": "COLOR",
                "source": "SHEESH_TEST_SHOW_OWNED_RGB_PALETTE",
                "evidence": {
                    "kind": "EXACT_OWNED_RGB_PALETTE_PLUS_SHOW_BOUND_RGB_CHANNELS",
                    "sequence": SHEESH_TEST_SEQUENCE,
                    "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
                    "expected_fixture_member_set": sorted(expected_members),
                    "current_fixture_ids_in_selection_order": list(current_members),
                    "fixture_types": rgb_profiles,
                    "current_preset_label": label,
                    "reuse_scope": "CURRENT_MATCHING_TEST_SHOW_RGB_GROUP_ONLY",
                },
            })

    result["bindings"] = bindings
    result["verified_groups"] = verified_groups
    result["rejected_groups"] = rejected_groups
    if bindings:
        result["status"] = "SHOW_BOUND_VERIFIED" if not rejected_groups else "PARTIAL"
    else:
        result["reason"] = "NO_CURRENT_GROUP_HAS_VERIFIED_RGB_PALETTE_APPLICABILITY"
    return result


def derive_sheesh_test_dimmer_bindings(
    profile: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Recover Group-bound Dimmer application evidence from real Build 001.

    This does not claim a universal FixtureType DIMMER capability. It only
    proves that the exact current Group member set matches the member set used
    by the successful Test Show build and that the committed Build 001 plan
    actually applied SET_DIMMER to that Group. Selection order may legitimately
    change later and is recorded as current evidence rather than treated as
    capability identity.
    """
    identity = show_identity(dict(profile))
    result: dict[str, Any] = {
        "schema": "zen.test_show_dimmer_binding_recovery.v0.1",
        "source": SOURCE,
        "show_identity": identity,
        "sequence": {
            "number": SHEESH_TEST_SEQUENCE,
            "label": SHEESH_TEST_SEQUENCE_LABEL,
            "current_match": False,
        },
        "status": "UNAVAILABLE",
        "bindings": [],
        "mismatched_groups": [],
        "reason": None,
    }

    if str(plan.get("schema") or "") != "zen.show_plan.v0.1" or plan.get("sequence") != SHEESH_TEST_SEQUENCE:
        result["reason"] = "COMMITTED_TEST_PLAN_IDENTITY_MISMATCH"
        return result
    if str(plan.get("sequence_label") or "") != SHEESH_TEST_SEQUENCE_LABEL:
        result["reason"] = "COMMITTED_TEST_SEQUENCE_LABEL_MISMATCH"
        return result
    if not _current_sequence_matches(profile):
        result["reason"] = "CURRENT_TEST_SEQUENCE_IDENTITY_NOT_PRESENT"
        return result
    result["sequence"]["current_match"] = True

    groups = {
        item.get("group_id"): item
        for item in profile.get("groups", [])
        if isinstance(item, Mapping) and isinstance(item.get("group_id"), int)
    }

    observed_cues: dict[int, set[int]] = {}
    for cue in plan.get("cues", []) if isinstance(plan.get("cues"), list) else []:
        if not isinstance(cue, Mapping):
            continue
        cue_number = cue.get("cue_number")
        for action in cue.get("actions", []) if isinstance(cue.get("actions"), list) else []:
            if not isinstance(action, Mapping) or action.get("operation") != "SET_DIMMER":
                continue
            target = action.get("target")
            group_id = target.get("ref") if isinstance(target, Mapping) and target.get("type") == "group" else None
            level = action.get("level")
            if (
                isinstance(group_id, int)
                and not isinstance(group_id, bool)
                and isinstance(level, (int, float))
                and not isinstance(level, bool)
                and 0 <= float(level) <= 100
                and isinstance(cue_number, int)
            ):
                observed_cues.setdefault(group_id, set()).add(cue_number)

    bindings: list[dict[str, Any]] = []
    mismatched: list[int] = []
    for group_id, expected_members in sorted(SHEESH_TEST_GROUP_FIXTURES.items()):
        group = groups.get(group_id)
        current_members = tuple(
            value
            for value in (group.get("fixture_ids_in_selection_order") or [])
            if isinstance(value, int) and not isinstance(value, bool)
        ) if isinstance(group, Mapping) else ()
        if len(current_members) != len(expected_members) or set(current_members) != set(expected_members):
            mismatched.append(group_id)
            continue
        cue_numbers = observed_cues.get(group_id, set())
        if not cue_numbers:
            continue
        bindings.append({
            "status": "SHOW_BOUND_VERIFIED",
            "show_identity": deepcopy(identity),
            "group_id": group_id,
            "capability": "DIMMER",
            "implementation": "SET_DIMMER",
            "source": SOURCE,
            "evidence": {
                "kind": "OBSERVED_REAL_MA2_TEST_BUILD_APPLICATION",
                "sequence": SHEESH_TEST_SEQUENCE,
                "sequence_label": SHEESH_TEST_SEQUENCE_LABEL,
                "cue_numbers": sorted(cue_numbers),
                "expected_fixture_member_set": sorted(expected_members),
                "current_fixture_ids_in_selection_order": list(current_members),
                "reuse_scope": "CURRENT_MATCHING_TEST_SHOW_GROUP_MEMBER_SET_ONLY",
            },
        })

    result["bindings"] = bindings
    result["mismatched_groups"] = mismatched
    if bindings:
        result["status"] = "SHOW_BOUND_VERIFIED" if not mismatched else "PARTIAL"
        result["reason"] = None if not mismatched else "SOME_CURRENT_GROUP_MEMBERSHIP_MISMATCH"
    else:
        result["reason"] = "NO_CURRENT_GROUP_MATCHES_OBSERVED_DIMMER_APPLICATION"
    return result


def test_show_palette_manifest(plan: Mapping[str, Any]) -> dict[str, str]:
    """Return the fixed Build 001 Color reference -> label manifest."""
    result: dict[str, str] = {}
    for item in plan.get("test_palette", []) if isinstance(plan.get("test_palette"), list) else []:
        if not isinstance(item, Mapping):
            continue
        number = item.get("preset")
        label = str(item.get("label") or "").strip()
        if isinstance(number, int) and not isinstance(number, bool) and 101 <= number <= 113 and label:
            result[f"4.{number}"] = label
    return result


def bounded_test_show_color_rows(
    plan: Mapping[str, Any],
    readbacks: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Build current Color inventory rows only from exact bounded readback.

    List Preset All on the verified Test Show can omit the newly-created
    4.101-4.113 Color rows. This helper accepts only the thirteen known Build
    001 references and only when the exact committed label is present in the
    fresh per-reference List response.
    """
    manifest = test_show_palette_manifest(plan)
    rows: list[dict[str, Any]] = []
    for reference, expected_label in sorted(manifest.items()):
        output = str(readbacks.get(reference) or "")
        upper = output.upper()
        if "OBJECT DOES NOT EXIST" in upper or "NO OBJECTS FOUND" in upper:
            continue
        if expected_label not in output:
            continue
        rows.append({
            "preset_type": "COLOR",
            "number": int(reference.split(".", 1)[1]),
            "reference": reference,
            "name": expected_label,
            "source": "FRESH_LIST_PRESET_REFERENCE_TEST_SHOW",
        })
    return rows
