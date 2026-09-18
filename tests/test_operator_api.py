import unittest

from zen_ma2_agent.operator_api import (
    ArtifactSummary,
    ComponentState,
    MAConnectionState,
    MATarget,
    OpenClawOperatorAdapter,
    PipelineState,
    PipelineStatus,
    UnknownOpenClawTool,
    WorkerStatus,
    build_operator_status,
)


class OperatorApiTests(unittest.TestCase):
    def _snapshot(self):
        return build_operator_status(
            field_core_available=True,
            field_core_state=ComponentState.ONLINE,
            ma_bridge_state=ComponentState.OFFLINE,
            ma_connection_state=MAConnectionState.DISCONNECTED,
            remote_ai_available=False,
            workers=(
                WorkerStatus("worker-a", ComponentState.OFFLINE, "GTX 1650", False),
                WorkerStatus("worker-b", ComponentState.UNKNOWN, None, None),
            ),
            pipeline=PipelineStatus(
                researcher=PipelineState.IDLE,
                designer=PipelineState.UNKNOWN,
                critic=PipelineState.UNKNOWN,
                finalizer=PipelineState.UNKNOWN,
            ),
            latest_artifact=ArtifactSummary(
                artifact_id="artifact-1",
                schema="zen.final_design.v0.1",
                request_hash="abc",
            ),
            ma_target=MATarget("127.0.0.1", 30000),
        )

    def test_snapshot_matches_contract_shape(self):
        data = self._snapshot().to_dict()
        self.assertEqual(data["schema"], "zen.operator_status.v0.1")
        self.assertEqual(data["field_core"], {"available": True, "state": "ONLINE"})
        self.assertEqual(data["ma"]["connection_state"], "DISCONNECTED")
        self.assertFalse(data["remote_ai_available"])
        self.assertEqual(data["pipeline"]["researcher"], "IDLE")
        self.assertEqual(data["pipeline"]["designer"], "UNKNOWN")

    def test_openclaw_is_not_required_to_build_field_status(self):
        data = self._snapshot().to_dict()
        self.assertTrue(data["field_core"]["available"])
        self.assertNotIn("openclaw_available", data)

    def test_unknown_worker_state_is_preserved(self):
        data = self._snapshot().to_dict()
        self.assertEqual(data["workers"][1]["state"], "UNKNOWN")
        self.assertIsNone(data["workers"][1]["gpu_name"])
        self.assertIsNone(data["workers"][1]["model_runtime_available"])

    def test_worker_limit_is_bounded(self):
        snapshot = build_operator_status(
            field_core_available=True,
            workers=tuple(WorkerStatus(f"w-{i}") for i in range(33)),
        )
        with self.assertRaises(ValueError):
            snapshot.to_dict()

    def test_status_tool_returns_schema_valid_shape(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.status")
        self.assertEqual(result["schema"], "zen.tool_result.v0.1")
        self.assertEqual(result["tool"], "zen.status")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIsNone(result["error"])
        self.assertEqual(result["result"]["schema"], "zen.operator_status.v0.1")

    def test_worker_status_is_read_only_projection(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.worker.status")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertFalse(result["result"]["remote_ai_available"])
        self.assertEqual(len(result["result"]["workers"]), 2)

    def test_ma_status_is_read_only_projection(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.ma.status")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["bridge_state"], "OFFLINE")
        self.assertEqual(result["result"]["connection_state"], "DISCONNECTED")
        self.assertEqual(result["result"]["target"]["host"], "127.0.0.1")

    def test_artifact_tool_returns_metadata_only(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.artifact.latest")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["artifact_id"], "artifact-1")
        self.assertNotIn("content", result["result"])

    def test_watchdog_tool_is_read_only_projection(self):
        adapter = OpenClawOperatorAdapter(
            self._snapshot,
            lambda: {
                "schema": "zen.watchdog_status.v0.1",
                "state": "ONLINE",
                "components": [],
                "recent_events": [],
            },
        )
        result = adapter.invoke("zen.watchdog.status")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["schema"], "zen.watchdog_status.v0.1")
        self.assertEqual(result["result"]["state"], "ONLINE")

    def test_watchdog_tool_is_not_implemented_without_provider(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.watchdog.status")
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(result["result"])

    def test_host_status_tool_is_read_only_projection(self):
        adapter = OpenClawOperatorAdapter(
            self._snapshot,
            host_status_provider=lambda: {
                "schema": "zen.host_status.v0.1",
                "state": "ONLINE",
                "cpu_percent": 12.5,
                "memory": {"percent": 50.0, "available_mb": 4096, "total_mb": 8192},
                "disk": {"path": "/", "percent": 40.0, "free_mb": 1000, "total_mb": 2000},
                "temperature_c": None,
                "errors": [],
            },
        )
        result = adapter.invoke("zen.host.status")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["result"]["schema"], "zen.host_status.v0.1")

    def test_host_status_tool_is_not_implemented_without_provider(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke("zen.host.status")
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(result["result"])

    def test_mutating_tools_are_reserved_but_not_implemented(self):
        adapter = OpenClawOperatorAdapter(self._snapshot)
        for name in ("zen.design.request", "zen.preview", "zen.approve"):
            with self.subTest(name=name):
                result = adapter.invoke(name)
                self.assertEqual(result["status"], "NOT_IMPLEMENTED")
                self.assertIsNone(result["result"])
                self.assertIsNone(result["error"])

    def test_unknown_tool_is_rejected_before_result_envelope(self):
        adapter = OpenClawOperatorAdapter(self._snapshot)
        with self.assertRaises(UnknownOpenClawTool):
            adapter.invoke("zen.shell")

    def test_unexpected_arguments_are_rejected(self):
        result = OpenClawOperatorAdapter(self._snapshot).invoke(
            "zen.status", {"command": "anything"}
        )
        self.assertEqual(result["status"], "REJECTED")
        self.assertEqual(result["error"]["code"], "UNEXPECTED_ARGUMENT")

    def test_invalid_or_oversized_payload_is_rejected(self):
        adapter = OpenClawOperatorAdapter(self._snapshot)
        non_json = adapter.invoke("zen.status", {"x": object()})
        self.assertEqual(non_json["status"], "REJECTED")
        self.assertEqual(non_json["error"]["code"], "PAYLOAD_INVALID_OR_TOO_LARGE")

        oversized = adapter.invoke("zen.status", {"x": "a" * 9000})
        self.assertEqual(oversized["status"], "REJECTED")
        self.assertEqual(oversized["error"]["code"], "PAYLOAD_INVALID_OR_TOO_LARGE")

    def test_request_id_is_bounded(self):
        adapter = OpenClawOperatorAdapter(self._snapshot)
        with self.assertRaises(ValueError):
            adapter.invoke("zen.status", request_id="x" * 129)


if __name__ == "__main__":
    unittest.main()
