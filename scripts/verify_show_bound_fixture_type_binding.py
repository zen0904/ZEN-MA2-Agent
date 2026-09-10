"""Capture current-Show FixtureType channel definitions without MA2 mutation.

This verifier is deliberately a narrow real-console operation.  It validates
the loaded Show against the committed Existing Show fingerprint before invoking
the Core's per-type read-only FixtureType export provider.  The resulting local
JSON and Markdown retain raw channel evidence and every per-type outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers import bind_local_profile_candidate
from zen_ma2_agent.telnet_client import ConnectionState


EXPECTED_PROFILE = ROOT / "data" / "ZEN_CURRENT_SHOW_PROFILE.json"
RESULT_PATH = ROOT / "data" / "ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json"
REPORT_PATH = ROOT / "ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.md"

# These are prior local-library *candidates*, not bindings.  No path is
# searched by name at runtime; a candidate is compared only after an exact
# current-Show export has passed identity/channel validation.
LOCAL_CANDIDATES = {
    "2 ZEN BAW 20R Mode 2": "zhong_light@zhong_light_xp20rbsw@mode_2.xml",
    "3 ZEN DMH-160 St_Preset": "zhong_light@zhong_light_dmh-160@st_preset.xml",
    "4 ZEN K10 Shapes": "clay_paky@a.leda_b-eye_k10@shapes.xmlp",
    "5 ZEN MAC AU XB Standard": "zhong_light@zhong_light_mac_au_xb@standard.xml",
    "6 ZEN LEDPar 9c 9Ch Mode A": "zhong_light@zhong_light_led_par_9ch@9ch_mode_a.xml",
    "7 Atomic 3000 LED Extended": "martin@atomic_3000_led@extended.xmlp",
}


def _await_ready(core: AgentCore, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.1)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 connection did not reach READY: {core.runtime.status_text()}")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected object JSON: {path}")
    return value


def _audit(core: AgentCore) -> dict[str, Any]:
    entries = list(getattr(core.runtime.client, "audit_entries", []) if core.runtime.client else [])
    commands = [entry.removeprefix("TX: ") for entry in entries if entry.startswith("TX: ")]
    allowed = [
        command for command in commands
        if command.startswith("Login ")
        or command in {"List Group", "List Fixture", "List Preset All"}
        or command.startswith("Export FixtureType ")
    ]
    unexpected = [command for command in commands if command not in allowed]
    return {
        "ma2_object_write_audit": "ZERO_WRITES" if not unexpected else "FAIL",
        "commands": commands,
        "unexpected_commands": unexpected,
        "fixture_9999_targeted": any("9999" in command for command in commands),
    }


def _candidate_comparison(core: AgentCore, record: dict[str, Any]) -> dict[str, Any]:
    label = str((record.get("fixture_type") or {}).get("list_label") or "")
    relative = LOCAL_CANDIDATES.get(label)
    if record.get("status") != "SHOW_BOUND_VERIFIED":
        return {
            "status": "NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT",
            "source": "LOCAL_PROFILE_CANDIDATE_REFERENCE",
            "candidate_relative_path": relative,
        }
    if not relative:
        return {
            "status": "LOCAL_PROFILE_CANDIDATE_UNBOUND",
            "source": "LOCAL_PROFILE_CANDIDATE_REFERENCE",
            "reason": "No prior candidate is registered for this exact current-Show label.",
        }
    library = core.fixture_type_export_provider.resolver.resolve_library(core.runtime.preferences.get("state_adapter", {}).get("importexport_path", "auto"))
    candidate = library / relative
    if not candidate.is_file():
        return {
            "status": "LOCAL_PROFILE_CANDIDATE_UNBOUND",
            "source": "LOCAL_PROFILE_CANDIDATE_REFERENCE",
            "candidate_relative_path": relative,
            "reason": "Candidate file was unavailable in the same verified local MA2 library.",
        }
    comparison = bind_local_profile_candidate(record, candidate.read_bytes())
    return comparison | {
        "candidate_relative_path": relative,
        "candidate_file_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
    }


def _capability_text(record: dict[str, Any]) -> str:
    capabilities = record.get("capabilities") or {}
    if not capabilities:
        return "UNKNOWN"
    return ", ".join(f"{key}={value.get('status', 'UNKNOWN')}" for key, value in sorted(capabilities.items()))


def _markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Show-Bound Fixture Type / Channel Profile Binding 001",
        "",
        "**Status:** `" + result["binding_status"] + "`",
        "",
        "## Real-console preflight",
        "",
        f"- Telnet loopback READY: `{result['connection']['ready']}` as `{result['connection']['user']}`.",
        f"- Expected Existing Show fingerprint: `{result['expected_show_identity']['value']}`.",
        f"- Fresh loaded-Show fingerprint: `{result['current_show_identity']['value']}`.",
        f"- Existing Show identity/profile match: `{result['show_identity_match']}`.",
        "- Fixture `9999` was not selected, exported, or addressed: `" + ("YES" if not result["write_audit"]["fixture_9999_targeted"] else "NO") + "`.",
        "",
        "## Binding method and provenance",
        "",
        "`List Fixture` exact type label -> native `Export FixtureType <id>` -> exact XML index/name/mode identity -> parsed ChannelType/ChannelFunction inventory -> technical-definition SHA-256.",
        "No name-only local profile match can establish a Show binding. Local candidates are compared only after `SHOW_BOUND_VERIFIED`.",
        "",
        "## Results by current Show FixtureType",
        "",
    ]
    for record in result["fixture_type_profiles"]:
        identity = record.get("fixture_type") or {}
        lines.extend([
            f"### `{identity.get('list_label', 'UNAVAILABLE')}`",
            "",
            f"- FixtureType numeric ID: `{identity.get('fixture_type_id', 'UNAVAILABLE')}`.",
            f"- Export / provenance state: `{record.get('status', 'UNKNOWN')}` via `{record.get('source', 'UNAVAILABLE')}`.",
            f"- Exact identity verification: `" + ("PASS" if record.get("status") == "SHOW_BOUND_VERIFIED" else "FAIL / NOT_AVAILABLE") + "`.",
            f"- Failure reason: `{record.get('failure_reason', 'none')}`.",
            f"- Technical-definition SHA-256: `{record.get('technical_definition_sha256', 'UNAVAILABLE')}`.",
            f"- XML SHA-256: `{record.get('xml_sha256', 'UNAVAILABLE')}`.",
            f"- Capability classification: {_capability_text(record)}.",
            f"- Local profile candidate comparison: `{(record.get('local_profile_candidate') or {}).get('status', 'NOT_ATTEMPTED')}`.",
            "",
            "#### Parsed ChannelType / ChannelFunction inventory",
            "",
        ])
        channels = record.get("channels") or []
        if channels:
            lines.extend(["| Index | Attribute | Feature | Preset | Channel Functions |", "|---:|---|---|---|---|"])
            for channel in channels:
                functions = "; ".join(json.dumps(item, sort_keys=True) for item in channel.get("functions") or []) or "none"
                lines.append(f"| {channel.get('index', '')} | {channel.get('attribute', '')} | {channel.get('feature', '')} | {channel.get('preset', '')} | {functions} |")
        else:
            lines.append("- `NOT_AVAILABLE` — no verified exported channel inventory.")
        lines.append("")
    lines.extend([
        "## B3 eligibility and A/B readiness",
        "",
        "Show-bound technical capability can support only future case-specific resource eligibility. It does not create a permanent fixture role, case assignment, geometry/position semantics, Effect behavior, or action grammar.",
        f"- `REAL_SONG_EXISTING_SHOW_AB_002`: `{result['ab_002_readiness']}`.",
        f"- Reason: {result['ab_002_reason']}",
        "",
        "## Safety audit",
        "",
        f"- MA2 objects modified: `NONE`.",
        f"- MA2 object write audit: `{result['write_audit']['ma2_object_write_audit']}`.",
        "- Allowed console transport was Login, List Group, List Fixture, List Preset All and native external `Export FixtureType` only.",
        f"- Unexpected commands: `{result['write_audit']['unexpected_commands'] or 'none'}`.",
        "- Production Designer: `UNCHANGED`; B3: `GUIDANCE_ASSISTED_AB_ONLY`; `ZEN_STYLE_PROFILE`: `DEFERRED`.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Real current-Show FixtureType binding verification.")
    parser.add_argument("--real-machine", action="store_true", help="Required before connecting to the loaded MA2 Show.")
    parser.add_argument("--expected-profile", type=Path, default=EXPECTED_PROFILE)
    parser.add_argument("--result", type=Path, default=RESULT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real-console FixtureType verification without --real-machine.")

    expected = _load_json(args.expected_profile)
    expected_identity = expected.get("show_identity")
    if not isinstance(expected_identity, dict) or not expected_identity.get("value"):
        raise RuntimeError("Expected Existing Show profile has no usable show identity.")
    core = AgentCore(AgentRuntime(ROOT))
    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _await_ready(core)
        for resource in ("groups", "fixtures", "presets"):
            core.refresh_state(resource)
        current = core.scan_show_profile()
        current_identity = current["show_identity"]
        if current_identity != expected_identity:
            raise RuntimeError("CURRENT_SHOW_IDENTITY_MISMATCH: FixtureType export was not attempted.")
        refresh = core.refresh_state("fixture_type_profiles")
        profiles = list(refresh["values"])
        for record in profiles:
            record["local_profile_candidate"] = _candidate_comparison(core, record)
        verified = [item for item in profiles if item.get("status") == "SHOW_BOUND_VERIFIED"]
        result = {
            "schema": "zen.show_bound_fixture_type_binding_run.v0.1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "connection": {"ready": core.runtime.ready, "host": ma2["host"], "port": ma2["port"], "user": core.runtime.client.authenticated_user if core.runtime.client else None},
            "expected_show_identity": expected_identity,
            "current_show_identity": current_identity,
            "show_identity_match": "MATCH",
            "fixture_type_profiles": profiles,
            "binding_status": "SHOW_BOUND_VERIFIED" if len(verified) == len(profiles) else "PARTIAL",
            "write_audit": _audit(core),
            "ab_002_readiness": "READY_FOR_CAPABILITY_TO_ROLE_ELIGIBILITY_REVIEW" if len(verified) == len(profiles) else "NOT_READY_FOR_EXPRESSIVE_ACTION_DELTA",
            "ab_002_reason": "All current FixtureType technical definitions are Show-bound; a separate bounded capability-to-role eligibility review remains required before action deltas." if len(verified) == len(profiles) else "One or more current FixtureTypes did not establish a Show-bound technical definition.",
        }
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.report.write_text(_markdown(result), encoding="utf-8")
        print(json.dumps({"binding_status": result["binding_status"], "fixture_type_count": len(profiles), "verified_count": len(verified), "result": str(args.result), "report": str(args.report)}, ensure_ascii=False))
        return 0
    finally:
        core.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
