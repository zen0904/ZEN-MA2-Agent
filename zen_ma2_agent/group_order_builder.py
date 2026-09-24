"""Deterministic, membership-preserving normal Group order builder.

This module owns only the small MA2 operation required to rebuild an existing
Group's selection order.  It never accepts provider commands or changes
membership: the caller supplies a verified member set and the builder emits
the native clear/select/store sequence in a deterministic form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class GroupOrderBuildError(ValueError):
    """A Group order request failed closed before transport."""


@dataclass(frozen=True)
class GroupOrderSpec:
    group_id: int
    group_name: str
    members_before: tuple[str, ...]
    desired_order: tuple[str, ...]

    @classmethod
    def create(
        cls,
        group_id: int,
        group_name: str,
        members_before: Iterable[object],
        desired_order: Iterable[object],
    ) -> "GroupOrderSpec":
        def ref(value: object) -> str:
            text = str(value).strip()
            if not text or text == "9999" or text.startswith("9999."):
                raise GroupOrderBuildError("Fixture 9999 is protected and cannot be in a Group order write.")
            if "." in text:
                fixture, sub = text.split(".", 1)
                if not (fixture.isdigit() and sub.isdigit() and int(fixture) > 0 and int(sub) > 0):
                    raise GroupOrderBuildError(f"Invalid fixture/subfixture reference: {text!r}")
                return f"{int(fixture)}.{int(sub)}"
            if not text.isdigit() or int(text) <= 0:
                raise GroupOrderBuildError(f"Invalid fixture reference: {text!r}")
            return str(int(text))

        if not isinstance(group_id, int) or isinstance(group_id, bool) or group_id < 1:
            raise GroupOrderBuildError("Group ID must be a positive integer.")
        name = str(group_name).strip()
        if not name:
            raise GroupOrderBuildError("Group name is required for identity verification.")
        before = tuple(ref(item) for item in members_before)
        desired = tuple(ref(item) for item in desired_order)
        if len(before) != len(set(before)):
            raise GroupOrderBuildError("Existing Group membership contains duplicate references.")
        if len(before) != len(desired) or set(before) != set(desired):
            raise GroupOrderBuildError("Group order write may change selection order only; membership must remain identical.")
        return cls(group_id, name, before, desired)

    @property
    def membership_changed(self) -> bool:
        return set(self.members_before) != set(self.desired_order)

    def commands(self) -> tuple[str, ...]:
        """Native commands using only the exact verified member references."""
        commands = ["ClearAll"]
        commands.extend(f"Fixture {item}" for item in self.desired_order)
        commands.append(f"Store Group {self.group_id} /overwrite /nc")
        commands.append("ClearAll")
        return tuple(commands)

    def verify(self, readback: Iterable[object]) -> None:
        actual = tuple(str(item).strip() for item in readback)
        if actual != self.desired_order:
            raise GroupOrderBuildError(
                f"Group {self.group_id} readback order mismatch: expected {self.desired_order!r}, got {actual!r}."
            )
        if set(actual) != set(self.members_before) or len(actual) != len(self.members_before):
            raise GroupOrderBuildError("Group readback membership changed unexpectedly.")
