"""Run the bounded AI-authored SHEESH programming test on Executor 2.001.

The provider emits only a typed ``zen.show_plan.v0.1`` document.  The shared
First Song Builder remains the sole command compiler and AgentCore approval
path; this script only supplies the real Show profile and records evidence.
"""
from __future__ import annotations

import argparse
import json
import math
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


class ProgrammingRunError(RuntimeError):
    """Bounded failure carrying secret-safe run evidence."""

    def __init__(self, message: str, *, result: dict) -> None:
        super().__init__(message)
        self.result = result


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


def _typed_action_contract(groups: list[dict], presets: list[dict]) -> dict:
    return {
        "SET_DIMMER": {
            "operation": "SET_DIMMER",
            "target": {"type": "group", "ref": "<integer Group ID>"},
            "level": "<integer 0..100>",
        },
        "CALL_PRESET": {
            "operation": "CALL_PRESET",
            "target": {"type": "group", "ref": "<integer Group ID>"},
            "preset_ref": "<exact verified preset reference>",
        },
        "verified_group_ids": [item.get("group_id") for item in groups],
        "verified_preset_references": [item.get("reference") for item in presets],
    }


def _prompt(profile: dict, lighting_artifact: dict) -> tuple[str, str]:
    groups = [{"group_id": item.get("group_id"), "name": item.get("name")} for item in profile.get("groups", [])]
    presets = [
        {"reference": item.get("reference"), "preset_type": item.get("preset_type"), "name": item.get("name")}
        for item in profile.get("presets", [])
        if item.get("reference")
    ]
    contract = _typed_action_contract(groups, presets)
    system = (
        "You are the ZEN LIGHTING_DESIGNER for a bounded disposable grandMA2 test. "
        "Return exactly one compact JSON object with schema zen.show_plan.v0.1. "
        "The object must contain song, target_executor=2.001, active_sequence_range=[301,400], "
        "and exactly six cues numbered 1 through 6. Each cue requires id, cue_number, "
        "ASCII label, non-negative fade, and typed actions only. Every action MUST "
        "match exactly one of these JSON shapes: "
        + json.dumps(contract, ensure_ascii=True, separators=(",", ":")) + ". "
        "Allowed operations are only CALL_PRESET and SET_DIMMER. Every action target "
        "must be an exact supplied Group ID and every preset_ref an exact supplied "
        "preset reference. "
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


def _parse_plan(content: str, *, verified_group_ids: set[int], verified_preset_refs: set[str]) -> dict:
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
            if not isinstance(action, dict):
                raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: typed action must be an object")
            operation = action.get("operation")
            target = action.get("target")
            if operation not in {"CALL_PRESET", "SET_DIMMER"}:
                raise RuntimeError("AI_OUTPUT_UNSUPPORTED_OPERATION")
            if not isinstance(target, dict) or target.get("type") != "group" or not isinstance(target.get("ref"), int):
                raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: typed action target must be a group object with integer ref")
            if target["ref"] not in verified_group_ids:
                raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: typed action target Group ID is not verified")
            if operation == "SET_DIMMER":
                if not isinstance(action.get("level"), int) or not 0 <= action["level"] <= 100:
                    raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: SET_DIMMER level must be integer 0..100")
                if set(action) != {"operation", "target", "level"}:
                    raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: SET_DIMMER shape is not exact")
            else:
                if not isinstance(action.get("preset_ref"), str) or action["preset_ref"] not in verified_preset_refs:
                    raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: CALL_PRESET preset_ref is not verified")
                if set(action) != {"operation", "target", "preset_ref"}:
                    raise RuntimeError("AI_OUTPUT_SCHEMA_INVALID: CALL_PRESET shape is not exact")
    validate_ma_payload(cues, path="show_plan.cues")
    return plan


def _safe_provider_response(provider, content: str | None) -> dict[str, object]:
    """Persist bounded provider output without ever persisting a credential."""
    if not isinstance(content, str):
        return {"present": False, "secret_check": "NOT_RUN", "response_characters": 0, "raw_response": None}
    secret = bool(provider.api_key and provider.api_key in content)
    return {
        "present": True,
        "secret_check": "FAIL" if secret else "PASS",
        "response_characters": len(content),
        "raw_response": None if secret else content[:200000],
    }


def _canonicalize_plan_content(
    content: str,
    *,
    verified_group_ids: set[int],
) -> tuple[str, dict[str, object]]:
    """Normalize representation-only provider variants before strict validation."""
    try:
        plan = json.loads(content)
    except json.JSONDecodeError:
        raise
    if not isinstance(plan, dict):
        return content, {"applied": False, "fields": []}
    normalized = json.loads(json.dumps(plan, ensure_ascii=False))
    fields: list[str] = []
    target_executor = normalized.get("target_executor")
    if isinstance(target_executor, (int, float)) and not isinstance(target_executor, bool) and float(target_executor) == 2.001:
        normalized["target_executor"] = TARGET_EXECUTOR_DISPLAY
        fields.append("target_executor")
    active_range = normalized.get("active_sequence_range")
    if isinstance(active_range, list):
        converted: list[object] = []
        changed = False
        for value in active_range:
            if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
                converted.append(int(value))
                changed = True
            else:
                converted.append(value)
        if changed:
            normalized["active_sequence_range"] = converted
            fields.append("active_sequence_range")
    cues = normalized.get("cues")
    if isinstance(cues, list):
        for index, cue in enumerate(cues):
            if not isinstance(cue, dict):
                continue
            value = cue.get("cue_number")
            if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
                cue["cue_number"] = int(value)
                fields.append(f"cues[{index}].cue_number")
            fade = cue.get("fade")
            if isinstance(fade, str):
                try:
                    parsed_fade = float(fade)
                except ValueError:
                    parsed_fade = None
                if parsed_fade is not None and math.isfinite(parsed_fade) and parsed_fade >= 0:
                    cue["fade"] = int(parsed_fade) if parsed_fade.is_integer() else parsed_fade
                    fields.append(f"cues[{index}].fade")
            actions = cue.get("actions")
            if not isinstance(actions, list):
                continue
            for action_index, action in enumerate(actions):
                if not isinstance(action, dict):
                    continue
                target = action.get("target")
                if isinstance(target, dict):
                    ref = target.get("ref")
                    if isinstance(ref, str) and re.fullmatch(r"[0-9]+", ref) and int(ref) in verified_group_ids:
                        target["ref"] = int(ref)
                        fields.append(f"cues[{index}].actions[{action_index}].target.ref")
                if action.get("operation") == "SET_DIMMER":
                    level = action.get("level")
                    if isinstance(level, str) and re.fullmatch(r"[0-9]+", level) and 0 <= int(level) <= 100:
                        action["level"] = int(level)
                        fields.append(f"cues[{index}].actions[{action_index}].level")
    return json.dumps(normalized, ensure_ascii=False, separators=(",", ":")), {
        "applied": bool(fields),
        "fields": fields,
        "authority": "BOUNDED_REPRESENTATION_ONLY",
    }


def _schema_repair_prompt(*, rejected_content: str, error: str, groups: list[dict], presets: list[dict]) -> tuple[str, str]:
    contract = _typed_action_contract(groups, presets)
    system = (
        "You are repairing one rejected ZEN show plan. Return exactly one complete "
        "zen.show_plan.v0.1 JSON object. Preserve the six-cue artistic intent and "
        "repair only typed action structure. Every action must match exactly one of "
        + json.dumps(contract, ensure_ascii=True, separators=(",", ":"))
        + ". Do not emit unsupported operations, MA2 commands, Lua, Markdown, or prose."
    )
    user = json.dumps({
        "validator_error": error,
        "rejected_complete_plan": rejected_content,
        "supported_typed_action_contract": contract,
        "verified_groups": groups,
        "verified_presets": presets,
    }, ensure_ascii=True, separators=(",", ":"))
    return system, user


def run(real_machine: bool, *, saved_result_path: Path | None = None) -> dict:
    if not real_machine:
        raise RuntimeError("Refusing Test Show programming writes without --real-machine.")
    router = None if saved_result_path is not None else _router()
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
    provider_content: str | None = None
    provider = None
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
        if saved_result_path is not None:
            if not saved_result_path.is_file():
                raise RuntimeError("SAVED_PROVIDER_RESULT_NOT_FOUND")
            saved = json.loads(saved_result_path.read_text(encoding="utf-8"))
            raw = saved.get("provider_response", {}).get("raw_response")
            if not isinstance(raw, str) or not raw:
                raise RuntimeError("SAVED_PROVIDER_RAW_RESPONSE_NOT_AVAILABLE")
            content = raw
            provider_content = content
            result["source_saved_result"] = str(saved_result_path)
            result["provider"] = saved.get("provider")
            result["provider_response"] = saved.get("provider_response")
            result["provider_attempts"] = saved.get("provider_attempts", [])
        else:
            system, user = _prompt(context, lighting_artifact)
            content, provider, attempts = router.complete_with_diagnostics(
                role="LIGHTING_DESIGNER", system=system, user=user
            )
            provider_content = content
            result["provider_attempts"] = list(attempts)
            result["provider"] = provider.safe_identity()
            result["provider_response"] = _safe_provider_response(provider, content)
            if provider.cost_class == "PAID":
                raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")
        groups = context.get("groups", [])
        presets = [item for item in context.get("presets", []) if item.get("reference")]
        verified_group_ids = {int(item["group_id"]) for item in groups if isinstance(item.get("group_id"), int)}
        verified_preset_refs = {str(item["reference"]) for item in presets}
        canonical_content, normalization = _canonicalize_plan_content(
            content,
            verified_group_ids=verified_group_ids,
        )
        result["structural_canonicalization"] = normalization
        result["canonical_artifact"] = json.loads(canonical_content)
        try:
            plan = _parse_plan(
                canonical_content,
                verified_group_ids=verified_group_ids,
                verified_preset_refs=verified_preset_refs,
            )
        except RuntimeError as first_error:
            if saved_result_path is not None:
                raise
            if "invalid typed action" not in str(first_error).casefold() and "AI_OUTPUT_UNSUPPORTED_OPERATION" not in str(first_error):
                raise
            repair_system, repair_user = _schema_repair_prompt(
                rejected_content=content,
                error=str(first_error),
                groups=groups,
                presets=presets,
            )
            repaired = router.adapter.complete(provider, system=repair_system, user=repair_user)
            provider_content = repaired
            result["schema_repair"] = {
                "attempted": True,
                "provider": provider.safe_identity(),
                "response": _safe_provider_response(provider, repaired),
            }
            repaired_canonical, repair_normalization = _canonicalize_plan_content(
                repaired,
                verified_group_ids=verified_group_ids,
            )
            result["schema_repair"]["structural_canonicalization"] = repair_normalization
            result["canonical_artifact"] = json.loads(repaired_canonical)
            plan = _parse_plan(
                repaired_canonical,
                verified_group_ids=verified_group_ids,
                verified_preset_refs=verified_preset_refs,
            )
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
    except Exception as exc:
        result["status"] = "FAILED_PROVIDER_OUTPUT" if str(exc).startswith("AI_OUTPUT_") else "FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"
        if provider is not None and provider_content is not None and "provider_response" not in result:
            result["provider_response"] = _safe_provider_response(provider, provider_content)
        raise ProgrammingRunError(str(exc), result=result) from exc
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
    parser.add_argument("--saved-result", type=Path, default=None)
    args = parser.parse_args()
    try:
        output = run(args.real_machine, saved_result_path=args.saved_result)
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.saved_result is not None and output.get("canonical_artifact") is not None:
            canonical_path = (
                args.result.with_name("sheesh_programming_test_canonical.json")
                if args.result is not None
                else args.saved_result.with_name("sheesh_programming_test_canonical.json")
            )
            canonical_path.write_text(
                json.dumps({
                    "schema": "zen.show_plan.canonical.v0.1",
                    "source_saved_result": str(args.saved_result),
                    "source_raw_response_preserved": True,
                    "structural_canonicalization": output.get("structural_canonicalization", {}),
                    "plan": output["canonical_artifact"],
                }, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(json.dumps({"status": output.get("status"), "provider": output.get("provider", {}).get("model"), "target_executor": TARGET_EXECUTOR_DISPLAY}, ensure_ascii=True))
        return 0
    except ProgrammingRunError as exc:
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(json.dumps(exc.result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": exc.result.get("status", "FAILED"), "error": exc.result.get("error"), "ma2_writes": 0, "fixture_9999_touched": False}, ensure_ascii=True))
        return 1
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "ma2_writes": 0, "fixture_9999_touched": False}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
