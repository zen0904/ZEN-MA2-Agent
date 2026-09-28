import unittest
from unittest.mock import Mock, patch

import httpx

from zen_ma2_agent.department_adapters import (
    DepartmentAdapterEndpoint,
    DepartmentAdapterRegistry,
)


class DepartmentAdapterTests(unittest.TestCase):
    def test_rejects_public_and_credentialed_urls(self):
        for url in (
            "https://8.8.8.8:8876",
            "http://user:pass@100.67.178.35:8876",
            "http://example.com:8876",
            "http://100.67.178.35:8876/path",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                DepartmentAdapterEndpoint("LIGHTING_GRANDMA2", url)

    def test_accepts_tailscale_private_and_loopback_addresses(self):
        for url in (
            "http://100.67.178.35:8876",
            "http://192.168.0.150:8876",
            "http://127.0.0.1:8876",
        ):
            endpoint = DepartmentAdapterEndpoint("LIGHTING_GRANDMA2", url)
            self.assertEqual(endpoint.base_url, url)

    @patch("zen_ma2_agent.department_adapters.httpx.Client")
    def test_snapshot_projects_bounded_remote_status(self, client_cls):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "schema": "zen.operator_status.v0.1",
            "field_core": {"available": True, "state": "ONLINE"},
            "ma": {
                "bridge_state": "ONLINE",
                "connection_state": "READY",
                "target": {"host": "127.0.0.1", "port": 30000},
            },
            "secret": "must-not-pass-through",
        }
        client = client_cls.return_value.__enter__.return_value
        client.get.return_value = response

        snapshot = DepartmentAdapterRegistry(
            [
                DepartmentAdapterEndpoint(
                    "LIGHTING_GRANDMA2",
                    "http://100.67.178.35:8876",
                )
            ]
        ).snapshot()

        self.assertEqual(
            snapshot["schema"],
            "zen.department_adapter_status.v0.1",
        )
        self.assertTrue(snapshot["read_only_federation"])
        self.assertEqual(snapshot["ma2_writes"], 0)
        adapter = snapshot["adapters"][0]
        self.assertEqual(adapter["state"], "ONLINE")
        self.assertEqual(adapter["ma"]["connection_state"], "READY")
        self.assertEqual(adapter["authority"], "REMOTE_READ_ONLY")
        self.assertNotIn("secret", adapter)

    @patch("zen_ma2_agent.department_adapters.httpx.Client")
    def test_preview_delegates_only_bounded_preview_tool(self, client_cls):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "schema": "zen.tool_result.v0.1",
            "tool": "zen.preview",
            "status": "SUCCESS",
            "result": {"action_id": "a1", "phase": "PREVIEW"},
            "error": None,
        }
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = response

        registry = DepartmentAdapterRegistry(
            [
                DepartmentAdapterEndpoint(
                    "LIGHTING_GRANDMA2",
                    "http://100.67.178.35:8876",
                )
            ]
        )
        result = registry.preview(
            "LIGHTING_GRANDMA2",
            "zen.preview",
            {"action_id": "a1"},
        )

        self.assertEqual(result["schema"], "zen.department_preview.v0.1")
        self.assertEqual(result["authority"], "REMOTE_PREVIEW_ONLY")
        self.assertEqual(result["ma2_writes"], 0)
        self.assertEqual(result["delegation_status"], "SUCCESS")
        self.assertEqual(result["remote_result"]["tool"], "zen.preview")
        client.post.assert_called_once_with(
            "http://100.67.178.35:8876/zen/v0.1/tools/zen.preview",
            json={"arguments": {"action_id": "a1"}},
        )

    @patch("zen_ma2_agent.department_adapters.httpx.Client")
    def test_preview_rejects_approve_before_network(self, client_cls):
        registry = DepartmentAdapterRegistry(
            [
                DepartmentAdapterEndpoint(
                    "LIGHTING_GRANDMA2",
                    "http://100.67.178.35:8876",
                )
            ]
        )
        result = registry.preview(
            "LIGHTING_GRANDMA2",
            "zen.approve",
            {"action_id": "a1", "danger_confirmed": False},
        )

        self.assertEqual(result["delegation_status"], "REJECTED")
        self.assertEqual(result["error"]["code"], "TOOL_NOT_ALLOWED")
        self.assertEqual(result["ma2_writes"], 0)
        client_cls.assert_not_called()

    @patch("zen_ma2_agent.department_adapters.httpx.Client")
    def test_preview_fails_closed_on_remote_schema_mismatch(self, client_cls):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "schema": "unexpected.schema",
            "tool": "zen.preview",
            "status": "SUCCESS",
            "result": {},
            "error": None,
        }
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value = response

        result = DepartmentAdapterRegistry(
            [
                DepartmentAdapterEndpoint(
                    "LIGHTING_GRANDMA2",
                    "http://100.67.178.35:8876",
                )
            ]
        ).preview("LIGHTING_GRANDMA2", "zen.preview", {"action_id": None})

        self.assertEqual(result["delegation_status"], "FAILED")
        self.assertEqual(result["error"]["code"], "REMOTE_PREVIEW_UNAVAILABLE")
        self.assertEqual(result["ma2_writes"], 0)

    @patch("zen_ma2_agent.department_adapters.httpx.Client")
    def test_network_failure_degrades_without_error_detail_leak(self, client_cls):
        client = client_cls.return_value.__enter__.return_value
        client.get.side_effect = httpx.ConnectError(
            "sensitive remote details"
        )

        adapter = DepartmentAdapterRegistry(
            [
                DepartmentAdapterEndpoint(
                    "LIGHTING_GRANDMA2",
                    "http://100.67.178.35:8876",
                )
            ]
        ).snapshot()["adapters"][0]

        self.assertEqual(adapter["state"], "OFFLINE")
        self.assertEqual(
            adapter["error"],
            {"class": "REMOTE_STATUS_UNAVAILABLE"},
        )
        self.assertEqual(adapter["ma2_writes"], 0)


if __name__ == "__main__":
    unittest.main()
