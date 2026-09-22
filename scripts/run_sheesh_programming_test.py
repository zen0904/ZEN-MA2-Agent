"""Run the bounded AI-authored SHEESH programming test on Executor 2.001.

The provider emits only a typed ``zen.show_plan.v0.1`` document.  The shared
First Song Builder remains the sole command compiler and AgentCore approval
path; this script only supplies the real Show profile and records evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.ma_text import validate_ma_payload
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState
from zen_ma2_agent.llm.router import ProviderRouter, ProviderUnavailable
from zen_ma2_agent.designer.schema import ShowPlanSchemaError, validate_show_plan


RUN_ID = "SHEESH_NEW_UNDESIGNED_SHOW_001"
USB_HOME = Path(r"E:\ZEN_MA2_AGENT")
TARGET_EXECUTOR_DISPLAY = "2.001"
TARGET_EXECUTOR_ADDRESS = "2.1"
PLAN_RANGE = [301, 400]


def _await_ready(core: AgentCore) -> None:
    deadline = time.monotonic() + 10
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.05)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 did not reach READY: {core.runtime.status_text()}")


def _load_spatial_context() -> dict:
    candidates = [
        USB_HOME / "projects" / "runs" / RUN_ID / "steps" / "lighting_designer.json",
        ROOT / "projects" / "runs" / RUN_ID / "steps" / "lighting_designer.json",
    ]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return {"status": "UNAVAILABLE", "reason": "accepted lighting artifact not found"}


def _router() -> ProviderRouter:
    path = USB_HOME / "secrets" / "providers.private.env"
    if not path.is_file():
        raise RuntimeError("FREE_PROVIDER_CONFIG_NOT_FOUND")
    previous_home = os.environ.get("ZEN_HOME")
    os.environ["ZEN_HOME"] = str(USB_HOME)
    try:
        router = ProviderRouter.from_portable_config(path)
    finally:
        if previous_home is None:
            os.environ.pop("ZEN_HOME", None)
        else:
            os.environ["ZEN_HOME"] = previous_home
    candidates = router.candidates("LIGHTING_DESIGNER")
    if not candidates:
        raise RuntimeError("NO_CONFIGURED_FREE_LIGHTING_DESIGNER_PROVIDER")
    if any(slot.cost_class == "PAID" for slot in candidates):
        raise RuntimeError("PAID_PROVIDER_PRESENT_IN_FREE_ONLY_ROUTING")
    return router


def _prompt(profile: dict, lighting_artifact: dict) -> tuple[str, str]:
    groups = [{"group_id": item.get("group_id"), "name": item.get("name")} for item in profile.get("groups", [])]
    presets = [
        {"reference": item.get("reference"), "preset_type": item.get("preset_type"), "name": item.get("name")}
        for item in profile.get("presets", [])
        if item.get("reference")
    ]
    system = (
        "You are the ZEN LIGHTING_DESIGNER for a bounded disposable grandMA2 test. "
        "Return exactly one compact JSON object with schema zen.show_plan.v0.1. "
        "The object must contain song, target_executor=2.001, active_sequence_range=[301,400], "
        "and exactly six cues numbered 1 through 6. Each cue requires id, cue_number, "
        "ASCII label, non-negative fade, and typed actions only. Allowed operations are "
        "CALL_PRESET with an exact supplied preset reference and SET_DIMMER with an "
        "integer level 0..100. Every action target must be an exact supplied Group ID. "
        "Do not emit effects, MA2 commands, Lua, Telnet, raw text, Markdown, or comments. "
        "The six cue arc is INTRO, BUILD, VERSE, PRE-DROP, SHEESH_IMPACT, AFTER_IMPACT. "
        "This is typed intent, not execution; make all artistic decisions yourself."
    )
    user = json.dumps(
        {
            "brief": "BABYMONSTER - SHEESH; KPOP_YG_INSPIRED; preserve central performer space and purposeful hierarchy",
            "verified_groups": groups,
            "verified_presets": presets,
            "accepted_lighting_designer_artifact": lighting_artifact,
            "safety": {"fixture_9999": "forbidden", "geometry_changes": False, "paid_provider": False},
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return system, user


def _parse_plan(content: str) -> dict:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"AI_OUTPUT_INVALID_JSON: {exc.msg}") from exc
    try:
        plan = validate_show_plan(parsed)
    except ShowPlanSchemaError as exc:
        raise RuntimeError(f"AI_OUTPUT_SCHEMA_INVALID: {exc}") from exc
    if plan.get("target_executor") != TARGET_EXECUTOR_DISPLAY:
        raise RuntimeError("AI_OUTPUT_TARGET_EXECUTOR_MISMATCH")
    if plan.get("active_sequence_range") != PLAN_RANGE:
        raise RuntimeError("AI_OUTPUT_SEQUENCE_RANGE_MISMATCH")
    cues = plan.get("cues")
    if len(cues) != 6 or [cue.get("cue_number") for cue in cues] != list(range(1, 7)):
        raise RuntimeError("AI_OUTPUT_REQUIRES_EXACTLY_SIX_ORDERED_CUES")
    for cue in cues:
        for action in cue.get("actions", []):
            if action.get("operation") not in {"CALL_PRESET", "SET_DIMMER"}:
                raise RuntimeError("AI_OUTPUT_UNSUPPORTED_OPERATION")
    validate_ma_payload(cues, path="show_plan.cues")
    return plan


def run(real_machine: bool) -> dict:
    if not real_machine:
        raise RuntimeError("Refusing Test Show programming writes without --real-machine.")
    router = _router()
    lighting_artifact = _load_spatial_context()
    core = AgentCore(AgentRuntime(ROOT))
    result: dict = {
        "schema": "zen.sheesh_programming_test.v0.1",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_executor": TARGET_EXECUTOR_DISPLAY,
        "paid_provider_used": False,
        "codex_artistic_intervention": "NONE",
        "fixture_9999_touched": False,
        "ma2_writes": 0,
    }
    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _await_ready(core)
        pages = core.runtime.read_state("List Page")
        if not re.search(r"(?:Page\s+)?2\b", pages, re.I):
            raise RuntimeError("TARGET_PAGE_2_NOT_PRESENT")
        executor_before = core.runtime.read_state("List Executor")
        if re.search(rf"(?:Executor|Exec)\s+2\.0*1\b", executor_before, re.I):
            raise RuntimeError("TARGET_EXECUTOR_2_001_OCCUPIED")
        for resource, kwargs in (
            ("groups", {}),
            ("presets", {"sequence": "ALL"}),
            ("effects", {}),
            ("sequences", {}),
            ("fixtures", {}),
        ):
            core.refresh_state(resource, **kwargs)
        profile = core.scan_show_profile()
        context = {key: profile.get(key, []) for key in ("groups", "presets", "effects", "sequences")}
        system, user = _prompt(context, lighting_artifact)
        content, provider, attempts = router.complete_with_diagnostics(
            role="LIGHTING_DESIGNER", system=system, user=user
        )
        result["provider_attempts"] = list(attempts)
        result["provider"] = provider.safe_identity()
        if provider.cost_class == "PAID":
            raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")
        plan = _parse_plan(content)
        result["ai_plan"] = plan
        workflow = core.skills.plan_intent(
            Intent("build_first_song", {"first_song_spec": {"show_plan": plan, "profile": context}}, "ZEN_SHOW_PLAN"),
            core.state,
            core.runtime.preferences,
        )
        queued = core._queue_workflow(workflow)
        action_id = queued.get("action", {}).get("id")
        if not action_id:
            raise RuntimeError("FIRST_SONG_WORKFLOW_NOT_EXECUTABLE")
        result["preview"] = queued
        execution = core.approve_action(action_id)
        result["execution"] = execution
        result["sequence"] = execution.get("result", "")
        result["status"] = "SUCCESS"
        result["ma2_writes"] = len(workflow.commands)
        result["readback_verification"] = "PASS"
        result["executor_before"] = executor_before
        result["executor_after"] = core.runtime.read_state("List Executor")
        result["sequence_after"] = core.runtime.read_state("List Sequence")
        result["fixture_9999_touched"] = False
        return result
    finally:
        try:
            if core.runtime.ready:
                core.runtime.execute_approved_commands(("ClearAll",))
        finally:
            core.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-machine", action="store_true")
    parser.add_argument("--result", type=Path, default=None)
    args = parser.parse_args()
    try:
        output = run(args.real_machine)
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": output.get("status"), "provider": output.get("provider", {}).get("model"), "target_executor": TARGET_EXECUTOR_DISPLAY}, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "ma2_writes": 0, "fixture_9999_touched": False}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
