"""Validate a declarative ZEN_SHOW_PLAN without embedding transport text."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..artistic_capabilities import ARTISTIC_DIMENSIONS, CAPABILITY_INTENT_USES


SHOW_PLAN_SCHEMA = "zen.show_plan.v0.1"
_FORBIDDEN_KEYS = {"command", "commands", "telnet", "ma_command", "raw_command", "lua"}
_OPERATIONS = {"CALL_PRESET", "SET_DIMMER", "CALL_EFFECT"}


class ShowPlanSchemaError(ValueError):
    pass


def _walk(value: Any) -> None:
    if isinstance(value, dict):
        if _FORBIDDEN_KEYS & set(value):
            raise ShowPlanSchemaError("Designer plans may not contain MA2 command strings.")
        for nested in value.values():
            _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            _walk(nested)


def validate_show_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized intent-only plan or raise a precise schema error."""
    if not isinstance(plan, dict) or plan.get("schema") != SHOW_PLAN_SCHEMA:
        raise ShowPlanSchemaError(f"Plan schema must be {SHOW_PLAN_SCHEMA}.")
    cues = plan.get("cues")
    if not isinstance(cues, list):
        raise ShowPlanSchemaError("Plan cues must be a list.")
    _walk(plan)
    normalized = deepcopy(plan)
    for index, cue in enumerate(normalized["cues"], start=1):
        if not isinstance(cue, dict) or not str(cue.get("id") or cue.get("label") or "").strip():
            raise ShowPlanSchemaError(f"Cue {index} requires an id.")
        if "actions" in cue:
            if not isinstance(cue.get("cue_number"), int) or cue["cue_number"] < 1:
                raise ShowPlanSchemaError(f"Cue {index} requires a positive cue_number.")
            if not isinstance(cue.get("fade"), (int, float)) or float(cue["fade"]) < 0:
                raise ShowPlanSchemaError(f"Cue {index} requires a non-negative fade.")
            if not isinstance(cue["actions"], list):
                raise ShowPlanSchemaError(f"Cue {index} actions must be a list.")
            pattern = cue.get("position_pattern")
            if pattern is not None and pattern not in {
                "CENTER", "LEFT", "RIGHT", "FRONT", "UPSTAGE", "NARROW_FAN",
                "WIDE_FAN", "CROSS", "ALTERNATE", "EXPLODE", "COLLAPSE",
            }:
                raise ShowPlanSchemaError(f"Cue {index} has invalid position_pattern.")
            scale = cue.get("position_scale")
            if scale is not None and (
                isinstance(scale, bool) or not isinstance(scale, (int, float)) or not 0.5 <= float(scale) <= 2.5
            ):
                raise ShowPlanSchemaError(f"Cue {index} has invalid position_scale.")
            replace_effect_ids = cue.get("replace_effect_ids", [])
            if not isinstance(replace_effect_ids, list) or any(
                isinstance(value, bool) or not isinstance(value, int) or value < 1
                for value in replace_effect_ids
            ) or len(set(replace_effect_ids)) != len(replace_effect_ids):
                raise ShowPlanSchemaError(f"Cue {index} replace_effect_ids must be unique positive integers.")
            capability_intent = cue.get("capability_intent", [])
            if not isinstance(capability_intent, list):
                raise ShowPlanSchemaError(f"Cue {index} capability_intent must be a list.")
            for item in capability_intent:
                if not isinstance(item, dict):
                    raise ShowPlanSchemaError(f"Cue {index} contains invalid capability intent.")
                group = item.get("group")
                dimension = str(item.get("dimension") or "").upper()
                use = str(item.get("use") or "").upper()
                reason = item.get("reason")
                if isinstance(group, bool) or not isinstance(group, int) or group < 1:
                    raise ShowPlanSchemaError(f"Cue {index} capability intent has invalid Group.")
                if dimension not in ARTISTIC_DIMENSIONS:
                    raise ShowPlanSchemaError(f"Cue {index} capability intent has invalid dimension.")
                if use not in CAPABILITY_INTENT_USES:
                    raise ShowPlanSchemaError(f"Cue {index} capability intent has invalid use mode.")
                if reason is not None and (not isinstance(reason, str) or len(reason) > 512):
                    raise ShowPlanSchemaError(f"Cue {index} capability intent reason is invalid.")
            for action in cue["actions"]:
                if not isinstance(action, dict) or action.get("operation") not in _OPERATIONS or not isinstance(action.get("target"), dict):
                    raise ShowPlanSchemaError(f"Cue {index} contains an invalid typed action.")
                if action.get("operation") == "CALL_EFFECT":
                    reference = action.get("effect_ref")
                    requirement_id = action.get("effect_requirement_id")
                    if reference is None and not isinstance(requirement_id, str):
                        raise ShowPlanSchemaError(f"Cue {index} CALL_EFFECT requires an Effect reference or requirement id.")
                    if reference is not None:
                        if not isinstance(reference, dict) or not isinstance(reference.get("id"), int) or reference["id"] < 1:
                            raise ShowPlanSchemaError(f"Cue {index} has an invalid typed Effect reference.")
        elif not isinstance(cue.get("intent", {}), dict):
            raise ShowPlanSchemaError(f"Cue {index} intent must be an object.")
    return normalized
