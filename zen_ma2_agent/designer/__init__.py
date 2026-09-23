"""Schema-only lighting design intent layer; it never emits MA2 commands."""

from .schema import SHOW_PLAN_SCHEMA, validate_show_plan
from .first_song import FirstSongDesigner
from ..design_guidance import (
    ADVISORY_SCHEMA,
    GUIDANCE_CONTEXT_SCHEMA,
    build_design_guidance_context,
    generate_shadow_advisories,
    run_shadow_designer,
)
from .lean_provider import LeanDesignIntelligence, build_provider_resource_contract, compile_lean_artistic_intent

__all__ = [
    "SHOW_PLAN_SCHEMA", "validate_show_plan", "FirstSongDesigner",
    "GUIDANCE_CONTEXT_SCHEMA", "ADVISORY_SCHEMA", "build_design_guidance_context",
    "generate_shadow_advisories", "run_shadow_designer",
    "LeanDesignIntelligence", "build_provider_resource_contract", "compile_lean_artistic_intent",
]
