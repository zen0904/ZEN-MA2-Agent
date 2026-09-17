import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from zen_ma2_agent.operator_api import (
    ComponentState,
    MAConnectionState,
    PipelineStatus,
    build_operator_status,
)
from zen_ma2_agent.operator_server import (
    OperatorServer,
    create_operator_app,
    status_provider_from_core,
)


class OperatorServerTests(unittest.TestCase):
    def _provider(self):
        return lambda: build_operator_status(
            field_core_available=True,
            field_core_state=ComponentState.ONLINE,
            ma_bridge_state=ComponentState.UNKNOWN,
            ma_connection_state=MAConnectionState.DISCONNECTED,
            remote_ai_available=False,
            pipeline=PipelineStatus(),
        )

    def test_health_is_small_and_deterministic(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"schema": "zen.operator_http_health.v0.1", "status": "OK"},
        )

    def test_status_returns_raw_operator_contract(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.get("/zen/v0.1/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schema"], "zen.operator_status.v0.1")
        self.assertTrue(data["field_core"]["available"])
        self.assertFalse(data["remote_ai_available"])
        self.assertNotIn("openclaw_available", data)

    def test_status_tool_uses_result_envelope(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.post(
            "/zen/v0.1/tools/zen.status",
            json={"arguments": {}, "request_id": "req-1"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["schema"], "zen.tool_result.v0.1")
        self.assertEqual(data["tool"], "zen.status")
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["request_id"], "req-1")

    def test_reserved_mutating_tool_is_not_implemented(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.post("/zen/v0.1/tools/zen.approve", json={})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "NOT_IMPLEMENTED")

    def test_unknown_tool_is_not_exposed(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.post("/zen/v0.1/tools/zen.shell", json={})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["code"], "UNKNOWN_TOOL")

    def test_invalid_envelope_is_rejected(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.post(
            "/zen/v0.1/tools/zen.status",
            json={"command": "anything"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_ENVELOPE")

    def test_arguments_must_be_object(self):
        client = TestClient(create_operator_app(self._provider()))
        response = client.post(
            "/zen/v0.1/tools/zen.status",
            json={"arguments": "not-an-object"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_ARGUMENTS")

    def test_core_provider_maps_local_runtime_without_snapshot(self):
        class FakeCore:
            def __init__(self):
                self.snapshot_called = False
                self.runtime = SimpleNamespace(
                    state=SimpleNamespace(value="NEGOTIATING"),
                    preferences={
                        "ma2": {
                            "host": "10.0.0.233",
                            "port": 30000,
                            "username": "SHOULD_NOT_LEAK",
                            "password": "SHOULD_NOT_LEAK",
                        }
                    },
                )

            def snapshot(self):
                self.snapshot_called = True
                raise AssertionError("operator provider must not call core.snapshot()")

        core = FakeCore()
        data = status_provider_from_core(core)().to_dict()
        self.assertFalse(core.snapshot_called)
        self.assertTrue(data["field_core"]["available"])
        self.assertEqual(data["ma"]["connection_state"], "CONNECTING")
        self.assertEqual(data["ma"]["target"], {"host": "10.0.0.233", "port": 30000})
        rendered = str(data)
        self.assertNotIn("SHOULD_NOT_LEAK", rendered)

    def test_core_provider_preserves_unknown_connection_state(self):
        core = SimpleNamespace(
            runtime=SimpleNamespace(
                state=SimpleNamespace(value="SOMETHING_NEW"),
                preferences={"ma2": {"host": "127.0.0.1", "port": 30000}},
            )
        )
        data = status_provider_from_core(core)().to_dict()
        self.assertEqual(data["ma"]["connection_state"], "UNKNOWN")
        self.assertEqual(data["ma"]["bridge_state"], "UNKNOWN")

    def test_non_loopback_bind_is_blocked_by_default(self):
        with self.assertRaises(ValueError):
            OperatorServer(self._provider(), host="0.0.0.0")

    def test_loopback_bind_is_allowed(self):
        server = OperatorServer(self._provider(), host="127.0.0.1")
        self.assertEqual(server.host, "127.0.0.1")
        self.assertEqual(server.port, 8876)


if __name__ == "__main__":
    unittest.main()
