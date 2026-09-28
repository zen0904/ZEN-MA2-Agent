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
