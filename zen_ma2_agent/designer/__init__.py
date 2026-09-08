"""Schema-only lighting design intent layer; it never emits MA2 commands."""

from .schema import SHOW_PLAN_SCHEMA, validate_show_plan

__all__ = ["SHOW_PLAN_SCHEMA", "validate_show_plan"]
