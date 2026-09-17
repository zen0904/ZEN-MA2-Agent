import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.artifacts import (
    ArtifactCache,
    ArtifactMetadata,
    StaleArtifactError,
    validate_remote_result,
)


class ArtifactTests(unittest.TestCase):
    def test_cache_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = ArtifactCache(Path(temp))
            metadata = ArtifactMetadata(
                artifact_id="artifact-1",
                request_hash="reqhash",
                show_context_hash="showhash",
                schema_version="zen.final_design.v0.1",
                created_at="2026-09-17T00:00:00Z",
                source_worker_id="worker-a",
                producer_version="test",
            )
            path = cache.put(metadata, {"ok": True})
            self.assertTrue(path.is_file())
            self.assertTrue(cache.exists("artifact-1"))
            loaded = cache.get("artifact-1")
            self.assertEqual(loaded["metadata"]["request_hash"], "reqhash")
            self.assertEqual(loaded["payload"], {"ok": True})

    def test_artifact_id_cannot_escape_cache_root(self):
        with tempfile.TemporaryDirectory() as temp:
            cache = ArtifactCache(Path(temp))
            with self.assertRaises(ValueError):
                cache.exists("../escape")

    def test_remote_result_identity_accepts_exact_match(self):
        result = {
            "job_id": "job-1",
            "job_type": "INFERENCE_RESERVED",
            "request_hash": "reqhash",
            "show_context_hash": "showhash",
            "schema_version": "zen.worker.result.v0.1",
        }
        validate_remote_result(
            result,
            expected_job_id="job-1",
            expected_job_type="INFERENCE_RESERVED",
            expected_request_hash="reqhash",
            expected_show_context_hash="showhash",
            expected_schema_version="zen.worker.result.v0.1",
        )

    def test_stale_remote_result_is_rejected(self):
        base = {
            "job_id": "job-1",
            "job_type": "INFERENCE_RESERVED",
            "request_hash": "reqhash",
            "show_context_hash": "showhash",
            "schema_version": "zen.worker.result.v0.1",
        }
        for field, bad in (
            ("job_id", "job-x"),
            ("job_type", "ECHO_TEST"),
            ("request_hash", "old"),
            ("show_context_hash", "old-show"),
            ("schema_version", "old.schema"),
        ):
            with self.subTest(field=field):
                changed = dict(base)
                changed[field] = bad
                with self.assertRaises(StaleArtifactError):
                    validate_remote_result(
                        changed,
                        expected_job_id="job-1",
                        expected_job_type="INFERENCE_RESERVED",
                        expected_request_hash="reqhash",
                        expected_show_context_hash="showhash",
                        expected_schema_version="zen.worker.result.v0.1",
                    )


if __name__ == "__main__":
    unittest.main()
