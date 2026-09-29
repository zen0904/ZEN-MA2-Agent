"""Native MCP facade for the existing bounded ZEN operator contract."""

from __future__ import annotations

import argparse
import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp.server import MCPServer
from mcp.types import ToolAnnotations

DEFAULT_OPERATOR_BASE_URL = "http://127.0.0.1:18878"
DEFAULT_CONTROLLER_BASE_URL = "http://127.0.0.1:18876"
DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 18879
DEFAULT_LIGHTING_ADAPTER_ID = "LIGHTING_GRANDMA2"
TOOL_RESULT_SCHEMA = "zen.tool_result.v0.1"
DEPARTMENT_PREVIEW_SCHEMA = "zen.department_preview.v0.1"

READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

OBSERVATION_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)
PREVIEW_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


def _loopback_base_url(value: str) -> str:
    parsed = urlparse(value.rstrip("/"))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("ZEN MCP upstream must be an http(s) URL.")
    host = parsed.hostname
    if host.lower() != "localhost":
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValueError("ZEN MCP upstream must remain loopback-only.") from exc
        if not address.is_loopback:
            raise ValueError("ZEN MCP upstream must remain loopback-only.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("ZEN MCP upstream URL must not contain credentials/query/fragment.")
    return value.rstrip("/")

def _invoke(
    base_url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = _loopback_base_url(base_url)
    response = httpx.post(
        f"{root}/zen/v0.1/tools/{tool_name}",
        json={"arguments": dict(arguments or {})},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError("ZEN operator returned a non-object payload.")
    if payload.get("schema") != TOOL_RESULT_SCHEMA:
        raise RuntimeError("ZEN operator returned an unexpected tool-result schema.")
    if payload.get("tool") != tool_name:
        raise RuntimeError("ZEN operator returned a mismatched tool identity.")
    return payload


def _invoke_department_preview(
    controller_base_url: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _invoke(
        controller_base_url,
        "zen.department.preview",
        {
            "adapter_id": DEFAULT_LIGHTING_ADAPTER_ID,
            "tool_name": tool_name,
            "arguments": dict(arguments or {}),
        },
    )

    if payload.get("status") != "SUCCESS":
        return payload
    delegation = payload.get("result")
    if not isinstance(delegation, dict):
        raise RuntimeError("ZEN Controller returned an invalid department preview result.")
    if (
        delegation.get("schema") != DEPARTMENT_PREVIEW_SCHEMA
        or delegation.get("authority") != "REMOTE_PREVIEW_ONLY"
        or delegation.get("ma2_writes") != 0
        or delegation.get("remote_tool") != tool_name
    ):
        raise RuntimeError("ZEN Controller department preview contract mismatch.")

    delegation_status = delegation.get("delegation_status")
    if delegation_status != "SUCCESS":
        rejected = delegation_status == "REJECTED"
        error = delegation.get("error")
        if not isinstance(error, dict):
            error = {
                "code": "DEPARTMENT_PREVIEW_REJECTED" if rejected else "DEPARTMENT_PREVIEW_FAILED",
                "message": "ZEN Controller did not complete preview delegation.",
            }
        return {
            "schema": TOOL_RESULT_SCHEMA,
            "tool": tool_name,
            "status": "REJECTED" if rejected else "FAILED",
            "result": None,
            "error": error,
            "request_id": payload.get("request_id"),
        }

    remote_result = delegation.get("remote_result")
    if not isinstance(remote_result, dict):
        raise RuntimeError("ZEN Controller returned an invalid remote preview payload.")
    if remote_result.get("schema") != TOOL_RESULT_SCHEMA:
        raise RuntimeError("ZEN remote preview returned an unexpected tool-result schema.")
    if remote_result.get("tool") != tool_name:
        raise RuntimeError("ZEN remote preview returned a mismatched tool identity.")
    return remote_result


def create_mcp_server(
    *,
    operator_base_url: str = DEFAULT_OPERATOR_BASE_URL,
    controller_base_url: str = DEFAULT_CONTROLLER_BASE_URL,
) -> MCPServer:
    operator = _loopback_base_url(operator_base_url)
    controller = _loopback_base_url(controller_base_url)
    server = MCPServer(
        "ZEN MA2",
        instructions=(
            "Typed ZEN grandMA2 tools. ZEN remains the safety, Preview, "
            "Approval, Builder, protected-object and native-readback authority. "
            "This MCP surface never exposes raw MA commands, shell, credentials, "
            "Patch/Address/Fixture mutation, or an approval bypass."
        ),
    )

    @server.tool(name="zen_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_status() -> dict[str, Any]:
        """Read ZEN Field Core and MA connection status. Read-only."""
        return _invoke(operator, "zen.status")

    @server.tool(name="zen_ma_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_ma_status() -> dict[str, Any]:
        """Read current ZEN MA bridge and grandMA2 connection status. Read-only."""
        return _invoke(operator, "zen.ma.status")

    @server.tool(name="zen_ma_visual", structured_output=True, annotations=OBSERVATION_ANNOTATIONS)
    def zen_ma_visual() -> dict[str, Any]:
        """Capture bounded pixel-grounded grandMA2 visual evidence. No MA writes."""
        return _invoke(operator, "zen.ma.visual")

    @server.tool(name="zen_ma_stage_visual", structured_output=True, annotations=OBSERVATION_ANNOTATIONS)
    def zen_ma_stage_visual() -> dict[str, Any]:
        """Navigate only fixed MA2 screen controls and capture Stage/3D evidence."""
        return _invoke(operator, "zen.ma.stage.visual")

    @server.tool(name="zen_design_request", structured_output=True, annotations=PREVIEW_ANNOTATIONS)
    def zen_design_request(request: str) -> dict[str, Any]:
        """Plan a bounded lighting request through ZEN preview only; never approve it."""
        return _invoke_department_preview(controller, "zen.design.request", {"request": request})

    @server.tool(name="zen_preview", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_preview(actionId: str | None = None) -> dict[str, Any]:
        """Read the current or specified ZEN action preview."""
        return _invoke_department_preview(
            controller,
            "zen.preview",
            {"action_id": actionId},
        )

    @server.tool(name="zen_position_preview", structured_output=True, annotations=PREVIEW_ANNOTATIONS)
    def zen_position_preview(
        expectedShowFingerprint: str,
        groupId: int,
        expectedGroupName: str,
        expectedExactRefs: list[str],
        presetRef: str,
        expectedPresetLabel: str,
    ) -> dict[str, Any]:
        """Freshly verify one exact Position applicability probe and register Preview."""
        return _invoke_department_preview(
            controller,
            "zen.position.preview",
            {
                "expected_show_fingerprint": expectedShowFingerprint,
                "group_id": groupId,
                "expected_group_name": expectedGroupName,
                "expected_exact_refs": expectedExactRefs,
                "preset_ref": presetRef,
                "expected_preset_label": expectedPresetLabel,
            },
        )

    @server.tool(name="zen_position_raw_preview", structured_output=True, annotations=PREVIEW_ANNOTATIONS)
    def zen_position_raw_preview(
        expectedShowFingerprint: str,
        groupId: int,
        expectedGroupName: str,
        expectedExactRefs: list[str],
    ) -> dict[str, Any]:
        """Register a raw Pan/Tilt Cue proof Preview; never approve or write MA2."""
        return _invoke_department_preview(
            controller,
            "zen.position.raw.preview",
            {
                "expected_show_fingerprint": expectedShowFingerprint,
                "group_id": groupId,
                "expected_group_name": expectedGroupName,
                "expected_exact_refs": expectedExactRefs,
            },
        )

    @server.tool(name="zen_position_calibration_preview", structured_output=True, annotations=PREVIEW_ANNOTATIONS)
    def zen_position_calibration_preview(
        expectedShowFingerprint: str,
        groupId: int,
        expectedGroupName: str,
        expectedExactRefs: list[str],
    ) -> dict[str, Any]:
        """Register approval-gated Position calibration Preview; never approve it."""

        return _invoke_department_preview(
            controller,
            "zen.position.calibration.preview",
            {
                "expected_show_fingerprint": expectedShowFingerprint,
                "group_id": groupId,
                "expected_group_name": expectedGroupName,
                "expected_exact_refs": expectedExactRefs,
            },
        )

    @server.tool(name="zen_position_semantic_bindings", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_position_semantic_bindings() -> dict[str, Any]:
        """List fresh verified Position application candidates and semantic mappings."""
        return _invoke(operator, "zen.position.semantic.bindings")

    @server.tool(name="zen_department_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_department_status() -> dict[str, Any]:
        """Read controller-visible department adapter state. Read-only."""
        return _invoke(controller, "zen.department.status")

    @server.tool(name="zen_worker_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_worker_status() -> dict[str, Any]:
        """Read the legacy ZEN remote-worker status projection. Read-only."""
        return _invoke(operator, "zen.worker.status")

    @server.tool(name="zen_watchdog_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_watchdog_status() -> dict[str, Any]:
        """Read bounded ZEN watchdog state. Read-only."""
        return _invoke(operator, "zen.watchdog.status")

    @server.tool(name="zen_host_status", structured_output=True, annotations=READ_ONLY_ANNOTATIONS)
    def zen_host_status() -> dict[str, Any]:
        """Read bounded ZEN execution-host metrics. Read-only."""
        return _invoke(operator, "zen.host.status")

    return server

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ZEN native MCP operator facade")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default=DEFAULT_MCP_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_MCP_PORT)
    parser.add_argument("--operator-base-url", default=DEFAULT_OPERATOR_BASE_URL)
    parser.add_argument("--controller-base-url", default=DEFAULT_CONTROLLER_BASE_URL)
    args = parser.parse_args(argv)

    server = create_mcp_server(
        operator_base_url=args.operator_base_url,
        controller_base_url=args.controller_base_url,
    )
    if args.transport == "stdio":
        server.run(transport="stdio")
        return 0

    if not 1 <= args.port <= 65535:
        parser.error("--port must be in range 1..65535")
    if args.host.lower() != "localhost":
        try:
            if not ipaddress.ip_address(args.host).is_loopback:
                parser.error("--host must remain loopback-only")
        except ValueError:
            parser.error("--host must remain loopback-only")

    server.run(
        transport="streamable-http",
        host=args.host,
        port=args.port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())