"""Console-validated grandMA2 3.9 Layout ``CObject`` token mappings.

The CObject tuple is an internal MA2 representation.  Do not add a mapping
from correlation alone: every entry requires a matching object probe on the
same grandMA2 3.9 family and a matching Layout export.
"""

from __future__ import annotations

from typing import Final, TypedDict


VALIDATED_REAL_MA2_3_9_PROBE: Final = "validated_real_ma2_3_9_probe"


class CObjectMapping(TypedDict):
    ma2_class: str
    object_type: str
    source: str


# Verified on grandMA2 3.9 with object probes and matching exported Layout
# CObject tuples: Preset 1.1 <-> [17, 1, 1, 1], Group 1 <-> [22, 1, 1].
VALIDATED_FIRST_TOKEN_CLASSES: Final[dict[str, CObjectMapping]] = {
    "17": {"ma2_class": "CMD_PRESET", "object_type": "preset", "source": VALIDATED_REAL_MA2_3_9_PROBE},
    "22": {"ma2_class": "CMD_GROUP", "object_type": "group", "source": VALIDATED_REAL_MA2_3_9_PROBE},
}


def validated_mapping(tokens: list[str]) -> CObjectMapping | None:
    """Return a mapping only when the full, observed tuple shape is valid."""
    mapping = VALIDATED_FIRST_TOKEN_CLASSES.get(tokens[0]) if tokens else None
    if mapping is None:
        return None
    if mapping["object_type"] == "preset" and len(tokens) == 4 and tokens[1] == "1" and tokens[2].isdigit() and tokens[3].isdigit() and int(tokens[2]) > 0 and int(tokens[3]) > 0:
        return mapping
    if mapping["object_type"] == "group" and len(tokens) == 3 and tokens[1] == "1" and tokens[2].isdigit() and int(tokens[2]) > 0:
        return mapping
    return None
