"""Single source of truth for MA2 objects no ZEN code path may touch.

Every Builder/Resolver that can allocate or modify a Sequence, Executor, or
Fixture must import from here instead of redefining its own protected list.
A protection that only exists as a local constant inside one script is not a
guarantee for any other code path.

Per the project owner: the current working Show is disposable test data, so
no Sequence is protected right now. Fixture 9999 is kept aside intentionally
and stays protected. If a future Show reuses real production Sequences,
populate PROTECTED_SEQUENCES below -- every caller already enforces it.
"""
from __future__ import annotations

#: Currently empty: the active Show is test-only and no Sequence needs
#: protection. Populate with real production Sequence numbers if/when this
#: Agent points at a Show that must not be overwritten.
PROTECTED_SEQUENCES: frozenset[int] = frozenset()

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
