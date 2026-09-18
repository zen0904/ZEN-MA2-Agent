from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

from .core import AgentCore
from .ma_bridge.server import (
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    BridgeDispatcher,
    BridgeServer,
)
from .operator_server import (
    DEFAULT_OPERATOR_HOST,
    DEFAULT_OPERATOR_PORT,
    OperatorServer,
    status_provider_from_core,
)
from .operator_api import ComponentState
from .remote_workers import WorkerRegistry
from .watchdog import WatchdogComponent, WatchdogMonitor, WatchdogService


@dataclass(frozen=True)
class FieldHostConfig:
    operator_host: str = DEFAULT_OPERATOR_HOST
    operator_port: int = DEFAULT_OPERATOR_PORT
    bridge_host: str = DEFAULT_BRIDGE_HOST
    bridge_port: int = DEFAULT_BRIDGE_PORT
    allow_remote_operator: bool = False
    allow_remote_bridge: bool = False
    watchdog_interval_seconds: float = 1.0


class FieldHost:
    """Headless ZEN Field Core host.

    OpenClaw is the operator UI. This host owns the local ZEN control plane and
    remains independently runnable when OpenClaw is stopped or unavailable.
    """

    def __init__(
        self,
        config: FieldHostConfig | None = None,
        *,
        core: AgentCore | None = None,
        worker_registry: WorkerRegistry | None = None,
    ) -> None:
        self.config = config or FieldHostConfig()
        self.core = core or AgentCore()
        self.worker_registry = worker_registry or WorkerRegistry()

        self.bridge = BridgeServer(
            BridgeDispatcher(status_payload_provider=self._bridge_status_payload),
            host=self.config.bridge_host,
            port=self.config.bridge_port,
            allow_remote=self.config.allow_remote_bridge,
        )
        self.watchdog = WatchdogService(
            WatchdogMonitor(),
            self._watchdog_observations,
            interval_seconds=self.config.watchdog_interval_seconds,
        )
        self._status_provider = status_provider_from_core(
            self.core,
            self.worker_registry,
            self.bridge,
        )
        self.operator = OperatorServer(
            self._status_provider,
            host=self.config.operator_host,
            port=self.config.operator_port,
            allow_remote=self.config.allow_remote_operator,
            watchdog_provider=self.watchdog.snapshot,
        )
        self._stop = threading.Event()

    def _bridge_status_payload(self) -> str:
        remote = "YES" if self.worker_registry.remote_ai_available else "NO"
        return f"FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE={remote}"

    def _watchdog_observations(self) -> tuple[WatchdogComponent, ...]:
        observations = [
            WatchdogComponent("field_core", ComponentState.ONLINE, required=True),
            WatchdogComponent(
                "ma_bridge",
                ComponentState.ONLINE if self.bridge.running else ComponentState.OFFLINE,
                required=True,
            ),
        ]

        runtime = getattr(self.core, "runtime", None)
        raw_state = str(
            getattr(getattr(runtime, "state", None), "value", getattr(runtime, "state", ""))
            or ""
        ).upper()
        if raw_state == "READY":
            ma_state = ComponentState.ONLINE
        elif raw_state in {"TCP_CONNECTED", "NEGOTIATING", "AUTHENTICATING", "CONNECTING"}:
            ma_state = ComponentState.DEGRADED
        elif raw_state in {"DISCONNECTED", "AUTH_FAILED"}:
            ma_state = ComponentState.OFFLINE
        else:
            ma_state = ComponentState.UNKNOWN
        observations.append(
            WatchdogComponent(
                "ma_connection",
                ma_state,
                required=False,
                detail=raw_state or None,
            )
        )

        for worker in self.worker_registry.operator_workers():
            observations.append(
                WatchdogComponent(
                    f"worker:{worker.worker_id}",
                    worker.state,
                    required=False,
                    detail=worker.gpu_name,
                )
            )
        return tuple(observations)

    def status(self) -> dict[str, Any]:
        return self._status_provider().to_dict()

    def start(self) -> None:
        self.bridge.start()
        self.watchdog.start()
        try:
            self.operator.start()
        except Exception:
            self.watchdog.stop()
            self.bridge.stop()
            raise

    def stop(self) -> None:
        self.operator.stop()
        self.watchdog.stop()
        self.bridge.stop()
        self._stop.set()

    def run_forever(self) -> None:
        self.start()
        try:
            self._stop.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
