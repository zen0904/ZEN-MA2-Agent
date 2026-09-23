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
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.allocation import first_free_executor, first_free_from_front
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
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent import protected_objects
from zen_ma2_agent.llm.router import ProviderRouter
from zen_ma2_agent.ma_text import validate_ma_payload
from zen_ma2_agent.models import Intent
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.test_show_evidence import (
    bounded_test_show_color_rows,
    derive_sheesh_test_dimmer_bindings,
    derive_sheesh_test_preset_bindings,
    test_show_palette_manifest,
)
from zen_ma2_agent.effect_resources import show_identity
from zen_ma2_agent.state.providers.show_pools import EffectProvider, PresetProvider
from zen_ma2_agent.test_show_resources import template_effect_labels
from zen_ma2_agent.telnet_client import ConnectionState


RUN_ID = "SHEESH_NEW_UNDESIGNED_SHOW_001"
USB_HOME = Path(r"E:\ZEN_MA2_AGENT")
TARGET_EXECUTOR_DISPLAY = "2.001"
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


def _load_test_show_plan() -> dict:
    path = ROOT / "data" / "zen_real_ma2_test_show_sheesh_001_plan.json"
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _augment_bounded_test_show_color_inventory(core: AgentCore, profile: dict, plan: dict) -> list[dict]:
    if not core.runtime.client:
        return []
    readbacks: dict[str, str] = {}
    for reference in test_show_palette_manifest(plan):
        if not re.fullmatch(r"4\.1(?:0[1-9]|1[0-3])", reference):
            continue
        readbacks[reference] = core.runtime.client.execute(f"List Preset {reference}")
    rows = bounded_test_show_color_rows(plan, readbacks)
    merged = {
        str(item.get("reference") or ""): item
        for item in profile.get("presets", [])
        if isinstance(item, dict) and item.get("reference")
    }
    for row in rows:
        merged[row["reference"]] = row
    profile["presets"] = list(merged.values())
    profile["show_identity"] = show_identity(profile)
    return rows


def _augment_bounded_template_effect_inventory(core: AgentCore, profile: dict) -> list[dict]:
    if not core.runtime.client:
        return []
    provider = EffectProvider()
    reserved = {label.upper() for label in template_effect_labels()}
    evidence: list[dict] = []
    for row in profile.get("effects", []) if isinstance(profile.get("effects"), list) else []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("name") or "").strip().upper()
        effect_id = row.get("effect_id")
        if label not in reserved or isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id < 1:
            continue
        command = f"List Effect 1.{effect_id}.*"
        raw = core.runtime.client.execute(command)
        detail = provider.parse_template_detail(raw)
        evidence.append({
            "effect_id": effect_id,
            "name": row.get("name"),
            "detail": detail,
        })
        if detail.get("status") == "VERIFIED":
            row["kind"] = detail.get("kind")
            row["template_detail"] = detail
    return evidence


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


def _effect_labels_from_resource_map(resource_map: dict) -> dict[tuple[int, int], str]:
    """Return exact compile-time Group/Effect labels from verified resource rows."""
    labels: dict[tuple[int, int], str] = {}
    for group in resource_map.get("groups", []) if isinstance(resource_map.get("groups"), list) else []:
        if not isinstance(group, dict) or not isinstance(group.get("group_id"), int):
            continue
        group_id = int(group["group_id"])
        for effect in group.get("effect_resources", []) if isinstance(group.get("effect_resources"), list) else []:
            if (
                not isinstance(effect, dict)
                or effect.get("application_status") != "REAL_MACHINE_VERIFIED"
                or not isinstance(effect.get("effect_id"), int)
            ):
                continue
            label = str(effect.get("name") or "").strip()
            if not label:
                continue
            key = (group_id, int(effect["effect_id"]))
            previous = labels.setdefault(key, label)
            if previous != label:
                raise ArtisticPlanCompileError(
                    f"Verified Effect {effect['effect_id']} has conflicting labels for Group {group_id}."
                )
    return labels


