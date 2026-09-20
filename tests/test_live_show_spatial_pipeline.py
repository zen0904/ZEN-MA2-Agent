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
    ROLE_SYSTEM_PROMPTS,
    _sha256,
    normalize_role_envelope,
    run_multi_agent_design,
    validate_final_spatial_consistency,
    validate_position_design_artifact,
    validate_rig_design_artifact,
)
from zen_ma2_agent.llm.router import ProviderRouter, ProviderSlot, ProviderUnavailable


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
        "coordinate_system": {"axis_semantics": "UNKNOWN"},
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
            return json.dumps(_position(normalized))
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
                    artifact = _position(payload["current_show_snapshot"])
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
