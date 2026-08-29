"""Only console-validated Layout CObject token mappings belong here.

The exported token tuple is an internal MA2 representation, not a public type
identifier.  Keep this registry empty until the paired API probe and a
single-object Layout export prove a mapping on grandMA2 3.9.
"""

from __future__ import annotations

from typing import Final


VALIDATED_FIRST_TOKEN_CLASSES: Final[dict[str, str]] = {}


def validated_class(tokens: list[str]) -> str | None:
    return VALIDATED_FIRST_TOKEN_CLASSES.get(tokens[0]) if tokens else None
