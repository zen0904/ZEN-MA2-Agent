"""Shared artistic capability vocabulary.

This module deliberately separates technical fixture capability from executable
MA2 resources. A fixture may expose PRISM, ZOOM, FROST, or STROBE while the
current Show still has no verified Preset/Effect/application grammar for that
dimension. In that case the Lighting Designer may reason about the capability,
but the deterministic compiler must keep execution blocked rather than invent
raw Attribute values.
"""
from __future__ import annotations

ARTISTIC_DIMENSIONS = (
    "DIMMER",
    "COLOR",
    "POSITION",
    "FOCUS",
    "BEAM",
    "GOBO",
    "GOBO_ROTATION",
    "PRISM",
    "PRISM_ROTATION",
    "ZOOM",
    "FROST",
    "IRIS",
    "SHUTTER",
    "STROBE",
    "EFFECT",
    "MOVEMENT",
)

TECHNICAL_CAPABILITY_KEYS = {
    "DIMMER": "DIMMER",
    "COLOR": "COLOR",
    "POSITION": "POSITION",
    "FOCUS": "FOCUS",
    "BEAM": "BEAM",
    "GOBO": "GOBO",
    "GOBO_ROTATION": "GOBO_ROTATION",
    "PRISM": "PRISM",
    "PRISM_ROTATION": "PRISM_ROTATION",
    "ZOOM": "ZOOM",
    "FROST": "FROST",
    "IRIS": "IRIS",
    "SHUTTER": "SHUTTER_STROBE",
    "STROBE": "SHUTTER_STROBE",
    "MOVEMENT": "POSITION",
}

CAPABILITY_INTENT_USES = frozenset({"USE", "AVOID", "OPTIONAL"})

ARTISTIC_SELECTION_POLICY_SCHEMA = "zen.artistic_selection_policy.v0.1"
_ARTISTIC_SELECTION_PRINCIPLES = (
    "FULL_REPERTOIRE_IS_AVAILABLE_FOR_REASONING_NOT_A_CHECKLIST",
    "RESOURCE_AVAILABILITY_IS_NOT_A_REQUIREMENT_TO_USE_IT",
    "EVERY_MECHANISM_IS_OPTIONAL_UNLESS_ARTISTICALLY_JUSTIFIED",
    "DELIBERATE_NON_USE_IS_A_VALID_DESIGN_CHOICE",
    "NO_PER_CUE_OR_PER_SONG_MECHANISM_QUOTA",
    "NO_MECHANISM_SHOULD_BE_USED_MERELY_TO_INCREASE_VARIETY_OR_COMPLEXITY",
    "SELECTION_SHOULD_FOLLOW_MUSIC_ARRANGEMENT_LYRICS_CHOREOGRAPHY_SPATIAL_STATE_SHOW_LANGUAGE_AND_NEIGHBORING_CUES",
    "REVIEW_SHOULD_NOTICE_BOTH_UNJUSTIFIED_OMISSION_AND_GRATUITOUS_OVERUSE",
    "IMPLEMENTATION_RESOURCES_DO_NOT_DEFINE_THE_ARTISTIC_ONTOLOGY",
    "UNEXECUTABLE_ARTISTIC_INTENT_MAY_REMAIN_EXPLICIT_BUT_EXECUTION_MUST_FAIL_CLOSED",
)


def artistic_selection_policy() -> dict[str, object]:
    """Return the global model-facing mechanism-selection contract.

    The complete vocabulary is intentionally visible so the Lighting Designer
    can think like a designer rather than like a pool-object picker. Visibility
    never creates an obligation to use a mechanism, and this policy grants no
    MA2 execution authority.
    """
    return {
        "schema": ARTISTIC_SELECTION_POLICY_SCHEMA,
        "repertoire_mode": "FULL_VOCABULARY_NOT_CHECKLIST",
        "artistic_repertoire": list(ARTISTIC_DIMENSIONS),
        "principles": list(_ARTISTIC_SELECTION_PRINCIPLES),
        "default_mechanism_state": "OPTIONAL",
        "selection_requires_artistic_reason": True,
        "deliberate_non_use_valid": True,
        "resource_availability_implies_use": False,
        "mechanism_quota": None,
    }


_COMPOSITE_DIMENSION_ALIASES = {
    "SHUTTER/STROBE": ("SHUTTER", "STROBE"),
    "SHUTTER_STROBE": ("SHUTTER", "STROBE"),
    "SHUTTER-STROBE": ("SHUTTER", "STROBE"),
    "PRISM/PRISM_ROTATION": ("PRISM", "PRISM_ROTATION"),
    "PRISM/PRISM ROTATION": ("PRISM", "PRISM_ROTATION"),
    "GOBO/GOBO_ROTATION": ("GOBO", "GOBO_ROTATION"),
    "GOBO/GOBO ROTATION": ("GOBO", "GOBO_ROTATION"),
}


def normalize_artistic_dimensions(value: object) -> tuple[str, ...]:
    """Normalize provider-friendly capability names without granting execution.

    This is intentionally limited to the artistic-intent vocabulary. Composite
    aliases expand into multiple intent dimensions; they do not create Presets,
    Effects, raw Attribute values, or MA commands. Unknown values remain unknown
    so the compiler can still fail closed.
    """
    text = str(value or "").strip().upper()
    if not text:
        return ()
    composite = _COMPOSITE_DIMENSION_ALIASES.get(text)
    if composite is not None:
        return composite
    canonical = text.replace("-", "_").replace(" ", "_")
    while "__" in canonical:
        canonical = canonical.replace("__", "_")
    if canonical in ARTISTIC_DIMENSIONS:
        return (canonical,)
    return (text,)

# These dimensions currently have a deterministic implementation resource in
# the generic ShowPlan contract. Others remain valid artistic intent but require
# a separately verified application resource before they can become commands.
PRESET_BACKED_DIMENSIONS = frozenset({"COLOR", "POSITION", "FOCUS", "BEAM", "GOBO"})

__all__ = [
    "ARTISTIC_DIMENSIONS",
    "TECHNICAL_CAPABILITY_KEYS",
    "CAPABILITY_INTENT_USES",
    "ARTISTIC_SELECTION_POLICY_SCHEMA",
    "PRESET_BACKED_DIMENSIONS",
    "artistic_selection_policy",
    "normalize_artistic_dimensions",
]
