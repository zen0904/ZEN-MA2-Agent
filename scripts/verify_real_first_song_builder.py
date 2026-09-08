"""Explicit real-MA2 verifier for the narrow First Song Builder PoC.

The script never exposes a raw MA2 command path.  It calls the same
AgentCore preview and approval lifecycle as Desktop/Mobile.  ``--real-machine``
is required before the approval call that can create a Sequence.
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

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.builder import ShowPlanBuilder
from zen_ma2_agent.designer import FirstSongDesigner
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


def _await_ready(core: AgentCore, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.1)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 connection did not reach READY: {core.runtime.status_text()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview or explicitly execute the First Song Builder against real MA2.")
    parser.add_argument("--real-machine", action="store_true", help="Allow the normal approved ActionPlan to create an Agent-owned Sequence.")
    parser.add_argument("--verify-existing", action="store_true", help="Read-only verification of the exact existing Agent-owned Sequence for this input.")
    parser.add_argument("--song-suffix", help="Create a separately labelled Agent-owned verification Sequence; letters, digits, _ and - only.")
    parser.add_argument("--input", type=Path, default=ROOT / "examples" / "FIRST_SONG_INPUT.json")
    args = parser.parse_args()
    song_input = json.loads(args.input.read_text(encoding="utf-8"))
    if args.song_suffix:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,24}", args.song_suffix):
            raise SystemExit("--song-suffix accepts only letters, digits, _ and -.")
        song_input["song_name"] = f"{song_input['song_name']}_{args.song_suffix}"
    core = AgentCore(AgentRuntime(ROOT))
    report: dict[str, Any] = {"mode": "real-machine" if args.real_machine else "preview-only", "input": str(args.input)}
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
            plan = FirstSongDesigner().design(song_input, profile)
            label = ShowPlanBuilder._sequence_label(plan["song"])
            sequence = next((item.get("number") for item in profile.get("sequences", []) if item.get("name") == label), None)
            if not isinstance(sequence, int):
                raise RuntimeError("No exact Agent-owned Sequence label exists for this input.")
            report["existing_verification"] = core.verify_first_song_metadata(sequence, label, plan["cues"])
            report["sequence"] = sequence
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        preview = core.preview_first_song(song_input)
        action = preview["action"]
        report["preview"] = preview["message"]
        report["action"] = {"id": action["id"], "status": action["status"], "sequence": action["task"]["intent"]["parameters"]["sequence"], "label": action["task"]["intent"]["parameters"]["sequence_label"]}
        report["commands"] = [step["command"] for step in action.get("steps", []) if step.get("kind") == "command" and step.get("command")]
        if not args.real_machine:
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0

        result = core.approve_action(action["id"])
        if result["status"] != "EXECUTED" or "Verification: PARTIAL" not in result["result"]:
            raise RuntimeError(f"First Song approved build was not verified: {result}")
        report["execution"] = result
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        core.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
