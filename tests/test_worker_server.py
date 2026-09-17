import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from zen_ma2_agent.worker.server import (
    WORKER_JOB_SCHEMA,
    WorkerConfig,
    create_worker_app,
    detect_capabilities,
)


class WorkerServerTests(unittest.TestCase):
    def setUp(self):
        self.config = WorkerConfig("worker-a")
        self.client = TestClient(create_worker_app(self.config))

    def test_health(self):
        data = self.client.get("/health").json()
        self.assertEqual(data["schema_version"], "zen.worker.health.v0.1")
        self.assertEqual(data["worker_id"], "worker-a")
        self.assertEqual(data["status"], "ONLINE")

    def test_capabilities_tolerate_missing_nvidia_tooling(self):
        with patch("zen_ma2_agent.worker.server.shutil.which", return_value=None):
            data = detect_capabilities(self.config)
        self.assertEqual(data["node_role"], "AI_WORKER")
        self.assertFalse(data["gpu_present"])
        self.assertIsNone(data["gpu_name"])
        self.assertIsNone(data["vram_total_mb"])
        self.assertIsNone(data["cuda_available"])
        self.assertFalse(data["model_runtime_available"])

    def _job(self, job_type="ECHO_TEST"):
        return {
            "schema_version": WORKER_JOB_SCHEMA,
            "job_id": "job-1",
            "job_type": job_type,
            "request_hash": "abc",
            "payload": {"hello": "world"},
            "created_at": "2026-09-17T00:00:00Z",
        }

    def test_echo_roundtrip(self):
        response = self.client.post("/jobs", json=self._job())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["result"], {"hello": "world"})
        self.assertEqual(data["request_hash"], "abc")
        self.assertEqual(data["worker_id"], "worker-a")

    def test_inference_is_reserved_only(self):
        data = self.client.post("/jobs", json=self._job("INFERENCE_RESERVED")).json()
        self.assertEqual(data["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(data["result"])

    def test_unknown_job_type_is_rejected(self):
        data = self.client.post("/jobs", json=self._job("SHELL")).json()
        self.assertEqual(data["status"], "REJECTED")
        self.assertEqual(data["error"]["code"], "UNKNOWN_JOB_TYPE")

    def test_malformed_job_is_rejected(self):
        response = self.client.post("/jobs", json={"schema_version": WORKER_JOB_SCHEMA})
        self.assertEqual(response.status_code, 400)

    def test_worker_id_is_bounded(self):
        with self.assertRaises(ValueError):
            WorkerConfig("")
        with self.assertRaises(ValueError):
            WorkerConfig("x" * 129)


if __name__ == "__main__":
    unittest.main()
