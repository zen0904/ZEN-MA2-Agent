from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Deque, Iterable, Optional, Tuple

from .operator_api import ComponentState

WATCHDOG_STATUS_SCHEMA = "zen.watchdog_status.v0.1"
MAX_COMPONENTS = 64
MAX_EVENTS = 128


class WatchdogSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class WatchdogComponent:
    component_id: str
    state: ComponentState
    required: bool = False
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, object]:
        component_id = _bounded_text(self.component_id, "component_id", 128)
        detail = _optional_bounded_text(self.detail, "detail", 512)
        return {
            "component_id": component_id,
            "state": ComponentState(self.state).value,
            "required": bool(self.required),
            "detail": detail,
        }


@dataclass(frozen=True)
class WatchdogEvent:
    sequence: int
    component_id: str
    previous_state: Optional[ComponentState]
    current_state: ComponentState
    severity: WatchdogSeverity
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": int(self.sequence),
            "component_id": _bounded_text(self.component_id, "component_id", 128),
            "previous_state": (
                ComponentState(self.previous_state).value
                if self.previous_state is not None
                else None
            ),
            "current_state": ComponentState(self.current_state).value,
            "severity": WatchdogSeverity(self.severity).value,
            "message": _bounded_text(self.message, "message", 512),
        }


ObservationProvider = Callable[[], Iterable[WatchdogComponent]]


class WatchdogMonitor:
    """Pure edge-triggered component monitor.

    The monitor never performs I/O, never reaches MA, and never calls an LLM.
    Callers provide bounded observations. Events are generated only when a
    component first appears unhealthy or changes state.
    """

    def __init__(self, *, event_capacity: int = MAX_EVENTS) -> None:
        if not isinstance(event_capacity, int) or not 1 <= event_capacity <= MAX_EVENTS:
            raise ValueError(f"event_capacity must be in range 1..{MAX_EVENTS}")
        self._event_capacity = event_capacity
        self._components: dict[str, WatchdogComponent] = {}
        self._events: Deque[WatchdogEvent] = deque(maxlen=event_capacity)
        self._sequence = 0
        self._lock = threading.RLock()

    def observe(self, components: Iterable[WatchdogComponent]) -> Tuple[WatchdogEvent, ...]:
        incoming = tuple(components)
        if len(incoming) > MAX_COMPONENTS:
            raise ValueError(f"watchdog components exceed limit of {MAX_COMPONENTS}")

        seen: set[str] = set()
        normalized: list[WatchdogComponent] = []
        for component in incoming:
            item = WatchdogComponent(
                component_id=_bounded_text(component.component_id, "component_id", 128),
                state=ComponentState(component.state),
                required=bool(component.required),
                detail=_optional_bounded_text(component.detail, "detail", 512),
            )
            if item.component_id in seen:
                raise ValueError(f"duplicate watchdog component: {item.component_id}")
            seen.add(item.component_id)
            normalized.append(item)

        generated: list[WatchdogEvent] = []
        with self._lock:
            for item in normalized:
                previous = self._components.get(item.component_id)
                self._components[item.component_id] = item
                previous_state = previous.state if previous is not None else None
                if previous_state == item.state:
                    continue
                event = self._transition_event(item, previous_state)
                if event is not None:
                    self._events.append(event)
                    generated.append(event)
        return tuple(generated)

    def _transition_event(
        self,
        component: WatchdogComponent,
        previous_state: Optional[ComponentState],
    ) -> Optional[WatchdogEvent]:
        state = component.state
        if previous_state is None and state in {ComponentState.ONLINE, ComponentState.UNKNOWN}:
            return None
        if state == ComponentState.UNKNOWN:
            return None

        if state == ComponentState.ONLINE:
            severity = WatchdogSeverity.INFO
            message = f"{component.component_id} recovered"
        elif state == ComponentState.DEGRADED:
            severity = WatchdogSeverity.WARNING
            message = f"{component.component_id} degraded"
        elif state == ComponentState.OFFLINE:
            severity = (
                WatchdogSeverity.CRITICAL
                if component.required
                else WatchdogSeverity.WARNING
            )
            message = f"{component.component_id} offline"
        else:
            return None

        if component.detail:
            message = f"{message}: {component.detail}"
        self._sequence += 1
        return WatchdogEvent(
            sequence=self._sequence,
            component_id=component.component_id,
            previous_state=previous_state,
            current_state=state,
            severity=severity,
            message=message,
        )

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            components = tuple(
                sorted(self._components.values(), key=lambda item: item.component_id)
            )
            events = tuple(self._events)

        overall = ComponentState.ONLINE
        if any(
            item.required and item.state == ComponentState.OFFLINE
            for item in components
        ):
            overall = ComponentState.OFFLINE
        elif any(
            item.state == ComponentState.DEGRADED
            or (not item.required and item.state == ComponentState.OFFLINE)
            for item in components
        ):
            overall = ComponentState.DEGRADED
        elif not components or any(item.state == ComponentState.UNKNOWN for item in components):
            overall = ComponentState.UNKNOWN

        return {
            "schema": WATCHDOG_STATUS_SCHEMA,
            "state": overall.value,
            "components": [item.to_dict() for item in components],
            "recent_events": [event.to_dict() for event in events],
        }


class WatchdogService:
    """Small polling wrapper around WatchdogMonitor."""

    def __init__(
        self,
        monitor: WatchdogMonitor,
        observation_provider: ObservationProvider,
        *,
        interval_seconds: float = 1.0,
    ) -> None:
        try:
            interval = float(interval_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("watchdog interval must be numeric") from exc
        if interval <= 0:
            raise ValueError("watchdog interval must be positive")
        self.monitor = monitor
        self.observation_provider = observation_provider
        self.interval_seconds = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def poll_once(self) -> Tuple[WatchdogEvent, ...]:
        return self.monitor.observe(self.observation_provider())

    def snapshot(self) -> dict[str, object]:
        return self.monitor.snapshot()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self.poll_once()
        self._thread = threading.Thread(
            target=self._run,
            name="zen-watchdog",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.poll_once()
            except Exception:
                # Observation failures must never crash Field Core. A future
                # host-metrics adapter can surface its own bounded DEGRADED
                # component instead of raising out of the watchdog thread.
                continue

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self.interval_seconds * 2))
        self._thread = None


def _bounded_text(value: str, field_name: str, max_length: int) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    if len(value) > max_length:
        raise ValueError(f"{field_name} exceeds maximum length {max_length}")
    return value


def _optional_bounded_text(
    value: Optional[str], field_name: str, max_length: int
) -> Optional[str]:
    if value is None:
        return None
    return _bounded_text(value, field_name, max_length)
