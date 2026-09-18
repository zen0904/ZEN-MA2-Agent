import unittest

import httpx

from zen_ma2_agent.operator_api import ComponentState
from zen_ma2_agent.remote_workers import RegisteredWorker, WorkerRegistry
from zen_ma2_agent.worker_health import (
    WorkerEndpoint,
    WorkerHealthProbe,
)


class _ClientFactory:
    def __init__(self, handler):
        self.transport = httpx.MockTransport(handler)

    def __call__(self, **kwargs):
        return httpx.Client(transport=self.transport, **kwargs)


class WorkerHealthProbeTests(unittest.TestCase):
    def _registry(self):
        return WorkerRegistry(
            (
                RegisteredWorker("worker-a", priority=10),
                RegisteredWorker("worker-b", priority=20),
            )
        )

    def test_online_worker_reuses_existing_health_and_capability_contracts(self):
        def handler(request):
            if request.url.path == "/health":
                return httpx.Response(
                    200,
                    json={
                        "schema_version": "zen.worker.health.v0.1",
                        "worker_id": "worker-a",
                        "status": "ONLINE",
                    },
                )
            if request.url.path == "/capabilities":
                return httpx.Response(
                    200,
                    json={
                        "schema_version": "zen.worker.capabilities.v0.1",
                        "worker_id": "worker-a",
                        "gpu_name": "GTX 1650",
                        "model_runtime_available": True,
                    },
                )
            return httpx.Response(404)

        registry = self._registry()
        probe = WorkerHealthProbe(
            registry,
            (WorkerEndpoint("worker-a", "http://10.0.0.10:8878"),),
            client_factory=_ClientFactory(handler),
        )
        probe.poll_once()
        worker = registry.get("worker-a")
        self.assertEqual(worker.state, ComponentState.ONLINE)
        self.assertEqual(worker.capabilities.gpu_name, "GTX 1650")
        self.assertTrue(worker.capabilities.model_runtime_available)
        self.assertEqual(worker.consecutive_failures, 0)

    def test_health_success_capabilities_failure_is_degraded(self):
        def handler(request):
            if request.url.path == "/health":
                return httpx.Response(
                    200,
                    json={
                        "schema_version": "zen.worker.health.v0.1",
                        "worker_id": "worker-a",
                        "status": "ONLINE",
                    },
                )
            return httpx.Response(503)

        registry = self._registry()
        probe = WorkerHealthProbe(
            registry,
            (WorkerEndpoint("worker-a", "http://10.0.0.10:8878"),),
            client_factory=_ClientFactory(handler),
        )
        probe.poll_once()
        worker = registry.get("worker-a")
        self.assertEqual(worker.state, ComponentState.DEGRADED)
        self.assertEqual(worker.consecutive_failures, 1)
        self.assertIn("capabilities unavailable", worker.last_error)

    def test_unreachable_worker_is_offline(self):
        def handler(request):
            raise httpx.ConnectError("no route", request=request)

        registry = self._registry()
        probe = WorkerHealthProbe(
            registry,
            (WorkerEndpoint("worker-b", "http://10.0.0.20:8878"),),
            client_factory=_ClientFactory(handler),
        )
        probe.poll_once()
        worker = registry.get("worker-b")
        self.assertEqual(worker.state, ComponentState.OFFLINE)
        self.assertEqual(worker.consecutive_failures, 1)

    def test_worker_identity_mismatch_fails_closed(self):
        def handler(request):
            return httpx.Response(
                200,
                json={
                    "schema_version": "zen.worker.health.v0.1",
                    "worker_id": "wrong-worker",
                    "status": "ONLINE",
                },
            )

        registry = self._registry()
        probe = WorkerHealthProbe(
            registry,
            (WorkerEndpoint("worker-a", "http://10.0.0.10:8878"),),
            client_factory=_ClientFactory(handler),
        )
        probe.poll_once()
        self.assertEqual(registry.get("worker-a").state, ComponentState.OFFLINE)
        self.assertIn("identity mismatch", registry.get("worker-a").last_error)

    def test_endpoint_rejects_credentials_query_and_paths(self):
        for url in (
            "ftp://10.0.0.10:8878",
            "http://user:pass@10.0.0.10:8878",
            "http://10.0.0.10:8878/path",
            "http://10.0.0.10:8878?x=1",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    WorkerEndpoint("worker-a", url)

    def test_endpoint_requires_registered_worker(self):
        registry = WorkerRegistry((RegisteredWorker("worker-a"),))
        with self.assertRaises(KeyError):
            WorkerHealthProbe(
                registry,
                (WorkerEndpoint("worker-b", "http://10.0.0.20:8878"),),
            )


if __name__ == "__main__":
    unittest.main()
