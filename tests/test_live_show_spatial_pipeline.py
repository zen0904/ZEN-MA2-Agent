from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.llm.live_show_snapshot import CurrentShowSnapshotInput, normalize_current_show_snapshot
from zen_ma2_agent.llm.multi_agent_runtime import (
    LIVE_SHOW_ROLE_SEQUENCE,
    MultiAgentRunError,
    ResearchSourceContractError,
    ROLE_SYSTEM_PROMPTS,
    _bootstrap_role_prompt,
    _load_postwrite_visual_evidence,
    _model_facing_current_show_snapshot,
    _sha256,
    build_position_context,
    normalize_role_envelope,
    run_multi_agent_design,
    run_spatial_revision_loop,
    validate_research_source_contract,
    validate_final_spatial_consistency,
    validate_position_design_artifact,
    validate_rig_design_artifact,
)
from zen_ma2_agent.llm.router import ProviderRouter, ProviderSlot, ProviderUnavailable
from zen_ma2_agent.llm.spatial_review import (
    CALIBRATION_FACT_FIELDS,
    CALIBRATION_SCHEMA,
    MA2_COORDINATE_CONCEPTS,
    MA2_FIXTURE_TRANSFORM_SEMANTICS,
)


FINGERPRINT = "a" * 64


def _snapshot(fingerprint: str = FINGERPRINT) -> dict[str, object]:
    return {
        "schema": "zen.sheesh_current_show_redesign_snapshot.v0.1",
        "captured_at": "2026-09-20T10:35:43Z",
        "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": fingerprint, "confidence": "PARTIAL"},
        "fixture_count": 3,
        "group_count": 1,
        "groups": [{"group_id": 1, "name": "SPOT", "fixture_ids_in_selection_order": [101, 102]}],
        "resource_status": {
            "fixtures": {"status": "available", "stale": False, "values": [
                {"number": 101, "name": "Spot 1", "fixture_type": "3 Example Profile"},
                {"number": 102, "name": "Spot 2", "fixture_type": "3 Example Profile"},
                {"number": 9999, "name": "Protected fixture", "fixture_type": "3 Example Profile"},
            ]},
            "fixture_geometry": {"status": "available", "stale": False, "values": [
                {"fixture_id": 101, "subfixture_id": 1, "position": {"x": -1, "y": 2, "z": 3}, "rotation": {"x": 0, "y": 0, "z": 0}, "patch": "10.001", "address": 1, "source": "MA2_FIXTURE_OBJECT_PROPERTY", "confidence": "REAL_MACHINE_VERIFIED"},
                {"fixture_id": 102, "subfixture_id": 1, "position": {"x": 1, "y": 2, "z": 3}, "rotation": {"x": 0, "y": 0, "z": 0}, "patch": "10.031", "address": 31, "source": "MA2_FIXTURE_OBJECT_PROPERTY", "confidence": "REAL_MACHINE_VERIFIED"},
                {"fixture_id": 9999, "subfixture_id": 1, "position": {"x": 0, "y": 0, "z": 0}, "rotation": {"x": 0, "y": 0, "z": 0}, "patch": "99.001", "address": 1, "source": "MA2_FIXTURE_OBJECT_PROPERTY", "confidence": "REAL_MACHINE_VERIFIED"},
            ]},
        },
        "stage_geometry_readability": {"status": "SUPPORTED"},
        "ma2_writes": 0,
        "codex_artistic_intervention": "NONE",
    }


def _operator_stage_context(fingerprint: str = FINGERPRINT) -> dict[str, object]:
    return {
        "schema": "zen.operator_current_show_stage_context.v0.1",
        "source_type": "OPERATOR_SUPPLIED_STAGE_CONTEXT",
        "status": "OPERATOR_VERIFIED",
        "show_fingerprint": fingerprint,
        "stage_view_image": {"sha256": "b" * 64, "media_type": "image/png", "viewpoint": "FACING_STAGE"},
        "asserted_by": "OPERATOR",
        "stage_region": {
            "status": "OPERATOR_VERIFIED", "shape": "SQUARE",
            "region": "ENTIRE_VISIBLE_GRAY_STAGE_PLANE", "visual_bounds_known": True,
            "metric_dimensions_known": False,
        },
        "orientation": {
            "viewpoint": "FACING_STAGE", "audience_side": "IMAGE_BOTTOM_FOREGROUND",
            "upstage_direction": "IMAGE_TOP_BACKGROUND", "stage_right": "IMAGE_LEFT",
            "stage_left": "IMAGE_RIGHT",
        },
        "performer_context": {
            "status": "OPERATOR_VERIFIED", "zone": "FRONT_STAGE_PRIORITY",
            "relation": "CLOSER_TO_AUDIENCE_THAN_UPSTAGE", "exact_metric_bounds_known": False,
        },
        "pan_tilt_calibration": {
            "status": "OPERATOR_VERIFIED", "tilt_negative_direction": "AUDIENCE",
            "tilt_positive_direction": "UPSTAGE_OR_INWARD", "pan_negative_direction": "STAGE_RIGHT",
            "pan_positive_direction": "STAGE_LEFT", "derive_xyz_sign_mapping": False,
        },
        "coordinate_sign_mapping": {
            "x": "UNKNOWN", "y": "UNKNOWN", "z": "UNKNOWN",
            "pan_tilt_may_fill_xyz_mapping": False,
            "image_may_fill_xyz_mapping_without_independent_evidence": False,
        },
        "conceptual_design_scope": {
            "enabled": True, "scope": "CONCEPTUAL_VIRTUAL_FIXTURE_PLACEMENT_ONLY",
            "truss_constraints": "DEFERRED", "mounting_feasibility": "DEFERRED",
            "structural_engineering": "OUT_OF_SCOPE", "cable_routing": "OUT_OF_SCOPE",
            "load_calculation": "OUT_OF_SCOPE", "obstruction_engineering": "DEFERRED",
            "installation_approval": "NOT_GRANTED",
        },
        "codex_artistic_intervention": "NONE", "ma2_writes": 0,
    }


def _show_bound_capabilities(fingerprint: str = FINGERPRINT) -> dict[str, object]:
    profiles = []
    for fixture_id in (101, 102):
        profiles.append({
            "show_fingerprint": fingerprint,
            "fixture_id": fixture_id,
            "fixture_type_identity": {"fixture_type_id": 3, "list_label": "3 Example Profile"},
            "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
            "observed_attributes": ["DIM", "PAN", "TILT"],
            "capabilities": {"DIMMER": {"status": "SHOW_BOUND_VERIFIED"}},
            "confidence": "SHOW_BOUND_VERIFIED",
            "artistic_role_inference": "NONE",
        })
    return {
        "schema": "zen.show_bound_fixture_capability_profiles.v0.1",
        "show_fingerprint": fingerprint,
        "profiles": profiles,
        "protected_fixture_ids": [9999],
        "capability_profile_count": len(profiles),
        "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
    }


def _research() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_research.v0.1", "research_status": "OFFLINE_CACHED_CONTEXT",
        "subject": "BABYMONSTER - SHEESH", "sources": [], "transferable_design_observations": [],
        "constraints": [], "uncertainties": [], "codex_artistic_intervention": "NONE",
    }


def _rig(snapshot: dict[str, object], *, fixture_id: int = 101) -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_rig_design.v0.1",
        "show_fingerprint": snapshot["show_fingerprint"],
        "spatial_strategy": "provider-authored spatial proposal",
        "resource_assignments": [{"spatial_intent": "provider-authored", "resource_refs": [{"fixture_id": fixture_id, "subfixture_id": 1}]}],
        "spatial_relationships": [], "constraints": [], "uncertainties": [],
        "codex_artistic_intervention": "NONE",
    }


def _position(snapshot: dict[str, object], *, placements: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_position_design.v0.1",
        "show_fingerprint": snapshot["show_fingerprint"],
        "coordinate_system": snapshot.get("coordinate_system", {"axis_semantics": "UNKNOWN"}),
        "spatial_groups": [],
        "placements": placements if placements is not None else [{
            "fixture_id": 101, "subfixture_id": 1, "show_fingerprint": snapshot["show_fingerprint"],
            "xyz": {"x": -2.0, "y": 1.0, "z": 4.0},
        }],
        "constraints": [], "uncertainties": [], "codex_artistic_intervention": "NONE",
    }


def _draft() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_designer_draft.v0.1", "design_intent": {}, "visual_strategy": {},
        "resource_considerations": [], "uncertainties": [], "codex_artistic_intervention": "NONE",
    }


def _critic() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_critic.v0.1", "strengths": [], "problems": [],
        "severity": "NONE", "revision_requests": [], "codex_artistic_intervention": "NONE",
    }


def _final(position: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "zen.autonomous_design.v0.1", "design_intent": {}, "visual_strategy": {},
        "virtual_rig": {}, "position_vocabulary": {}, "main_sequence": {}, "free_cue_layer": {},
        "evidence_trace": {},
        "position_design_reference": {
            "show_fingerprint": position["show_fingerprint"],
            "position_artifact_sha256": _sha256(position),
        },
        "codex_artistic_intervention": "NONE",
    }


class _RoleAdapter:
    def __init__(self, snapshot: dict[str, object]):
        self.snapshot = snapshot
        self.calls: list[tuple[str, dict[str, object]]] = []

    def complete(self, slot, *, system, user):
        payload = json.loads(user)
        self.calls.append((system.split(". ", 1)[0], payload))
        role = self.calls[-1][0]
        if role == "ROLE: RESEARCHER":
            return json.dumps(_research())
        normalized = payload.get("current_show_snapshot")
        if role == "ROLE: RIG_DESIGNER":
            return json.dumps(_rig(normalized))
        if role == "ROLE: POSITION_DESIGNER":
            return json.dumps(_position(payload["position_context"]))
        if role == "ROLE: LIGHTING_DESIGNER":
            return json.dumps(_draft())
        if role == "ROLE: CRITIC":
            return json.dumps(_critic())
        if role == "ROLE: FINALIZER":
            return json.dumps(_final(payload["position_design_artifact"]))
        raise AssertionError(role)


class LiveShowSpatialPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"ZEN_HOME": self.temp.name}, clear=False)
        self.environment.start()
        self.repo_root = Path(__file__).resolve().parents[1]
        self.raw_snapshot = _snapshot()
        self.input = CurrentShowSnapshotInput(self.raw_snapshot)
        self.normalized = normalize_current_show_snapshot(self.input)

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def _router(self, adapter):
        slot = ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "test-local", "http://127.0.0.1:8080/v1", "", (), 5)
        return ProviderRouter("PRIMARY_ONLY", (slot,), adapter)

    def test_live_snapshot_runs_six_roles_and_lighting_critic_receive_exact_upstream_artifacts(self):
        adapter = _RoleAdapter(self.normalized)
        run = run_multi_agent_design(
            self._router(adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id="live-spatial-six-roles", current_show_snapshot=self.input,
        )
        self.assertEqual(tuple(item[0] for item in adapter.calls), tuple(f"ROLE: {name.upper()}" for name in LIVE_SHOW_ROLE_SEQUENCE))
        self.assertEqual(json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))["ROLE_EXECUTION_ORDER"], list(LIVE_SHOW_ROLE_SEQUENCE))
        rig = json.loads((run.run_path / "steps" / "rig_designer.json").read_text(encoding="utf-8"))["artifact"]
        position = json.loads((run.run_path / "steps" / "position_designer.json").read_text(encoding="utf-8"))["artifact"]
        designer_payload = next(payload for role, payload in adapter.calls if role == "ROLE: LIGHTING_DESIGNER")
        critic_payload = next(payload for role, payload in adapter.calls if role == "ROLE: CRITIC")
        final_payload = next(payload for role, payload in adapter.calls if role == "ROLE: FINALIZER")
        self.assertEqual(designer_payload["rig_design_artifact"], rig)
        self.assertEqual(designer_payload["position_design_artifact"], position)
        self.assertEqual(critic_payload["rig_design_artifact"], rig)
        self.assertEqual(critic_payload["position_design_artifact"], position)
        self.assertEqual(final_payload["rig_design_artifact"], rig)
        self.assertEqual(final_payload["position_design_artifact"], position)
        self.assertEqual(final_payload["latest_lighting_designer_artifact"], _draft())
        self.assertEqual(final_payload["latest_critic_artifact"], _critic())
        self.assertEqual(final_payload["design_review_state"]["design_review_status"], "REVIEW_PASSED")
        self.assertEqual(designer_payload["current_show_snapshot"], self.normalized)
        self.assertEqual(designer_payload["design_context"]["fixture_technical_capability"]["status"], "UNKNOWN_FOR_CURRENT_FINGERPRINT")
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")
        self.assertEqual(json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))["CURRENT_SHOW_FINGERPRINT"], FINGERPRINT)
        rig_diag = json.loads((run.run_path / "diagnostics" / "rig_designer-01.json").read_text(encoding="utf-8"))
        self.assertEqual(rig_diag["role"], "rig_designer")
        self.assertEqual(rig_diag["provider_routing"]["semantic_role"], "RIG_DESIGNER")
        self.assertEqual(rig_diag["provider_routing"]["provider_capability_role"], "LIGHTING_DESIGNER")
        self.assertEqual(rig_diag["structural_normalization"], {"applied": False, "fields_added": []})
        self.assertFalse((run.run_path / "attempts" / "rig_designer-01.json").exists())

        position_role_payload = next(payload for role, payload in adapter.calls if role == "ROLE: POSITION_DESIGNER")
        position_context = position_role_payload["position_context"]
        self.assertNotIn("current_show_snapshot", position_role_payload)
        self.assertEqual(position_context["coordinate_system"], self.normalized["coordinate_system"])
        self.assertEqual(position_role_payload["rig_design_artifact"], rig)
        self.assertEqual(position_context["show_fingerprint"], FINGERPRINT)

    def test_critic_blocker_keeps_execution_complete_and_finalizer_cannot_clear_review(self):
        class BlockerAdapter(_RoleAdapter):
            def complete(self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                self.calls.append((role, payload))
                if role == "ROLE: CRITIC":
                    return json.dumps({
                        "schema": "zen.multi_agent_critic.v0.1",
                        "strengths": [], "problems": ["verified blocker"],
                        "severity": {"classification": "BLOCKER", "rationale": "unverified physical facts"},
                        "revision_requests": [{"request": "Calibrate physical semantics."}],
                        "codex_artistic_intervention": "NONE",
                    })
                return super().complete(slot, system=system, user=user)

        adapter = BlockerAdapter(self.normalized)
        run = run_multi_agent_design(
            self._router(adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id="live-review-blocker", current_show_snapshot=self.input,
        )
        state = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        review = json.loads((run.run_path / "design_review.json").read_text(encoding="utf-8"))
        finalizer_envelope = json.loads((run.run_path / "steps" / "finalizer.json").read_text(encoding="utf-8"))
        final_payload = next(payload for role, payload in adapter.calls if role == "ROLE: FINALIZER")
        self.assertEqual(state["status"], "COMPLETE")
        self.assertEqual(state["execution_status"], "COMPLETE")
        self.assertEqual(state["design_review_status"], "BLOCKED_BY_CRITIC")
        self.assertEqual(run.design_review_status, "BLOCKED_BY_CRITIC")
        self.assertEqual(review["critic_severity"], "BLOCKER")
        self.assertEqual(review["WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(review["RESOLVER_ELIGIBLE"], "NO")
        self.assertEqual(review["PREVIEW_FOR_WRITEBACK_ELIGIBLE"], "NO")
        self.assertEqual(final_payload["design_review_state"]["design_review_status"], "BLOCKED_BY_CRITIC")
        self.assertEqual(final_payload["latest_critic_artifact"]["severity"]["classification"], "BLOCKER")
        self.assertEqual(finalizer_envelope["design_review_state"]["design_review_status"], "BLOCKED_BY_CRITIC")
        self.assertEqual(finalizer_envelope["design_review_state"]["execution_status"], "COMPLETE")

    def _completed_calibration(self, run_id: str) -> dict[str, object]:
        facts = {field: "UNKNOWN" for field in CALIBRATION_FACT_FIELDS}
        facts.update(MA2_COORDINATE_CONCEPTS)
        facts.update({
            "COORDINATE_FRAME_VERIFIED": "PARTIAL",
            "CURRENT_SHOW_FINGERPRINT_MATCHES_LIVE_SCAN": "VERIFIED",
            "GEOMETRY_BEARING_RESOURCES_AVAILABLE": "VERIFIED",
            "PROTECTED_RESOURCES_IDENTIFIED": "VERIFIED",
            "CURRENT_SHOW_X_SIGN_MAPPING": "OPERATOR_VERIFIED_POSITIVE_X_STAGE_LEFT",
            "CURRENT_SHOW_Y_SIGN_MAPPING": "OPERATOR_VERIFIED_NEGATIVE_Y_AUDIENCE",
            "CURRENT_SHOW_Z_SIGN_MAPPING": "OPERATOR_VERIFIED_POSITIVE_Z_UP",
            "AUDIENCE_DIRECTION_KNOWN": "OPERATOR_VERIFIED",
            "STAGE_LEFT_RIGHT_KNOWN": "OPERATOR_VERIFIED",
            "UPSTAGE_DOWNSTAGE_KNOWN": "OPERATOR_VERIFIED",
            "STAGE_BOUNDS_KNOWN": "KNOWN_FROM_OPERATOR_STAGE_PLAN",
            "PERFORMER_ZONE_KNOWN": "KNOWN_FROM_OPERATOR_STAGE_PLAN",
            "CURRENT_FINGERPRINT_CAPABILITY_PROFILES_AVAILABLE": "SHOW_BOUND_VERIFIED",
        })
        return {
            "schema": CALIBRATION_SCHEMA,
            "gate_id": "SHEESH_SPATIAL_FACT_CALIBRATION_001",
            "show_fingerprint": FINGERPRINT,
            "source_artifacts": {
                "run_id": run_id,
                "normalized_snapshot_source_hash": self.normalized["source_artifact_hash"],
            },
            "facts": facts,
            "fact_evidence": {
                field: "Synthetic evidence with explicit scope; unknown remains unknown."
                for field in CALIBRATION_FACT_FIELDS
            },
            "software_coordinate_semantics": {
                "values": dict(MA2_COORDINATE_CONCEPTS),
                "fixture_transform": dict(MA2_FIXTURE_TRANSFORM_SEMANTICS),
                "sources": [
                    {
                        "title": "grandMA2 XYZ coordinate help",
                        "url": "https://help.malighting.com/grandMA2/en/help/key_xyz.html",
                        "scope": "Software coordinate concepts only; not venue mapping or fixture-position units.",
                    },
                    {
                        "title": "grandMA2 fixture position help",
                        "url": "https://help.malighting.com/grandMA2/en/help/key_patch_position_fixtures.html",
                        "scope": "Fixture Pos/Rot and Stage/Object axis controls; not venue signs or Pos units.",
                    },
                ],
            },
            "geometry_evidence": {
                "geometry_bearing_resource_count": 2,
                "protected_fixture_ids": [9999],
            },
            "current_live_machine_observation": {"show_fingerprint": FINGERPRINT},
            "show_bound_capability_profiles": {"profiles": [{
                "show_fingerprint": FINGERPRINT,
                "fixture_id": 101,
                "confidence": "SHOW_BOUND_VERIFIED",
                "observed_attributes": ["DIM"],
            }]},
            "current_show_venue_mapping_evidence": {
                "show_fingerprint": FINGERPRINT,
                "source_type": "OPERATOR_SUPPLIED_CURRENT_SHOW_COORDINATE_MAPPING",
                "independent_of_pan_tilt": True,
                "independent_of_software_convention": True,
                "source_reference": "synthetic operator stage-plan annotation",
                "mappings": {
                    "CURRENT_SHOW_X_SIGN_MAPPING": facts["CURRENT_SHOW_X_SIGN_MAPPING"],
                    "CURRENT_SHOW_Y_SIGN_MAPPING": facts["CURRENT_SHOW_Y_SIGN_MAPPING"],
                    "CURRENT_SHOW_Z_SIGN_MAPPING": facts["CURRENT_SHOW_Z_SIGN_MAPPING"],
                },
            },
            "CODEX_ARTISTIC_INTERVENTION": "NONE",
        }

    def _bootstrap_input(self):
        return CurrentShowSnapshotInput(
            self.raw_snapshot,
            spatial_bootstrap_mode="NEW_UNDESIGNED_SHOW",
            operator_stage_context=_operator_stage_context(),
            show_bound_capability_profiles=_show_bound_capabilities(),
        )

    def _create_bootstrap_source(self, run_id: str):
        bootstrap_input = self._bootstrap_input()
        adapter = _RoleAdapter(self.normalized)
        source = run_multi_agent_design(
            self._router(adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id=run_id, current_show_snapshot=bootstrap_input,
        )
        return bootstrap_input, source

    def test_owner_rejects_non_blocker_bootstrap_run_with_brief_and_visual_evidence(self):
        run_id = "owner-revision-bootstrap"
        bootstrap_input, source = self._create_bootstrap_source(run_id)
        source_state_before = json.loads((source.run_path / "run.json").read_text(encoding="utf-8"))
        source_critic_before = (source.run_path / "steps" / "critic.json").read_bytes()
        # Simulate a completed pre-provenance legacy run: its run.json hash is
        # authoritative, but the original request bytes were never retained.
        (source.run_path / "source_request.txt").unlink()
        visual_bytes = (
            b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + (1151).to_bytes(4, "big") + (680).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
        )
        writeback = source.run_path / "writeback"
        writeback.mkdir()
        (writeback / "actual.png").write_bytes(visual_bytes)
        visual_hash = hashlib.sha256(visual_bytes).hexdigest()
        visual_metadata = {
            "schema": "zen.ma2_postwrite_stage_view_evidence.v0.1",
            "source_run_id": run_id,
            "show_fingerprint": FINGERPRINT,
            "evidence_type": "MA2_POSTWRITE_STAGE_VIEW",
            "capture_time": "2026-09-21T17:41:25.793+08:00",
            "sha256": visual_hash,
            "mime_type": "image/png",
            "pixel_width": 1151,
            "pixel_height": 680,
            "relative_path": "writeback/actual.png",
        }

        class RevisionAdapter:
            def __init__(self): self.calls = []
            def complete(self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                self.calls.append((role, payload, None, system))
                if role == "ROLE: RIG_DESIGNER_REVISION":
                    return json.dumps(_rig(payload["current_show_snapshot"]))
                if role == "ROLE: POSITION_DESIGNER_REVISION":
                    return json.dumps(_position(payload["position_context"]))
                if role == "ROLE: LIGHTING_DESIGNER": return json.dumps(_draft())
                if role == "ROLE: CRITIC": return json.dumps(_critic())
                if role == "ROLE: FINALIZER": return json.dumps(_final(payload["position_design_artifact"]))
                raise AssertionError(role)
            def complete_with_image(self, slot, *, system, user, visual_evidence):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                self.calls.append((role, payload, visual_evidence.sha256, system))
                if role == "ROLE: RIG_DESIGNER_REVISION":
                    return json.dumps(_rig(payload["current_show_snapshot"]))
                if role == "ROLE: POSITION_DESIGNER_REVISION":
                    return json.dumps(_position(payload["position_context"]))
                if role == "ROLE: CRITIC": return json.dumps(_critic())
                raise AssertionError(f"Unexpected visual provider role: {role}")

        adapter = RevisionAdapter()
        brief = "owner directed structure brief"
        result = run_spatial_revision_loop(
            self._router(adapter), request="guessed replacement must not become source authority", repo_root=self.repo_root,
            run_id=run_id, current_show_snapshot=bootstrap_input,
            owner_decision="REJECT_FOR_REVISION", owner_revision_brief=brief,
            postwrite_visual_evidence=visual_metadata, revision_id="owner-directed",
            max_cycles=1,
        )
        roles = [item[0] for item in adapter.calls]
        self.assertEqual(roles, [
            "ROLE: RIG_DESIGNER_REVISION", "ROLE: POSITION_DESIGNER_REVISION",
            "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC", "ROLE: FINALIZER",
        ])
        self.assertEqual([item[2] for item in adapter.calls if item[2]], [visual_hash])
        for role in ("rig_designer", "position_designer"):
            step = json.loads((result.run_path / "cycle_01" / "steps" / f"{role}.json").read_text(encoding="utf-8"))
            self.assertEqual(step["VISUAL_EVIDENCE_SENT"], "NO")
            self.assertIsNone(step["VISUAL_EVIDENCE_SHA256"])
        critic_step = json.loads((result.run_path / "cycle_01" / "steps" / "critic.json").read_text(encoding="utf-8"))
        self.assertEqual(critic_step["VISUAL_EVIDENCE_SENT"], "YES")
        self.assertEqual(critic_step["VISUAL_EVIDENCE_SHA256"], visual_hash)
        self.assertEqual(critic_step["VISUAL_CRITIC_STATUS"], "PASS")
        position_call = next(call for call in adapter.calls if call[0] == "ROLE: POSITION_DESIGNER_REVISION")
        self.assertNotIn("postwrite_visual_evidence", position_call[1])
        self.assertEqual(result.design_review_state["design_review_status"], "REVIEW_PASSED")
        saved = json.loads((result.run_path / "revision_run.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["REVISION_TRIGGER"], "OWNER_REJECT_FOR_REVISION")
        self.assertEqual(saved["SOURCE_CRITIC_SEVERITY"], "NONE")
        self.assertEqual(saved["SPATIAL_FACT_CALIBRATION_STATUS"], "NOT_APPLICABLE_NEW_UNDESIGNED_SHOW")
        self.assertEqual(saved["OWNER_REVISION_BRIEF"], brief)
        self.assertEqual(saved["OWNER_REVISION_BRIEF_HASH"], hashlib.sha256(brief.encode("utf-8")).hexdigest())
        self.assertTrue(saved["POSTWRITE_VISUAL_EVIDENCE_VERIFIED"])
        self.assertEqual(saved["SOURCE_REQUEST_HASH"], source_state_before["REQUEST_HASH"])
        self.assertEqual(saved["ORIGINAL_REQUEST_TEXT_STATUS"], "UNAVAILABLE_LEGACY_RUN")
        self.assertEqual(saved["SOURCE_REQUEST_HASH_AUTHORITY"], "RUN_JSON")
        self.assertTrue(all("user_request" not in call[1] for call in adapter.calls))
        self.assertTrue(all(
            call[1]["request_provenance"] == {
                "original_request_text": "UNAVAILABLE_LEGACY_RUN",
                "original_request_hash": source_state_before["REQUEST_HASH"],
                "source_request_hash_authority": "RUN_JSON",
            }
            for call in adapter.calls
        ))
        source_state_after = json.loads((source.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(source_state_after["REQUEST_HASH"], source_state_before["REQUEST_HASH"])
        self.assertEqual(source_state_after["CONTEXT_HASH"], source_state_before["CONTEXT_HASH"])
        self.assertEqual(source_state_after["CURRENT_SHOW_FINGERPRINT"], source_state_before["CURRENT_SHOW_FINGERPRINT"])
        self.assertEqual((source.run_path / "steps" / "critic.json").read_bytes(), source_critic_before)
        critic_payload = next(call[1] for call in adapter.calls if call[0] == "ROLE: CRITIC")
        self.assertNotIn("relative_path", critic_payload["postwrite_visual_evidence"])

    def test_visual_critic_provider_failure_falls_back_to_required_text_critic(self):
        run_id = "owner-revision-visual-best-effort"
        bootstrap_input, source = self._create_bootstrap_source(run_id)
        visual_bytes = (
            b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + (1151).to_bytes(4, "big") + (680).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
        )
        writeback = source.run_path / "writeback"
        writeback.mkdir()
        (writeback / "actual.png").write_bytes(visual_bytes)
        evidence = {
            "schema": "zen.ma2_postwrite_stage_view_evidence.v0.1",
            "source_run_id": run_id,
            "show_fingerprint": FINGERPRINT,
            "evidence_type": "MA2_POSTWRITE_STAGE_VIEW",
            "capture_time": "2026-09-21T17:41:25.793+08:00",
            "sha256": hashlib.sha256(visual_bytes).hexdigest(),
            "mime_type": "image/png", "pixel_width": 1151, "pixel_height": 680,
            "relative_path": "writeback/actual.png",
        }

        class VisionUnavailableAdapter(_RoleAdapter):
            def __init__(self, snapshot):
                super().__init__(snapshot)
                self.visual_calls = 0

            def complete(self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                if role == "ROLE: RIG_DESIGNER_REVISION":
                    self.calls.append((role, payload))
                    return json.dumps(_rig(payload["current_show_snapshot"]))
                if role == "ROLE: POSITION_DESIGNER_REVISION":
                    self.calls.append((role, payload))
                    return json.dumps(_position(payload["position_context"]))
                return super().complete(slot, system=system, user=user)

            def complete_with_image(self, slot, *, system, user, visual_evidence):
                self.visual_calls += 1
                raise ProviderUnavailable("Provider slot 1 request failed: HTTPError 400")

        adapter = VisionUnavailableAdapter(self.normalized)
        result = run_spatial_revision_loop(
            self._router(adapter), repo_root=self.repo_root, run_id=run_id,
            current_show_snapshot=bootstrap_input,
            owner_decision="REJECT_FOR_REVISION", owner_revision_brief="owner brief",
            postwrite_visual_evidence=evidence, revision_id="visual-best-effort",
            max_cycles=1, max_role_attempts=1,
        )
        self.assertEqual(adapter.visual_calls, 1)
        self.assertEqual(result.design_review_state["design_review_status"], "REVIEW_PASSED")
        critic_step = json.loads((result.run_path / "cycle_01" / "steps" / "critic.json").read_text(encoding="utf-8"))
        self.assertEqual(critic_step["STRUCTURAL_CRITIC_COMPLETE"], "YES")
        self.assertEqual(critic_step["VISUAL_CRITIC_STATUS"], "UNAVAILABLE_FREE_PROVIDER")
        self.assertEqual(critic_step["VISUAL_CRITIC_FAILURE_CLASS"], "PROVIDER_ERROR")
        self.assertEqual(critic_step["VISUAL_EVIDENCE_SENT"], "NO")
        self.assertTrue((result.run_path / "cycle_01" / "visual_critic" / "diagnostics" / "critic_visual-01.json").exists())
        self.assertEqual(critic_step["artifact"]["schema"], "zen.multi_agent_critic.v0.1")

    def test_legacy_revision_fails_closed_without_well_formed_request_hash(self):
        for run_id, bad_value, error in (
            ("legacy-missing-request-hash", None, "valid REQUEST_HASH"),
            ("legacy-malformed-request-hash", "not-a-sha256", "valid REQUEST_HASH"),
        ):
            with self.subTest(run_id=run_id):
                bootstrap_input, source = self._create_bootstrap_source(run_id)
                (source.run_path / "source_request.txt").unlink()
                state_path = source.run_path / "run.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if bad_value is None:
                    state.pop("REQUEST_HASH", None)
                else:
                    state["REQUEST_HASH"] = bad_value
                state_path.write_text(json.dumps(state), encoding="utf-8")

                class NoCallAdapter:
                    def complete(self, slot, *, system, user):
                        raise AssertionError("provider must not run for invalid legacy request provenance")

                with self.assertRaisesRegex(MultiAgentRunError, error):
                    run_spatial_revision_loop(
                        self._router(NoCallAdapter()), repo_root=self.repo_root,
                        run_id=run_id, current_show_snapshot=bootstrap_input,
                        owner_decision="REJECT_FOR_REVISION", owner_revision_brief="owner brief",
                        revision_id="invalid-request-provenance",
                    )

    def test_source_request_is_persisted_exactly_and_future_revision_rejects_tampering(self):
        run_id = "source-request-tamper"
        bootstrap_input, source = self._create_bootstrap_source(run_id)
        source_request = (source.run_path / "source_request.txt").read_bytes()
        self.assertEqual(source_request, "BABYMONSTER - SHEESH".encode("utf-8"))
        state = json.loads((source.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(state["REQUEST_HASH"], _sha256({"user_request": source_request.decode("utf-8")}))
        self.assertEqual(state["ORIGINAL_REQUEST_TEXT_STATUS"], "AVAILABLE_SOURCE_REQUEST")
        self.assertEqual(state["SOURCE_REQUEST_HASH_AUTHORITY"], "SOURCE_REQUEST_FILE_AND_RUN_JSON")
        (source.run_path / "source_request.txt").write_bytes(b"changed request")

        class NoCallAdapter:
            def complete(self, slot, *, system, user):
                raise AssertionError("provider must not run after source request tampering")

        with self.assertRaisesRegex(MultiAgentRunError, "source_request.txt hash does not match"):
            run_spatial_revision_loop(
                self._router(NoCallAdapter()), repo_root=self.repo_root,
                run_id=run_id, current_show_snapshot=bootstrap_input,
                owner_decision="REJECT_FOR_REVISION", owner_revision_brief="owner brief",
                revision_id="tampered-source-request",
            )
        with self.assertRaisesRegex(MultiAgentRunError, "source_request.txt hash does not match"):
            run_multi_agent_design(
                self._router(NoCallAdapter()), request="BABYMONSTER - SHEESH",
                repo_root=self.repo_root, run_id=run_id, current_show_snapshot=bootstrap_input,
            )

    def test_revision_rejects_context_fingerprint_and_checkpoint_mismatch(self):
        run_id = "revision-provenance-mismatch"
        bootstrap_input, source = self._create_bootstrap_source(run_id)
        state_path = source.run_path / "run.json"
        original_state_bytes = state_path.read_bytes()
        researcher_path = source.run_path / "steps" / "researcher.json"
        original_researcher_bytes = researcher_path.read_bytes()

        class NoCallAdapter:
            def complete(self, slot, *, system, user):
                raise AssertionError("provider must not run after source provenance mismatch")

        try:
            for field, invalid_value, expected_error in (
                ("CONTEXT_HASH", "0" * 64, "context hash"),
                ("CURRENT_SHOW_FINGERPRINT", "0" * 64, "Show fingerprint"),
                ("CURRENT_SHOW_SNAPSHOT_SOURCE_HASH", "0" * 64, "snapshot source hash"),
            ):
                with self.subTest(field=field):
                    state = json.loads(original_state_bytes)
                    state[field] = invalid_value
                    state_path.write_text(json.dumps(state), encoding="utf-8")
                    with self.assertRaisesRegex(MultiAgentRunError, expected_error):
                        run_spatial_revision_loop(
                            self._router(NoCallAdapter()), repo_root=self.repo_root,
                            run_id=run_id, current_show_snapshot=bootstrap_input,
                            owner_decision="REJECT_FOR_REVISION", owner_revision_brief="owner brief",
                            revision_id=f"mismatch-{field.lower()}",
                        )
            state_path.write_bytes(original_state_bytes)
            researcher = json.loads(original_researcher_bytes)
            researcher["artifact_hash"] = "0" * 64
            researcher_path.write_text(json.dumps(researcher), encoding="utf-8")
            with self.assertRaisesRegex(MultiAgentRunError, "artifact hash does not match"):
                run_spatial_revision_loop(
                    self._router(NoCallAdapter()), repo_root=self.repo_root,
                    run_id=run_id, current_show_snapshot=bootstrap_input,
                    owner_decision="REJECT_FOR_REVISION", owner_revision_brief="owner brief",
                    revision_id="mismatch-checkpoint",
                )
        finally:
            state_path.write_bytes(original_state_bytes)
            researcher_path.write_bytes(original_researcher_bytes)

    def test_non_blocker_revision_requires_nonempty_owner_brief(self):
        run_id = "owner-revision-brief-required"
        bootstrap_input, _source = self._create_bootstrap_source(run_id)
        class NoCallAdapter:
            def complete(self, slot, *, system, user):
                raise AssertionError("revision provider must not run without owner brief")
        with self.assertRaisesRegex(MultiAgentRunError, "non-empty owner_revision_brief"):
            run_spatial_revision_loop(
                self._router(NoCallAdapter()), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
                run_id=run_id, current_show_snapshot=bootstrap_input,
                owner_decision="REJECT_FOR_REVISION", revision_id="missing-owner-brief",
            )

    def test_imported_show_still_requires_exact_calibration_provenance(self):
        run_id = "imported-calibration-provenance"
        source_adapter = _RoleAdapter(self.normalized)
        run_multi_agent_design(
            self._router(source_adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id=run_id, current_show_snapshot=self.input,
        )
        calibration = self._completed_calibration(run_id)
        calibration["source_artifacts"]["run_id"] = "different-run"
        class NoCallAdapter:
            def complete(self, slot, *, system, user):
                raise AssertionError("provider must not run after calibration provenance mismatch")
        with self.assertRaisesRegex(MultiAgentRunError, "source_artifact|provenance|source run|Spatial revision evidence rejected"):
            run_spatial_revision_loop(
                self._router(NoCallAdapter()), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
                run_id=run_id, current_show_snapshot=self.input,
                calibration_artifact=calibration, owner_decision="REJECT_FOR_REVISION",
                owner_revision_brief="owner brief",
            )

    def _visual_evidence_fixture(self, root: Path, *, relative_path="writeback/image.png"):
        image_bytes = (
            b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + (10).to_bytes(4, "big") + (20).to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
        )
        (root / "writeback").mkdir(exist_ok=True)
        (root / "writeback" / "image.png").write_bytes(image_bytes)
        return image_bytes, {
            "schema": "zen.ma2_postwrite_stage_view_evidence.v0.1",
            "source_run_id": "visual-source",
            "show_fingerprint": FINGERPRINT,
            "evidence_type": "MA2_POSTWRITE_STAGE_VIEW",
            "capture_time": "2026-09-21T17:41:25.793+08:00",
            "sha256": hashlib.sha256(image_bytes).hexdigest(),
            "mime_type": "image/png", "pixel_width": 10, "pixel_height": 20,
            "relative_path": relative_path,
        }

    def test_visual_evidence_sha_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "visual-source"
            root.mkdir()
            _image, evidence = self._visual_evidence_fixture(root)
            evidence["sha256"] = "0" * 64
            with self.assertRaisesRegex(MultiAgentRunError, "SHA-256 does not match"):
                _load_postwrite_visual_evidence(evidence, source_run_id="visual-source", show_fingerprint=FINGERPRINT, source_run_path=root)

    def test_missing_visual_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "visual-source"
            root.mkdir()
            evidence = {
                "schema": "zen.ma2_postwrite_stage_view_evidence.v0.1", "source_run_id": "visual-source",
                "show_fingerprint": FINGERPRINT, "evidence_type": "MA2_POSTWRITE_STAGE_VIEW",
                "capture_time": "2026-09-21T17:41:25.793+08:00", "sha256": "0" * 64,
                "mime_type": "image/png", "pixel_width": 10, "pixel_height": 20,
                "relative_path": "writeback/missing.png",
            }
            with self.assertRaisesRegex(MultiAgentRunError, "missing"):
                _load_postwrite_visual_evidence(evidence, source_run_id="visual-source", show_fingerprint=FINGERPRINT, source_run_path=root)

    def test_visual_evidence_outside_source_run_writeback_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "visual-source"
            root.mkdir()
            _image, evidence = self._visual_evidence_fixture(root, relative_path="../outside.png")
            with self.assertRaisesRegex(MultiAgentRunError, "safe relative path"):
                _load_postwrite_visual_evidence(evidence, source_run_id="visual-source", show_fingerprint=FINGERPRINT, source_run_path=root)

    def test_revision_loop_passes_exact_prior_artifacts_and_stops_after_two_blockers(self):
        class InitialBlockerAdapter(_RoleAdapter):
            def complete(self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                if role == "ROLE: CRITIC":
                    return json.dumps({
                        "schema": "zen.multi_agent_critic.v0.1", "strengths": [],
                        "problems": ["blocker"],
                        "severity": {"classification": "BLOCKER", "rationale": "test evidence"},
                        "revision_requests": [{"request": "Consider verified facts only."}],
                        "codex_artistic_intervention": "NONE",
                    })
                return super().complete(slot, system=system, user=user)

        initial_adapter = InitialBlockerAdapter(self.normalized)
        source_run = run_multi_agent_design(
            self._router(initial_adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id="revision-source-blocker", current_show_snapshot=self.input,
        )
        source_artifacts = {
            name: json.loads((source_run.run_path / "steps" / f"{name}.json").read_text(encoding="utf-8"))["artifact"]
            for name in ("researcher", "rig_designer", "position_designer", "lighting_designer", "critic")
        }

        class RevisionAdapter:
            def __init__(self):
                self.calls = []

            def complete(self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                self.calls.append((role, payload))
                if role == "ROLE: RIG_DESIGNER_REVISION":
                    return json.dumps(_rig(payload["current_show_snapshot"]))
                if role == "ROLE: POSITION_DESIGNER_REVISION":
                    return json.dumps(_position(payload["position_context"]))
                if role == "ROLE: LIGHTING_DESIGNER":
                    return json.dumps(_draft())
                if role == "ROLE: CRITIC":
                    return json.dumps({
                        "schema": "zen.multi_agent_critic.v0.1", "strengths": [],
                        "problems": ["still blocked"],
                        "severity": {"classification": "BLOCKER", "rationale": "test evidence"},
                        "revision_requests": [{"request": "Continue only if evidence supports it."}],
                        "codex_artistic_intervention": "NONE",
                    })
                if role == "ROLE: FINALIZER":
                    return json.dumps(_final(payload["position_design_artifact"]))
                raise AssertionError(role)

        adapter = RevisionAdapter()
        result = run_spatial_revision_loop(
            self._router(adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
            run_id="revision-source-blocker", current_show_snapshot=self.input,
            calibration_artifact=self._completed_calibration("revision-source-blocker"), owner_decision="REJECT_FOR_REVISION",
            revision_id="bounded-two-cycles",
        )
        self.assertEqual(result.cycles_completed, 2)
        self.assertEqual(result.design_review_state["design_review_status"], "BLOCKED_AFTER_REVISION_LIMIT")
        self.assertEqual(result.design_review_state["WRITEBACK_ELIGIBLE"], "NO")
        role_calls = [role for role, _payload in adapter.calls]
        self.assertEqual(role_calls, [
            "ROLE: RIG_DESIGNER_REVISION", "ROLE: POSITION_DESIGNER_REVISION", "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC",
            "ROLE: RIG_DESIGNER_REVISION", "ROLE: POSITION_DESIGNER_REVISION", "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC",
            "ROLE: FINALIZER",
        ])
        cycle_one_rig = json.loads((result.run_path / "cycle_01" / "steps" / "rig_designer.json").read_text(encoding="utf-8"))["artifact"]
        cycle_one_position = json.loads((result.run_path / "cycle_01" / "steps" / "position_designer.json").read_text(encoding="utf-8"))["artifact"]
        cycle_one_lighting = json.loads((result.run_path / "cycle_01" / "steps" / "lighting_designer.json").read_text(encoding="utf-8"))["artifact"]
        cycle_one_critic = json.loads((result.run_path / "cycle_01" / "steps" / "critic.json").read_text(encoding="utf-8"))["artifact"]
        first_rig_payload = adapter.calls[0][1]
        self.assertEqual(first_rig_payload["semantic_role"], "RIG_DESIGNER_REVISION")
        self.assertEqual(first_rig_payload["revision_context"]["previous_rig_artifact"], source_artifacts["rig_designer"])
        self.assertEqual(first_rig_payload["revision_context"]["previous_position_artifact"], source_artifacts["position_designer"])
        self.assertEqual(first_rig_payload["revision_context"]["previous_lighting_artifact"], source_artifacts["lighting_designer"])
        self.assertEqual(first_rig_payload["revision_context"]["previous_critic_artifact"], source_artifacts["critic"])
        second_rig_payload = adapter.calls[4][1]
        self.assertEqual(second_rig_payload["semantic_role"], "RIG_DESIGNER_REVISION")
        self.assertEqual(second_rig_payload["revision_context"]["previous_rig_artifact"], cycle_one_rig)
        self.assertEqual(second_rig_payload["revision_context"]["previous_position_artifact"], cycle_one_position)
        self.assertEqual(second_rig_payload["revision_context"]["previous_lighting_artifact"], cycle_one_lighting)
        self.assertEqual(second_rig_payload["revision_context"]["previous_critic_artifact"], cycle_one_critic)
        finalizer_payload = adapter.calls[-1][1]
        self.assertEqual(finalizer_payload["rig_design_artifact"], result.latest_artifacts["rig_designer"])
        self.assertEqual(finalizer_payload["position_design_artifact"], result.latest_artifacts["position_designer"])
        self.assertEqual(finalizer_payload["latest_lighting_designer_artifact"], result.latest_artifacts["lighting_designer"])
        self.assertEqual(finalizer_payload["latest_critic_artifact"], result.latest_artifacts["critic"])
        self.assertEqual(finalizer_payload["design_review_state"]["design_review_status"], "BLOCKED_AFTER_REVISION_LIMIT")
        finalizer_envelope = json.loads((result.run_path / "steps" / "finalizer.json").read_text(encoding="utf-8"))
        self.assertEqual(finalizer_envelope["design_review_state"]["design_review_status"], "BLOCKED_AFTER_REVISION_LIMIT")
        self.assertEqual(result.final_design["position_design_reference"]["position_artifact_sha256"], _sha256(result.latest_artifacts["position_designer"]))
        self.assertEqual(result.latest_artifacts["position_designer"], _position(self.normalized))
        saved = json.loads((result.run_path / "revision_run.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["MA2_WRITES"], 0)
        self.assertEqual(saved["MAX_SPATIAL_REVISION_CYCLES"], 2)
        rig_diagnostic = json.loads((result.run_path / "cycle_01" / "diagnostics" / "rig_designer_revision-01.json").read_text(encoding="utf-8"))
        self.assertEqual(rig_diagnostic["role"], "rig_designer_revision")
        self.assertEqual(rig_diagnostic["provider_routing"]["semantic_role"], "RIG_DESIGNER_REVISION")

    def test_unknown_calibration_stops_before_provider_calls(self):
        class NoCallAdapter:
            def __init__(self):
                self.calls = []

            def complete(self, slot, *, system, user):
                self.calls.append((system, user))
                raise AssertionError("provider must not be called with unknown physical semantics")

        adapter = NoCallAdapter()
        unknown = {
            "schema": CALIBRATION_SCHEMA,
            "gate_id": "SHEESH_SPATIAL_FACT_CALIBRATION_001",
            "show_fingerprint": FINGERPRINT,
            "source_artifacts": {
                "run_id": "missing-run-not-reached",
                "normalized_snapshot_source_hash": self.normalized["source_artifact_hash"],
            },
            "facts": {**{field: "UNKNOWN" for field in CALIBRATION_FACT_FIELDS}, **MA2_COORDINATE_CONCEPTS},
            "fact_evidence": {field: "UNKNOWN in the synthetic test fixture." for field in CALIBRATION_FACT_FIELDS},
            "software_coordinate_semantics": {
                "values": dict(MA2_COORDINATE_CONCEPTS),
                "fixture_transform": dict(MA2_FIXTURE_TRANSFORM_SEMANTICS),
                "sources": [
                    {
                        "title": "grandMA2 XYZ coordinate help",
                        "url": "https://help.malighting.com/grandMA2/en/help/key_xyz.html",
                        "scope": "Software coordinate concepts only; not venue mapping or fixture-position units.",
                    },
                    {
                        "title": "grandMA2 fixture position help",
                        "url": "https://help.malighting.com/grandMA2/en/help/key_patch_position_fixtures.html",
                        "scope": "Fixture Pos/Rot and Stage/Object axis controls; not venue signs or Pos units.",
                    },
                ],
            },
            "geometry_evidence": {"geometry_bearing_resource_count": 2, "protected_fixture_ids": [9999]},
            "current_live_machine_observation": {"show_fingerprint": FINGERPRINT},
            "show_bound_capability_profiles": {"profiles": []},
            "CODEX_ARTISTIC_INTERVENTION": "NONE",
        }
        with self.assertRaisesRegex(MultiAgentRunError, "BLOCKED_MISSING_EVIDENCE"):
            run_spatial_revision_loop(
                self._router(adapter), request="BABYMONSTER - SHEESH", repo_root=self.repo_root,
                run_id="missing-run-not-reached", current_show_snapshot=self.input,
                calibration_artifact=unknown, owner_decision="REJECT_FOR_REVISION",
            )
        self.assertEqual(adapter.calls, [])

    def test_position_context_is_compact_deterministic_and_excludes_protected_geometry(self):
        context = build_position_context(self.normalized)
        self.assertEqual(context, build_position_context(self.normalized))
        self.assertEqual(context["coordinate_system"], self.normalized["coordinate_system"])
        self.assertEqual(
            context["geometry_resources"],
            [
                {
                    "fixture_id": 101,
                    "subfixture_id": 1,
                    "current_xyz": {"x": -1.0, "y": 2.0, "z": 3.0},
                    "current_rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "availability": "AVAILABLE_INVENTORY_ONLY",
                },
                {
                    "fixture_id": 102,
                    "subfixture_id": 1,
                    "current_xyz": {"x": 1.0, "y": 2.0, "z": 3.0},
                    "current_rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "availability": "AVAILABLE_INVENTORY_ONLY",
                },
            ],
        )
        self.assertEqual(context["allowed_placement_refs"], [
            {"fixture_id": 101, "subfixture_id": 1},
            {"fixture_id": 102, "subfixture_id": 1},
        ])
        self.assertEqual(context["protected_refs"], [{"fixture_id": 9999, "subfixture_id": 1}])
        encoded = json.dumps(context).casefold()
        self.assertNotIn("patch", encoded)
        self.assertNotIn('"address"', encoded)

    def test_new_undesigned_show_uses_canonical_frame_without_fixture_geometry_or_groups(self):
        raw = _snapshot()
        raw["groups"] = []
        raw["group_count"] = 0
        raw["resource_status"]["fixture_geometry"] = {
            "status": "not_available", "stale": False, "values": [],
        }
        supplied = CurrentShowSnapshotInput(
            raw,
            spatial_bootstrap_mode="NEW_UNDESIGNED_SHOW",
            operator_stage_context=_operator_stage_context(),
            show_bound_capability_profiles=_show_bound_capabilities(),
        )
        normalized = normalize_current_show_snapshot(supplied)
        frame = normalized["stage_frame"]
        self.assertEqual(normalized["initial_fixture_geometry"], "UNDESIGNED")
        self.assertEqual(normalized["geometry_record_count"], 0)
        self.assertEqual(frame["frame_id"], "ZEN_STAGE_FRAME_V1")
        self.assertEqual(frame["origin"], "STAGE_CENTER")
        self.assertEqual(frame["axes"], {
            "X_POSITIVE": "STAGE_LEFT", "X_NEGATIVE": "STAGE_RIGHT",
            "Y_POSITIVE": "UPSTAGE", "Y_NEGATIVE": "DOWNSTAGE_AUDIENCE",
            "Z_POSITIVE": "UP",
        })
        self.assertEqual(frame["raw_ma2_fixture_xyz_mapping"], "UNKNOWN_AND_NOT_INFERRED")
        self.assertEqual(frame["pan_tilt_calibration"]["xyz_sign_mapping_inference"], "PROHIBITED")
        varied_geometry = _snapshot()
        varied_geometry["resource_status"]["fixture_geometry"]["values"] = [
            {"fixture_id": fixture_id, "subfixture_id": 1,
             "position": {"x": 9000 + fixture_id, "y": -3000, "z": 700},
             "rotation": {"x": 20, "y": 40, "z": 60}}
            for fixture_id in (101, 102, 9999)
        ]
        varied = normalize_current_show_snapshot(CurrentShowSnapshotInput(
            varied_geometry,
            spatial_bootstrap_mode="NEW_UNDESIGNED_SHOW",
            operator_stage_context=_operator_stage_context(),
            show_bound_capability_profiles=_show_bound_capabilities(),
        ))
        self.assertEqual(varied["stage_frame"], frame)
        context = build_position_context(normalized)
        self.assertEqual(context["allowed_placement_refs"], [{"fixture_id": 101}, {"fixture_id": 102}])
        self.assertNotIn("current_xyz", json.dumps(context))
        self.assertNotIn("patch", json.dumps(context).casefold())
        self.assertNotIn('"address"', json.dumps(context).casefold())
        self.assertTrue(context["verified_capability_profiles"])

    def test_bootstrap_role_snapshot_excludes_scanned_positions(self):
        raw = _snapshot()
        raw["resource_status"]["fixture_geometry"]["values"] = [
            {"fixture_id": fixture_id, "subfixture_id": 1,
             "position": {"x": 0, "y": 0, "z": 0},
             "rotation": {"x": 0, "y": 0, "z": 0}}
            for fixture_id in (101, 102, 9999)
        ]
        normalized = normalize_current_show_snapshot(CurrentShowSnapshotInput(
            raw,
            spatial_bootstrap_mode="NEW_UNDESIGNED_SHOW",
            operator_stage_context=_operator_stage_context(),
            show_bound_capability_profiles=_show_bound_capabilities(),
        ))
        model_snapshot = _model_facing_current_show_snapshot(normalized)
        encoded = json.dumps(model_snapshot)
        self.assertIn("ZEN_STAGE_FRAME_V1", encoded)
        self.assertIn('"initial_fixture_geometry": "UNDESIGNED"', encoded)
        self.assertNotIn('"xyz"', encoded)
        self.assertNotIn('"rotation"', encoded)
        self.assertNotIn('"x": 0', encoded)

    def test_bootstrap_ignores_origin_geometry_and_allows_verified_inventory_layout(self):
        raw = _snapshot()
        raw["resource_status"]["fixture_geometry"]["values"] = [
            {"fixture_id": fixture_id, "subfixture_id": 1,
             "position": {"x": 0, "y": 0, "z": 0},
             "rotation": {"x": 0, "y": 0, "z": 0}}
            for fixture_id in (101, 102, 9999)
        ]
        supplied = CurrentShowSnapshotInput(
            raw,
            spatial_bootstrap_mode="NEW_UNDESIGNED_SHOW",
            operator_stage_context=_operator_stage_context(),
            show_bound_capability_profiles=_show_bound_capabilities(),
        )
        normalized = normalize_current_show_snapshot(supplied)
        self.assertNotIn("xyz", normalized["fixture_inventory"][0]["geometry"][0])
        position_context = build_position_context(normalized)
        self.assertEqual(position_context["coordinate_system"], normalized["stage_frame"])
        self.assertEqual(position_context["allowed_placement_refs"], [
            {"fixture_id": 101, "subfixture_id": 1},
            {"fixture_id": 102, "subfixture_id": 1},
        ])
        self.assertNotIn('"x": 0', json.dumps(position_context))

        artifact = _position(normalized, placements=[
            {"fixture_id": 101, "subfixture_id": 1, "show_fingerprint": FINGERPRINT,
             "xyz": {"x": -1, "y": -1, "z": 1}},
            {"fixture_id": 102, "subfixture_id": 1, "show_fingerprint": FINGERPRINT,
             "xyz": {"x": 1, "y": 0, "z": 2}},
        ])
        artifact["coordinate_system"] = normalized["stage_frame"]
        self.assertIs(validate_position_design_artifact(artifact, normalized), artifact)

    def test_position_prompt_has_exact_typed_contract_and_authoritative_coordinate_metadata(self):
        prompt = ROLE_SYSTEM_PROMPTS["position_designer"]
        for required in (
            'first key must be "schema" with exact value "zen.multi_agent_position_design.v0.1"',
            "show_fingerprint (string)",
            "coordinate_system (object copied exactly from position_context.coordinate_system)",
            "spatial_groups (array)",
            "placements (array)",
            "constraints (array)",
            "uncertainties (array)",
            'codex_artistic_intervention (exactly "NONE")',
            "Do not return coordinate_system as a string",
            "Do not omit empty arrays",
            "position_context.allowed_placement_refs",
        ):
            self.assertIn(required, prompt)

    def test_bootstrap_position_prompt_requires_layout_for_rig_selected_resources(self):
        prompt = _bootstrap_role_prompt("position_designer", ROLE_SYSTEM_PROMPTS["position_designer"])
        self.assertIn("every resource the validated Rig Designer explicitly selected for placement", prompt)
        self.assertIn("Do not silently omit a selected resource", prompt)
        self.assertEqual(
            _bootstrap_role_prompt("researcher", "base"),
            "base",
        )

    def test_bootstrap_position_prompt_requires_layout_for_rig_selected_resources(self):
        # The bootstrap-only contract is appended at runtime; this constant
        # prompt remains compatible with imported-Show runs.
        from zen_ma2_agent.llm.multi_agent_runtime import _bootstrap_role_prompt

        prompt = _bootstrap_role_prompt("position_designer", ROLE_SYSTEM_PROMPTS["position_designer"])
        self.assertIn("every resource the validated Rig Designer explicitly selected for placement", prompt)
        self.assertIn("Do not silently omit a selected resource", prompt)

    def test_position_retry_contract_is_specific_without_reauthoring_geometry(self):
        class RetryPositionAdapter(_RoleAdapter):
            def __init__(inner_self, snapshot):
                super().__init__(snapshot)
                inner_self.position_systems = []
                inner_self.position_calls = 0

            def complete(inner_self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                if role == "ROLE: POSITION_DESIGNER":
                    inner_self.calls.append((role, payload))
                    inner_self.position_systems.append(system)
                    inner_self.position_calls += 1
                    artifact = _position(payload["position_context"])
                    if inner_self.position_calls == 1:
                        artifact["coordinate_system"] = "UNKNOWN"
                    return json.dumps(artifact)
                return super(RetryPositionAdapter, inner_self).complete(slot, system=system, user=user)

        adapter = RetryPositionAdapter(self.normalized)
        run = run_multi_agent_design(
            self._router(adapter), request="position retry structure", repo_root=self.repo_root,
            run_id="position-retry-contract", current_show_snapshot=self.input,
        )
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")
        self.assertEqual(adapter.position_calls, 2)
        retry_prompt = adapter.position_systems[1]
        self.assertIn("coordinate_system must be the exact object supplied in position_context.coordinate_system", retry_prompt)
        self.assertIn("Preserve valid XYZ/artistic choices", retry_prompt)

    def test_position_coordinate_system_must_match_authoritative_snapshot_object(self):
        artifact = _position(self.normalized)
        artifact["coordinate_system"] = {"frame": "SCANNED_MA2_FIXTURE_COORDINATES", "axis_semantics": "STAGE_LEFT_RIGHT", "units": "METERS"}
        with self.assertRaisesRegex(MultiAgentRunError, "exactly match"):
            validate_position_design_artifact(artifact, self.normalized)

    def test_position_structural_required_fields_and_coordinate_type_remain_fail_closed(self):
        cases = (
            ("coordinate_system", "UNKNOWN", "coordinate_system must be an object"),
            ("placements", None, "missing required fields"),
            ("constraints", None, "missing required fields"),
            ("uncertainties", None, "missing required fields"),
            ("codex_artistic_intervention", None, "missing required fields"),
        )
        for field, replacement, message in cases:
            with self.subTest(field=field):
                artifact = _position(self.normalized)
                if replacement is None:
                    artifact.pop(field)
                else:
                    artifact[field] = replacement
                with self.assertRaisesRegex(MultiAgentRunError, message):
                    validate_position_design_artifact(artifact, self.normalized)

        wrong_fingerprint = _position(self.normalized)
        wrong_fingerprint["show_fingerprint"] = "b" * 64
        with self.assertRaisesRegex(MultiAgentRunError, "fingerprint"):
            validate_position_design_artifact(wrong_fingerprint, self.normalized)

    def test_current_show_facts_are_evidence_refs_not_research_sources(self):
        class CurrentShowEvidenceAdapter(_RoleAdapter):
            def complete(inner_self, slot, *, system, user):
                if system.split(". ", 1)[0] == "ROLE: RESEARCHER":
                    evidence_ref = f"CURRENT_SHOW:{inner_self.snapshot['show_fingerprint']}:fixture_inventory"
                    return json.dumps(_research() | {"evidence_refs": [evidence_ref]})
                return super(CurrentShowEvidenceAdapter, inner_self).complete(slot, system=system, user=user)

        adapter = CurrentShowEvidenceAdapter(self.normalized)
        run = run_multi_agent_design(
            self._router(adapter),
            request="BABYMONSTER - SHEESH",
            repo_root=self.repo_root,
            run_id="live-show-evidence-separation",
            current_show_snapshot=self.input,
        )
        researcher = json.loads((run.run_path / "steps" / "researcher.json").read_text(encoding="utf-8"))["artifact"]
        diagnostic = json.loads((run.run_path / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        evidence_ref = f"CURRENT_SHOW:{self.normalized['show_fingerprint']}:fixture_inventory"
        self.assertEqual(researcher["evidence_refs"], [evidence_ref])
        self.assertEqual(researcher["sources"], [])
        self.assertEqual(diagnostic["RESEARCHER_EVIDENCE_REFS_VALID"], "PASS")
        self.assertEqual(diagnostic["RESEARCHER_SOURCE_CONTRACT_VALID"], "PASS")
        self.assertEqual(diagnostic["RESEARCHER_CANONICAL_SOURCE_RESOLUTION"], "PASS")
        with self.assertRaises(ResearchSourceContractError):
            validate_research_source_contract([evidence_ref], [])
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")

    def test_spatial_role_prompts_require_exact_first_schema_key(self):
        self.assertIn(
            'first key must be "schema" with exact value "zen.multi_agent_rig_design.v0.1"',
            ROLE_SYSTEM_PROMPTS["rig_designer"],
        )
        self.assertIn(
            'first key must be "schema" with exact value "zen.multi_agent_position_design.v0.1"',
            ROLE_SYSTEM_PROMPTS["position_designer"],
        )

    def test_rig_missing_only_schema_is_normalized_then_validated(self):
        raw = _rig(self.normalized)
        del raw["schema"]

        normalized, audit = normalize_role_envelope("rig_designer", raw)

        self.assertTrue(audit["applied"])
        self.assertEqual(audit["fields_added"], ["schema"])
        self.assertEqual(next(iter(normalized)), "schema")
        self.assertEqual(dict(list(normalized.items())[1:]), raw)
        self.assertEqual(validate_rig_design_artifact(normalized, self.normalized), normalized)

    def test_position_missing_only_schema_is_normalized_then_validated(self):
        raw = _position(self.normalized)
        del raw["schema"]

        normalized, audit = normalize_role_envelope("position_designer", raw)

        self.assertTrue(audit["applied"])
        self.assertEqual(audit["schema_value"], "zen.multi_agent_position_design.v0.1")
        self.assertEqual(next(iter(normalized)), "schema")
        self.assertEqual(dict(list(normalized.items())[1:]), raw)
        self.assertEqual(validate_position_design_artifact(normalized, self.normalized), normalized)

    def test_wrong_or_malformed_spatial_schema_is_never_replaced(self):
        for role_name, artifact, validator in (
            ("rig_designer", _rig(self.normalized), validate_rig_design_artifact),
            ("position_designer", _position(self.normalized), validate_position_design_artifact),
        ):
            for wrong_schema in ("wrong.schema", None, ""):
                with self.subTest(role=role_name, schema=wrong_schema):
                    raw = dict(artifact)
                    raw["schema"] = wrong_schema
                    normalized, audit = normalize_role_envelope(role_name, raw)
                    self.assertIs(normalized, raw)
                    self.assertFalse(audit["applied"])
                    with self.assertRaisesRegex(MultiAgentRunError, "schema"):
                        validator(normalized, self.normalized)

    def test_missing_other_required_spatial_field_blocks_normalization(self):
        cases = (
            ("rig_designer", _rig(self.normalized), "spatial_strategy", validate_rig_design_artifact),
            ("rig_designer", _rig(self.normalized), "resource_assignments", validate_rig_design_artifact),
            ("position_designer", _position(self.normalized), "placements", validate_position_design_artifact),
        )
        for role_name, artifact, missing, validator in cases:
            with self.subTest(role=role_name, missing=missing):
                del artifact["schema"]
                del artifact[missing]
                normalized, audit = normalize_role_envelope(role_name, artifact)
                self.assertFalse(audit["applied"])
                with self.assertRaises(MultiAgentRunError):
                    validator(normalized, self.normalized)

    def test_codex_intervention_contract_blocks_spatial_normalization(self):
        for role_name, artifact, validator in (
            ("rig_designer", _rig(self.normalized), validate_rig_design_artifact),
            ("position_designer", _position(self.normalized), validate_position_design_artifact),
        ):
            for value in (None, "ARTISTIC_EDIT"):
                with self.subTest(role=role_name, value=value):
                    del artifact["schema"]
                    if value is None:
                        artifact.pop("codex_artistic_intervention")
                    else:
                        artifact["codex_artistic_intervention"] = value
                    normalized, audit = normalize_role_envelope(role_name, artifact)
                    self.assertFalse(audit["applied"])
                    with self.assertRaises(MultiAgentRunError):
                        validator(normalized, self.normalized)
                    artifact = _rig(self.normalized) if role_name == "rig_designer" else _position(self.normalized)

    def test_spatial_reference_validation_still_runs_after_schema_normalization(self):
        for fixture_id, message in ((777, "unknown fixture"), (9999, "9999")):
            raw = _rig(self.normalized, fixture_id=fixture_id)
            del raw["schema"]
            normalized, audit = normalize_role_envelope("rig_designer", raw)
            self.assertTrue(audit["applied"])
            with self.assertRaisesRegex(MultiAgentRunError, message):
                validate_rig_design_artifact(normalized, self.normalized)
        for fixture_id, message in ((777, "unknown geometry-bearing"), (9999, "9999")):
            raw = _position(self.normalized, placements=[{
                "fixture_id": fixture_id,
                "subfixture_id": 1,
                "show_fingerprint": FINGERPRINT,
                "xyz": {"x": 0, "y": 0, "z": 0},
            }])
            del raw["schema"]
            normalized, audit = normalize_role_envelope("position_designer", raw)
            self.assertTrue(audit["applied"])
            with self.assertRaisesRegex(MultiAgentRunError, message):
                validate_position_design_artifact(normalized, self.normalized)

    def test_pipeline_preserves_raw_response_when_spatial_schema_is_normalized(self):
        class MissingSchemaAdapter(_RoleAdapter):
            def complete(inner_self, slot, *, system, user):
                payload = json.loads(user)
                role = system.split(". ", 1)[0]
                inner_self.calls.append((role, payload))
                if role == "ROLE: RESEARCHER":
                    return json.dumps(_research())
                if role == "ROLE: RIG_DESIGNER":
                    artifact = _rig(payload["current_show_snapshot"])
                    del artifact["schema"]
                    return json.dumps(artifact)
                if role == "ROLE: POSITION_DESIGNER":
                    artifact = _position(payload["position_context"])
                    del artifact["schema"]
                    return json.dumps(artifact)
                if role == "ROLE: LIGHTING_DESIGNER":
                    return json.dumps(_draft())
                if role == "ROLE: CRITIC":
                    return json.dumps(_critic())
                if role == "ROLE: FINALIZER":
                    return json.dumps(_final(payload["position_design_artifact"]))
                raise AssertionError(role)

        adapter = MissingSchemaAdapter(self.normalized)
        run = run_multi_agent_design(
            self._router(adapter), request="schema normalization audit", repo_root=self.repo_root,
            run_id="spatial-schema-normalization", current_show_snapshot=self.input,
        )

        for role_name in ("rig_designer", "position_designer"):
            step = json.loads((run.run_path / "steps" / f"{role_name}.json").read_text(encoding="utf-8"))
            diagnostic = json.loads((run.run_path / "diagnostics" / f"{role_name}-01.json").read_text(encoding="utf-8"))
            attempt = json.loads((run.run_path / "attempts" / f"{role_name}-01.json").read_text(encoding="utf-8"))
            self.assertTrue(step["structural_normalization"]["applied"])
            self.assertTrue(diagnostic["structural_normalization"]["applied"])
            self.assertTrue(attempt["structural_normalization"]["applied"])
            self.assertNotIn("schema", json.loads(attempt["raw_response"]))
            self.assertEqual(
                attempt["response_sha256"],
                hashlib.sha256(attempt["raw_response"].encode("utf-8")).hexdigest(),
            )
            self.assertIn("schema", step["artifact"])

    def test_structural_normalization_raw_response_remains_secret_safe(self):
        secret = "private-spatial-provider-key"

        class SecretAdapter:
            def complete(inner_self, slot, *, system, user):
                payload = json.loads(user)
                if system.startswith("ROLE: RESEARCHER"):
                    return json.dumps(_research())
                if system.startswith("ROLE: RIG_DESIGNER"):
                    artifact = _rig(payload["current_show_snapshot"])
                    del artifact["schema"]
                    artifact["spatial_strategy"] = secret
                    return json.dumps(artifact)
                raise AssertionError(system)

        slot = ProviderSlot(1, "OPENAI_COMPATIBLE", "secret-test", "https://example.test/v1", secret, (), 5)
        with self.assertRaisesRegex(MultiAgentRunError, "provider secret"):
            run_multi_agent_design(
                ProviderRouter("PRIMARY_ONLY", (slot,), SecretAdapter()),
                request="secret-safe normalization", repo_root=self.repo_root,
                run_id="spatial-schema-secret-guard", current_show_snapshot=self.input,
            )
        attempt_path = Path(self.temp.name) / "projects" / "runs" / "spatial-schema-secret-guard" / "attempts" / "rig_designer-01.json"
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        self.assertEqual(attempt["secret_check"], "FAIL")
        self.assertNotIn("raw_response", attempt)
        self.assertNotIn(secret, json.dumps(attempt))

    def test_existing_schema_valid_spatial_outputs_are_unchanged(self):
        for role_name, artifact in (
            ("rig_designer", _rig(self.normalized)),
            ("position_designer", _position(self.normalized)),
        ):
            normalized, audit = normalize_role_envelope(role_name, artifact)
            self.assertIs(normalized, artifact)
            self.assertEqual(audit, {"applied": False, "fields_added": []})

    def test_legacy_four_role_path_remains_compatible_without_live_snapshot(self):
        class FourRoleAdapter:
            def __init__(self):
                self.roles = []

            def complete(self, slot, *, system, user):
                role = system.split(". ", 1)[0]
                self.roles.append(role)
                artifact = {
                    "ROLE: RESEARCHER": _research(),
                    "ROLE: LIGHTING_DESIGNER": _draft(),
                    "ROLE: CRITIC": _critic(),
                    "ROLE: FINALIZER": _final(_position(self.normalized)),
                }[role]
                return json.dumps(artifact)

        adapter = FourRoleAdapter()
        adapter.normalized = self.normalized
        run = run_multi_agent_design(self._router(adapter), request="legacy", repo_root=self.repo_root, run_id="no-live-four-roles")
        self.assertEqual(adapter.roles, ["ROLE: RESEARCHER", "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC", "ROLE: FINALIZER"])
        state = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertIsNone(state["CURRENT_SHOW_FINGERPRINT"])
        self.assertEqual(state["LIVE_SHOW_SNAPSHOT_IN_CONTEXT"], "NO")
        self.assertEqual(state["execution_status"], "COMPLETE")
        self.assertEqual(state["design_review_status"], "NOT_APPLICABLE")
        self.assertEqual(run.design_review_status, "NOT_APPLICABLE")

    def test_snapshot_changes_context_hash_and_is_saved_as_normalized_run_input(self):
        adapter = _RoleAdapter(self.normalized)
        run = run_multi_agent_design(self._router(adapter), request="SHEESH", repo_root=self.repo_root, run_id="context-hash-live", current_show_snapshot=self.input)
        state = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(state["CONTEXT_HASH"], run.context_hash)
        self.assertEqual(state["CURRENT_SHOW_FINGERPRINT"], FINGERPRINT)
        saved = json.loads((run.run_path / "normalized_current_show_snapshot.json").read_text(encoding="utf-8"))
        self.assertEqual(saved, self.normalized)
        self.assertNotIn("patch", json.dumps(saved).casefold())
        self.assertNotIn('"address"', json.dumps(saved).casefold())

    def test_changed_show_fingerprint_rejects_checkpoint_resume(self):
        class InterruptedAdapter:
            def __init__(self):
                self.calls = 0

            def complete(self, slot, *, system, user):
                self.calls += 1
                if system.startswith("ROLE: RESEARCHER"):
                    return json.dumps(_research())
                raise ProviderUnavailable("bounded simulated stop")

        first_adapter = InterruptedAdapter()
        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(self._router(first_adapter), request="SHEESH", repo_root=self.repo_root, run_id="fingerprint-resume", current_show_snapshot=self.input, max_role_attempts=1)
        changed = _snapshot("b" * 64)
        changed_adapter = _RoleAdapter(normalize_current_show_snapshot(changed))
        with self.assertRaisesRegex(MultiAgentRunError, "fingerprint"):
            run_multi_agent_design(self._router(changed_adapter), request="SHEESH", repo_root=self.repo_root, run_id="fingerprint-resume", current_show_snapshot=CurrentShowSnapshotInput(changed))
        self.assertEqual(changed_adapter.calls, [])

    def test_normalizer_excludes_patch_and_marks_fixture_9999_protected(self):
        normalized = self.normalized
        fixture_9999 = next(item for item in normalized["fixture_inventory"] if item["fixture_id"] == 9999)
        self.assertEqual(fixture_9999["availability"], "PROTECTED_UNAVAILABLE")
        encoded = json.dumps(normalized).casefold()
        self.assertNotIn("patch", encoded)
        self.assertNotIn('"address"', encoded)
        self.assertEqual(normalized["coordinate_system"]["axis_semantics"], "UNKNOWN")

    def test_profile_fingerprint_mismatch_is_rejected(self):
        profile = {"schema": "zen.show_profile.v0.1", "show_identity": {"value": "b" * 64}}
        with self.assertRaisesRegex(ValueError, "does not match"):
            normalize_current_show_snapshot(CurrentShowSnapshotInput(self.raw_snapshot, profile))

    def test_rig_rejects_unknown_fixture_and_fixture_9999(self):
        with self.assertRaisesRegex(MultiAgentRunError, "unknown fixture"):
            validate_rig_design_artifact(_rig(self.normalized, fixture_id=777), self.normalized)
        with self.assertRaisesRegex(MultiAgentRunError, "9999"):
            validate_rig_design_artifact(_rig(self.normalized, fixture_id=9999), self.normalized)

    def test_position_rejects_unknown_refs_duplicate_refs_and_non_finite_xyz(self):
        unknown = _position(self.normalized, placements=[{
            "fixture_id": 777, "subfixture_id": 1, "show_fingerprint": FINGERPRINT,
            "xyz": {"x": 0, "y": 0, "z": 0},
        }])
        with self.assertRaisesRegex(MultiAgentRunError, "unknown geometry-bearing"):
            validate_position_design_artifact(unknown, self.normalized)
        duplicate_placement = _position(self.normalized)
        duplicate_placement["placements"].append(dict(duplicate_placement["placements"][0]))
        with self.assertRaisesRegex(MultiAgentRunError, "duplicate"):
            validate_position_design_artifact(duplicate_placement, self.normalized)
        non_finite = _position(self.normalized)
        non_finite["placements"][0]["xyz"]["x"] = math.inf
        with self.assertRaisesRegex(MultiAgentRunError, "finite"):
            validate_position_design_artifact(non_finite, self.normalized)
        protected = _position(self.normalized, placements=[{
            "fixture_id": 9999, "subfixture_id": 1, "show_fingerprint": FINGERPRINT,
            "xyz": {"x": 0, "y": 0, "z": 0},
        }])
        with self.assertRaisesRegex(MultiAgentRunError, "9999"):
            validate_position_design_artifact(protected, self.normalized)

    def test_position_rejects_executable_command_fields_and_text(self):
        artifact = _position(self.normalized)
        artifact["ma2_commands"] = ["Store Sequence 1"]
        with self.assertRaisesRegex(MultiAgentRunError, "prohibited executable"):
            validate_position_design_artifact(artifact, self.normalized)
        artifact = _position(self.normalized)
        artifact["constraints"] = ["Move3D Fixture 101.1"]
        with self.assertRaisesRegex(MultiAgentRunError, "prohibited command"):
            validate_position_design_artifact(artifact, self.normalized)

    def test_rig_rejects_patch_fixture_type_identity_and_mutation_fields(self):
        artifact = _rig(self.normalized)
        artifact["patch"] = "10.001"
        with self.assertRaisesRegex(MultiAgentRunError, "patch mutation"):
            validate_rig_design_artifact(artifact, self.normalized)

    def test_finalizer_spatial_reference_and_geometry_consistency_are_enforced(self):
        position = _position(self.normalized)
        final = _final(position)
        validate_final_spatial_consistency(final, position, FINGERPRINT)
        contradictory = dict(final)
        contradictory["virtual_rig"] = {"placements": [{
            "fixture_id": 101, "subfixture_id": 1, "xyz": {"x": 99, "y": 1, "z": 4},
        }]}
        with self.assertRaisesRegex(MultiAgentRunError, "contradicts"):
            validate_final_spatial_consistency(contradictory, position, FINGERPRINT)

    def test_llm_runtime_has_no_ma_transport_builder_or_resolver_import(self):
        source = (self.repo_root / "zen_ma2_agent" / "llm" / "multi_agent_runtime.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("ma2" in name.casefold() or "builder" in name.casefold() or "resolver" in name.casefold() for name in imports))


if __name__ == "__main__":
    unittest.main()
