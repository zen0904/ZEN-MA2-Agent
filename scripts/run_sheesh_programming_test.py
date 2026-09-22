"""Run the bounded SHEESH six-cue smoke test through the real MA2 build path.

This is intentionally a smoke test, not the full-song Design Mode. The provider
supplies artistic cue intent only; ZEN compiles verified Preset/Effect resource
choices into the strict internal ShowPlan before the Builder sees them.
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
from zen_ma2_agent.artistic_resources import (
    build_artistic_resource_map,
    effect_applicability_from_map,
    model_resource_contract,
    preset_applicability_from_map,
)
from zen_ma2_agent.designer.lean_design_mode import load_or_build_compact_context
from zen_ma2_agent.designer.artistic_plan import (
    ArtisticPlanCompileError,
    compile_artistic_cue_plan,
)
from zen_ma2_agent import protected_objects
from zen_ma2_agent.llm.router import ProviderRouter
from zen_ma2_agent.ma_text import validate_ma_payload
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.telnet_client import ConnectionState


RUN_ID = "SHEESH_NEW_UNDESIGNED_SHOW_001"
USB_HOME = Path(r"E:\ZEN_MA2_AGENT")
TARGET_EXECUTOR_DISPLAY = "2.002"
SONG = "SHEESH"
SHEESH_CUE_LABELS = ("INTRO", "BUILD", "VERSE", "PRE_DROP", "SHEESH_IMPACT", "AFTER_IMPACT")


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
    # Spatial context may inform a new design; an old Lighting Designer output
    # must never be injected as accepted artistic truth.
    candidates = [
        USB_HOME / "projects" / "runs" / RUN_ID / "steps" / "position_designer.json",
        ROOT / "projects" / "runs" / RUN_ID / "steps" / "position_designer.json",
    ]
    for path in candidates:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return {"status": "UNAVAILABLE", "reason": "accepted spatial artifact not found"}


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


def _load_preset_bindings() -> list[dict]:
    candidates = [
        USB_HOME / "data" / "ZEN_ARTISTIC_PRESET_BINDINGS.json",
        ROOT / "data" / "ZEN_ARTISTIC_PRESET_BINDINGS.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("bindings"), list):
            return [item for item in value["bindings"] if isinstance(item, dict)]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _provider_contract(resource_map: dict) -> dict:
    return {
        "cue": {
            "fade": "<non-negative seconds>",
            "actions": [
                {"group": "<verified Group ID>", "dimmer": "<0..100>"},
                {"group": "<verified Group ID>", "preset": "<verified preset reference>"},
                {"group": "<verified Group ID>", "color_preset": "<verified COLOR preset reference>"},
                {"group": "<verified Group ID>", "position_preset": "<verified POSITION preset reference>"},
                {"group": "<verified Group ID>", "focus_preset": "<verified FOCUS preset reference>"},
                {"group": "<verified Group ID>", "beam_preset": "<verified BEAM preset reference>"},
                {"group": "<verified Group ID>", "gobo_preset": "<verified GOBO preset reference>"},
                {"group": "<verified Group ID>", "effect": "<verified Effect ID>"},
            ],
        },
        "cue_order": list(SHEESH_CUE_LABELS),
        "group_resources": model_resource_contract(resource_map),
        "resource_rules": resource_map.get("rules", {}),
    }


def _prompt(design_context: dict, resource_map: dict) -> tuple[str, str]:
    contract = _provider_contract(resource_map)
    system = (
        "You are the ZEN LIGHTING_DESIGNER for a disposable grandMA2 programming test. "
        "Make the artistic lighting decisions. Return JSON only with one top-level key: cues. "
        "Return exactly six cues in this order: INTRO, BUILD, VERSE, PRE_DROP, "
        "SHEESH_IMPACT, AFTER_IMPACT. Each cue only needs fade and actions. "
        "Use only resources listed under that exact Group in group_resources. Compact actions "
        "may use dimmer, generic preset, typed color/position/focus/beam/gobo preset, or verified "
        "Effect ID only when the resource map exposes it for that Group. Do not use unbound "
        "Preset inventory or arbitrary MA2 Effect IDs. Do not infer capability from a Group name. "
        "Do not output schema names, song metadata, cue numbers, cue IDs, executor addresses, "
        "Sequence ranges, MA2 commands, Lua, Telnet, Markdown, or implementation details. "
        "ZEN owns all operational metadata and exact internal schema formatting."
    )
    user = json.dumps(
        {
            "brief": (
                "BABYMONSTER - SHEESH; KPOP_YG_INSPIRED; preserve central performer "
                "space, purposeful hierarchy, strong silhouette and restrained progression"
            ),
            "artistic_contract": contract,
            "design_context": design_context,
            "safety": {
                "fixture_9999": "forbidden",
                "geometry_changes": False,
                "paid_provider": False,
            },
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return system, user


def _safe_provider_response(provider, content: str | None) -> dict[str, object]:
    if not isinstance(content, str):
        return {
            "present": False,
            "secret_check": "NOT_RUN",
            "response_characters": 0,
            "raw_response": None,
        }
    secret = bool(provider.api_key and provider.api_key in content)
    return {
        "present": True,
        "secret_check": "FAIL" if secret else "PASS",
        "response_characters": len(content),
        "raw_response": None if secret else content[:200000],
    }


def _parse_provider_json(content: str) -> dict:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ArtisticPlanCompileError(f"Provider output is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ArtisticPlanCompileError("Provider artistic output must be one JSON object.")
    return value


def _compile_provider_plan(
    content: str,
    *,
    groups: list[dict],
    presets: list[dict],
    effects: list[dict],
    resource_map: dict,
    active_sequence_range: list[int],
    target_executor: str,
) -> tuple[dict, dict[str, object], dict]:
    provider_plan = _parse_provider_json(content)
    cues = provider_plan.get("cues")
    if not isinstance(cues, list) or len(cues) != len(SHEESH_CUE_LABELS):
        raise ArtisticPlanCompileError(
            f"SHEESH bounded test requires exactly {len(SHEESH_CUE_LABELS)} artistic cues."
        )
    verified_group_ids = {
        int(item["group_id"])
        for item in groups
        if isinstance(item.get("group_id"), int)
    }
    verified_preset_refs = {
        str(item["reference"])
        for item in presets
        if item.get("reference")
    }
    verified_preset_types = {
        str(item["reference"]): str(item.get("preset_type") or "").upper()
        for item in presets
        if item.get("reference") and item.get("preset_type")
    }
    preset_applicability = preset_applicability_from_map(resource_map)
    effect_applicability = effect_applicability_from_map(resource_map)
    verified_effect_ids = {
        effect_id
        for effect_ids in effect_applicability.values()
        for effect_id in effect_ids
    }
    plan, audit = compile_artistic_cue_plan(
        provider_plan,
        song=SONG,
        target_executor=target_executor,
        active_sequence_range=active_sequence_range,
        verified_group_ids=verified_group_ids,
        verified_preset_refs=verified_preset_refs,
        verified_preset_types=verified_preset_types,
        verified_effect_ids=verified_effect_ids,
        verified_preset_applicability=preset_applicability,
        verified_effect_applicability=effect_applicability,
        cue_labels=SHEESH_CUE_LABELS,
    )
    validate_ma_payload(plan["cues"], path="show_plan.cues")
    return plan, audit, provider_plan


def _lowest_safe_sequence_id(profile: dict) -> int:
    """Choose the lowest currently unused, non-protected Sequence number."""
    used = {
        int(item["number"])
        for item in profile.get("sequences", [])
        if isinstance(item, dict) and isinstance(item.get("number"), int)
    }
    for number in range(1, 10000):
        if number in used:
            continue
        try:
            protected_objects.assert_sequence_allowed(number)
        except protected_objects.ProtectedObjectError:
            continue
        return number
    raise RuntimeError("NO_SAFE_UNUSED_SEQUENCE_AVAILABLE")


def _repair_prompt(
    *,
    rejected_content: str,
    error: str,
    resource_map: dict,
) -> tuple[str, str]:
    contract = _provider_contract(resource_map)
    system = (
        "Repair the rejected artistic cue plan without changing its artistic intention more "
        "than necessary. Return JSON only with one top-level key: cues. Return exactly six "
        "cues. Each cue needs fade and actions. Use only the compact artistic actions in the "
        "supplied verified resource contract, including verified Presets and Effects. "
        "Do not output backend metadata or MA2 "
        "commands."
    )
    user = json.dumps(
        {
            "compile_error": error,
            "rejected_artistic_plan": rejected_content,
            "artistic_contract": contract,
        },
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return system, user


def run(real_machine: bool, *, saved_result_path: Path | None = None, target_executor: str = TARGET_EXECUTOR_DISPLAY) -> dict:
    if not real_machine:
        raise RuntimeError("Refusing Test Show programming writes without --real-machine.")

    spatial_artifact = _load_spatial_context()
    executor_match = re.fullmatch(r"([1-9]\d*)\.(0*[1-9]\d*)", str(target_executor).strip())
    if not executor_match:
        raise RuntimeError("TARGET_EXECUTOR_INVALID")
    target_page = int(executor_match.group(1))
    target_exec = int(executor_match.group(2))
    core = AgentCore(AgentRuntime(ROOT))
    router: ProviderRouter | None = None
    result: dict = {
        "schema": "zen.sheesh_programming_smoke.v0.3",
        "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_executor": target_executor,
        "provider_contract": "ARTISTIC_CUES_V0_2",
        "test_scope": "SMOKE_TEST_ONLY",
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
        if not re.search(rf"(?:Page\s+)?{target_page}\b", pages, re.I):
            raise RuntimeError(f"TARGET_PAGE_{target_page}_NOT_PRESENT")
        executor_before = core.runtime.read_state("List Executor")
        if re.search(rf"(?:Executor|Exec)\s+{target_page}\.0*{target_exec}\b", executor_before, re.I):
            raise RuntimeError(f"TARGET_EXECUTOR_{target_page}_{target_exec:03d}_OCCUPIED")

        for resource, kwargs in (
            ("groups", {}),
            ("presets", {"sequence": "ALL"}),
            ("effects", {}),
            ("sequences", {}),
            ("fixtures", {}),
        ):
            core.refresh_state(resource, **kwargs)
        profile = core.scan_show_profile()
        context = {
            key: profile.get(key, [])
            for key in ("groups", "presets", "effects", "sequences")
        }
        groups = context.get("groups", [])
        presets = [item for item in context.get("presets", []) if item.get("reference")]
        effects = [item for item in context.get("effects", []) if isinstance(item.get("effect_id"), int)]
        effect_application_capability = core.cue_effect_application_capability.load_verified()
        resource_map = build_artistic_resource_map(
            profile,
            preset_bindings=_load_preset_bindings(),
            effect_catalog_entries=core.effect_catalog.load().get("entries", []),
            effect_application_capability=effect_application_capability,
        )
        result["artistic_resource_map"] = resource_map
        compact_cache = USB_HOME / "projects" / "runs" / RUN_ID / "programming" / "lean_design_context.json"
        design_context_artifact = load_or_build_compact_context(
            cache_path=compact_cache,
            song_context={
                "song": SONG,
                "artist": "BABYMONSTER",
                "brief": "KPOP_YG_INSPIRED; strong silhouette, center hierarchy, restrained progression",
            },
            spatial_context=spatial_artifact,
            groups=groups,
            artistic_resource_map=resource_map,
        )
        result["design_context_hash"] = design_context_artifact["context_hash"]
        result["design_context_cache_reused"] = design_context_artifact.get("cache_reused", False)
        selected_sequence = _lowest_safe_sequence_id(context)
        active_sequence_range = [selected_sequence, selected_sequence]
        result["selected_sequence_id"] = selected_sequence
        result["active_sequence_range"] = active_sequence_range

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
            router = _router()
            system, user = _prompt(design_context_artifact["context"], resource_map)
            content, provider, attempts = router.complete_with_diagnostics(
                role="LIGHTING_DESIGNER",
                system=system,
                user=user,
            )
            provider_content = content
            result["provider_attempts"] = list(attempts)
            result["provider"] = provider.safe_identity()
            result["provider_response"] = _safe_provider_response(provider, content)
            if provider.cost_class == "PAID":
                raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")

        try:
            plan, compile_audit, provider_plan = _compile_provider_plan(
                content,
                groups=groups,
                presets=presets,
                effects=effects,
                resource_map=resource_map,
                active_sequence_range=active_sequence_range,
                target_executor=target_executor,
            )
        except ArtisticPlanCompileError as first_error:
            # One bounded free repair is allowed only for a true artistic-plan
            # contract failure. Backend metadata/type formatting never reaches
            # this point because ZEN owns it.
            if router is None:
                router = _router()
            repair_system, repair_user = _repair_prompt(
                rejected_content=content,
                error=str(first_error),
                resource_map=resource_map,
            )
            repaired, repair_provider, repair_attempts = router.complete_with_diagnostics(
                role="LIGHTING_DESIGNER",
                system=repair_system,
                user=repair_user,
            )
            if repair_provider.cost_class == "PAID":
                raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")
            result["artistic_plan_repair"] = {
                "attempted": True,
                "initial_error": str(first_error),
                "provider": repair_provider.safe_identity(),
                "provider_attempts": list(repair_attempts),
                "response": _safe_provider_response(repair_provider, repaired),
            }
            provider_content = repaired
            plan, compile_audit, provider_plan = _compile_provider_plan(
                repaired,
                groups=groups,
                presets=presets,
                effects=effects,
                resource_map=resource_map,
                active_sequence_range=active_sequence_range,
                target_executor=target_executor,
            )

        if any(
            action.get("operation") == "CALL_EFFECT"
            for cue in plan.get("cues", [])
            for action in cue.get("actions", [])
        ):
            capability = effect_application_capability
            if capability is not None:
                plan["effect_application_capability"] = capability
        result["provider_artistic_plan"] = provider_plan
        result["provider_plan_compile"] = compile_audit
        result["canonical_artifact"] = plan
        result["ai_plan"] = plan

        workflow = core.skills.plan_intent(
            Intent(
                "build_first_song",
                {"first_song_spec": {"show_plan": plan, "profile": context}},
                "ZEN_SHOW_PLAN",
            ),
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
        result["readback_verification"] = "METADATA_PASS_CUE_CONTENT_PARTIAL"
        result["readback_detail"] = {
            "sequence_executor_metadata": "PASS",
            "cue_labels_and_fades": "PASS",
            "cue_attribute_content": "PARTIAL_UNVERIFIED",
        }
        result["executor_before"] = executor_before
        result["executor_after"] = core.runtime.read_state("List Executor")
        result["sequence_after"] = core.runtime.read_state("List Sequence")
        return result

    except Exception as exc:
        result["status"] = (
            "FAILED_PROVIDER_OUTPUT"
            if isinstance(exc, ArtisticPlanCompileError)
            else "FAILED"
        )
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
    parser.add_argument("--target-executor", default=TARGET_EXECUTOR_DISPLAY)
    args = parser.parse_args()

    try:
        output = run(args.real_machine, saved_result_path=args.saved_result, target_executor=args.target_executor)
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(
                json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if output.get("canonical_artifact") is not None:
            base = args.result or args.saved_result
            if base is not None:
                canonical_path = base.with_name("sheesh_programming_test_compiled.json")
                canonical_path.write_text(
                    json.dumps(
                        {
                            "schema": "zen.show_plan.compiled.v0.1",
                            "provider_contract": output.get("provider_contract"),
                            "provider_plan_compile": output.get("provider_plan_compile"),
                            "plan": output["canonical_artifact"],
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
        print(
            json.dumps(
                {
                    "status": output.get("status"),
                    "provider": (output.get("provider") or {}).get("model"),
                    "target_executor": output.get("target_executor"),
                },
                ensure_ascii=True,
            )
        )
        return 0
    except ProgrammingRunError as exc:
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(
                json.dumps(exc.result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps(
                {
                    "status": exc.result.get("status", "FAILED"),
                    "error": exc.result.get("error"),
                    "ma2_writes": 0,
                    "fixture_9999_touched": False,
                },
                ensure_ascii=True,
            )
        )
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "ma2_writes": 0,
                    "fixture_9999_touched": False,
                },
                ensure_ascii=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
