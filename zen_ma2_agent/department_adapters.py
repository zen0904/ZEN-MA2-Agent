from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

import httpx

DEPARTMENT_ADAPTER_STATUS_SCHEMA = "zen.department_adapter_status.v0.1"
REMOTE_OPERATOR_STATUS_SCHEMA = "zen.operator_status.v0.1"
MAX_DEPARTMENT_ADAPTERS = 16
_TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")


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
    """Read-only typed federation of department-local ZEN Operator APIs."""
    def __init__(
        self,
        endpoints: Iterable[DepartmentAdapterEndpoint] = (),
        *,
        timeout_seconds: float = 2.0,
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
        self._timeout_seconds = max(0.1, min(float(timeout_seconds), 10.0))

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": DEPARTMENT_ADAPTER_STATUS_SCHEMA,
            "read_only_federation": True,
            "ma2_writes": 0,
            "adapters": [self._probe(endpoint) for endpoint in self._endpoints],
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
