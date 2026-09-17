from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

from .operator_api import ComponentState, WorkerStatus

MAX_REGISTERED_WORKERS = 32
MAX_WORKER_ID_LENGTH = 128


def _validate_worker_id(worker_id: str) -> str:
    if not isinstance(worker_id, str) or not worker_id:
        raise ValueError("worker_id must be a non-empty string")
    if len(worker_id) > MAX_WORKER_ID_LENGTH:
        raise ValueError(f"worker_id exceeds maximum length {MAX_WORKER_ID_LENGTH}")
    return worker_id


@dataclass(frozen=True)
class WorkerCapabilities:
    gpu_name: Optional[str] = None
    model_runtime_available: Optional[bool] = None

    def to_operator_status(self, worker_id: str, state: ComponentState) -> WorkerStatus:
        return WorkerStatus(
            worker_id=worker_id,
            state=state,
            gpu_name=self.gpu_name,
            model_runtime_available=self.model_runtime_available,
        )


@dataclass
class RegisteredWorker:
    worker_id: str
    priority: int = 100
    state: ComponentState = ComponentState.UNKNOWN
    capabilities: WorkerCapabilities = field(default_factory=WorkerCapabilities)
    last_error: Optional[str] = None
    consecutive_failures: int = 0

    def __post_init__(self) -> None:
        self.worker_id = _validate_worker_id(self.worker_id)
        if not isinstance(self.priority, int):
            raise ValueError("worker priority must be an integer")

    def operator_status(self) -> WorkerStatus:
        return self.capabilities.to_operator_status(self.worker_id, self.state)


@dataclass(frozen=True)
class WorkerRouteDecision:
    selected_worker_id: Optional[str]
    reason: str
    remote_ai_available: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_worker_id": self.selected_worker_id,
            "reason": self.reason,
            "remote_ai_available": self.remote_ai_available,
        }


class WorkerRegistry:
    """Deterministic in-memory worker state used by the Field Node control plane.

    This class performs no network access. Health probing and authenticated
    transport are separate layers. Keeping registry/routing pure makes the field
    invariant testable even when no home worker or Internet connection exists.
    """

    def __init__(self, workers: Iterable[RegisteredWorker] = ()):
        self._workers: Dict[str, RegisteredWorker] = {}
        for worker in workers:
            self.register(worker)

    def register(self, worker: RegisteredWorker) -> None:
        if worker.worker_id not in self._workers and len(self._workers) >= MAX_REGISTERED_WORKERS:
            raise ValueError(f"worker registry exceeds limit of {MAX_REGISTERED_WORKERS}")
        self._workers[worker.worker_id] = worker

    def get(self, worker_id: str) -> RegisteredWorker:
        worker_id = _validate_worker_id(worker_id)
        try:
            return self._workers[worker_id]
        except KeyError as exc:
            raise KeyError(f"unknown worker: {worker_id}") from exc

    def set_state(
        self,
        worker_id: str,
        state: ComponentState,
        *,
        capabilities: Optional[WorkerCapabilities] = None,
        error: Optional[str] = None,
    ) -> None:
        worker = self.get(worker_id)
        worker.state = ComponentState(state)
        if capabilities is not None:
            worker.capabilities = capabilities
        if state == ComponentState.ONLINE:
            worker.last_error = None
            worker.consecutive_failures = 0
        else:
            worker.last_error = error[:512] if isinstance(error, str) else None
            if state in {ComponentState.OFFLINE, ComponentState.DEGRADED}:
                worker.consecutive_failures += 1

    @property
    def remote_ai_available(self) -> bool:
        return any(worker.state == ComponentState.ONLINE for worker in self._workers.values())

    def operator_workers(self) -> Tuple[WorkerStatus, ...]:
        ordered = sorted(self._workers.values(), key=lambda item: (item.priority, item.worker_id))
        return tuple(worker.operator_status() for worker in ordered)

    def route(self) -> WorkerRouteDecision:
        online = [
            worker
            for worker in self._workers.values()
            if worker.state == ComponentState.ONLINE
        ]
        if not online:
            return WorkerRouteDecision(
                selected_worker_id=None,
                reason="NO_WORKER_AVAILABLE",
                remote_ai_available=False,
            )
        selected = min(online, key=lambda item: (item.priority, item.worker_id))
        return WorkerRouteDecision(
            selected_worker_id=selected.worker_id,
            reason="PREFERRED_ONLINE_WORKER",
            remote_ai_available=True,
        )
