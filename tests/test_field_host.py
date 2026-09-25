import unittest
from unittest.mock import patch
from types import SimpleNamespace

from zen_ma2_agent.field_host import FieldHost, FieldHostConfig
from zen_ma2_agent.operator_api import ComponentState
from zen_ma2_agent.remote_workers import RegisteredWorker, WorkerRegistry
from zen_ma2_agent.worker_health import WorkerEndpoint


class _FakeCore:
    def __init__(self):
        self.design_intelligence_provider = None
        self.runtime = SimpleNamespace(
            state=SimpleNamespace(value="DISCONNECTED"),
            preferences={"ma2": {"host": "127.0.0.1", "port": 30000}},
        )


class _AutoConnectCore:
    def __init__(self, *, fail_connect: bool = False):
        self.design_intelligence_provider = None
        self.fail_connect = fail_connect
        self.connect_calls = []
        self.tick_calls = 0
        self.disconnect_calls = 0
        self.runtime = SimpleNamespace(
            state=SimpleNamespace(value="DISCONNECTED"),
            preferences={
                "ma2": {
                    "host": "127.0.0.1",
                    "port": 30000,
                    "username": "MM",
                }
            },
        )

    def connect(self, host, port, username, password=""):
        self.connect_calls.append((host, port, username, password))
        if self.fail_connect:
            raise ConnectionError("offline")
        self.runtime.state.value = "AUTHENTICATING"
        return "connecting"

    def tick(self):
        self.tick_calls += 1
        if self.runtime.state.value == "AUTHENTICATING":
            self.runtime.state.value = "READY"

    def disconnect(self):
        self.disconnect_calls += 1
        self.runtime.state.value = "DISCONNECTED"


