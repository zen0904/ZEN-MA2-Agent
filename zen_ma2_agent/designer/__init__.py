"""Schema-only lighting design intent layer; it never emits MA2 commands."""

from .schema import SHOW_PLAN_SCHEMA, validate_show_plan
from .first_song import FirstSongDesigner

__all__ = ["SHOW_PLAN_SCHEMA", "validate_show_plan", "FirstSongDesigner"]
