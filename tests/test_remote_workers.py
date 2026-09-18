import unittest

from zen_ma2_agent.operator_api import ComponentState
from zen_ma2_agent.remote_workers import (
    MAX_REGISTERED_WORKERS,
    RegisteredWorker,
    WorkerCapabilities,
    WorkerRegistry,
)


class RemoteWorkerRegistryTests(unittest.TestCase):
    def test_zero_workers_means_remote_ai_unavailable(self):
        registry = WorkerRegistry()
        self.assertFalse(registry.remote_ai_available)
        decision = registry.route()
        self.assertIsNone(decision.selected_worker_id)
        self.assertFalse(decision.remote_ai_available)
        self.assertEqual(decision.reason, "NO_WORKER_AVAILABLE")

    def test_preferred_online_worker_is_selected(self):
        registry = WorkerRegistry(
            (
                RegisteredWorker(
                    "worker-b",
                    priority=20,
                    state=ComponentState.ONLINE,
                    capabilities=WorkerCapabilities(model_runtime_available=True),
                ),
                RegisteredWorker(
                    "worker-a",
                    priority=10,
                    state=ComponentState.ONLINE,
                    capabilities=WorkerCapabilities(model_runtime_available=True),
                ),
            )
        )
        decision = registry.route()
        self.assertEqual(decision.selected_worker_id, "worker-a")
        self.assertTrue(decision.remote_ai_available)

    def test_offline_preferred_worker_falls_back(self):
        registry = WorkerRegistry(
            (
                RegisteredWorker("worker-a", priority=10, state=ComponentState.OFFLINE),
                RegisteredWorker(
                    "worker-b",
                    priority=20,
                    state=ComponentState.ONLINE,
                    capabilities=WorkerCapabilities(model_runtime_available=True),
                ),
            )
        )
        self.assertEqual(registry.route().selected_worker_id, "worker-b")

    def test_unknown_is_not_online(self):
        registry = WorkerRegistry((RegisteredWorker("worker-a"),))
        self.assertFalse(registry.remote_ai_available)
        self.assertIsNone(registry.route().selected_worker_id)

    def test_online_worker_without_confirmed_model_runtime_is_not_ai_available(self):
        registry = WorkerRegistry(
            (RegisteredWorker("worker-a", state=ComponentState.ONLINE),)
        )
        self.assertFalse(registry.remote_ai_available)
        self.assertIsNone(registry.route().selected_worker_id)

    def test_online_worker_with_model_runtime_false_is_not_routed(self):
        registry = WorkerRegistry(
            (
                RegisteredWorker(
                    "worker-a",
                    state=ComponentState.ONLINE,
                    capabilities=WorkerCapabilities(model_runtime_available=False),
                ),
            )
        )
        self.assertFalse(registry.remote_ai_available)
        self.assertIsNone(registry.route().selected_worker_id)

    def test_state_recovery_clears_failure_counter(self):
        registry = WorkerRegistry((RegisteredWorker("worker-a"),))
        registry.set_state("worker-a", ComponentState.OFFLINE, error="timeout")
        self.assertEqual(registry.get("worker-a").consecutive_failures, 1)
        self.assertEqual(registry.get("worker-a").last_error, "timeout")
        registry.set_state("worker-a", ComponentState.ONLINE)
        self.assertEqual(registry.get("worker-a").consecutive_failures, 0)
        self.assertIsNone(registry.get("worker-a").last_error)

    def test_capabilities_project_into_operator_contract(self):
        registry = WorkerRegistry((RegisteredWorker("worker-a"),))
        registry.set_state(
            "worker-a",
            ComponentState.ONLINE,
            capabilities=WorkerCapabilities(
                gpu_name="GTX 1650",
                model_runtime_available=False,
            ),
        )
        worker = registry.operator_workers()[0].to_dict()
        self.assertEqual(worker["worker_id"], "worker-a")
        self.assertEqual(worker["state"], "ONLINE")
        self.assertEqual(worker["gpu_name"], "GTX 1650")
        self.assertFalse(worker["model_runtime_available"])

    def test_worker_order_is_deterministic(self):
        registry = WorkerRegistry(
            (
                RegisteredWorker("worker-c", priority=20),
                RegisteredWorker("worker-b", priority=10),
                RegisteredWorker("worker-a", priority=10),
            )
        )
        self.assertEqual(
            [worker.worker_id for worker in registry.operator_workers()],
            ["worker-a", "worker-b", "worker-c"],
        )

    def test_registry_limit_is_bounded(self):
        registry = WorkerRegistry(
            RegisteredWorker(f"w-{index}") for index in range(MAX_REGISTERED_WORKERS)
        )
        with self.assertRaises(ValueError):
            registry.register(RegisteredWorker("too-many"))

    def test_duplicate_registration_replaces_same_worker_without_growing(self):
        registry = WorkerRegistry((RegisteredWorker("worker-a", priority=20),))
        registry.register(RegisteredWorker("worker-a", priority=5))
        self.assertEqual(registry.get("worker-a").priority, 5)
        self.assertEqual(len(registry.operator_workers()), 1)


if __name__ == "__main__":
    unittest.main()
