from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

import httpx

from .operator_api import ComponentState
from .remote_workers import WorkerCapabilities, WorkerRegistry

WORKER_HEALTH_SCHEMA = "zen.worker.health.v0.1"
WORKER_CAPABILITIES_SCHEMA = "zen.worker.capabilities.v0.1"
MAX_WORKER_ENDPOINTS = 32


@dataclass(frozen=True)
class WorkerEndpoint:
    worker_id: str
    base_url: str

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id or len(self.worker_id) > 128:
            raise ValueError("worker_id must be a non-empty string up to 128 characters")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("worker base_url must use http or https")
        if not parsed.hostname:
            raise ValueError("worker base_url must include a host")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("worker base_url must not contain credentials, query, or fragment")
        if parsed.path not in {"", "/"}:
            raise ValueError("worker base_url must not contain a path")

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")


ClientFactory = Callable[..., httpx.Client]


class WorkerHealthProbe:
    """Reuse the existing Worker /health and /capabilities contracts.

    This client updates only WorkerRegistry state. It has no MA, shell, or LLM
    authority. A capability failure after a successful health response maps to
    DEGRADED rather than pretending the Worker is fully healthy.
    """

    def __init__(
        self,
        registry: WorkerRegistry,
        endpoints: Iterable[WorkerEndpoint],
        *,
        timeout_seconds: float = 2.0,
        client_factory: ClientFactory = httpx.Client,
    ) -> None:
        items = tuple(endpoints)
        if len(items) > MAX_WORKER_ENDPOINTS:
            raise ValueError(f"worker endpoints exceed limit of {MAX_WORKER_ENDPOINTS}")
        seen: set[str] = set()
        for item in items:
            if item.worker_id in seen:
                raise ValueError(f"duplicate worker endpoint: {item.worker_id}")
            seen.add(item.worker_id)
            registry.get(item.worker_id)
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("worker health timeout must be numeric") from exc
        if timeout <= 0:
            raise ValueError("worker health timeout must be positive")
        self.registry = registry
        self.endpoints = items
        self.timeout_seconds = timeout
        self.client_factory = client_factory

    def poll_once(self) -> None:
        for endpoint in self.endpoints:
            self._poll_endpoint(endpoint)

    def _poll_endpoint(self, endpoint: WorkerEndpoint) -> None:
        try:
            with self.client_factory(timeout=self.timeout_seconds) as client:
                health = client.get(f"{endpoint.normalized_base_url}/health")
                health.raise_for_status()
                health_data = health.json()
                self._validate_health(endpoint, health_data)

                try:
                    capabilities = client.get(
                        f"{endpoint.normalized_base_url}/capabilities"
                    )
                    capabilities.raise_for_status()
                    capability_data = capabilities.json()
                    self._validate_capabilities(endpoint, capability_data)
                except (httpx.HTTPError, ValueError, TypeError) as exc:
                    self.registry.set_state(
                        endpoint.worker_id,
                        ComponentState.DEGRADED,
                        error=f"capabilities unavailable: {str(exc)[:400]}",
                    )
                    return

                self.registry.set_state(
                    endpoint.worker_id,
                    ComponentState.ONLINE,
                    capabilities=WorkerCapabilities(
                        gpu_name=capability_data.get("gpu_name"),
                        model_runtime_available=capability_data.get(
                            "model_runtime_available"
                        ),
                    ),
                )
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            self.registry.set_state(
                endpoint.worker_id,
                ComponentState.OFFLINE,
                error=f"worker health unavailable: {str(exc)[:400]}",
            )

    @staticmethod
    def _validate_health(endpoint: WorkerEndpoint, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("worker health payload must be an object")
        if payload.get("schema_version") != WORKER_HEALTH_SCHEMA:
            raise ValueError("worker health schema mismatch")
        if payload.get("worker_id") != endpoint.worker_id:
            raise ValueError("worker health identity mismatch")
        if payload.get("status") != "ONLINE":
            raise ValueError("worker health status is not ONLINE")

    @staticmethod
    def _validate_capabilities(endpoint: WorkerEndpoint, payload: object) -> None:
        if not isinstance(payload, dict):
            raise ValueError("worker capabilities payload must be an object")
        if payload.get("schema_version") != WORKER_CAPABILITIES_SCHEMA:
            raise ValueError("worker capabilities schema mismatch")
        if payload.get("worker_id") != endpoint.worker_id:
            raise ValueError("worker capabilities identity mismatch")
        gpu_name = payload.get("gpu_name")
        if gpu_name is not None and not isinstance(gpu_name, str):
            raise ValueError("worker gpu_name must be string or null")
        runtime = payload.get("model_runtime_available")
        if runtime is not None and not isinstance(runtime, bool):
            raise ValueError("worker model_runtime_available must be boolean or null")


class WorkerHealthService:
    """Background polling wrapper for WorkerHealthProbe."""

    def __init__(
        self,
        probe: WorkerHealthProbe,
        *,
        interval_seconds: float = 5.0,
    ) -> None:
        try:
            interval = float(interval_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("worker health interval must be numeric") from exc
        if interval <= 0:
            raise ValueError("worker health interval must be positive")
        self.probe = probe
        self.interval_seconds = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self.probe.poll_once()
        self._thread = threading.Thread(
            target=self._run,
            name="zen-worker-health",
            daemon=True,
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.probe.poll_once()
            except Exception:
                # Per-worker failures are handled inside WorkerHealthProbe. This
                # guard prevents an unexpected probe bug from killing Field Core.
                continue

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self.interval_seconds * 2))
        self._thread = None
