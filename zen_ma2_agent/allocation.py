"""Deterministic, non-destructive allocation for new MA2 objects.

Allocation safety comes from a fresh inventory: every occupied slot is skipped
regardless of ownership.  ZEN never treats a high numeric ID as a substitute
for checking whether an object is safe to create.
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


class AllocationError(ValueError):
    pass


def _positive_numbers(values: Iterable[object]) -> set[int]:
    return {
        value
        for value in values
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
    }


def first_free_from_front(
    occupied: Iterable[object],
    *,
    protected: Iterable[object] = (),
    start: int = 1,
    end: int = 9999,
) -> int:
    """Return the first unoccupied, unprotected positive ID in a bounded pool.

    Freshly observed foreign and Agent-owned objects are intentionally treated
    identically: both are occupied and neither may be overwritten.
    """
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 1
        or end < start
    ):
        raise AllocationError("Allocation bounds must be positive integers with start <= end.")
    unavailable = _positive_numbers(occupied) | _positive_numbers(protected)
    for candidate in range(start, end + 1):
        if candidate not in unavailable:
            return candidate
    raise AllocationError("No safe free allocation remains in the requested range.")


_EXECUTOR_RE = re.compile(r"(?:Executor|Exec)\s+(\d+)\.(\d+)\b", re.IGNORECASE)


def occupied_executor_numbers(inventory: str | Iterable[Mapping[str, object]], *, page: int) -> set[int]:
    """Extract occupied executor numbers for one Page from fresh inventory."""
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise AllocationError("Executor Page must be a positive integer.")
    if isinstance(inventory, str):
        return {
            int(number)
            for inventory_page, number in _EXECUTOR_RE.findall(inventory)
            if int(inventory_page) == page and int(number) > 0
        }
    occupied: set[int] = set()
    for item in inventory:
        if not isinstance(item, Mapping):
            continue
        item_page = item.get("page")
        number = item.get("executor")
        if item_page == page and isinstance(number, int) and not isinstance(number, bool) and number > 0:
            occupied.add(number)
    return occupied


def first_free_executor(
    inventory: str | Iterable[Mapping[str, object]],
    *,
    page: int,
    protected: Iterable[object] = (),
    start: int = 1,
    end: int = 999,
) -> str:
    """Return a display address such as ``2.003`` using front-first allocation."""
    number = first_free_from_front(
        occupied_executor_numbers(inventory, page=page),
        protected=protected,
        start=start,
        end=end,
    )
    return f"{page}.{number:03d}"
