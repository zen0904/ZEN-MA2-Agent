from __future__ import annotations

import copy
import unittest

from zen_ma2_agent.llm.spatial_review import (
    CALIBRATION_FACT_FIELDS,
    CALIBRATION_SCHEMA,
    MAX_SPATIAL_REVISION_CYCLES,
    build_design_review_state,
    geometry_delta,
    spatial_revision_readiness,
    validate_spatial_fact_calibration,
)
from zen_ma2_agent.llm.multi_agent_runtime import MultiAgentRunError, validate_critic_artifact


FINGERPRINT = "a" * 64


def _critic(classification: str) -> dict[str, object]:
    severity: object = classification
    if classification == "BLOCKER":
        severity = {"classification": classification, "rationale": "fixture review evidence"}
    return {
        "schema": "zen.multi_agent_critic.v0.1",
        "strengths": [],
        "problems": [],
        "severity": severity,
        "revision_requests": [{"request": "Use calibrated facts."}],
        "codex_artistic_intervention": "NONE",
    }


def _calibration(facts: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema": CALIBRATION_SCHEMA,
        "gate_id": "SHEESH_SPATIAL_FACT_CALIBRATION_001",
        "show_fingerprint": FINGERPRINT,
        "source_artifacts": {
            "run_id": "synthetic-run",
            "normalized_snapshot_source_hash": "c" * 64,
        },
        "facts": facts or {field: "UNKNOWN" for field in CALIBRATION_FACT_FIELDS},
        "fact_evidence": {field: "UNKNOWN in this synthetic calibration fixture." for field in CALIBRATION_FACT_FIELDS},
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }


class SpatialReviewTests(unittest.TestCase):
    def test_critic_severity_contract_accepts_blocker_and_rejects_unknown_classification(self):
        accepted = _critic("BLOCKER")
        self.assertIs(validate_critic_artifact(accepted), accepted)
        invalid = _critic("UNBOUNDED_SCORE_97")
        with self.assertRaisesRegex(MultiAgentRunError, "unsupported"):
            validate_critic_artifact(invalid)

    def test_blocker_blocks_all_writeback_eligibility_while_execution_can_complete(self):
        artifact = _critic("BLOCKER")
        original = copy.deepcopy(artifact)
        state = build_design_review_state(artifact, live_show=True, execution_status="COMPLETE")
        self.assertEqual(state["execution_status"], "COMPLETE")
        self.assertEqual(state["design_review_status"], "BLOCKED_BY_CRITIC")
        self.assertEqual(state["WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(state["RESOLVER_ELIGIBLE"], "NO")
        self.assertEqual(state["PREVIEW_FOR_WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(state["revision_requests"], _critic("BLOCKER")["revision_requests"])
        state["revision_requests"].append({"request": "mutation test"})
        self.assertEqual(artifact, original)

    def test_finalizer_cannot_clear_blocker_and_revision_limit_is_bounded(self):
        critic = _critic("BLOCKER")
        before = build_design_review_state(critic, live_show=True, execution_status="COMPLETE")
        _finalizer_claim = {"design_review_status": "REVIEW_PASSED", "schema": "zen.autonomous_design.v0.1"}
        after = build_design_review_state(
            critic,
            live_show=True,
            revision_cycles_completed=MAX_SPATIAL_REVISION_CYCLES,
            execution_status="COMPLETE",
        )
        self.assertEqual(before["design_review_status"], "BLOCKED_BY_CRITIC")
        self.assertEqual(after["design_review_status"], "BLOCKED_AFTER_REVISION_LIMIT")
        self.assertEqual(after["WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(MAX_SPATIAL_REVISION_CYCLES, 2)

    def test_non_blocker_can_pass_review_but_never_authorizes_writeback(self):
        state = build_design_review_state(_critic("DESIGN_WEAKNESS"), live_show=True)
        self.assertEqual(state["design_review_status"], "REVIEW_PASSED")
        self.assertEqual(state["WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(state["SPATIAL_WRITEBACK_APPROVED"], "NO")

    def test_unknown_calibration_facts_are_valid_but_block_revision_readiness(self):
        artifact = _calibration()
        validated = validate_spatial_fact_calibration(
            artifact, expected_show_fingerprint=FINGERPRINT
        )
        self.assertIs(validated, artifact)
        readiness = spatial_revision_readiness(artifact)
        self.assertEqual(readiness["status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertFalse(readiness["ready"])
        self.assertIn("X_AXIS_SEMANTICS", readiness["blocking_facts"])

    def test_calibration_rejects_wrong_show_fingerprint(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_spatial_fact_calibration(
                _calibration(), expected_show_fingerprint="b" * 64
            )

    def test_calibration_source_hash_and_run_id_are_bound(self):
        with self.assertRaisesRegex(ValueError, "source hash"):
            validate_spatial_fact_calibration(
                _calibration(), expected_snapshot_source_hash="d" * 64
            )
        with self.assertRaisesRegex(ValueError, "run ID"):
            validate_spatial_fact_calibration(
                _calibration(), expected_run_id="different-run"
            )

    def test_zero_geometry_delta_is_reported_without_becoming_validation_failure(self):
        snapshot = {
            "fixture_inventory": [{
                "fixture_id": 101,
                "geometry": [{
                    "subfixture_id": 1,
                    "xyz": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                }],
            }],
        }
        position = {"placements": [{
            "fixture_id": 101,
            "subfixture_id": 1,
            "xyz": {"x": 1.0, "y": 2.0, "z": 3.0},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
        }]}
        original_snapshot = copy.deepcopy(snapshot)
        original_position = copy.deepcopy(position)
        delta = geometry_delta(snapshot, position)
        self.assertEqual(delta["geometry_delta_from_snapshot"], "ZERO")
        self.assertEqual(delta["placements_unchanged_count"], 1)
        self.assertEqual(delta["rotations_unchanged_count"], 1)
        self.assertFalse(delta["is_artistic_validation_failure"])
        self.assertEqual(snapshot, original_snapshot)
        self.assertEqual(position, original_position)


if __name__ == "__main__":
    unittest.main()
