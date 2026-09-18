from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple


OPERATOR_STATUS_SCHEMA = "zen.operator_status.v0.1"
TOOL_RESULT_SCHEMA = "zen.tool_result.v0.1"
MAX_TOOL_PAYLOAD_BYTES = 8192
MAX_WORKERS = 32


class ComponentState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class MAConnectionState(str, Enum):
    READY = "READY"
    CONNECTING = "CONNECTING"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class PipelineState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MATarget:
    host: str
    port: int

    def to_dict(self) -> Dict[str, Any]:
        host = _bounded_text(self.host, "ma.target.host", 255)
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("ma.target.port must be in range 1..65535")
        return {"host": host, "port": int(self.port)}


@dataclass(frozen=True)
class WorkerStatus:
    worker_id: str
    state: ComponentState = ComponentState.UNKNOWN
    gpu_name: Optional[str] = None
    model_runtime_available: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": _bounded_text(self.worker_id, "worker_id", 128),
            "state": self.state.value,
            "gpu_name": _optional_bounded_text(self.gpu_name, "gpu_name", 256),
            "model_runtime_available": self.model_runtime_available,
        }


@dataclass(frozen=True)
class PipelineStatus:
    researcher: PipelineState = PipelineState.UNKNOWN
    designer: PipelineState = PipelineState.UNKNOWN
    critic: PipelineState = PipelineState.UNKNOWN
    finalizer: PipelineState = PipelineState.UNKNOWN

    def to_dict(self) -> Dict[str, str]:
        return {
            "researcher": self.researcher.value,
            "designer": self.designer.value,
            "critic": self.critic.value,
            "finalizer": self.finalizer.value,
        }


@dataclass(frozen=True)
class ArtifactSummary:
    artifact_id: str
    schema: str
    request_hash: str
    show_context_hash: Optional[str] = None
    created_at: Optional[str] = None
    source_worker_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": _bounded_text(self.artifact_id, "artifact_id", 256),
            "schema": _bounded_text(self.schema, "artifact.schema", 128),
            "request_hash": _bounded_text(self.request_hash, "request_hash", 128),
            "show_context_hash": _optional_bounded_text(
                self.show_context_hash, "show_context_hash", 128
            ),
            "created_at": self.created_at,
            "source_worker_id": _optional_bounded_text(
                self.source_worker_id, "source_worker_id", 128
            ),
        }


@dataclass(frozen=True)
class OperatorStatusSnapshot:
    field_core_available: bool
    field_core_state: ComponentState
    ma_bridge_state: ComponentState
    ma_connection_state: MAConnectionState
    remote_ai_available: bool
    workers: Tuple[WorkerStatus, ...]
    pipeline: PipelineStatus
    latest_artifact: Optional[ArtifactSummary] = None
    generated_at: Optional[str] = None
    ma_target: Optional[MATarget] = None

    def to_dict(self) -> Dict[str, Any]:
        if len(self.workers) > MAX_WORKERS:
            raise ValueError(f"workers exceeds contract limit of {MAX_WORKERS}")
        return {
            "schema": OPERATOR_STATUS_SCHEMA,
            "generated_at": self.generated_at,
            "field_core": {
                "available": bool(self.field_core_available),
                "state": self.field_core_state.value,
            },
            "ma": {
                "bridge_state": self.ma_bridge_state.value,
                "connection_state": self.ma_connection_state.value,
                "target": self.ma_target.to_dict() if self.ma_target is not None else None,
            },
            "remote_ai_available": bool(self.remote_ai_available),
            "workers": [worker.to_dict() for worker in self.workers],
            "pipeline": self.pipeline.to_dict(),
            "latest_artifact": (
                self.latest_artifact.to_dict() if self.latest_artifact is not None else None
            ),
        }


def build_operator_status(
    *,
    field_core_available: bool,
    field_core_state: ComponentState = ComponentState.UNKNOWN,
    ma_bridge_state: ComponentState = ComponentState.UNKNOWN,
    ma_connection_state: MAConnectionState = MAConnectionState.UNKNOWN,
    remote_ai_available: bool = False,
    workers: Iterable[WorkerStatus] = (),
    pipeline: Optional[PipelineStatus] = None,
    latest_artifact: Optional[ArtifactSummary] = None,
    generated_at: Optional[str] = None,
    ma_target: Optional[MATarget] = None,
) -> OperatorStatusSnapshot:
    """Build the read-only operator snapshot used by an OpenClaw adapter.

    This helper deliberately has no OpenClaw dependency. OpenClaw availability
    is not an input and therefore cannot silently change Field Core health.
    """

    return OperatorStatusSnapshot(
        field_core_available=bool(field_core_available),
        field_core_state=field_core_state,
        ma_bridge_state=ma_bridge_state,
        ma_connection_state=ma_connection_state,
        remote_ai_available=bool(remote_ai_available),
        workers=tuple(workers),
        pipeline=pipeline or PipelineStatus(),
        latest_artifact=latest_artifact,
        generated_at=generated_at,
        ma_target=ma_target,
    )


