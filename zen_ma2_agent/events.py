from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any


class EventBus:
    """Small frontend-neutral event bus; payloads never contain chain-of-thought."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[dict[str, Any]], None]] = []
        self._lock = RLock()

    def subscribe(self, listener: Callable[[dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def emit(self, kind: str, data: dict[str, Any]) -> None:
        event = {"type": kind, "data": data}
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            listener(event)
