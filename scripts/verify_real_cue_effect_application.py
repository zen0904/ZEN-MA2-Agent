"""Run the one isolated Cue Effect Application POC through AgentCore.

This verifier requires explicit authorization and never sends a raw MA2
command.  It uses the same Preview -> Approval route as Desktop/mobile.
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the isolated real-MA2 Cue Effect application grammar.")
    parser.add_argument("--real-machine", action="store_true", help="Required: permits connection to the designated real Test Show for fresh Preview evidence.")
    parser.add_argument("--approve", action="store_true", help="Explicitly approve and execute the previewed Agent-owned Sequence/Cue POC.")
    parser.add_argument("--effect", type=int, default=3520, help="Existing verified Agent-owned Effect number (default: 3520).")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 connection without --real-machine.")

    runtime = AgentRuntime(ROOT)
    core = AgentCore(runtime)
    settings = runtime.preferences["ma2"]
    core.connect(settings["host"], settings["port"], settings["username"], "")
    deadline = time.monotonic() + 5.0
    while not runtime.ready and runtime.state.value == "AUTHENTICATING" and time.monotonic() < deadline:
        time.sleep(0.05)
        runtime.poll_connection()
    if not runtime.ready:
        raise SystemExit("MA2 did not reach READY; no write was attempted.")
    report: dict[str, object] = {"connection": runtime.status_text(), "effect": args.effect}
    try:
        preview = core.preview_cue_effect_application_poc(args.effect)
        report["preview"] = {"type": preview["type"], "message": preview["message"], "action": preview["action"]}
        action = preview.get("action") or {}
        if action.get("status") != "PENDING_APPROVAL":
            raise RuntimeError("Cue Effect POC did not create an approval-gated ActionPlan.")
        if args.approve:
            result = core.approve_action(str(action["id"]))
            report["result"] = result
            report["capability"] = core.cue_effect_application_capability.load_verified()
            report["status"] = "PASS" if report["capability"] else "PARTIAL"
        else:
            report["result"] = None
            report["capability"] = core.cue_effect_application_capability.load_verified()
            report["status"] = "PREVIEW_ONLY"
    finally:
        runtime.disconnect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