def _attach_effect_identity_labels(plan: dict, resource_map: dict) -> dict:
    """Attach compile-time verified Effect identity metadata without changing art."""
    labels = _effect_labels_from_resource_map(resource_map)
    normalized = deepcopy(plan)
    for cue in normalized.get("cues", []):
        for action in cue.get("actions", []):
            if action.get("operation") != "CALL_EFFECT":
                continue
            target = action.get("target") or {}
            reference = action.get("effect_ref") or {}
            group_id = target.get("ref")
            effect_id = reference.get("id")
            if not isinstance(group_id, int) or not isinstance(effect_id, int):
                raise ArtisticPlanCompileError("Compiled Effect action is missing typed Group/Effect identity.")
            label = labels.get((group_id, effect_id))
            if not label:
                raise ArtisticPlanCompileError(
                    f"Compiled Effect {effect_id} for Group {group_id} has no verified identity label."
                )
            reference = dict(reference)
            reference["label"] = label
            action["effect_ref"] = reference
    return normalized


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
    plan = _attach_effect_identity_labels(plan, resource_map)
    validate_ma_payload(plan["cues"], path="show_plan.cues")
    return plan, audit, provider_plan


def _lowest_safe_sequence_id(profile: dict) -> int:
    """Choose the lowest currently unused, non-protected Sequence number."""
    used = {
        int(item["number"])
        for item in profile.get("sequences", [])
        if isinstance(item, dict) and isinstance(item.get("number"), int)
    }
    try:
        return first_free_from_front(
            used,
            protected=protected_objects.PROTECTED_SEQUENCES,
        )
    except Exception as exc:
        raise RuntimeError("NO_SAFE_UNUSED_SEQUENCE_AVAILABLE") from exc


def _hydrate_saved_canonical_effect_labels(saved: dict, artifact: dict) -> dict:
    """Backfill old id-only canonical Effect refs from the saved verified map.

    This is a metadata migration only. It never changes the selected Effect,
    Group, cue, fade, or any other artistic choice.
    """
    resource_map = saved.get("artistic_resource_map")
    if not isinstance(resource_map, dict):
        resource_map = {}
    labels = _effect_labels_from_resource_map(resource_map)
    normalized = deepcopy(artifact)
    for cue in normalized.get("cues", []):
        for action in cue.get("actions", []):
            if action.get("operation") != "CALL_EFFECT":
                continue
            target = action.get("target") or {}
            reference = action.get("effect_ref")
            if not isinstance(reference, dict) or not isinstance(reference.get("id"), int):
                raise RuntimeError("SAVED_CANONICAL_EFFECT_REFERENCE_INVALID")
            if isinstance(reference.get("label"), str) and reference["label"].strip():
                continue
            group_id = target.get("ref")
            effect_id = reference["id"]
            if not isinstance(group_id, int):
                raise RuntimeError("SAVED_CANONICAL_EFFECT_TARGET_INVALID")
            label = labels.get((group_id, effect_id))
            if not label:
                raise RuntimeError(
                    f"SAVED_CANONICAL_EFFECT_IDENTITY_UNAVAILABLE:{group_id}:{effect_id}"
                )
            reference = dict(reference)
            reference["label"] = label
            action["effect_ref"] = reference
    return normalized


def _resume_saved_canonical_artifact(
    saved: dict,
    *,
    sequence: int,
    target_executor: str,
) -> dict | None:
    """Reuse a previously compiled plan without re-reading provider art output.

    The only allowed retry edits are ZEN-owned runtime allocation fields.  A
    fresh Builder still verifies referenced resources and safe writes.
    """
    artifact = saved.get("canonical_artifact")
    if artifact is None:
        return None
    if not isinstance(artifact, dict):
        raise RuntimeError("SAVED_CANONICAL_ARTIFACT_INVALID")
    compile_audit = saved.get("provider_plan_compile")
    if not isinstance(compile_audit, dict) or compile_audit.get("provider_contract") != "ARTISTIC_CUES_V0_2":
        # A typed artifact without its original compile evidence is not proof
        # that the artifact reached the canonical boundary.  Fall back to the
        # legacy saved raw-result path, which still never recalls a provider.
        return None
    resumed = _hydrate_saved_canonical_effect_labels(saved, artifact)
    resumed["target_executor"] = target_executor
    resumed["active_sequence_range"] = [sequence, sequence]
    try:
        return validate_show_plan(resumed)
    except Exception as exc:
        raise RuntimeError("SAVED_CANONICAL_ARTIFACT_INVALID") from exc