class FieldHostTests(unittest.TestCase):
    def test_openclaw_is_not_required_for_field_core_status(self):
        host = FieldHost(
            FieldHostConfig(operator_port=8876, bridge_port=8877),
            core=_FakeCore(),
            worker_registry=WorkerRegistry(),
        )
        status = host.status()
        self.assertTrue(status["field_core"]["available"])
        self.assertFalse(status["remote_ai_available"])
        self.assertNotIn("openclaw_available", status)

    def test_bridge_status_payload_is_deterministic_without_workers(self):
        host = FieldHost(
            FieldHostConfig(operator_port=8876, bridge_port=8877),
            core=_FakeCore(),
            worker_registry=WorkerRegistry(),
        )
        self.assertEqual(
            host._bridge_status_payload(),
            "FIELD_CORE_AVAILABLE=YES REMOTE_AI_AVAILABLE=NO",
        )

    def test_headless_ma_poll_auto_connects_and_advances_authentication(self):
        core = _AutoConnectCore()
        host = FieldHost(
            FieldHostConfig(
                operator_port=8876,
                bridge_port=8877,
                auto_connect_ma2=True,
            ),
            core=core,
            worker_registry=WorkerRegistry(),
        )

        host._poll_ma_runtime_once()

        self.assertEqual(
            core.connect_calls,
            [("127.0.0.1", 30000, "MM", "")],
        )
        self.assertEqual(core.tick_calls, 1)
        self.assertEqual(core.runtime.state.value, "READY")
        self.assertEqual(host.ma_runtime_status["state"], "READY")
        self.assertIsNone(host.ma_runtime_status["last_error"])

    def test_headless_ma_poll_throttles_failed_reconnect_without_crashing_host(self):
        core = _AutoConnectCore(fail_connect=True)
        host = FieldHost(
            FieldHostConfig(
                operator_port=8876,
                bridge_port=8877,
                auto_connect_ma2=True,
                ma_reconnect_interval_seconds=10.0,
            ),
            core=core,
            worker_registry=WorkerRegistry(),
        )

        host._poll_ma_runtime_once()
        host._poll_ma_runtime_once()

        self.assertEqual(len(core.connect_calls), 1)
        self.assertEqual(core.tick_calls, 2)
        self.assertEqual(core.runtime.state.value, "DISCONNECTED")
        self.assertEqual(host.ma_runtime_status["last_error"], "ConnectionError")

    def test_worker_endpoints_auto_register_primary_workers_without_network_io(self):
        host = FieldHost(
            FieldHostConfig(operator_port=8876, bridge_port=8877),
            core=_FakeCore(),
            worker_endpoints=(
                WorkerEndpoint("worker-a", "http://10.0.0.10:8878"),
                WorkerEndpoint("worker-b", "http://10.0.0.20:8878"),
            ),
        )
        self.assertIsNotNone(host.worker_health)
        self.assertEqual(
            [item.worker_id for item in host.worker_registry.operator_workers()],
            ["worker-a", "worker-b"],
        )
        self.assertFalse(host.worker_registry.remote_ai_available)

    def test_watchdog_observes_field_bridge_ma_and_primary_workers(self):
        registry = WorkerRegistry(
            (
                RegisteredWorker("worker-a", priority=10, state=ComponentState.ONLINE),
                RegisteredWorker("worker-b", priority=20, state=ComponentState.OFFLINE),
            )
        )
        host = FieldHost(
            FieldHostConfig(operator_port=8876, bridge_port=8877),
            core=_FakeCore(),
            worker_registry=registry,
        )
        host.watchdog.poll_once()
        snapshot = host.watchdog.snapshot()
        components = {item["component_id"]: item for item in snapshot["components"]}
        self.assertEqual(components["field_core"]["state"], "ONLINE")
        self.assertIn(components["host_metrics"]["state"], {"ONLINE", "DEGRADED"})
        self.assertEqual(components["ma_bridge"]["state"], "OFFLINE")
        self.assertTrue(components["ma_bridge"]["required"])
        self.assertEqual(components["ma_connection"]["state"], "OFFLINE")
        self.assertEqual(components["worker:worker-a"]["state"], "ONLINE")
        self.assertEqual(components["worker:worker-b"]["state"], "OFFLINE")
        self.assertFalse(components["worker:worker-b"]["required"])
        self.assertEqual(snapshot["state"], "OFFLINE")
        severities = [event["severity"] for event in snapshot["recent_events"]]
        self.assertIn("CRITICAL", severities)
        self.assertIn("WARNING", severities)

    def test_default_field_host_injects_portable_lean_provider_without_network_call(self):
        provider = object()
        fake_core = _FakeCore()
        with patch(
            "zen_ma2_agent.field_host.load_portable_lean_design_intelligence",
            return_value=provider,
        ) as load, patch("zen_ma2_agent.field_host.AgentCore", return_value=fake_core) as core_cls:
            host = FieldHost(
                FieldHostConfig(operator_port=8876, bridge_port=8877),
                worker_registry=WorkerRegistry(),
            )
        load.assert_called_once_with()
        core_cls.assert_called_once_with(design_intelligence_provider=provider)
        self.assertIs(host.core, fake_core)
        self.assertTrue(host.design_intelligence_status["configured"])
        self.assertEqual(host.design_intelligence_status["source"], "portable_provider_router")

    def test_injected_core_never_loads_portable_provider_config(self):
        fake_core = _FakeCore()
        with patch("zen_ma2_agent.field_host.load_portable_lean_design_intelligence") as load:
            host = FieldHost(
                FieldHostConfig(operator_port=8876, bridge_port=8877),
                core=fake_core,
                worker_registry=WorkerRegistry(),
            )
        load.assert_not_called()
        self.assertIs(host.core, fake_core)
        self.assertEqual(host.design_intelligence_status["source"], "injected_core")

    def test_invalid_provider_config_degrades_to_no_design_provider(self):
        fake_core = _FakeCore()
        with patch(
            "zen_ma2_agent.field_host.load_portable_lean_design_intelligence",
            side_effect=ValueError("bad provider config"),
        ), patch("zen_ma2_agent.field_host.AgentCore", return_value=fake_core) as core_cls:
            host = FieldHost(
                FieldHostConfig(operator_port=8876, bridge_port=8877),
                worker_registry=WorkerRegistry(),
            )
        core_cls.assert_called_once_with(design_intelligence_provider=None)
        self.assertFalse(host.design_intelligence_status["configured"])
        self.assertEqual(host.design_intelligence_status["error_class"], "CONFIGURATION_ERROR")



if __name__ == "__main__":
    unittest.main()
