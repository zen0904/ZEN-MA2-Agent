from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Iterable

from .core import AgentCore
from .host_metrics import HostMetricsProvider
from .llm.lean_design_adapter import load_portable_lean_design_intelligence
from .llm.openclaw_infer_adapter import load_openclaw_infer_design_intelligence
from .ma2_visual_observation import load_ma2_visual_observation_service
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
from .remote_workers import RegisteredWorker, WorkerRegistry
from .watchdog import WatchdogComponent, WatchdogMonitor, WatchdogService
from .worker_health import WorkerEndpoint, WorkerHealthProbe, WorkerHealthService


@dataclass(frozen=True)
class FieldHostConfig:
    operator_host: str = DEFAULT_OPERATOR_HOST
    operator_port: int = DEFAULT_OPERATOR_PORT
    bridge_host: str = DEFAULT_BRIDGE_HOST
    bridge_port: int = DEFAULT_BRIDGE_PORT
    allow_remote_operator: bool = False
    allow_remote_bridge: bool = False
    watchdog_interval_seconds: float = 1.0
    worker_health_interval_seconds: float = 5.0
    worker_health_timeout_seconds: float = 2.0
    auto_connect_ma2: bool = True
    ma_poll_interval_seconds: float = 0.05
    ma_reconnect_interval_seconds: float = 2.0


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
        worker_endpoints: Iterable[WorkerEndpoint] = (),
    ) -> None:
        self.config = config or FieldHostConfig()
        self.design_intelligence_status: dict[str, Any] = {
            "configured": False,
            "source": "portable_provider_router",
            "error_class": None,
        }
        if core is None:
            try:
                design_intelligence = load_portable_lean_design_intelligence()
            except (OSError, ValueError):
                design_intelligence = None
                self.design_intelligence_status["error_class"] = "CONFIGURATION_ERROR"

            if design_intelligence is None:
                try:
                    design_intelligence = load_openclaw_infer_design_intelligence()
                except (OSError, ValueError):
                    if self.design_intelligence_status["error_class"] is None:
                        self.design_intelligence_status["error_class"] = "CONFIGURATION_ERROR"
                else:
                    if design_intelligence is not None:
                        self.design_intelligence_status["source"] = "openclaw_sdk_isolated_completion"
                        self.design_intelligence_status["error_class"] = None

            self.design_intelligence_status["configured"] = design_intelligence is not None
            self.core = AgentCore(design_intelligence_provider=design_intelligence)
        else:
            # Explicit Core injection remains authoritative for tests,
            # embedding, and alternate runtimes.
            self.core = core
            self.design_intelligence_status["source"] = "injected_core"
            self.design_intelligence_status["configured"] = (
                getattr(core, "design_intelligence_provider", None) is not None
            )
        endpoints = tuple(worker_endpoints)
        if worker_registry is None:
            self.worker_registry = WorkerRegistry(
                RegisteredWorker(endpoint.worker_id, priority=(index + 1) * 10)
                for index, endpoint in enumerate(endpoints)
            )
        else:
            self.worker_registry = worker_registry
        self.worker_health = (
            WorkerHealthService(
                WorkerHealthProbe(
                    self.worker_registry,
                    endpoints,
                    timeout_seconds=self.config.worker_health_timeout_seconds,
                ),
                interval_seconds=self.config.worker_health_interval_seconds,
            )
            if endpoints
            else None
        )

        self.host_metrics = HostMetricsProvider()
        try:
            self.visual_observation_service = load_ma2_visual_observation_service()
        except (OSError, ValueError):
            self.visual_observation_service = None
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
        design_handler = getattr(self.core, "program_show_request", None)
        preview_handler = getattr(self.core, "preview_action", None)
        approve_method = getattr(self.core, "approve_action", None)
        approve_handler = (
            (lambda action_id, danger_confirmed: approve_method(action_id, danger_confirmed=danger_confirmed))
            if approve_method is not None
            else None
        )
        self.operator = OperatorServer(
            self._status_provider,
            host=self.config.operator_host,
            port=self.config.operator_port,
            allow_remote=self.config.allow_remote_operator,
            watchdog_provider=self.watchdog.snapshot,
            host_status_provider=self.host_metrics.snapshot,
            visual_observation_provider=(
                self.visual_observation_service.observe
                if self.visual_observation_service is not None
                else None
            ),
            design_request_handler=design_handler,
            preview_handler=preview_handler,
            approve_handler=approve_handler,
            position_preview_handler=getattr(self.core, "preview_position_application_poc", None),
            raw_position_preview_handler=getattr(self.core, "preview_position_raw_cue_poc", None),
            position_calibration_preview_handler=getattr(
                self.core, "preview_position_calibration", None
            ),
        )
        self._stop = threading.Event()
        self._ma_thread: threading.Thread | None = None
        self._ma_next_retry_at = 0.0
        self.ma_runtime_status: dict[str, Any] = {
            "state": "IDLE",
            "last_error": None,
        }

    def _ma_settings(self) -> dict[str, Any]:
        runtime = getattr(self.core, "runtime", None)
        preferences = getattr(runtime, "preferences", {}) if runtime is not None else {}
        ma2 = preferences.get("ma2", {}) if isinstance(preferences, dict) else {}
        return dict(ma2) if isinstance(ma2, dict) else {}

    def _poll_ma_runtime_once(self) -> None:
        """Advance the existing MA client state machine and retry safe local connects.

        Connection establishment is transport setup only. It never authorizes or
        executes MA writes; Preview/Approval/Builder remain the mutation boundary.
        """
        runtime = getattr(self.core, "runtime", None)
        if runtime is None:
            self.ma_runtime_status = {"state": "NO_RUNTIME", "last_error": None}
            return

        raw_state = str(
            getattr(getattr(runtime, "state", None), "value", getattr(runtime, "state", ""))
            or ""
        ).upper()
        now = time.monotonic()

        if (
            self.config.auto_connect_ma2
            and raw_state == "DISCONNECTED"
            and now >= self._ma_next_retry_at
        ):
            ma2 = self._ma_settings()
            username = ma2.get("username")
            host = ma2.get("host")
            port = ma2.get("port")
            connect = getattr(self.core, "connect", None)
            if callable(connect) and isinstance(username, str) and username.strip():
                try:
                    connect(str(host or "127.0.0.1"), port or 30000, username, "")
                except Exception as exc:
                    self._ma_next_retry_at = now + max(
                        0.1, float(self.config.ma_reconnect_interval_seconds)
                    )
                    self.ma_runtime_status = {
                        "state": "RETRY_WAIT",
                        "last_error": type(exc).__name__,
                    }
                else:
                    self._ma_next_retry_at = 0.0
                    self.ma_runtime_status = {
                        "state": "CONNECTING",
                        "last_error": None,
                    }

        tick = getattr(self.core, "tick", None)
        if callable(tick):
            try:
                tick()
            except Exception as exc:
                self.ma_runtime_status = {
                    "state": "POLL_ERROR",
                    "last_error": type(exc).__name__,
                }
                return

        current = str(
            getattr(getattr(runtime, "state", None), "value", getattr(runtime, "state", ""))
            or ""
        ).upper()
        if current:
            self.ma_runtime_status = {
                "state": current,
                "last_error": self.ma_runtime_status.get("last_error"),
            }

    def _ma_runtime_loop(self) -> None:
        interval = max(0.01, float(self.config.ma_poll_interval_seconds))
        while not self._stop.is_set():
            self._poll_ma_runtime_once()
            self._stop.wait(interval)

    def _bridge_status_payload(self) -> str:
        remote = "YES" if self.worker_registry.remote_ai_available else "NO"
        return f"FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE={remote}"

    def _watchdog_observations(self) -> tuple[WatchdogComponent, ...]:
        host_status = self.host_metrics.snapshot()
        host_detail = (
            f"CPU={host_status.get('cpu_percent')}% "
            f"RAM={host_status.get('memory', {}).get('percent')}% "
            f"DISK={host_status.get('disk', {}).get('percent')}%"
        )
        observations = [
            WatchdogComponent("field_core", ComponentState.ONLINE, required=True),
            WatchdogComponent(
                "host_metrics",
                ComponentState(host_status["state"]),
                required=False,
                detail=host_detail,
            ),
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
        self._stop.clear()
        self.bridge.start()
        if self.worker_health is not None:
            self.worker_health.start()
        self._ma_thread = threading.Thread(
            target=self._ma_runtime_loop,
            name="zen-ma-runtime",
            daemon=True,
        )
        self._ma_thread.start()
        self.watchdog.start()
        try:
            self.operator.start()
        except Exception:
            self._stop.set()
            if self._ma_thread is not None:
                self._ma_thread.join(timeout=1.0)
            self.watchdog.stop()
            if self.worker_health is not None:
                self.worker_health.stop()
            self.bridge.stop()
            raise

    def stop(self) -> None:
        self._stop.set()
        if self._ma_thread is not None:
            self._ma_thread.join(timeout=1.0)
            self._ma_thread = None
        self.operator.stop()
        self.watchdog.stop()
        if self.worker_health is not None:
            self.worker_health.stop()
        self.bridge.stop()
        disconnect = getattr(self.core, "disconnect", None)
        if callable(disconnect):
            try:
                disconnect()
            except Exception:
                pass

    def run_forever(self) -> None:
        self.start()
        try:
            self._stop.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
