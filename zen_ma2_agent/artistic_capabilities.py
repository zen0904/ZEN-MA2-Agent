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

# These dimensions currently have a deterministic implementation resource in
# the generic ShowPlan contract. Others remain valid artistic intent but require
# a separately verified application resource before they can become commands.
PRESET_BACKED_DIMENSIONS = frozenset({"COLOR", "POSITION", "FOCUS", "BEAM", "GOBO"})

__all__ = [
    "ARTISTIC_DIMENSIONS",
    "TECHNICAL_CAPABILITY_KEYS",
    "CAPABILITY_INTENT_USES",
    "PRESET_BACKED_DIMENSIONS",
]
