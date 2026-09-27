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
    "PRESET_BACKED_DIMENSIONS",
    "normalize_artistic_dimensions",
]