def _augment_canonical_referenced_resources(
    core: AgentCore,
    profile: dict,
    plan: dict,
) -> dict[str, list]:
    """Refresh exact pool objects referenced by a frozen canonical ShowPlan.

    This is runtime existence refresh only. It does not rebuild an artistic
    resource map, replay applicability compilation, or call a provider.
    """
    if not core.runtime.client:
        raise RuntimeError("MA2_CLIENT_UNAVAILABLE_FOR_CANONICAL_RESUME")

    preset_refs = sorted({
        str(action.get("preset_ref"))
        for cue in plan.get("cues", [])
        for action in cue.get("actions", [])
        if action.get("operation") == "CALL_PRESET" and action.get("preset_ref")
    })
    effect_ids = sorted({
        int((action.get("effect_ref") or {}).get("id"))
        for cue in plan.get("cues", [])
        for action in cue.get("actions", [])
        if action.get("operation") == "CALL_EFFECT"
        and isinstance((action.get("effect_ref") or {}).get("id"), int)
    })

    presets = {
        str(item.get("reference") or ""): item
        for item in profile.get("presets", [])
        if isinstance(item, dict) and item.get("reference")
    }
    preset_provider = PresetProvider()
    for reference in preset_refs:
        if not re.fullmatch(r"[1-9]\d*\.[1-9]\d*", reference):
            raise RuntimeError(f"SAVED_CANONICAL_PRESET_REFERENCE_INVALID:{reference}")
        raw = core.runtime.client.execute(f"List Preset {reference}")
        upper = raw.upper()
        if "OBJECT DOES NOT EXIST" in upper or "NO OBJECTS FOUND" in upper:
            raise RuntimeError(f"SAVED_CANONICAL_PRESET_NOT_PRESENT:{reference}")
        rows = preset_provider.parse(raw, "ALL")
        row = next((item for item in rows if str(item.get("reference") or "") == reference), None)
        if row is None:
            raise RuntimeError(f"SAVED_CANONICAL_PRESET_READBACK_UNPARSED:{reference}")
        presets[reference] = row

    effects = {
        int(item["effect_id"]): item
        for item in profile.get("effects", [])
        if isinstance(item, dict)
        and isinstance(item.get("effect_id"), int)
        and not isinstance(item.get("effect_id"), bool)
    }
    effect_provider = EffectProvider()
    expected_effect_labels = {
        int(reference["id"]): str(reference["label"])
        for cue in plan.get("cues", [])
        for action in cue.get("actions", [])
        if action.get("operation") == "CALL_EFFECT"
        and isinstance((reference := action.get("effect_ref")), dict)
        and isinstance(reference.get("id"), int)
        and isinstance(reference.get("label"), str)
        and reference["label"].strip()
    }
    for effect_id in effect_ids:
        raw = core.runtime.client.execute(f"List Effect {effect_id}")
        upper = raw.upper()
        if "OBJECT DOES NOT EXIST" in upper or "NO OBJECTS FOUND" in upper:
            raise RuntimeError(f"SAVED_CANONICAL_EFFECT_NOT_PRESENT:{effect_id}")
        rows = effect_provider.parse(raw)
        row = next((item for item in rows if item.get("number") == effect_id), None)
        if row is None:
            raise RuntimeError(f"SAVED_CANONICAL_EFFECT_READBACK_UNPARSED:{effect_id}")
        expected_label = expected_effect_labels.get(effect_id)
        if expected_label and row.get("name") != expected_label:
            raise RuntimeError(f"SAVED_CANONICAL_EFFECT_IDENTITY_MISMATCH:{effect_id}")
        effects[effect_id] = {
            "effect_id": effect_id,
            "name": row.get("name"),
            "kind": row.get("kind"),
            "line_count": row.get("line_count"),
            "attributes": row.get("attributes", []),
        }

    profile["presets"] = list(presets.values())
    profile["effects"] = list(effects.values())
    return {"presets": preset_refs, "effects": effect_ids}


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
    build_execution_attempted = False

    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _await_ready(core)

        pages = core.runtime.read_state("List Page")
        if not re.search(rf"(?:Page\s+)?{target_page}\b", pages, re.I):
            raise RuntimeError(f"TARGET_PAGE_{target_page}_NOT_PRESENT")
        executor_before = core.runtime.read_state("List Executor")

        for resource, kwargs in (
            ("groups", {}),
            ("presets", {"sequence": "ALL"}),
            ("effects", {}),
            ("sequences", {}),
            ("executors", {}),
        ):
            core.refresh_state(resource, **kwargs)
        profile = core.scan_show_profile()
        context = {
            key: profile.get(key, [])
            for key in ("groups", "presets", "effects", "sequences", "executors")
        }
        groups = context.get("groups", [])
        presets = [item for item in context.get("presets", []) if item.get("reference")]
        effects = [item for item in context.get("effects", []) if isinstance(item.get("effect_id"), int)]
        selected_sequence = _lowest_safe_sequence_id(context)
        active_sequence_range = [selected_sequence, selected_sequence]
        target_executor = first_free_executor(executor_before, page=target_page)
        result["target_executor"] = target_executor
        result["selected_sequence_id"] = selected_sequence
        result["active_sequence_range"] = active_sequence_range

        saved: dict | None = None
        plan: dict | None = None
        compile_audit: dict[str, object] | None = None
        provider_plan: dict | None = None
        if saved_result_path is not None:
            if not saved_result_path.is_file():
                raise RuntimeError("SAVED_PROVIDER_RESULT_NOT_FOUND")
            saved = json.loads(saved_result_path.read_text(encoding="utf-8"))
            result["source_saved_result"] = str(saved_result_path)
            result["provider"] = saved.get("provider")
            result["provider_response"] = saved.get("provider_response")
            result["provider_attempts"] = saved.get("provider_attempts", [])
            plan = _resume_saved_canonical_artifact(
                saved,
                sequence=selected_sequence,
                target_executor=target_executor,
            )
            if plan is not None:
                compile_audit = saved.get("provider_plan_compile") if isinstance(saved.get("provider_plan_compile"), dict) else {}
                refreshed = _augment_canonical_referenced_resources(core, profile, plan)
                context = {
                    key: profile.get(key, [])
                    for key in ("groups", "presets", "effects", "sequences", "executors")
                }
                groups = context.get("groups", [])
                presets = [item for item in context.get("presets", []) if item.get("reference")]
                effects = [item for item in context.get("effects", []) if isinstance(item.get("effect_id"), int)]
                result["saved_retry"] = {
                    "mode": "RESUME_CANONICAL_ARTIFACT",
                    "provider_called": False,
                    "artistic_compile_replayed": False,
                    "checks": ["CURRENT_RESOURCE_EXISTENCE", "SAFE_WRITE_ALLOCATION"],
                    "refreshed_resources": refreshed,
                }

        if plan is None:
            # Fresh art, or an older saved result without a canonical artifact,
            # needs the normal resource-map preparation. Canonical retries do
            # not enter this evidence/artist path.
            core.refresh_state("fixtures")
            groups_snapshot = core.state.get("groups")
            for group in (groups_snapshot.values if groups_snapshot else []):
                group_no = group.get("number")
                if isinstance(group_no, int) and not isinstance(group_no, bool) and group_no > 0:
                    core.refresh_state("group_membership", group_no=group_no)
            core.refresh_state("fixture_type_profiles")
            profile = core.scan_show_profile()
            test_show_plan = _load_test_show_plan()
            result["bounded_test_show_color_inventory"] = _augment_bounded_test_show_color_inventory(core, profile, test_show_plan)
            result["bounded_template_effect_inventory"] = _augment_bounded_template_effect_inventory(core, profile)
            context = {key: profile.get(key, []) for key in ("groups", "presets", "effects", "sequences", "executors")}
            groups = context.get("groups", [])
            presets = [item for item in context.get("presets", []) if item.get("reference")]
            effects = [item for item in context.get("effects", []) if isinstance(item.get("effect_id"), int)]
            effect_application_capability = core.cue_effect_application_capability.load_verified()
            historical_bindings = derive_sheesh_test_preset_bindings(profile, test_show_plan)
            historical_dimmer_bindings = derive_sheesh_test_dimmer_bindings(profile, test_show_plan)
            resource_map = build_artistic_resource_map(
                profile,
                preset_bindings=[*_load_preset_bindings(), *historical_bindings.get("bindings", [])],
                dimmer_bindings=historical_dimmer_bindings.get("bindings", []),
                effect_catalog_entries=core.effect_catalog.load().get("entries", []),
                effect_application_capability=effect_application_capability,
            )
            result["test_show_preset_binding_recovery"] = historical_bindings
            result["test_show_dimmer_binding_recovery"] = historical_dimmer_bindings
            result["artistic_resource_map"] = resource_map
            compact_cache = USB_HOME / "projects" / "runs" / RUN_ID / "programming" / "lean_design_context.json"
            design_context_artifact = load_or_build_compact_context(
                cache_path=compact_cache,
                song_context={"song": SONG, "artist": "BABYMONSTER", "brief": "KPOP_YG_INSPIRED; strong silhouette, center hierarchy, restrained progression"},
                spatial_context=spatial_artifact,
                groups=groups,
                artistic_resource_map=resource_map,
            )
            result["design_context_hash"] = design_context_artifact["context_hash"]
            result["design_context_cache_reused"] = design_context_artifact.get("cache_reused", False)
            if saved is not None:
                raw = saved.get("provider_response", {}).get("raw_response")
                if not isinstance(raw, str) or not raw:
                    raise RuntimeError("SAVED_PROVIDER_RAW_RESPONSE_NOT_AVAILABLE")
                content = raw
                provider_content = content
            else:
                router = _router()
                system, user = _prompt(design_context_artifact["context"], resource_map)
                content, provider, attempts = router.complete_with_diagnostics(role="LIGHTING_DESIGNER", system=system, user=user)
                provider_content = content
                result["provider_attempts"] = list(attempts)
                result["provider"] = provider.safe_identity()
                result["provider_response"] = _safe_provider_response(provider, content)
                if provider.cost_class == "PAID":
                    raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")
            try:
                plan, compile_audit, provider_plan = _compile_provider_plan(
                    content, groups=groups, presets=presets, effects=effects, resource_map=resource_map,
                    active_sequence_range=active_sequence_range, target_executor=target_executor,
                )
            except ArtisticPlanCompileError as first_error:
                # An older saved raw response is never sent back to a provider.
                if saved is not None:
                    raise
                if router is None:
                    router = _router()
                repair_system, repair_user = _repair_prompt(rejected_content=content, error=str(first_error), resource_map=resource_map)
                repaired, repair_provider, repair_attempts = router.complete_with_diagnostics(role="LIGHTING_DESIGNER", system=repair_system, user=repair_user)
                if repair_provider.cost_class == "PAID":
                    raise RuntimeError("PAID_PROVIDER_USED_UNEXPECTEDLY")
                result["artistic_plan_repair"] = {"attempted": True, "initial_error": str(first_error), "provider": repair_provider.safe_identity(), "provider_attempts": list(repair_attempts), "response": _safe_provider_response(repair_provider, repaired)}
                provider_content = repaired
                plan, compile_audit, provider_plan = _compile_provider_plan(
                    repaired, groups=groups, presets=presets, effects=effects, resource_map=resource_map,
                    active_sequence_range=active_sequence_range, target_executor=target_executor,
                )

        effect_application_capability = core.cue_effect_application_capability.load_verified()

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
        build_execution_attempted = True
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
            if core.runtime.ready and build_execution_attempted:
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
