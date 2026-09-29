from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from zen_ma2_agent.mcp_operator_server import (
    _invoke,
    _invoke_department_preview,
    _loopback_base_url,
    create_mcp_server,
)


class _Response:
    def __init__(self, payload: object):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self._payload


class McpOperatorServerTests(unittest.TestCase):
    def test_loopback_upstream_only(self) -> None:
        self.assertEqual(
            _loopback_base_url("http://127.0.0.1:18878/"),
            "http://127.0.0.1:18878",
        )
        self.assertEqual(
            _loopback_base_url("http://localhost:18876"),
            "http://localhost:18876",
        )
        for invalid in (
            "http://10.0.0.50:18878",
            "https://example.com",
            "http://user:pass@127.0.0.1:18878",
            "http://127.0.0.1:18878?token=no",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    _loopback_base_url(invalid)

    @patch("zen_ma2_agent.mcp_operator_server.httpx.post")
    def test_invoke_preserves_typed_tool_contract(self, post) -> None:
        post.return_value = _Response({
            "schema": "zen.tool_result.v0.1",
            "tool": "zen.status",
            "status": "SUCCESS",
            "result": {"ok": True},
            "error": None,
        })
        result = _invoke("http://127.0.0.1:18878", "zen.status")
        self.assertEqual(result["status"], "SUCCESS")
        post.assert_called_once_with(
            "http://127.0.0.1:18878/zen/v0.1/tools/zen.status",
            json={"arguments": {}},
            timeout=20.0,
        )

    @patch("zen_ma2_agent.mcp_operator_server.httpx.post")
    def test_invoke_rejects_mismatched_tool_identity(self, post) -> None:
        post.return_value = _Response({
            "schema": "zen.tool_result.v0.1",
            "tool": "zen.ma.status",
            "status": "SUCCESS",
            "result": {},
            "error": None,
        })
        with self.assertRaisesRegex(RuntimeError, "mismatched tool identity"):
            _invoke("http://127.0.0.1:18878", "zen.status")

    @patch("zen_ma2_agent.mcp_operator_server._invoke")
    def test_department_preview_preserves_remote_preview_only_boundary(self, invoke) -> None:
        invoke.return_value = {
            "schema": "zen.tool_result.v0.1",
            "tool": "zen.department.preview",
            "status": "SUCCESS",
            "result": {
                "schema": "zen.department_preview.v0.1",
                "authority": "REMOTE_PREVIEW_ONLY",
                "ma2_writes": 0,
                "remote_tool": "zen.design.request",
                "delegation_status": "SUCCESS",
                "remote_result": {
                    "schema": "zen.tool_result.v0.1",
                    "tool": "zen.design.request",
                    "status": "SUCCESS",
                    "result": {"action_id": "preview-1"},
                    "error": None,
                },
            },
            "error": None,
        }
        result = _invoke_department_preview(
            "http://127.0.0.1:18876",
            "zen.design.request",
            {"request": "test"},
        )
        self.assertEqual(result["tool"], "zen.design.request")
        invoke.assert_called_once_with(
            "http://127.0.0.1:18876",
            "zen.department.preview",
            {
                "adapter_id": "LIGHTING_GRANDMA2",
                "tool_name": "zen.design.request",
                "arguments": {"request": "test"},
            },
        )

    @patch("zen_ma2_agent.mcp_operator_server._invoke")
    def test_department_preview_rejects_broadened_authority(self, invoke) -> None:
        invoke.return_value = {
            "schema": "zen.tool_result.v0.1",
            "tool": "zen.department.preview",
            "status": "SUCCESS",
            "result": {
                "schema": "zen.department_preview.v0.1",
                "authority": "REMOTE_WRITE",
                "ma2_writes": 1,
                "remote_tool": "zen.design.request",
                "delegation_status": "SUCCESS",
                "remote_result": {
                    "schema": "zen.tool_result.v0.1",
                    "tool": "zen.design.request",
                    "status": "SUCCESS",
                    "result": {},
                    "error": None,
                },
            },
            "error": None,
        }
        with self.assertRaisesRegex(RuntimeError, "contract mismatch"):
            _invoke_department_preview(
                "http://127.0.0.1:18876",
                "zen.design.request",
                {"request": "test"},
            )

    def test_catalog_replaces_openclaw_plugin_without_approve(self) -> None:
        async def inspect_tools():
            return await create_mcp_server().list_tools()

        tools = asyncio.run(inspect_tools())
        names = {tool.name for tool in tools}
        self.assertEqual(
            names,
            {
                "zen_status",
                "zen_ma_status",
                "zen_ma_visual",
                "zen_ma_stage_visual",
                "zen_design_request",
                "zen_preview",
                "zen_position_preview",
                "zen_position_raw_preview",
                "zen_position_calibration_preview",
                "zen_position_semantic_bindings",
                "zen_department_status",
                "zen_worker_status",
                "zen_watchdog_status",
                "zen_host_status",
            },
        )
        self.assertNotIn("zen_approve", names)
        preview_mutations = {
            "zen_design_request",
            "zen_position_preview",
            "zen_position_raw_preview",
            "zen_position_calibration_preview",
        }
        by_name = {tool.name: tool for tool in tools}
        for name, tool in by_name.items():
            self.assertIsNotNone(tool.annotations)
            self.assertFalse(tool.annotations.destructive_hint)
            self.assertFalse(tool.annotations.open_world_hint)
            if name in preview_mutations:
                self.assertFalse(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.idempotent_hint)
            else:
                self.assertTrue(tool.annotations.read_only_hint)


if __name__ == "__main__":
    unittest.main()
