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
PROHIBITED_FORMULAIC_INTERPRETATIONS = {
    "REPEAT_ALWAYS_BIGGER", "SECOND_DROP_ALWAYS_BIGGER", "LED_LOW_COLOR_ONLY",
    "LED_MEDIUM_ADDS_DENSITY", "LED_HIGH_ADDS_TIMING", "ENERGY_EQUALS_LAYER_COUNT",
    "ASYMMETRY_MUST_BE_EMPHASIZED", "MINIMAL_VERSE_ALWAYS_SPARSE",
    "REFRAIN_ALWAYS_ADDS_LAYERS",
}
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


def _energy_state(value: Any) -> str:
    return "LOW" if not isinstance(value, (int, float)) or value <= 0.35 else "MEDIUM" if value <= 0.70 else "HIGH"


def _section_events(song_input: dict[str, Any], section_id: str) -> list[dict[str, Any]]:
    return [item for item in song_input.get("events", []) if item.get("section_id") == section_id]


def _event_summary(events: list[dict[str, Any]]) -> tuple[int, float]:
    relevant = [item for item in events if str(item.get("type", "")).upper() in {"ACCENT", "HIT", "KICK", "DRUM", "TRANSIENT"}]
    return len(relevant), max((float(item.get("strength", 0.0)) for item in relevant), default=0.0)


