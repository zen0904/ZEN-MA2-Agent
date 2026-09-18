import unittest
from types import SimpleNamespace

from zen_ma2_agent.field_host import FieldHost, FieldHostConfig
from zen_ma2_agent.remote_workers import WorkerRegistry


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


if __name__ == "__main__":
    unittest.main()
