"""Guarded real-MA2 Effect Resource Resolver verifier.

This is intentionally limited to the existing approved Effect Builder v1 path.
It never emits a Cue Effect application command: that grammar has no
real-machine evidence and remains a blocked continuation after the resource is
verified.  The created resource, if any, is Agent-owned and retained.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.runtime import AgentRuntime


def _song_input() -> dict[str, object]:
    # Exactly one PRE_CHORUS produces one deterministic SLOW Dimmer Chase.
    # The other sections only satisfy the intentionally narrow first-song
    # schema and do not create more Effect resources.
    return {
        "song_name": "ZEN_AI_EFFECT_RESOURCE_TEST",
        "active_sequence_range": [1, 9999],
        "effect_policy": "DIMMER_CHASE_V1",
        "sections": [
            {"name": "INTRO", "role": "INTRO", "energy": 0.2},
            {"name": "VERSE", "role": "VERSE", "energy": 0.4},
            {"name": "PRE", "role": "PRE_CHORUS", "energy": 0.6},
            {"name": "BRIDGE", "role": "BRIDGE", "energy": 0.5},
            {"name": "OUTRO", "role": "OUTRO", "energy": 0.2},
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify typed Effect Resource Resolver against a real MA2 only when explicitly authorized.")
    parser.add_argument("--real-machine", action="store_true", help="Required: permits one normal approved Agent-owned Effect Builder workflow.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 connection without --real-machine.")

    runtime = AgentRuntime(ROOT)
    core = AgentCore(runtime)
    settings = runtime.preferences["ma2"]
    core.connect(settings["host"], settings["port"], settings["username"], "")
    deadline = time.monotonic() + 4.0
    while not runtime.ready and runtime.state.value == "AUTHENTICATING" and time.monotonic() < deadline:
        time.sleep(0.05)
        runtime.poll_connection()
    if not runtime.ready:
        raise SystemExit("MA2 did not reach READY; no write was attempted.")
    report: dict[str, object] = {"connection": runtime.status_text(), "song": _song_input()["song_name"], "created_effect": None, "cue_effect_application": "BLOCKED_NO_REAL_MACHINE_GRAMMAR"}
    try:
        phase_a = core.preview_first_song(_song_input())
        report["phase_a"] = {"type": phase_a["type"], "message": phase_a["message"], "action": phase_a["action"]}
        action = phase_a.get("action") or {}
        if action.get("status") == "PENDING_APPROVAL":
            result = core.approve_action(str(action["id"]))
            report["created_effect"] = {"result": result, "catalog": core.effect_catalog.load()}
            # A fresh second preview must resolve the catalog row and stop at
            # the explicit Cue Effect grammar gate.  It does not create Cues.
            phase_b = core.preview_first_song(_song_input())
            report["phase_b"] = {"type": phase_b["type"], "message": phase_b["message"], "action": phase_b["action"]}
            if "EFFECT_APPLICATION_UNVERIFIED" not in phase_b["message"]:
                raise RuntimeError("Expected the unresolved Cue Effect grammar gate after resource verification.")
        elif action.get("status") == "PREVIEW_ONLY":
            report["existing_effect_reused"] = True
        else:
            raise RuntimeError("Resolver did not produce a safe resource preview.")
        report["status"] = "PASS"
    finally:
        runtime.disconnect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