def _experimental_resource_choices(song_input: dict[str, Any], bindings: dict[str, dict[str, Any]], guidance_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Select experimental role composition from song signals, never an energy ladder.

    Energy remains an inspectable input, but timing comes from actual accents,
    density from measured density, and repeat changes need additional musical
    evidence.  Consequently a low section can use timing and a high section
    can omit it when those choices fit the song better.
    """
    available = tuple(bindings)
    previous_by_role: dict[str, dict[str, Any]] = {}
    previous_choice: dict[str, Any] | None = None
    active_style_names = sorted(item["name"] for item in guidance_context.get("active_user_style", []) if item.get("name") in {
        "CLEAN_VISUAL_HIERARCHY", "PALETTE_COHERENCE", "MUSIC_STRUCTURE_ALIGNMENT",
        "RHYTHMIC_ACCENT_SYNC", "DYNAMIC_CONTOUR_TRACKING", "INTENTIONAL_RESTRAINT",
        "PROGRESSIVE_ENERGY_ARC", "EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK",
        "CONTROLLED_HIGH_IMPACT", "CONTROLLED_MAXIMALISM",
    })
    result: dict[str, dict[str, Any]] = {}
    for index, section in enumerate(song_input.get("sections", [])):
        section_id, role = str(section["id"]), str(section.get("role", ""))
        events = _section_events(song_input, section_id)
        event_count, event_strength = _event_summary(events)
        density = float(section.get("density", 0.0))
        accent_level = float(section.get("accent_level", 0.0))
        selected: list[str] = []
        # Palette and hierarchy are useful starting dimensions when available;
        # neither implies that a complete low look is merely a dimmed high look.
        for candidate in ("PRIMARY_FOCUS", "COLOR_FIELD"):
            if candidate in bindings:
                selected.append(candidate)
        if "DENSITY_LAYER" in bindings and density >= 0.50:
            selected.append("DENSITY_LAYER")
        # Rhythm, not energy state, is the bounded reason for timing activity.
        if "TIMING_LAYER" in bindings and event_count:
            selected.append("TIMING_LAYER")
        previous = previous_by_role.get(role)
        rising_density = previous is not None and density > previous["density"] + 0.10
        if "MOVER_TEXTURE_LAYER" in bindings and (rising_density or event_count > 1 or accent_level >= 0.20):
            selected.append("MOVER_TEXTURE_LAYER")
        if "BROAD_ENVIRONMENT" in bindings and role in {"INTRO", "OUTRO", "BREAK", "BRIDGE"}:
            selected.append("BROAD_ENVIRONMENT")
        if "LEFT_RIGHT_RELATIONSHIP" in bindings and event_count > 1:
            selected.append("LEFT_RIGHT_RELATIONSHIP")
        if not selected and available:
            selected.append(available[0])
        selected = list(dict.fromkeys(selected))
        omitted = [candidate for candidate in available if candidate not in selected]
        reduced = [candidate for candidate in omitted if candidate in {"BROAD_ENVIRONMENT", "PRIMARY_FOCUS"}]
        omitted = [candidate for candidate in omitted if candidate not in reduced]
        development_basis: list[str] = []
        if previous:
            if event_count > previous["event_count"]:
                development_basis.append("MORE_EXPLICIT_RHYTHMIC_EVENTS")
            if event_strength > previous["event_strength"] + 0.10:
                development_basis.append("STRONGER_TRANSIENT_EVIDENCE")
            if density > previous["density"] + 0.10:
                development_basis.append("DENSER_SECTION_EVIDENCE")
        development = {
            "status": "MUSICALLY_JUSTIFIED_DELTA" if development_basis else "INTENTIONAL_SIMILARITY",
            "basis": development_basis,
            "previous_same_role_section_id": previous.get("section_id") if previous else None,
        }
        multipliers = {candidate: 1.0 for candidate in selected}
        if "TIMING_LAYER" in multipliers:
            # A stronger/more numerous transient context changes the timing
            # emphasis; a repeat number alone never does.
            multipliers["TIMING_LAYER"] = min(1.0, 0.65 + 0.15 * event_count + 0.10 * event_strength)
        if "DENSITY_LAYER" in multipliers:
            multipliers["DENSITY_LAYER"] = min(1.0, 0.50 + 0.50 * density)
        for candidate in reduced:
            multipliers[candidate] = 0.45
        result[section_id] = {
            "section_id": section_id, "section_role": role, "energy_state": _energy_state(section.get("energy")),
            "KEEP": selected, "REDUCE": reduced, "OMIT": omitted, "SUBSTITUTE": [],
            "RESOURCE_OUTCOME": "RESOURCE_CONFIGURATION", "role_level_multipliers": multipliers,
            "development": development,
            "selection_basis": {
                "section_structure": role, "dynamic_density": density, "section_accent_level": accent_level,
                "rhythmic_event_count": event_count, "rhythmic_event_strength": event_strength,
                "energy_is_not_a_layer_count": True, "human_style_constraints": active_style_names,
                "previous_look_roles": list(previous_choice["KEEP"]) if previous_choice else [],
                "headroom_preserved": bool(omitted),
            },
        }
        previous_by_role[role] = {"section_id": section_id, "event_count": event_count, "event_strength": event_strength, "density": density}
        previous_choice = result[section_id]
    return result


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
        bindings = _binding_map(guidance_context, profile)
        if not bindings:
            return self._mark_no_binding_change(baseline, "No confirmed role-to-scanned-Group bindings were supplied; abstract rig roles cannot select resources.")
        choices = _experimental_resource_choices(song_input, bindings, guidance_context)
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
                    level = max(1, round(base_level * float(choice["role_level_multipliers"].get(role, 1.0))))
                    actions.extend(_action(binding["target"], role, level, focus, color))
                    selected_roles.append(role)
            for role in choice["REDUCE"]:
                binding = bindings.get(role)
                if binding:
                    level = max(1, round(base_level * float(choice["role_level_multipliers"].get(role, 0.45))))
                    actions.extend(_action(binding["target"], role, level, focus, color))
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
                "evidence_references": list(advisory["evidence_references"]) if advisory else [],
                "development": deepcopy(choice["development"]), "selection_basis": deepcopy(choice["selection_basis"]),
                "role_level_multipliers": deepcopy(choice["role_level_multipliers"]),
                "human_review": "UNSET", "scope": "EXPERIMENTAL_TYPED_INTENT_ONLY",
            }
        used_requirements = {action.get("effect_requirement_id") for cue in plan["cues"] for action in cue.get("actions", []) if action.get("operation") == "CALL_EFFECT"}
        plan["effect_requirements"] = {key: value for key, value in plan.get("effect_requirements", {}).items() if key in used_requirements}
        plan["warnings"] = list(plan.get("warnings", [])) + ["GUIDANCE_ASSISTED_AB_ONLY: experimental candidate; not routed to production Builder."]
        plan["designer"] = {
            **deepcopy(plan.get("designer", {})), "kind": "GUIDANCE_ASSISTED_AB_EXPERIMENTAL", "mode": GUIDANCE_ASSISTED_MODE,
            "production_designer_modified": False, "guidance_context_schema": guidance_context["schema"],
            "role_binding_policy": "CONFIRMED_RIG_CONTEXT_BINDINGS_ONLY", "changed_typed_actions": changed,
            "formulaic_interpretations_rejected": sorted(PROHIBITED_FORMULAIC_INTERPRETATIONS),
        }
        return validate_show_plan(plan)

    @staticmethod
    def _mark_no_binding_change(plan: dict[str, Any], reason: str) -> dict[str, Any]:
        experimental = deepcopy(plan)
        experimental["warnings"] = list(experimental.get("warnings", [])) + [f"GUIDANCE_ASSISTED_AB_ONLY: {reason}"]
        experimental["designer"] = {
            **deepcopy(experimental.get("designer", {})), "kind": "GUIDANCE_ASSISTED_AB_EXPERIMENTAL", "mode": GUIDANCE_ASSISTED_MODE,
            "production_designer_modified": False, "role_binding_policy": "NO_CONFIRMED_BINDING_NO_ACTION_CHANGE", "changed_typed_actions": False,
            "formulaic_interpretations_rejected": sorted(PROHIBITED_FORMULAIC_INTERPRETATIONS),
        }
        return validate_show_plan(experimental)
