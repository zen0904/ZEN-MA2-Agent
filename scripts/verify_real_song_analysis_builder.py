"""Explicit real-MA2 verifier for the structured Song Analysis pipeline.

``--real-machine`` is required before the shared approval lifecycle is allowed
to create the new Agent-owned Sequence.  There is no raw Telnet escape hatch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.builder import ShowPlanBuilder
from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.song_analysis import SongAnalysisAdapter, validate_song_analysis
from zen_ma2_agent.telnet_client import ConnectionState


def _await_ready(core: AgentCore, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.1)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 connection did not reach READY: {core.runtime.status_text()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or execute structured Song Analysis through the existing approved Builder.")
    parser.add_argument("--real-machine", action="store_true", help="Allow normal approval to create a new Agent-owned Sequence.")
    parser.add_argument("--verify-existing", action="store_true", help="Read-only verification of the exact Agent-owned Sequence for this analysis.")
    parser.add_argument("--song-suffix", help="Create a separately labelled verification Sequence; letters, digits, _ and - only.")
    parser.add_argument("--analysis", type=Path, default=ROOT / "examples" / "REALISTIC_SONG_ANALYSIS.json")
    args = parser.parse_args()
    analysis = validate_song_analysis(json.loads(args.analysis.read_text(encoding="utf-8")))
    if args.song_suffix:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,24}", args.song_suffix):
            raise SystemExit("--song-suffix accepts only letters, digits, _ and -.")
        analysis["song"]["title"] = f"{analysis['song']['title']}_{args.song_suffix}"
    core = AgentCore(AgentRuntime(ROOT))
    report: dict[str, Any] = {"mode": "real-machine" if args.real_machine else "preview-only", "analysis": str(args.analysis), "analysis_schema": analysis["schema"]}
    try:
        settings = core.runtime.preferences["ma2"]
        report["build_identity"] = core.build_identity
        report["connection"] = core.connect(settings["host"], settings["port"], settings["username"], "")
        _await_ready(core)
        report["ready"] = {"state": core.runtime.state.value, "user": core.runtime.client.authenticated_user if core.runtime.client else None}
        if args.verify_existing:
            for resource, kwargs in (("groups", {}), ("presets", {"sequence": "ALL"}), ("sequences", {})):
                core.refresh_state(resource, **kwargs)
            profile = core.scan_show_profile()
            plan = FirstSongDesigner().design(SongAnalysisAdapter().to_designer_input(analysis), profile)
            label = ShowPlanBuilder._sequence_label(plan["song"])
            sequence = next((item.get("number") for item in profile.get("sequences", []) if item.get("name") == label), None)
            if not isinstance(sequence, int):
                raise RuntimeError("No exact Agent-owned Sequence label exists for this analysis.")
            report["existing_verification"] = core.verify_first_song_metadata(sequence, label, plan["cues"])
            report["sequence"] = sequence
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        preview = core.preview_song_analysis(analysis)
        action = preview["action"]
        report["preview"] = preview["message"]
        report["action"] = {"id": action["id"], "status": action["status"], "sequence": action["task"]["intent"]["parameters"]["sequence"], "label": action["task"]["intent"]["parameters"]["sequence_label"]}
        report["commands"] = [step["command"] for step in action.get("steps", []) if step.get("kind") == "command" and step.get("command")]
        if not args.real_machine:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        result = core.approve_action(action["id"])
        if result["status"] != "EXECUTED" or "Verification: PARTIAL" not in result["result"]:
            raise RuntimeError(f"Approved Song Analysis build was not verified: {result}")
        report["execution"] = result
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        core.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