StatusProvider = Callable[[], OperatorStatusSnapshot]
WatchdogProvider = Callable[[], Mapping[str, Any]]
HostStatusProvider = Callable[[], Mapping[str, Any]]


class UnknownOpenClawTool(ValueError):
    pass


class OpenClawOperatorAdapter:
    """Thin OpenClaw-facing adapter with no MA-write or LLM authority."""

    READ_ONLY_TOOLS = frozenset(
        {
            "zen.status",
            "zen.worker.status",
            "zen.ma.status",
            "zen.artifact.latest",
            "zen.watchdog.status",
            "zen.host.status",
        }
    )
    RESERVED_TOOLS = frozenset(
        {
            "zen.design.request",
            "zen.preview",
            "zen.approve",
        }
    )
    ALLOWED_TOOLS = READ_ONLY_TOOLS | RESERVED_TOOLS

    def __init__(
        self,
        status_provider: StatusProvider,
        watchdog_provider: Optional[WatchdogProvider] = None,
        host_status_provider: Optional[HostStatusProvider] = None,
    ):
        self._status_provider = status_provider
        self._watchdog_provider = watchdog_provider
        self._host_status_provider = host_status_provider

    def invoke(
        self,
        tool_name: str,
        payload: Optional[Mapping[str, Any]] = None,
        *,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if tool_name not in self.ALLOWED_TOOLS:
            # The public result schema only permits known tool names, so an
            # unknown tool is rejected before a schema-valid result envelope
            # is constructed.
            raise UnknownOpenClawTool(tool_name)

        request_id = _optional_bounded_text(request_id, "request_id", 128)
        safe_payload = dict(payload or {})
        if not _payload_within_limit(safe_payload):
            return self._result(
                tool_name,
                "REJECTED",
                None,
                {"code": "PAYLOAD_INVALID_OR_TOO_LARGE", "message": "Payload is not accepted."},
                request_id,
            )
        if safe_payload:
            return self._result(
                tool_name,
                "REJECTED",
                None,
                {"code": "UNEXPECTED_ARGUMENT", "message": "This tool accepts no arguments."},
                request_id,
            )

        if tool_name in self.RESERVED_TOOLS:
            return self._result(tool_name, "NOT_IMPLEMENTED", None, None, request_id)

        if tool_name == "zen.watchdog.status":
            if self._watchdog_provider is None:
                return self._result(tool_name, "NOT_IMPLEMENTED", None, None, request_id)
            return self._result(
                tool_name,
                "SUCCESS",
                dict(self._watchdog_provider()),
                None,
                request_id,
            )

        if tool_name == "zen.host.status":
            if self._host_status_provider is None:
                return self._result(tool_name, "NOT_IMPLEMENTED", None, None, request_id)
            return self._result(
                tool_name,
                "SUCCESS",
                dict(self._host_status_provider()),
                None,
                request_id,
            )

        snapshot = self._status_provider()
        snapshot_data = snapshot.to_dict()
        if tool_name == "zen.status":
            result: Any = snapshot_data
        elif tool_name == "zen.worker.status":
            result = {
                "remote_ai_available": snapshot_data["remote_ai_available"],
                "workers": snapshot_data["workers"],
            }
        elif tool_name == "zen.ma.status":
            result = snapshot_data["ma"]
        elif tool_name == "zen.artifact.latest":
            result = snapshot_data["latest_artifact"]
        else:  # pragma: no cover
            raise UnknownOpenClawTool(tool_name)

        return self._result(tool_name, "SUCCESS", result, None, request_id)

    @staticmethod
    def _result(
        tool_name: str,
        status: str,
        result: Any,
        error: Optional[Dict[str, str]],
        request_id: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "schema": TOOL_RESULT_SCHEMA,
            "tool": tool_name,
            "status": status,
            "result": result,
            "error": error,
            "request_id": request_id,
        }


def _payload_within_limit(payload: Mapping[str, Any]) -> bool:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return False
    return len(encoded) <= MAX_TOOL_PAYLOAD_BYTES


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
