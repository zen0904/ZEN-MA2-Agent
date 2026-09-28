from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import json
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

import httpx

DEPARTMENT_ADAPTER_STATUS_SCHEMA = "zen.department_adapter_status.v0.1"
DEPARTMENT_PREVIEW_SCHEMA = "zen.department_preview.v0.1"
REMOTE_OPERATOR_STATUS_SCHEMA = "zen.operator_status.v0.1"
REMOTE_TOOL_RESULT_SCHEMA = "zen.tool_result.v0.1"
MAX_DEPARTMENT_ADAPTERS = 16
MAX_REMOTE_PREVIEW_RESULT_BYTES = 2 * 1024 * 1024
_TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")

PREVIEW_TOOL_NAMES = frozenset(
    {
        "zen.design.request",
        "zen.preview",
        "zen.position.preview",
        "zen.position.raw.preview",
        "zen.position.calibration.preview",
    }
)
_REMOTE_TOOL_STATUSES = frozenset(
    {"SUCCESS", "NOT_IMPLEMENTED", "REJECTED", "FAILED"}
)
_REMOTE_RESULT_KEYS = frozenset(
    {"schema", "tool", "status", "result", "error", "request_id"}
)


def _bounded(value: object, *, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError(
            f"{field} must be a non-empty string of at most {limit} characters"
        )
    return value


def _private_endpoint_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("department adapter URL must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("department adapter URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError(
            "department adapter URL must contain only scheme, host and optional port"
        )
    host = parsed.hostname
    if not host:
        raise ValueError("department adapter URL requires a host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError(
            "department adapter host must be a literal private or Tailscale IP"
        ) from exc
    if not (address.is_loopback or address.is_private or address in _TAILSCALE_NET):
        raise ValueError(
            "department adapter host must be loopback, private LAN, or Tailscale CGNAT"
        )
    if parsed.port is not None and not 1 <= parsed.port <= 65535:
        raise ValueError("department adapter port must be in range 1..65535")
    return value.rstrip("/")


@dataclass(frozen=True)
class DepartmentAdapterEndpoint:
    adapter_id: str
    base_url: str
    department: str = "LIGHTING"
    adapter_kind: str = "GRANDMA2"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "adapter_id",
            _bounded(self.adapter_id, field="adapter_id", limit=128),
        )
        object.__setattr__(
            self,
            "department",
            _bounded(self.department, field="department", limit=64).upper(),
        )
        object.__setattr__(
            self,
            "adapter_kind",
            _bounded(self.adapter_kind, field="adapter_kind", limit=64).upper(),
        )
        object.__setattr__(self, "base_url", _private_endpoint_url(self.base_url))


class DepartmentAdapterRegistry:
    """Typed, bounded federation of department-local ZEN Operator APIs.

    Status projection is read-only. Preview delegation is restricted to a
    fixed tool allowlist that cannot approve or execute MA writes.
    """

    def __init__(
        self,
        endpoints: Iterable[DepartmentAdapterEndpoint] = (),
        *,
        timeout_seconds: float = 2.0,
        preview_timeout_seconds: float = 25.0,
    ) -> None:
        items = tuple(endpoints)
        if len(items) > MAX_DEPARTMENT_ADAPTERS:
            raise ValueError(
                f"department adapters exceed contract limit of {MAX_DEPARTMENT_ADAPTERS}"
            )
        ids = [item.adapter_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("department adapter ids must be unique")
        self._endpoints = items
        self._endpoints_by_id = {item.adapter_id: item for item in items}
        self._timeout_seconds = max(0.1, min(float(timeout_seconds), 10.0))
        self._preview_timeout_seconds = max(
            1.0, min(float(preview_timeout_seconds), 90.0)
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": DEPARTMENT_ADAPTER_STATUS_SCHEMA,
            "read_only_federation": True,
            "ma2_writes": 0,
            "adapters": [self._probe(endpoint) for endpoint in self._endpoints],
        }

    def preview(
        self,
        adapter_id: str,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        base = {
            "schema": DEPARTMENT_PREVIEW_SCHEMA,
            "adapter_id": adapter_id,
            "authority": "REMOTE_PREVIEW_ONLY",
            "ma2_writes": 0,
            "remote_tool": tool_name,
        }
        endpoint = self._endpoints_by_id.get(adapter_id)
        if endpoint is None:
            return {
                **base,
                "delegation_status": "REJECTED",
                "remote_result": None,
                "error": {
                    "code": "ADAPTER_NOT_FOUND",
                    "message": "Requested department adapter is not registered.",
                },
            }
        if tool_name not in PREVIEW_TOOL_NAMES:
            return {
                **base,
                "delegation_status": "REJECTED",
                "remote_result": None,
                "error": {
                    "code": "TOOL_NOT_ALLOWED",
                    "message": "Requested operation is not a preview-only department tool.",
                },
            }
        if not isinstance(arguments, Mapping):
            return {
                **base,
                "delegation_status": "REJECTED",
                "remote_result": None,
                "error": {
                    "code": "INVALID_ARGUMENTS",
                    "message": "Preview arguments must be a JSON object.",
                },
            }

        try:
            with httpx.Client(
                timeout=self._preview_timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = client.post(
                    f"{endpoint.base_url}/zen/v0.1/tools/{tool_name}",
                    json={"arguments": dict(arguments)},
                )
            if response.status_code != 200:
                raise ValueError("REMOTE_HTTP_STATUS")
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise ValueError("REMOTE_RESULT_INVALID")
            required = {"schema", "tool", "status", "result", "error"}
            if not required.issubset(payload) or set(payload) - _REMOTE_RESULT_KEYS:
                raise ValueError("REMOTE_RESULT_INVALID")
            if payload.get("schema") != REMOTE_TOOL_RESULT_SCHEMA:
                raise ValueError("REMOTE_SCHEMA_MISMATCH")
            if payload.get("tool") != tool_name:
                raise ValueError("REMOTE_TOOL_MISMATCH")
            if payload.get("status") not in _REMOTE_TOOL_STATUSES:
                raise ValueError("REMOTE_STATUS_INVALID")
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(encoded) > MAX_REMOTE_PREVIEW_RESULT_BYTES:
                raise ValueError("REMOTE_RESULT_TOO_LARGE")
            return {
                **base,
                "delegation_status": "SUCCESS",
                "remote_result": dict(payload),
                "error": None,
            }
        except (httpx.HTTPError, ValueError, TypeError):
            return {
                **base,
                "delegation_status": "FAILED",
                "remote_result": None,
                "error": {
                    "code": "REMOTE_PREVIEW_UNAVAILABLE",
                    "message": "Department preview adapter did not return a valid bounded result.",
                },
            }

    def _probe(self, endpoint: DepartmentAdapterEndpoint) -> dict[str, Any]:
        base = {
            "adapter_id": endpoint.adapter_id,
            "department": endpoint.department,
            "adapter_kind": endpoint.adapter_kind,
            "transport": "PRIVATE_HTTP",
            "authority": "REMOTE_READ_ONLY",
            "ma2_writes": 0,
        }
        try:
            with httpx.Client(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = client.get(f"{endpoint.base_url}/zen/v0.1/status")
            if response.status_code != 200:
                raise ValueError("REMOTE_HTTP_STATUS")
            payload = response.json()
            if (
                not isinstance(payload, Mapping)
                or payload.get("schema") != REMOTE_OPERATOR_STATUS_SCHEMA
            ):
                raise ValueError("REMOTE_SCHEMA_MISMATCH")

            field_core = payload.get("field_core")
            ma = payload.get("ma")
            if not isinstance(field_core, Mapping) or not isinstance(ma, Mapping):
                raise ValueError("REMOTE_STATUS_INVALID")

            field_state = str(field_core.get("state") or "UNKNOWN").upper()
            if field_state not in {"ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"}:
                field_state = "UNKNOWN"
            bridge_state = str(ma.get("bridge_state") or "UNKNOWN").upper()
            if bridge_state not in {"ONLINE", "OFFLINE", "DEGRADED", "UNKNOWN"}:
                bridge_state = "UNKNOWN"
            connection_state = str(ma.get("connection_state") or "UNKNOWN").upper()
            if connection_state not in {
                "READY",
                "CONNECTING",
                "DISCONNECTED",
                "DEGRADED",
                "UNKNOWN",
            }:
                connection_state = "UNKNOWN"

            target = ma.get("target")
            safe_target = None
            if isinstance(target, Mapping):
                host = target.get("host")
                port = target.get("port")
                if (
                    isinstance(host, str)
                    and host
                    and len(host) <= 255
                    and isinstance(port, int)
                    and not isinstance(port, bool)
                    and 1 <= port <= 65535
                ):
                    safe_target = {"host": host, "port": port}

            return {
                **base,
                "state": "ONLINE" if field_state == "ONLINE" else field_state,
                "remote_schema": REMOTE_OPERATOR_STATUS_SCHEMA,
                "field_core_state": field_state,
                "ma": {
                    "bridge_state": bridge_state,
                    "connection_state": connection_state,
                    "target": safe_target,
                },
                "error": None,
            }
        except (httpx.HTTPError, ValueError, TypeError):
            return {
                **base,
                "state": "OFFLINE",
                "remote_schema": None,
                "field_core_state": "UNKNOWN",
                "ma": {
                    "bridge_state": "UNKNOWN",
                    "connection_state": "UNKNOWN",
                    "target": None,
                },
                "error": {"class": "REMOTE_STATUS_UNAVAILABLE"},
            }
