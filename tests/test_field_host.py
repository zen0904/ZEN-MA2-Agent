import unittest
from types import SimpleNamespace

from zen_ma2_agent.field_host import FieldHost, FieldHostConfig
from zen_ma2_agent.operator_api import ComponentState
from zen_ma2_agent.remote_workers import RegisteredWorker, WorkerRegistry


class _FakeCore:
    def __init__(self):
        self.runtime = SimpleNamespace(
            state=SimpleNamespace(value="DISCONNECTED"),
            preferences={"ma2": {"host": "127.0.0.1", "port": 30000}},
        )


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


if __name__ == "__main__":
    unittest.main()
