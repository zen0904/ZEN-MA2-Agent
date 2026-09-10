"""Explicit A/B-only guidance-assisted alternative to the production Designer.

The production ``FirstSongDesigner`` remains untouched.  This adapter first
obtains its ordinary typed plan, then may alter actions only when the normalized
Rig Context contains an explicit, provenance-bearing binding from an available
role to an already scanned Group.  Abstract roles are never treated as MA2
resources by themselves.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .design_guidance import GUIDANCE_CONTEXT_SCHEMA, generate_shadow_advisories
from .designer.first_song import FirstSongDesigner
from .designer.schema import validate_show_plan


GUIDANCE_ASSISTED_MODE = "GUIDANCE_ASSISTED_AB_ONLY"
EXPERIMENT_SCHEMA = "zen.guidance_assisted_designer_experiment.v0.1"
_FORBIDDEN = {"command", "commands", "raw_command", "telnet", "lua", "ma_command", "ma2_command"}


def _safe(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN & set(value):
            raise ValueError("Guidance-assisted experimental design may not contain MA2 command fields.")
        for nested in value.values():
            _safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _safe(nested)


def _resource_advisory(context: dict[str, Any]) -> dict[str, Any] | None:
    return next((item for item in generate_shadow_advisories(context) if item["advisory_id"] == "advisory-resource-adaptation"), None)


def _binding_map(context: dict[str, Any], profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profile_groups = {item.get("group_id") for item in profile.get("groups", []) if isinstance(item.get("group_id"), int)}
    bindings: dict[str, dict[str, Any]] = {}
    for item in context.get("case_context", {}).get("role_bindings", []):
        target = item.get("target") or {}
        if item.get("certainty") == "CONFIRMED" and target.get("type") == "group" and target.get("ref") in profile_groups:
            bindings.setdefault(str(item.get("role")), deepcopy(item))
    return bindings


def _preset(profile: dict[str, Any], *types: str) -> dict[str, Any] | None:
    accepted = {item.upper() for item in types}
    return next((deepcopy(item) for item in profile.get("presets", []) if str(item.get("preset_type") or "").upper() in accepted and item.get("reference")), None)


def _action(target: dict[str, Any], role: str, level: int, focus: dict[str, Any] | None, color: dict[str, Any] | None) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    preset = focus if role == "PRIMARY_FOCUS" else color if role in {"COLOR_FIELD", "COLOR_LAYER"} else None
    if preset:
        actions.append({"target": deepcopy(target), "operation": "CALL_PRESET", "preset_ref": preset["reference"], "preset_type": preset.get("preset_type")})
    actions.append({"target": deepcopy(target), "operation": "SET_DIMMER", "level": level})
    return actions


class GuidanceAssistedExperimentalDesigner:
    """Generate an opt-in candidate plan; never alter the default path."""

    def __init__(self, baseline_designer: FirstSongDesigner | None = None):
        self._baseline = baseline_designer or FirstSongDesigner()

    def design(self, song_input: dict[str, Any], profile: dict[str, Any], guidance_context: dict[str, Any]) -> dict[str, Any]:
        if guidance_context.get("schema") != GUIDANCE_CONTEXT_SCHEMA or guidance_context.get("runtime_mode") != "SHADOW_ONLY":
            raise ValueError("Guidance-assisted experiments require a shadow-only guidance context.")
        _safe(guidance_context)
        baseline = self._baseline.design(deepcopy(song_input), deepcopy(profile))
        advisory = _resource_advisory(guidance_context)
        if not advisory or not advisory.get("resource_choices"):
            return self._mark_no_binding_change(baseline, "No bounded resource advisory was available.")
        choices = {item["section_id"]: item for item in advisory["resource_choices"]}
        bindings = _binding_map(guidance_context, profile)
        if not bindings:
            return self._mark_no_binding_change(baseline, "No confirmed role-to-scanned-Group bindings were supplied; abstract rig roles cannot select resources.")
        focus, color = _preset(profile, "FOCUS"), _preset(profile, "COLOR", "COLOR1")
        plan = deepcopy(baseline)
        changed = False
        for cue in plan["cues"]:
            choice = choices.get(cue.get("source_section_id"))
            if not choice:
                continue
            base_level = next((action.get("level") for action in cue.get("actions", []) if action.get("operation") == "SET_DIMMER"), 0)
            if not isinstance(base_level, int):
                continue
            actions: list[dict[str, Any]] = []
            selected_roles: list[str] = []
            for role in choice["KEEP"]:
                binding = bindings.get(role)
                if binding:
                    actions.extend(_action(binding["target"], role, base_level, focus, color))
                    selected_roles.append(role)
            for role in choice["REDUCE"]:
                binding = bindings.get(role)
                if binding:
                    actions.extend(_action(binding["target"], role, max(1, round(base_level * 0.45)), focus, color))
                    selected_roles.append(role)
            # Existing effect actions are retained only where a declared timing
            # role is actively kept/reduced.  No new Effect is created or named.
            if "TIMING_LAYER" in selected_roles:
                for action in cue.get("actions", []):
                    if action.get("operation") == "CALL_EFFECT":
                        timing_binding = bindings.get("TIMING_LAYER")
                        retained = deepcopy(action)
                        if timing_binding:
                            retained["target"] = deepcopy(timing_binding["target"])
                        actions.append(retained)
            if not actions:
                continue
            changed = changed or actions != cue.get("actions", [])
            cue["actions"] = actions
            cue["experimental_design"] = {
                "schema": EXPERIMENT_SCHEMA, "mode": GUIDANCE_ASSISTED_MODE,
                "selected_roles": selected_roles, "omitted_roles": list(choice["OMIT"]),
                "reduced_roles": list(choice["REDUCE"]), "substitutions": deepcopy(choice["SUBSTITUTE"]),
                "resource_outcome": choice["RESOURCE_OUTCOME"], "song_section_id": choice["section_id"],
                "evidence_references": list(advisory["evidence_references"]), "scope": "EXPERIMENTAL_TYPED_INTENT_ONLY",
            }
        used_requirements = {action.get("effect_requirement_id") for cue in plan["cues"] for action in cue.get("actions", []) if action.get("operation") == "CALL_EFFECT"}
        plan["effect_requirements"] = {key: value for key, value in plan.get("effect_requirements", {}).items() if key in used_requirements}
        plan["warnings"] = list(plan.get("warnings", [])) + ["GUIDANCE_ASSISTED_AB_ONLY: experimental candidate; not routed to production Builder."]
        plan["designer"] = {
            **deepcopy(plan.get("designer", {})), "kind": "GUIDANCE_ASSISTED_AB_EXPERIMENTAL", "mode": GUIDANCE_ASSISTED_MODE,
            "production_designer_modified": False, "guidance_context_schema": guidance_context["schema"],
            "role_binding_policy": "CONFIRMED_RIG_CONTEXT_BINDINGS_ONLY", "changed_typed_actions": changed,
        }
        return validate_show_plan(plan)

    @staticmethod
    def _mark_no_binding_change(plan: dict[str, Any], reason: str) -> dict[str, Any]:
        experimental = deepcopy(plan)
        experimental["warnings"] = list(experimental.get("warnings", [])) + [f"GUIDANCE_ASSISTED_AB_ONLY: {reason}"]
        experimental["designer"] = {
            **deepcopy(experimental.get("designer", {})), "kind": "GUIDANCE_ASSISTED_AB_EXPERIMENTAL", "mode": GUIDANCE_ASSISTED_MODE,
            "production_designer_modified": False, "role_binding_policy": "NO_CONFIRMED_BINDING_NO_ACTION_CHANGE", "changed_typed_actions": False,
        }
        return validate_show_plan(experimental)
