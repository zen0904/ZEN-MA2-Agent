"""Read-only current-Show Position application probe Preview.

This script never registers an approvable action or sends a Show write. A
future separately reviewed execution boundary is required before the probe
can be performed on MA2 and its Cue content verified.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.position_application_evidence import build_position_poc_preview
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.show_pools import PresetProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview a non-executable Position Preset application probe")
    parser.add_argument("--group-id", type=int, required=True)
    parser.add_argument("--preset-ref", required=True)
    parser.add_argument("--result", type=Path, default=Path("data/position_application_poc_preview_001.json"))
    args = parser.parse_args()
    runtime = AgentRuntime(Path.cwd())
    core = AgentCore(runtime)
    try:
        core.connect("127.0.0.1", 30000, "MM")
        runtime.poll_connection()
        if not runtime.ready:
            raise RuntimeError("MA2_READ_ONLY_CONNECTION_NOT_READY")
        for resource in ("groups", "fixtures", "fixture_geometry", "sequences", "presets"):
            result = core.refresh_state(resource)
            if result["status"] != "available":
                raise RuntimeError(f"FRESH_{resource.upper()}_READ_FAILED: {result.get('error')}")
        for group in core.state.get("groups").values:
            result = core.refresh_state("group_membership", group_no=group["number"])
            if result["status"] != "available":
                raise RuntimeError(f"EXACT_GROUP_{group['number']}_EXPORT_FAILED: {result.get('error')}")
        result = core.refresh_state("fixture_type_profiles")
        if result["status"] != "available":
            raise RuntimeError(f"FIXTURE_TYPE_PROFILES_FAILED: {result.get('error')}")
        # List Preset All supplies pool inventory. Re-read the chosen exact
        # reference independently; type/label must agree at preview time.
        direct = PresetProvider().parse(runtime.read_state(f"List Preset {args.preset_ref}"), "POSITION")
        profile = core.scan_show_profile()
        # Use the same bounded read-only profile enrichment as the normal
        # OpenClaw path, so later exact Show identity comparison is meaningful.
        core._recover_bounded_test_show_evidence(profile)
        candidate = [row for row in profile["presets"] if row.get("reference") == args.preset_ref]
        if (len(candidate) != 1 or len(direct) != 1
                or direct[0].get("reference") != args.preset_ref
                or direct[0].get("preset_type") != "POSITION"
                or direct[0].get("name") != candidate[0].get("name")):
            raise RuntimeError("POSITION_PRESET_DIRECT_IDENTITY_MISMATCH")
        preview = build_position_poc_preview(profile, group_id=args.group_id, preset_ref=args.preset_ref)
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": preview["status"], "preview_id": preview["preview_id"],
                          "path": str(args.result.resolve()), "show_identity": preview["show_identity"],
                          "ma2_writes": 0}, ensure_ascii=False))
        return 0
    finally:
        core.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
