from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.llm.spatial_review import (
    CALIBRATION_FACT_FIELDS,
    CALIBRATION_SCHEMA,
    MA2_COORDINATE_CONCEPTS,
    MA2_FIXTURE_TRANSFORM_SEMANTICS,
    MAX_SPATIAL_REVISION_CYCLES,
    STAGE_VIEW_EVIDENCE_SCHEMA,
    bind_show_bound_capability_profiles,
    build_design_review_state,
    geometry_delta,
    spatial_revision_readiness,
    validate_operator_pan_tilt_calibration,
    validate_operator_stage_view_evidence,
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
    fact_values = {field: "UNKNOWN" for field in CALIBRATION_FACT_FIELDS}
    fact_values.update(MA2_COORDINATE_CONCEPTS)
    fact_values.update(facts or {})
    return {
        "schema": CALIBRATION_SCHEMA,
        "gate_id": "SHEESH_SPATIAL_FACT_CALIBRATION_001",
        "show_fingerprint": FINGERPRINT,
        "source_artifacts": {
            "run_id": "synthetic-run",
            "normalized_snapshot_source_hash": "c" * 64,
        },
        "facts": fact_values,
        "fact_evidence": {field: "UNKNOWN in this synthetic calibration fixture." for field in CALIBRATION_FACT_FIELDS},
        "software_coordinate_semantics": {
            "values": dict(MA2_COORDINATE_CONCEPTS),
            "fixture_transform": dict(MA2_FIXTURE_TRANSFORM_SEMANTICS),
            "sources": [
                {
                    "title": "grandMA2 XYZ coordinate help",
                    "url": "https://help.malighting.com/grandMA2/en/help/key_xyz.html",
                    "scope": "MA2 software coordinate concepts only; not current-Show sign mapping or venue orientation.",
                },
                {
                    "title": "grandMA2 fixture position help",
                    "url": "https://help.malighting.com/grandMA2/en/help/key_patch_position_fixtures.html",
                    "scope": "Fixture Pos/Rot and Stage/Object axis controls; does not establish Pos field units or venue signs.",
                },
            ],
        },
        "geometry_evidence": {
            "geometry_bearing_resource_count": 2,
            "protected_fixture_ids": [9999],
        },
        "current_live_machine_observation": {"show_fingerprint": FINGERPRINT},
        "show_bound_capability_profiles": {"profiles": []},
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }


def _operator_calibration() -> dict[str, object]:
    return {
        "source_type": "OPERATOR_SUPPLIED_CALIBRATION",
        "status": "OPERATOR_VERIFIED",
        "gate_id": "SHEESH_SPATIAL_FACT_CALIBRATION_001",
        "show_fingerprint": FINGERPRINT,
        "scope": "This current Test Show and operator convention only.",
        "directions": {
            "TILT_NEGATIVE_DIRECTION": "AUDIENCE",
            "TILT_POSITIVE_DIRECTION": "UPSTAGE_OR_INWARD",
            "PAN_NEGATIVE_DIRECTION": "STAGE_RIGHT_WHEN_FACING_STAGE_FROM_AUDIENCE",
            "PAN_POSITIVE_DIRECTION": "STAGE_LEFT_WHEN_FACING_STAGE_FROM_AUDIENCE",
        },
        "xyz_sign_mapping_inferred": False,
        "universal_ma2_rule": False,
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

    def test_software_coordinate_concepts_are_separate_from_current_show_mapping(self):
        artifact = _calibration()
        validate_spatial_fact_calibration(artifact, expected_show_fingerprint=FINGERPRINT)
        self.assertEqual(artifact["facts"]["MA2_X_AXIS_CONCEPT"], "HORIZONTAL_STAGE_COORDINATE")
        self.assertEqual(artifact["facts"]["MA2_Y_AXIS_CONCEPT"], "TOWARD_AWAY_FROM_AUDIENCE_DIMENSION")
        self.assertEqual(artifact["facts"]["MA2_Z_AXIS_CONCEPT"], "VERTICAL_STAGE_COORDINATE")
        for field in (
            "CURRENT_SHOW_X_SIGN_MAPPING", "CURRENT_SHOW_Y_SIGN_MAPPING", "CURRENT_SHOW_Z_SIGN_MAPPING"
        ):
            self.assertEqual(artifact["facts"][field], "UNKNOWN")

    def test_software_semantics_cannot_auto_fill_current_show_sign_mapping(self):
        artifact = _calibration({"CURRENT_SHOW_X_SIGN_MAPPING": "POSITIVE_X_IS_STAGE_LEFT"})
        with self.assertRaisesRegex(ValueError, "separate venue evidence"):
            validate_spatial_fact_calibration(artifact)

    def test_operator_pan_tilt_calibration_is_show_scoped_and_never_maps_xyz(self):
        operator = _operator_calibration()
        self.assertIs(validate_operator_pan_tilt_calibration(operator, expected_show_fingerprint=FINGERPRINT), operator)
        artifact = _calibration({
            "PAN_TILT_ORIENTATION_SEMANTICS": "OPERATOR_VERIFIED",
            "OPERATOR_PAN_TILT_CALIBRATION": "VERIFIED_BY_OPERATOR",
        })
        artifact["operator_supplied_pan_tilt_calibration"] = operator
        validated = validate_spatial_fact_calibration(artifact)
        self.assertEqual(validated["facts"]["CURRENT_SHOW_X_SIGN_MAPPING"], "UNKNOWN")
        self.assertFalse(validated["operator_supplied_pan_tilt_calibration"]["xyz_sign_mapping_inferred"])
        self.assertFalse(validated["operator_supplied_pan_tilt_calibration"]["universal_ma2_rule"])

    def test_pan_tilt_evidence_cannot_be_used_as_xyz_sign_mapping_evidence(self):
        artifact = _calibration({
            "CURRENT_SHOW_X_SIGN_MAPPING": "POSITIVE_X_IS_STAGE_LEFT",
            "PAN_TILT_ORIENTATION_SEMANTICS": "OPERATOR_VERIFIED",
            "OPERATOR_PAN_TILT_CALIBRATION": "VERIFIED_BY_OPERATOR",
        })
        artifact["operator_supplied_pan_tilt_calibration"] = _operator_calibration()
        artifact["current_show_venue_mapping_evidence"] = {
            "show_fingerprint": FINGERPRINT,
            "source_type": "OPERATOR_SUPPLIED_CURRENT_SHOW_COORDINATE_MAPPING",
            "independent_of_pan_tilt": False,
            "independent_of_software_convention": True,
            "source_reference": "Pan/Tilt operator note",
            "mappings": {"CURRENT_SHOW_X_SIGN_MAPPING": "POSITIVE_X_IS_STAGE_LEFT"},
        }
        with self.assertRaisesRegex(ValueError, "independently sourced"):
            validate_spatial_fact_calibration(artifact, expected_show_fingerprint=FINGERPRINT)

    def test_stage_bounds_are_not_inferred_from_fixture_extents(self):
        snapshot = {"fixture_inventory": [{"fixture_id": 101, "geometry": [{"xyz": {"x": -1000, "y": 9000, "z": 2}}]}]}
        self.assertIn("fixture_inventory", snapshot)
        calibration = _calibration({"STAGE_BOUNDS_KNOWN": "UNKNOWN"})
        readiness = spatial_revision_readiness(calibration)
        self.assertEqual(calibration["facts"]["STAGE_BOUNDS_KNOWN"], "UNKNOWN")
        self.assertIn("STAGE_AND_PERFORMER_CONTEXT", readiness["blocking_categories"])

    def test_performer_zone_is_not_inferred_from_fixture_geometry(self):
        calibration = _calibration({"PERFORMER_ZONE_KNOWN": "UNKNOWN"})
        self.assertEqual(calibration["facts"]["PERFORMER_ZONE_KNOWN"], "UNKNOWN")
        self.assertIn("STAGE_AND_PERFORMER_CONTEXT", spatial_revision_readiness(calibration)["blocking_categories"])

    def test_fixture_capability_is_not_inferred_from_fixture_or_group_labels(self):
        snapshot = {
            "show_fingerprint": FINGERPRINT,
            "fixture_inventory": [{"fixture_id": 101, "name": "Spot 1", "fixture_type_identity": "2 Spot Mode"}],
        }
        export_batch = {
            "show_identity_match": "MATCH",
            "current_show_identity": {"value": FINGERPRINT},
            "binding_status": "PARTIAL",
            "fixture_type_profiles": [],
        }
        with self.assertRaisesRegex(ValueError, "not bound"):
            bind_show_bound_capability_profiles(snapshot, export_batch)
        self.assertNotIn("capabilities", snapshot["fixture_inventory"][0])

    def test_exact_current_show_fixture_type_attributes_create_identity_bound_profiles(self):
        snapshot = {
            "show_fingerprint": FINGERPRINT,
            "fixture_inventory": [
                {"fixture_id": 101, "name": "Anything 1", "fixture_type_identity": "2 Exact Profile Mode", "availability": "AVAILABLE_INVENTORY_ONLY"},
                {"fixture_id": 9999, "name": "Protected", "fixture_type_identity": "2 Exact Profile Mode", "availability": "PROTECTED_UNAVAILABLE"},
            ],
        }
        profile = {
            "status": "SHOW_BOUND_VERIFIED",
            "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
            "fixture_type": {"fixture_type_id": 2, "list_label": "2 Exact Profile Mode"},
            "channels": [{"attribute": "DIM"}, {"attribute": "PAN"}],
            "capabilities": {"DIMMER": {"status": "SHOW_BOUND_VERIFIED"}},
        }
        bound = bind_show_bound_capability_profiles(snapshot, {
            "show_identity_match": "MATCH",
            "current_show_identity": {"value": FINGERPRINT},
            "binding_status": "SHOW_BOUND_VERIFIED",
            "fixture_type_profiles": [profile],
        })
        self.assertEqual(bound["schema"], "zen.show_bound_fixture_capability_profiles.v0.1")
        self.assertEqual(bound["capability_profile_count"], 1)
        exact = bound["profiles"][0]
        self.assertEqual(exact["show_fingerprint"], FINGERPRINT)
        self.assertEqual(exact["fixture_id"], 101)
        self.assertEqual(exact["fixture_type_identity"]["list_label"], "2 Exact Profile Mode")
        self.assertEqual(exact["observed_attributes"], ["DIM", "PAN"])
        self.assertEqual(exact["confidence"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(bound["protected_fixture_ids"], [9999])
        self.assertNotIn(9999, [item["fixture_id"] for item in bound["profiles"]])

    def test_fixture_type_export_from_another_show_fingerprint_is_rejected(self):
        snapshot = {
            "show_fingerprint": FINGERPRINT,
            "fixture_inventory": [{"fixture_id": 101, "fixture_type_identity": "2 Exact Profile Mode"}],
        }
        with self.assertRaisesRegex(ValueError, "exact Show fingerprint"):
            bind_show_bound_capability_profiles(snapshot, {
                "show_identity_match": "MISMATCH",
                "current_show_identity": {"value": "b" * 64},
                "binding_status": "SHOW_BOUND_VERIFIED",
                "fixture_type_profiles": [{
                    "status": "SHOW_BOUND_VERIFIED",
                    "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
                    "fixture_type": {"fixture_type_id": 2, "list_label": "2 Exact Profile Mode"},
                    "channels": [{"attribute": "DIM"}],
                }],
            })

    def test_fuzzy_fixture_name_matching_cannot_create_capability_profile(self):
        snapshot = {
            "show_fingerprint": FINGERPRINT,
            "fixture_inventory": [{"fixture_id": 301, "name": "Matching SPOT name", "fixture_type_identity": "2 SPOT Model"}],
        }
        profile = {
            "status": "SHOW_BOUND_VERIFIED",
            "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
            "fixture_type": {"fixture_type_id": 7, "list_label": "7 Manufacturer Spot Model"},
            "channels": [{"attribute": "DIM"}],
        }
        with self.assertRaisesRegex(ValueError, "No exact show-bound FixtureType"):
            bind_show_bound_capability_profiles(snapshot, {
                "show_identity_match": "MATCH",
                "current_show_identity": {"value": FINGERPRINT},
                "binding_status": "SHOW_BOUND_VERIFIED",
                "fixture_type_profiles": [profile],
            })

    def test_operator_stage_view_evidence_is_fingerprint_bound_and_annotation_tagged(self):
        png = b"\x89PNG\r\n\x1a\n" + b"calibration-test"
        digest = hashlib.sha256(png).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stage.png"
            path.write_bytes(png)
            annotation = {
                "value": "Audience is below the stage view.",
                "source_type": "OPERATOR_SUPPLIED_ANNOTATION",
                "asserted_by": "OPERATOR",
                "show_fingerprint": FINGERPRINT,
            }
            evidence = {
                "schema": STAGE_VIEW_EVIDENCE_SCHEMA,
                "source_type": "OPERATOR_SUPPLIED_STAGE_VIEW_IMAGE",
                "show_fingerprint": FINGERPRINT,
                "captured_at": "2026-09-21T12:00:00+08:00",
                "image": {"relative_path": "stage.png", "sha256": digest, "media_type": "image/png"},
                "notes": {
                    "value": "Operator note remains separately attributed.",
                    "source_type": "OPERATOR_SUPPLIED_ANNOTATION",
                    "asserted_by": "OPERATOR",
                    "show_fingerprint": FINGERPRINT,
                },
                "operator_asserted_audience_direction": annotation,
                "operator_assertions": {
                    "operator_asserted_audience_direction": dict(annotation),
                    "notes": {
                        "source_type": "OPERATOR_SUPPLIED_ANNOTATION",
                        "asserted_by": "OPERATOR",
                        "show_fingerprint": FINGERPRINT,
                        "value": "Operator note remains separately attributed.",
                    },
                },
                "visual_observations": [{
                    "observation": "Fixtures appear in two visible clusters.",
                    "evidence_class": "VISUAL_OBSERVATION",
                    "verified_physical_fact": False,
                    "source_image_sha256": digest,
                }],
            }
            result = validate_operator_stage_view_evidence(
                evidence, expected_show_fingerprint=FINGERPRINT, evidence_root=Path(directory)
            )
        self.assertEqual(result["source_type"], "OPERATOR_SUPPLIED_STAGE_VIEW_IMAGE")
        self.assertEqual(result["operator_annotations_status"], "PROVENANCE_SEPARATE_FROM_IMAGE")
        self.assertEqual(result["visual_observations"][0]["evidence_class"], "VISUAL_OBSERVATION")
        self.assertFalse(result["visual_observations"][0]["verified_physical_fact"])
        self.assertNotIn("facts", result)

    def test_visual_observations_cannot_silently_promote_to_verified_facts(self):
        png = b"\x89PNG\r\n\x1a\n" + b"visual-only"
        digest = hashlib.sha256(png).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "stage.png").write_bytes(png)
            evidence = {
                "schema": STAGE_VIEW_EVIDENCE_SCHEMA,
                "source_type": "OPERATOR_SUPPLIED_STAGE_VIEW_IMAGE",
                "show_fingerprint": FINGERPRINT,
                "captured_at": "2026-09-21T12:00:00+08:00",
                "image": {"relative_path": "stage.png", "sha256": digest, "media_type": "image/png"},
                "operator_assertions": {},
                "visual_observations": [{
                    "observation": "Possible truss visible.",
                    "evidence_class": "VISUAL_OBSERVATION",
                    "verified_physical_fact": True,
                    "source_image_sha256": digest,
                }],
            }
            with self.assertRaisesRegex(ValueError, "cannot silently become"):
                validate_operator_stage_view_evidence(
                    evidence, expected_show_fingerprint=FINGERPRINT, evidence_root=Path(directory)
                )

    def test_stage_view_input_rejects_wrong_fingerprint_and_wrong_image_hash(self):
        evidence = {
            "schema": STAGE_VIEW_EVIDENCE_SCHEMA,
            "source_type": "OPERATOR_SUPPLIED_STAGE_VIEW_IMAGE",
            "show_fingerprint": FINGERPRINT,
            "captured_at": "2026-09-21T12:00:00+08:00",
            "image": {"relative_path": "stage.png", "sha256": "0" * 64, "media_type": "image/png"},
            "operator_assertions": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "stage.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                validate_operator_stage_view_evidence(
                    evidence, expected_show_fingerprint="b" * 64, evidence_root=Path(directory)
                )
            with self.assertRaisesRegex(ValueError, "hash"):
                validate_operator_stage_view_evidence(
                    evidence, expected_show_fingerprint=FINGERPRINT, evidence_root=Path(directory)
                )

    def test_unknown_calibration_facts_are_valid_but_block_revision_readiness(self):
        artifact = _calibration()
        validated = validate_spatial_fact_calibration(artifact, expected_show_fingerprint=FINGERPRINT)
        self.assertIs(validated, artifact)
        readiness = spatial_revision_readiness(artifact)
        self.assertEqual(readiness["status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertFalse(readiness["ready"])
        self.assertIn("VENUE_COORDINATE_ORIENTATION", readiness["blocking_categories"])

    def test_committed_calibration_retains_operator_pan_tilt_and_stays_blocked(self):
        path = Path(__file__).resolve().parents[1] / "data" / "sheesh_spatial_fact_calibration_001.json"
        artifact = json.loads(path.read_text(encoding="utf-8"))
        validate_spatial_fact_calibration(artifact)
        readiness = spatial_revision_readiness(artifact)
        self.assertEqual(artifact["facts"]["CURRENT_SHOW_X_SIGN_MAPPING"], "UNKNOWN")
        self.assertEqual(artifact["facts"]["CURRENT_SHOW_Y_SIGN_MAPPING"], "UNKNOWN")
        self.assertEqual(artifact["facts"]["CURRENT_SHOW_Z_SIGN_MAPPING"], "UNKNOWN")
        self.assertEqual(artifact["facts"]["PAN_TILT_ORIENTATION_SEMANTICS"], "OPERATOR_VERIFIED")
        self.assertFalse(artifact["operator_supplied_pan_tilt_calibration"]["xyz_sign_mapping_inferred"])
        self.assertEqual(artifact["show_bound_capability_profiles"]["capability_profile_count"], 0)
        self.assertEqual(readiness["status"], "BLOCKED_MISSING_EVIDENCE")
        self.assertEqual(artifact["PROVIDER_ARTISTIC_CALLS"], 0)
        self.assertEqual(artifact["MA2_WRITES"], 0)

    def test_readiness_uses_minimum_evidence_not_every_possible_calibration_field(self):
        facts = {
            "CURRENT_SHOW_FINGERPRINT_MATCHES_LIVE_SCAN": "VERIFIED",
            "GEOMETRY_BEARING_RESOURCES_AVAILABLE": "VERIFIED",
            "PROTECTED_RESOURCES_IDENTIFIED": "VERIFIED",
            "CURRENT_SHOW_X_SIGN_MAPPING": "OPERATOR_VERIFIED_POSITIVE_X_STAGE_LEFT",
            "CURRENT_SHOW_Y_SIGN_MAPPING": "OPERATOR_VERIFIED_NEGATIVE_Y_AUDIENCE",
            "CURRENT_SHOW_Z_SIGN_MAPPING": "OPERATOR_VERIFIED_POSITIVE_Z_UP",
            "PAN_TILT_ORIENTATION_SEMANTICS": "OPERATOR_VERIFIED",
            "OPERATOR_PAN_TILT_CALIBRATION": "VERIFIED_BY_OPERATOR",
            "AUDIENCE_DIRECTION_KNOWN": "OPERATOR_VERIFIED",
            "STAGE_LEFT_RIGHT_KNOWN": "OPERATOR_VERIFIED",
            "UPSTAGE_DOWNSTAGE_KNOWN": "OPERATOR_VERIFIED",
            "STAGE_BOUNDS_KNOWN": "KNOWN_FROM_OPERATOR_STAGE_PLAN",
            "PERFORMER_ZONE_KNOWN": "KNOWN_FROM_OPERATOR_STAGE_PLAN",
            "CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE": "SHOW_BOUND_VERIFIED",
        }
        artifact = _calibration(facts)
        artifact["operator_supplied_pan_tilt_calibration"] = _operator_calibration()
        artifact["current_show_venue_mapping_evidence"] = {
            "show_fingerprint": FINGERPRINT,
            "source_type": "OPERATOR_SUPPLIED_CURRENT_SHOW_COORDINATE_MAPPING",
            "independent_of_pan_tilt": True,
            "independent_of_software_convention": True,
            "source_reference": "synthetic operator stage-plan annotation",
            "mappings": {
                field: facts[field]
                for field in (
                    "CURRENT_SHOW_X_SIGN_MAPPING", "CURRENT_SHOW_Y_SIGN_MAPPING", "CURRENT_SHOW_Z_SIGN_MAPPING"
                )
            },
        }
        artifact["show_bound_capability_profiles"] = {"profiles": [{
            "show_fingerprint": FINGERPRINT,
            "fixture_id": 101,
            "confidence": "SHOW_BOUND_VERIFIED",
            "observed_attributes": ["DIM"],
        }]}
        artifact["geometry_evidence"] = {"geometry_bearing_resource_count": 64, "protected_fixture_ids": [9999]}
        readiness = spatial_revision_readiness(artifact)
        self.assertTrue(readiness["ready"])
        self.assertEqual(readiness["status"], "READY")
        self.assertIn("COORDINATE_UNITS_VERIFIED", readiness["non_blocking_limitations"])
        self.assertIn("OBSTRUCTION_DATA_AVAILABLE", readiness["non_blocking_limitations"])
        self.assertIn("TRUSS_OR_SUPPORT_GEOMETRY_AVAILABLE", readiness["non_blocking_limitations"])

    def test_calibration_rejects_wrong_show_fingerprint(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            validate_spatial_fact_calibration(_calibration(), expected_show_fingerprint="b" * 64)

    def test_calibration_source_hash_and_run_id_are_bound(self):
        with self.assertRaisesRegex(ValueError, "source hash"):
            validate_spatial_fact_calibration(_calibration(), expected_snapshot_source_hash="d" * 64)
        with self.assertRaisesRegex(ValueError, "run ID"):
            validate_spatial_fact_calibration(_calibration(), expected_run_id="different-run")

    def test_zero_geometry_delta_is_reported_without_becoming_validation_failure(self):
        snapshot = {"fixture_inventory": [{
            "fixture_id": 101,
            "geometry": [{
                "subfixture_id": 1,
                "xyz": {"x": 1.0, "y": 2.0, "z": 3.0},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            }],
        }]}
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
