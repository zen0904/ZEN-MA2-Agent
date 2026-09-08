"""Validate a declarative ZEN_SHOW_PLAN without embedding transport text."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


SHOW_PLAN_SCHEMA = "zen.show_plan.v0.1"
_FORBIDDEN_KEYS = {"command", "commands", "telnet", "ma_command", "raw_command"}


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
        if not isinstance(cue, dict) or not str(cue.get("id") or "").strip():
            raise ShowPlanSchemaError(f"Cue {index} requires an id.")
        if not isinstance(cue.get("intent", {}), dict):
            raise ShowPlanSchemaError(f"Cue {index} intent must be an object.")
    return normalized
