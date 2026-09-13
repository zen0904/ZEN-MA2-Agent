"""Single source of truth for MA2 objects no ZEN code path may touch.

Every Builder/Resolver that can allocate or modify a Sequence, Executor, or
Fixture must import from here instead of redefining its own protected list.
A protection that only exists as a local constant inside one script is not a
guarantee for any other code path.
"""
from __future__ import annotations

#: Sequences that belong to the existing production show. No ZEN code path
#: may create, relabel, or store a Cue into one of these without an explicit,
#: separately-recorded human authorization for that exact Sequence number.
PROTECTED_SEQUENCES: frozenset[int] = frozenset({201, 202, 204, 205})

#: Fixture 9999 must never be selected, patched, addressed, or referenced by
#: any automatically generated action.
PROTECTED_FIXTURE_IDS: frozenset[int] = frozenset({9999})


class ProtectedObjectError(ValueError):
    """Raised when a code path attempts to touch a protected MA2 object."""


def assert_sequence_allowed(sequence: int) -> None:
    if sequence in PROTECTED_SEQUENCES:
        raise ProtectedObjectError(f"Sequence {sequence} is protected and cannot be allocated or modified automatically.")


def assert_fixture_allowed(fixture_id: int) -> None:
    if fixture_id in PROTECTED_FIXTURE_IDS:
        raise ProtectedObjectError(f"Fixture {fixture_id} is protected and cannot be selected or modified automatically.")
