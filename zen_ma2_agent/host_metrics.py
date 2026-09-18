from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

try:
    import psutil as _psutil
except ImportError:  # pragma: no cover - dependency guard for broken deployments
    _psutil = None

from .operator_api import ComponentState

HOST_STATUS_SCHEMA = "zen.host_status.v0.1"
MAX_ERRORS = 8


@dataclass(frozen=True)
class HostStatusSnapshot:
    state: ComponentState
    cpu_percent: Optional[float]
    memory_percent: Optional[float]
    memory_available_mb: Optional[int]
    memory_total_mb: Optional[int]
    disk_path: str
    disk_percent: Optional[float]
    disk_free_mb: Optional[int]
    disk_total_mb: Optional[int]
    temperature_c: Optional[float]
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": HOST_STATUS_SCHEMA,
            "state": self.state.value,
            "cpu_percent": self.cpu_percent,
            "memory": {
                "percent": self.memory_percent,
                "available_mb": self.memory_available_mb,
                "total_mb": self.memory_total_mb,
            },
            "disk": {
                "path": self.disk_path,
                "percent": self.disk_percent,
                "free_mb": self.disk_free_mb,
                "total_mb": self.disk_total_mb,
            },
            "temperature_c": self.temperature_c,
            "errors": list(self.errors),
        }


class HostMetricsProvider:
    """Cross-platform host metrics backed by psutil.

    Unsupported temperature sensors remain unknown rather than degrading the
    host. CPU, memory, and disk collection failures are surfaced as DEGRADED.
    """

    def __init__(self, *, disk_path: Optional[str] = None, psutil_module: Any = None):
        if disk_path is None:
            disk_path = Path(__file__).resolve().anchor or "/"
        if not isinstance(disk_path, str) or not disk_path:
            raise ValueError("disk_path must be a non-empty string")
        self.disk_path = disk_path
        self._psutil = psutil_module if psutil_module is not None else _psutil

    def snapshot(self) -> dict[str, Any]:
        return self.collect().to_dict()

    def collect(self) -> HostStatusSnapshot:
        errors: list[str] = []
        cpu_percent: Optional[float] = None
        memory_percent: Optional[float] = None
        memory_available_mb: Optional[int] = None
        memory_total_mb: Optional[int] = None
        disk_percent: Optional[float] = None
        disk_free_mb: Optional[int] = None
        disk_total_mb: Optional[int] = None
        temperature_c: Optional[float] = None

        psutil = self._psutil
        if psutil is None:
            errors.append("psutil unavailable")
        else:
            try:
                cpu_percent = _bounded_percent(float(psutil.cpu_percent(interval=None)))
            except Exception as exc:
                errors.append(_error_text("cpu", exc))

            try:
                memory = psutil.virtual_memory()
                memory_percent = _bounded_percent(float(memory.percent))
                memory_available_mb = _bytes_to_mb(memory.available)
                memory_total_mb = _bytes_to_mb(memory.total)
            except Exception as exc:
                errors.append(_error_text("memory", exc))

            try:
                disk = psutil.disk_usage(self.disk_path)
                disk_percent = _bounded_percent(float(disk.percent))
                disk_free_mb = _bytes_to_mb(disk.free)
                disk_total_mb = _bytes_to_mb(disk.total)
            except Exception as exc:
                errors.append(_error_text("disk", exc))

            temperature_c = _temperature_c(psutil)

        state = ComponentState.ONLINE if not errors else ComponentState.DEGRADED
        return HostStatusSnapshot(
            state=state,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_available_mb=memory_available_mb,
            memory_total_mb=memory_total_mb,
            disk_path=self.disk_path,
            disk_percent=disk_percent,
            disk_free_mb=disk_free_mb,
            disk_total_mb=disk_total_mb,
            temperature_c=temperature_c,
            errors=tuple(errors[:MAX_ERRORS]),
        )


def _temperature_c(psutil: Any) -> Optional[float]:
    sensors = getattr(psutil, "sensors_temperatures", None)
    if not callable(sensors):
        return None
    try:
        payload = sensors()
    except (AttributeError, NotImplementedError, OSError):
        return None
    readings: list[float] = []
    if not isinstance(payload, dict):
        return None
    for entries in payload.values():
        for entry in entries or ():
            current = getattr(entry, "current", None)
            try:
                value = float(current)
            except (TypeError, ValueError):
                continue
            if math.isfinite(value):
                readings.append(value)
    return max(readings) if readings else None


def _bounded_percent(value: float) -> float:
    if not math.isfinite(value):
        raise ValueError("metric is not finite")
    return max(0.0, min(100.0, round(value, 2)))


def _bytes_to_mb(value: object) -> int:
    number = int(value)
    if number < 0:
        raise ValueError("byte metric cannot be negative")
    return number // (1024 * 1024)


def _error_text(name: str, exc: Exception) -> str:
    return f"{name}: {type(exc).__name__}: {str(exc)[:240]}"
