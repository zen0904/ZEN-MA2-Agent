"""Read-only discovery for the currently running grandMA2 Show.

This verifier intentionally uses only AgentCore's allow-listed state readers
and native Group exports.  ``--real-machine`` is required before it connects;
there is no ActionPlan approval path because the verifier has no MA2 write
operation.  It produces a new Show-bound JSON profile and a human review
report without updating the old Effect Catalog or any production object.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.effect_resources import show_identity
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


PROFILE_PATH = ROOT / "data" / "ZEN_CURRENT_SHOW_PROFILE.json"
JSON_PATH = ROOT / "data" / "ZEN_CURRENT_SHOW_DISCOVERY.json"
REPORT_PATH = ROOT / "ZEN_CURRENT_SHOW_RESOURCE_REPORT.md"


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _await_ready(core: AgentCore, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.1)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 connection did not reach READY: {core.runtime.status_text()}")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _state_status(core: AgentCore) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "status": item["status"],
            "count": item["count"],
            "source": item["source"],
            "stale": item["stale"],
            "error": item["error"],
            "capability": item["capability"],
        }
        for name, item in core.state.summary().items()
    }


def _geometry_summary(values: list[dict[str, Any]], capability: dict[str, Any] | None) -> dict[str, Any]:
    missing = list((capability or {}).get("missing_subfixtures") or [])
    expected = len(values) + len(missing)
    usable: list[tuple[int, int, float, float, float]] = []
    for item in values:
        position = item.get("position") or {}
        try:
            usable.append((int(item["fixture_id"]), int(item["subfixture_id"]), float(position["x"]), float(position["y"]), float(position["z"])))
        except (KeyError, TypeError, ValueError):
            continue
    positions: dict[tuple[float, float, float], list[str]] = defaultdict(list)
    for fixture, subfixture, x, y, z in usable:
        positions[(x, y, z)].append(f"{fixture}.{subfixture}")
    duplicates = [
        {"position": {"x": point[0], "y": point[1], "z": point[2]}, "fixture_subfixtures": members}
        for point, members in sorted(positions.items())
        if len(members) > 1
    ]
    nonzero = [item for item in usable if any(abs(value) > 0.0001 for value in item[2:])]
    coverage = round(len(usable) / expected, 4) if expected else 0.0
    if not usable:
        status, reason = "GEOMETRY_PARTIAL", "No geometry-bearing Subfixture rows were returned."
    elif coverage < 1.0:
        status, reason = "GEOMETRY_PARTIAL", "At least one expected Subfixture geometry row is missing."
    elif not nonzero or len(positions) <= 1:
        status, reason = "GEOMETRY_UNINITIALIZED", "All returned Fixtures overlap at a zero or single coordinate."
    else:
        status, reason = "GEOMETRY_READY", "Fresh Subfixture geometry has non-zero, non-identical coordinates."
    return {
        "status": status,
        "reason": reason,
        "fixture_subfixture_count": len(usable),
        "expected_subfixture_count": expected,
        "coverage_ratio": coverage,
        "nonzero_xyz_count": len(nonzero),
        "unique_xyz_positions": len(positions),
        "duplicate_xyz_clusters": duplicates,
        "missing_subfixtures": missing,
    }


def _group_summary(profile: dict[str, Any]) -> list[dict[str, Any]]:
    fixture_types = {item.get("fixture_id"): item.get("fixture_type") for item in profile.get("fixtures", []) if isinstance(item, dict)}
    result: list[dict[str, Any]] = []
    for group in profile.get("groups", []):
        if not isinstance(group, dict):
            continue
        members = list(group.get("fixture_ids_in_selection_order") or [])
        type_counts = Counter(str(fixture_types.get(member) or "UNAVAILABLE") for member in members)
        result.append({
            "id": group.get("group_id"),
            "name": group.get("name"),
            "fixture_count": len(members),
            "membership_status": (group.get("membership") or {}).get("status"),
            "members": members,
            "fixture_types": dict(sorted(type_counts.items())),
        })
    return result


def _effect_summary(profile: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    effects = [item for item in profile.get("effects", []) if isinstance(item, dict)]
    effect_by_id = {item.get("effect_id"): item for item in effects}
    identity = profile["show_identity"]
    # A persisted catalog was produced by an earlier Agent session.  This
    # read-only show-switch pass must not make it reusable merely because an
    # ID and label happen to be present in the new inventory.  The normal
    # resolver performs its own fresh exact-object validation later.
    verified: list[dict[str, Any]] = []
    legacy_isolated: list[dict[str, Any]] = []
    for entry in catalog.get("entries", []):
        effect = effect_by_id.get(entry.get("effect_id"))
        if not effect or entry.get("show_identity") != identity or effect.get("name") != entry.get("label"):
            continue
        legacy_isolated.append(
            {
                "id": effect["effect_id"],
                "name": effect.get("name"),
                "verification": entry.get("verification"),
                "source": entry.get("source"),
                "reason": "SHOW_SWITCH_DISCOVERY_REQUIRES_FRESH_RESOLVER_VERIFICATION",
            }
        )
    strict = [
        {"id": item.get("effect_id"), "name": item.get("name")}
        for item in effects
        if re.fullmatch(r"FX_DIM_CHASE_(?:SLOW|MED|FAST)", str(item.get("name") or "").strip(), re.I)
    ]
    verified_ids = {item["id"] for item in verified}
    strict_ids = {item["id"] for item in strict}
    unlabeled = [item for item in effects if not str(item.get("name") or "").strip() or str(item.get("name")).strip() == str(item.get("effect_id"))]
    named = [item for item in effects if item.get("effect_id") not in verified_ids | strict_ids and item not in unlabeled]
    return {
        "total": len(effects),
        "verified_agent_owned": verified,
        "strict_semantic_template": strict,
        "named_unverified_count": len(named),
        "named_unverified_shortlist": [{"id": item.get("effect_id"), "name": item.get("name")} for item in named[:30]],
        "unlabeled_count": len(unlabeled),
        "legacy_isolated": legacy_isolated,
    }


def _preset_summary(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in profile.get("presets", []):
        if isinstance(item, dict):
            grouped[str(item.get("preset_type") or "UNKNOWN")].append({"reference": item.get("reference"), "id": item.get("pool_id"), "name": item.get("name")})
    return {name: sorted(values, key=lambda value: (str(value.get("reference") or ""), str(value.get("name") or ""))) for name, values in sorted(grouped.items())}


def _read_only_audit(core: AgentCore) -> dict[str, Any]:
    messages = list(getattr(core.runtime.client, "audit_entries", []) if core.runtime.client else [])
    commands = [item.removeprefix("TX: ") for item in messages if item.startswith("TX: ")]
    allowed = [
        command for command in commands
        if command.startswith("Login ") or command.startswith("List ") or re.fullmatch(r'Export Group \d+ "ZEN_AGENT_G[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml" /nc', command)
    ]
    unexpected = [command for command in commands if command not in allowed]
    return {"status": "ZERO_WRITES" if not unexpected else "FAIL", "commands": commands, "unexpected_commands": unexpected}


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ZEN Current Show Resource Report",
        "",
        "**Scope:** fresh read-only discovery of the currently running grandMA2 Show.",
        "",
        "## Show identity",
        "",
        f"- Current: `{report['show_identity']['value']}` ({report['show_identity']['kind']})",
        f"- Previous profile identity: `{report['previous_identity'] or 'unavailable'}`",
        f"- Identity comparison: **{report['previous_identity_comparison']}**",
        f"- Previous Show-bound cache isolated: **{report['previous_cache_invalidated']}**",
        "- Old Effect/Preset/Group/Sequence references are not treated as current resources.",
        "",
        "## Groups",
        "",
        "| ID | Name | Members | Ordered fixture IDs | Fixture types | Freshness |",
        "|---:|---|---:|---|---|---|",
    ]
    for item in report["groups"]:
        members = ", ".join(map(str, item["members"])) or "(empty)"
        types = "; ".join(f"{name} ×{count}" for name, count in item["fixture_types"].items()) or "UNAVAILABLE"
        lines.append(f"| {item['id']} | {item['name']} | {item['fixture_count']} | {members} | {types} | {item['membership_status']} |")
    lines.extend(["", "## Fixtures and Subfixtures", "", f"- Unique Fixtures: **{report['fixture_count']}**", f"- Geometry-bearing Subfixtures: **{report['geometry']['fixture_subfixture_count']}**", "", "### Fixture Types", ""])
    for name, count in report["fixture_types"].items():
        lines.append(f"- `{name}`: {count} fixture(s)")
    lines.extend(["", "## Presets", ""])
    for pool, entries in report["presets"].items():
        lines.extend([f"### {pool}", "", "| Reference | ID | Exact name |", "|---|---:|---|"])
        for item in entries:
            lines.append(f"| {item['reference'] or 'UNAVAILABLE'} | {item['id'] or 'UNAVAILABLE'} | {item['name'] or ''} |")
        lines.append("")
    if not report["semantic_positions"]:
        lines.extend(["## Semantic Position Presets", "", "NONE — no registry label has a fresh exact match in this Show.", ""])
    else:
        lines.extend(["## Semantic Position Presets", ""])
        for item in report["semantic_positions"]:
            lines.append(f"- `{item.get('label')}` → `{item.get('semantic_role')}` ({item.get('reference')})")
        lines.append("")
    effects = report["effects"]
    lines.extend(["## Effects", "", f"- Total: {effects['total']}", f"- Verified Agent-owned reusable: {len(effects['verified_agent_owned'])}", f"- Legacy catalog entries isolated: {len(effects['legacy_isolated'])}", f"- Strict semantic templates: {len(effects['strict_semantic_template'])}", f"- Named unverified: {effects['named_unverified_count']}", f"- Unlabeled: {effects['unlabeled_count']}", ""])
    for title, rows in (("Verified Agent-owned", effects["verified_agent_owned"]), ("Legacy catalog entries isolated", effects["legacy_isolated"]), ("Strict semantic templates", effects["strict_semantic_template"]), ("Named unverified shortlist", effects["named_unverified_shortlist"])):
        lines.extend([f"### {title}", ""])
        if rows:
            for row in rows:
                lines.append(f"- {row['id']}: `{row['name']}`")
        else:
            lines.append("- None")
        lines.append("")
    geometry = report["geometry"]
    lines.extend([
        "## Geometry",
        "",
        f"- State: **{geometry['status']}** — {geometry['reason']}",
        f"- Coverage: {geometry['fixture_subfixture_count']}/{geometry['expected_subfixture_count']} ({geometry['coverage_ratio']:.0%})",
        f"- Non-zero XYZ Subfixtures: {geometry['nonzero_xyz_count']}",
        f"- Unique XYZ positions: {geometry['unique_xyz_positions']}",
        f"- Duplicate XYZ clusters: {len(geometry['duplicate_xyz_clusters'])}",
        "- Terms are numeric X/Y/Z only; Stage Left/Right is intentionally unassigned.",
        "",
        "## Sequence / Cue / Page / Executor / Timecode occupancy",
        "",
        f"- Sequences: {report['sequence_count']}",
        f"- Cue discovery: {report['cue_discovery_status']} ({report['cue_count']} parsed)",
        f"- Pages: {report['page_count']}",
        f"- Executors: {report['executor_count']}",
        f"- Timecodes: {report['timecode_count']}",
        "",
        "### Existing Sequences",
        "",
    ])
    if report["sequences"]:
        for item in report["sequences"]:
            lines.append(f"- {item.get('number')}: `{item.get('name')}`")
    else:
        lines.append("- None")
    lines.extend([
        "",
        "### Cue inventory limitation",
        "",
        "- " + ("The Show owner confirmed this template intentionally has no Cues. The generic Cue inventory reader is still not a portable enumeration backend because MA2 returned Error #28." if report["cue_discovery_status"] == "EXPECTED_EMPTY_USER_CONFIRMED" else "The generic Cue inventory reader was rejected by MA2 with Error #28; no conclusion about actual Cue occupancy is made." if report["cue_discovery_status"] == "ERROR" else "Cue inventory was read through the current supported provider."),
        "",
        "## Creative resource analysis",
        "",
        f"- Fresh non-empty Groups: {report['creative_diversity']['nonempty_groups']} — {report['creative_group_names'] or 'none'}.",
        f"- Fixture-type diversity: {len(report['fixture_types'])} types across {report['fixture_count']} Fixtures.",
        f"- Safe Preset inventory returned by MA2: {report['creative_diversity']['preset_references']} reference(s).",
        f"- Current verified reusable Effects: {report['creative_diversity']['verified_or_template_effects']}; legacy catalog entries remain isolated.",
        f"- Geometry strategies: {report['geometry_strategy_status']}.",
        f"- Auto-Geometry candidates: {report['auto_geometry_candidates'] or 'none'}.",
        "",
        "## Designer resource readiness",
        "",
        f"- Overall: **{report['designer_readiness']}**",
        f"- Without geometry: **{report['designer_without_geometry']}**",
        f"- Auto Geometry readiness: **{report['auto_geometry_readiness']}**",
        f"- Creative diversity: {report['creative_diversity']}",
        f"- Exact limitation: {report['limitation']}",
        "",
        "## MA2 write audit",
        "",
        f"- **{report['write_audit']['status']}**",
        "- Allowed transport was Login, List, and Agent-owned `Export Group` only.",
        f"- Unexpected commands: {report['write_audit']['unexpected_commands'] or 'none'}",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fresh, read-only discovery of the running MA2 Show.")
    parser.add_argument("--real-machine", action="store_true", help="Required before connecting to the real MA2 console.")
    parser.add_argument("--profile", type=Path, default=PROFILE_PATH)
    parser.add_argument("--json", dest="json_path", type=Path, default=JSON_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--expected-empty-cues", action="store_true", help="Record the operator-confirmed empty Cue inventory without treating Error #28 as a Show problem.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real Show discovery without --real-machine.")

    previous = _read_json(ROOT / "data" / "ZEN_SHOW_PROFILE.json")
    previous_identity = (previous or {}).get("show_identity") or (show_identity(previous) if previous else None)
    core = AgentCore(AgentRuntime(ROOT))
    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _await_ready(core)
        for resource in ("groups", "fixtures", "fixture_geometry", "presets", "effects", "sequences", "pages", "executors", "timecodes"):
            print(f"READ {resource}", flush=True)
            core.refresh_state(resource)
        groups = core.state.get("groups")
        group_numbers = sorted(int(_value(item, "number")) for item in (groups.values if groups else []) if _value(item, "number") is not None)
        for group_no in group_numbers:
            print(f"EXPORT GROUP {group_no}", flush=True)
            core.refresh_state("group_membership", group_no=group_no)
        sequences = core.state.get("sequences")
        sequence_numbers = sorted(int(_value(item, "number")) for item in (sequences.values if sequences else []) if _value(item, "number") is not None)
        for index, sequence in enumerate(sequence_numbers, start=1):
            print(f"READ CUES {index}/{len(sequence_numbers)}: {sequence}", flush=True)
            core.refresh_state("cues", sequence=sequence)

        profile = core.scan_show_profile(args.profile)
        identity = profile["show_identity"]
        geometry_snapshot = core.state.get("fixture_geometry")
        geometry = _geometry_summary(list(geometry_snapshot.values if geometry_snapshot else []), geometry_snapshot.capability if geometry_snapshot else None)
        groups_summary = _group_summary(profile)
        fixture_types = Counter(str(item.get("fixture_type") or "UNAVAILABLE") for item in profile.get("fixtures", []) if isinstance(item, dict))
        catalog = core.effect_catalog.load()
        effects = _effect_summary(profile, catalog)
        presets = _preset_summary(profile)
        audit = _read_only_audit(core)
        cue_reader_error = any("NO CUE SOURCE GIVEN" in line.upper() for line in audit["commands"] + list(getattr(core.runtime.client, "audit_entries", []) if core.runtime.client else []))
        cue_discovery_status = "EXPECTED_EMPTY_USER_CONFIRMED" if cue_reader_error and args.expected_empty_cues else "ERROR" if cue_reader_error else "SUPPORTED"
        memberships = [item for item in groups_summary if item["membership_status"] == "SUPPORTED" and item["fixture_count"] > 0]
        useful_presets = sum(len(rows) for rows in presets.values())
        verified_or_template_effects = len(effects["verified_agent_owned"]) + len(effects["strict_semantic_template"])
        designer_without_geometry = "READY" if len(memberships) > 1 and useful_presets > 1 else "PARTIAL" if memberships and useful_presets else "NO"
        if geometry["status"] == "GEOMETRY_READY":
            auto_geometry = "NOT_NEEDED"
        elif memberships and fixture_types:
            auto_geometry = "READY"
        elif memberships:
            auto_geometry = "PARTIAL"
        else:
            auto_geometry = "BLOCKED"
        designer = "YES" if designer_without_geometry == "READY" and verified_or_template_effects else "PARTIAL" if designer_without_geometry != "NO" else "NO"
        limitations: list[str] = []
        if cue_discovery_status == "ERROR":
            limitations.append("Cue inventory is unavailable: the current List Cue <sequence> reader received MA2 Error #28 (NO CUE SOURCE GIVEN) for each scanned Sequence; zero parsed Cues is not an empty-Cue conclusion.")
        elif cue_discovery_status == "EXPECTED_EMPTY_USER_CONFIRMED":
            limitations.append("This template's empty Cue inventory is operator-confirmed. MA2 Error #28 means the generic Cue inventory reader remains unsuitable for inferring Cue emptiness in other Shows.")
        if geometry["status"] != "GEOMETRY_READY":
            limitations.append(f"Fixture geometry is {geometry['status']}; it is not used as a creative placement guarantee.")
        if designer == "NO":
            limitations.append("No fresh non-empty Group membership and useful Preset combination was available.")
        if not limitations:
            limitations.append("Fresh Group membership and Fixture/Subfixture discovery completed.")
        comparison = "DIFFERENT" if previous_identity and previous_identity != identity else "SAME_FINGERPRINT" if previous_identity else "UNAVAILABLE"
        creative_group_names = ", ".join(f"{item['id']} {item['name']}" for item in memberships)
        auto_geometry_candidates = ", ".join(f"Group {item['id']} {item['name']}" for item in memberships) if auto_geometry in {"READY", "PARTIAL"} else ""
        geometry_strategy_status = "AVAILABLE_FROM_FRESH_SUBFIXTURE_GEOMETRY" if geometry["status"] == "GEOMETRY_READY" else "NOT_AVAILABLE — no positioning, pairing, or row inference is safe while all XYZ values overlap"
        report = {
            "schema": "zen.current_show_discovery.v0.1",
            "read_only": True,
            "connection": {"state": core.runtime.state.value, "user": core.runtime.client.authenticated_user if core.runtime.client else None},
            "show_identity": identity,
            "previous_identity": previous_identity.get("value") if isinstance(previous_identity, dict) else None,
            "previous_identity_comparison": comparison,
            "previous_cache_invalidated": "YES",
            "state": _state_status(core),
            "groups": groups_summary,
            "fixture_count": len(profile.get("fixtures", [])),
            "fixture_types": dict(sorted(fixture_types.items())),
            "presets": presets,
            "semantic_positions": list(profile.get("semantic_presets", [])),
            "effects": effects,
            "geometry": geometry,
            "sequence_count": len(profile.get("sequences", [])),
            "sequences": list(profile.get("sequences", [])),
            "cue_count": len(profile.get("cues", [])),
            "cue_discovery_status": cue_discovery_status,
            "page_count": len(profile.get("pages", [])),
            "executor_count": len(profile.get("executors", [])),
            "timecode_count": len(profile.get("timecodes", [])),
            "designer_readiness": designer,
            "designer_without_geometry": designer_without_geometry,
            "auto_geometry_readiness": auto_geometry,
            "creative_diversity": {"nonempty_groups": len(memberships), "preset_references": useful_presets, "verified_or_template_effects": verified_or_template_effects, "geometry_state": geometry["status"]},
            "creative_group_names": creative_group_names,
            "auto_geometry_candidates": auto_geometry_candidates,
            "geometry_strategy_status": geometry_strategy_status,
            "limitation": " ".join(limitations),
            "write_audit": audit,
        }
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.report.write_text(_markdown(report), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["write_audit"]["status"] == "ZERO_WRITES" else 2
    finally:
        core.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
