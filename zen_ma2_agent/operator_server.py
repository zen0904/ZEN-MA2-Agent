from __future__ import annotations

import ipaddress
import threading
from typing import Any, Mapping, Optional

import uvicorn
from fastapi import FastAPI, HTTPException

from .operator_api import (
    ComponentState,
    MAConnectionState,
    OpenClawOperatorAdapter,
    PipelineStatus,
    StatusProvider,
    UnknownOpenClawTool,
    build_operator_status,
)
from .remote_workers import WorkerRegistry

OPERATOR_HTTP_SCHEMA = "zen.operator_http.v0.1"
OPERATOR_HEALTH_SCHEMA = "zen.operator_http_health.v0.1"
DEFAULT_OPERATOR_HOST = "127.0.0.1"
DEFAULT_OPERATOR_PORT = 8876
MAX_REQUEST_ENVELOPE_KEYS = frozenset({"arguments", "request_id"})


def _ma_connection_state(value: object) -> MAConnectionState:
    text = str(getattr(value, "value", value) or "").upper()
    if text == "READY":
        return MAConnectionState.READY
    if text in {"TCP_CONNECTED", "NEGOTIATING", "AUTHENTICATING", "CONNECTING"}:
        return MAConnectionState.CONNECTING
    if text == "DISCONNECTED":
        return MAConnectionState.DISCONNECTED
    if text == "DEGRADED":
        return MAConnectionState.DEGRADED
    return MAConnectionState.UNKNOWN


def _bridge_state(bridge_server: Any) -> ComponentState:
    if bridge_server is None:
        return ComponentState.UNKNOWN
    try:
        return ComponentState.ONLINE if bool(bridge_server.running) else ComponentState.OFFLINE
    except Exception:
        return ComponentState.DEGRADED


def status_provider_from_core(
    core: Any,
    worker_registry: Optional[WorkerRegistry] = None,
    bridge_server: Any = None,
) -> StatusProvider:
    """Create a read-only status provider without calling AgentCore.snapshot().

    AgentCore.snapshot() also performs Internet-status bookkeeping. The OpenClaw
    control-plane contract should not cause unrelated external network probes, so
    this adapter reads only the local runtime state that it needs.
    """

    def provider():
        runtime = getattr(core, "runtime", None)
        preferences = getattr(runtime, "preferences", {}) if runtime is not None else {}
        ma2 = preferences.get("ma2", {}) if isinstance(preferences, Mapping) else {}

        ma_target = None
        host = ma2.get("host") if isinstance(ma2, Mapping) else None
        port = ma2.get("port") if isinstance(ma2, Mapping) else None
        if isinstance(host, str) and host:
            try:
                port_number = int(port)
            except (TypeError, ValueError):
                port_number = 0
            if 1 <= port_number <= 65535:
                from .operator_api import MATarget

                ma_target = MATarget(host=host, port=port_number)

        workers = worker_registry.operator_workers() if worker_registry is not None else ()
        remote_ai_available = (
            worker_registry.remote_ai_available if worker_registry is not None else False
        )

        return build_operator_status(
            field_core_available=True,
            field_core_state=ComponentState.ONLINE,
            ma_bridge_state=_bridge_state(bridge_server),
            ma_connection_state=_ma_connection_state(
                getattr(runtime, "state", None) if runtime is not None else None
            ),
            remote_ai_available=remote_ai_available,
            workers=workers,
            pipeline=PipelineStatus(),
            latest_artifact=None,
            ma_target=ma_target,
        )

    return provider


def create_operator_app(status_provider: StatusProvider) -> FastAPI:
    """Build the narrow localhost-first API intended for the OpenClaw adapter."""

    adapter = OpenClawOperatorAdapter(status_provider)
    app = FastAPI(
        title="ZEN Operator API",
        version="0.1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        return {
            "schema": OPERATOR_HEALTH_SCHEMA,
            "status": "OK",
        }

    @app.get("/zen/v0.1/status")
    def status() -> dict[str, Any]:
        return status_provider().to_dict()

    @app.post("/zen/v0.1/tools/{tool_name}")
    def invoke_tool(tool_name: str, envelope: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        body = dict(envelope or {})
        unexpected = set(body) - MAX_REQUEST_ENVELOPE_KEYS
        if unexpected:
            raise HTTPException(
                status_code=400,
                detail={
                    "schema": OPERATOR_HTTP_SCHEMA,
                    "code": "INVALID_ENVELOPE",
                    "message": "Only arguments and request_id are accepted.",
                },
            )

        arguments = body.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            raise HTTPException(
                status_code=400,
                detail={
                    "schema": OPERATOR_HTTP_SCHEMA,
                    "code": "INVALID_ARGUMENTS",
                    "message": "arguments must be a JSON object.",
                },
            )

        request_id = body.get("request_id")
        if request_id is not None and not isinstance(request_id, str):
            raise HTTPException(
                status_code=400,
                detail={
                    "schema": OPERATOR_HTTP_SCHEMA,
                    "code": "INVALID_REQUEST_ID",
                    "message": "request_id must be a string or null.",
                },
            )

        try:
            return adapter.invoke(tool_name, arguments, request_id=request_id)
        except UnknownOpenClawTool as exc:
            raise HTTPException(
                status_code=404,
                detail={
                    "schema": OPERATOR_HTTP_SCHEMA,
                    "code": "UNKNOWN_TOOL",
                    "message": "Tool is not part of the ZEN OpenClaw contract.",
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "schema": OPERATOR_HTTP_SCHEMA,
                    "code": "INVALID_REQUEST",
                    "message": str(exc)[:512],
                },
            ) from exc

    return app


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OperatorServer:
    """Small uvicorn wrapper with a loopback-only safe default."""

    def __init__(
        self,
        status_provider: StatusProvider,
        port: int = DEFAULT_OPERATOR_PORT,
        *,
        host: str = DEFAULT_OPERATOR_HOST,
        allow_remote: bool = False,
    ):
        if not 1 <= int(port) <= 65535:
            raise ValueError("operator port must be in range 1..65535")
        if not allow_remote and not _is_loopback_host(host):
            raise ValueError(
                "non-loopback operator bind requires allow_remote=True and separate security review"
            )
        self.host = host
        self.port = int(port)
        self.app = create_operator_app(status_provider)
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._server = uvicorn.Server(
            uvicorn.Config(
                self.app,
                host=self.host,
                port=self.port,
                log_level="warning",
            )
        )
        self._thread = threading.Thread(
            target=self._server.run,
            name="zen-operator-api",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
