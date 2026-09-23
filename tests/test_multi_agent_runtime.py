from __future__ import annotations

import json
import hashlib
import os
import tempfile
import unittest
import ast
import inspect
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.llm.autonomous_designer import build_designer_context
from zen_ma2_agent.llm.multi_agent_runtime import (
    MultiAgentRunError,
    ResearchSourceContractError,
    ROLE_SYSTEM_PROMPTS,
    _role_context,
    _run_role,
    _validate_artifact_evidence,
    run_multi_agent_design,
    validate_research_source_contract,
)
from zen_ma2_agent.llm.router import ProviderRouter, ProviderSlot, ProviderUnavailable
from zen_ma2_agent.run_checkpoints import read_step_artifact


def _research() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_research.v0.1",
        "research_status": "OFFLINE_CACHED_CONTEXT",
        "subject": "test request",
        "sources": [],
        "transferable_design_observations": [],
        "constraints": [],
        "uncertainties": [],
        "codex_artistic_intervention": "NONE",
    }


def _draft() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_designer_draft.v0.1",
        "design_intent": {"test": True},
        "visual_strategy": {"test": True},
        "resource_considerations": [],
        "uncertainties": [],
        "codex_artistic_intervention": "NONE",
    }


def _critic() -> dict[str, object]:
    return {
        "schema": "zen.multi_agent_critic.v0.1",
        "strengths": [],
        "problems": [],
        "severity": "NONE",
        "revision_requests": [],
        "codex_artistic_intervention": "NONE",
    }


def _final() -> dict[str, object]:
    return {
        "schema": "zen.autonomous_design.v0.1",
        "design_intent": {},
        "visual_strategy": {},
        "virtual_rig": {},
        "position_vocabulary": {},
        "main_sequence": {},
        "free_cue_layer": {},
        "evidence_trace": {},
        "codex_artistic_intervention": "NONE",
    }


class _SequenceAdapter:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)
        self.calls: list[tuple[int, str, str]] = []

    def complete(self, slot, *, system, user):
        self.calls.append((slot.number, system, user))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return json.dumps(value) if isinstance(value, dict) else value


class MultiAgentRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"ZEN_HOME": self.temp.name}, clear=False)
        self.environment.start()
        self.repo_root = Path(__file__).resolve().parents[1]

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    @staticmethod
    def _local_slot(*, roles=(), api_key=""):
        return ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "test-local", "http://127.0.0.1:8080/v1", api_key, roles, 5)

    def _router(self, responses, *, roles=(), mode="PRIMARY_ONLY"):
        adapter = _SequenceAdapter(responses)
        return ProviderRouter(mode, (self._local_slot(roles=roles),), adapter), adapter

    def _run_parallel_validation_case(self, run_id, failed_response, *, failed_api_key="private-candidate-key"):
        class Adapter:
            def complete(_self, slot, *, system, user):
                role = system.split(". ", 1)[0]
                if role == "ROLE: RESEARCHER":
                    return json.dumps(_research())
                if role == "ROLE: LIGHTING_DESIGNER":
                    return failed_response if slot.number == 1 else json.dumps(_draft())
                if role == "ROLE: CRITIC":
                    return json.dumps(_critic())
                if role == "ROLE: FINALIZER":
                    return json.dumps(_final())
                raise AssertionError(role)

        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE", "candidate-1", "https://one.example.test/v1", failed_api_key, ("LIGHTING_DESIGNER",), 5),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "candidate-2", "https://two.example.test/v1", "private-candidate-key-2", ("LIGHTING_DESIGNER",), 5),
            ProviderSlot(3, "OPENAI_COMPATIBLE_LOCAL", "support", "http://127.0.0.1:8080/v1", "", ("RESEARCHER", "CRITIC", "FINALIZER"), 5),
        )
        router = ProviderRouter(
            "FALLBACK", slots, Adapter(), parallelism=2,
            parallel_roles=("LIGHTING_DESIGNER",),
        )
        run = run_multi_agent_design(
            router, request="parallel validation diagnostic request", repo_root=self.repo_root,
            run_id=run_id, max_role_attempts=1,
        )
        return run, failed_api_key

    def _run_single_role_with_provider_fallback(self, role_name, success_artifact):
        role = role_name.upper()
        slots = tuple(
            ProviderSlot(
                number=number,
                provider_type="OPENAI_COMPATIBLE",
                model=f"provider-{number}",
                base_url=f"https://provider-{number}.example.test/v1",
                api_key=f"private-credential-{number}",
                roles=(role,),
                timeout_seconds=5,
            )
            for number in (1, 2, 3)
        )
        adapter = _SequenceAdapter([
            ProviderUnavailable("Provider slot 1 request failed: HTTPError 503 private-credential-1"),
            ProviderUnavailable("Provider slot 2 request failed: HTTPError 429 private-credential-2"),
            success_artifact,
        ])
        router = ProviderRouter("FALLBACK", slots, adapter, parallelism=1)
        run_path = Path(self.temp.name) / "projects" / "runs" / f"{role_name}-fallback"
        run_path.mkdir(parents=True, exist_ok=True)
        artifact, selected, attempts = _run_role(
            router,
            role_name=role_name,
            payload={"evidence_ledger": {"entries": []}},
            max_attempts=1,
            run_path=run_path,
        )
        diagnostic = json.loads((run_path / "diagnostics" / f"{role_name}-01.json").read_text(encoding="utf-8"))
        return router, adapter, artifact, selected, attempts, diagnostic

    def test_researcher_fallback_preserves_all_ordered_provider_attempts(self):
        router, adapter, artifact, selected, attempts, diagnostic = self._run_single_role_with_provider_fallback(
            "researcher", _research()
        )
        routing = diagnostic["provider_routing"]
        self.assertEqual([slot.number for slot in router.candidates("RESEARCHER")], [1, 2, 3])
        self.assertEqual([call[0] for call in adapter.calls], [1, 2, 3])
        self.assertEqual(selected.number, 3)
        self.assertEqual(attempts, 1)
        self.assertEqual(artifact["schema"], "zen.multi_agent_research.v0.1")
        self.assertEqual(
            [row["slot"] for row in routing["eligible_ordered_provider_candidates"]],
            [1, 2, 3],
        )
        self.assertEqual(routing["attempted_provider_slots"], [1, 2, 3])
        self.assertEqual(routing["selected_successful_slot"], 3)
        self.assertTrue(routing["fallback_used"])
        self.assertEqual([row["transport_status"] for row in routing["provider_attempts"]], ["FAILURE", "FAILURE", "SUCCESS"])
        self.assertEqual([row["failure_reason"] for row in routing["provider_attempts"][:2]], ["HTTPError 503", "HTTPError 429"])
        self.assertTrue(all(isinstance(row["provider_elapsed_seconds"], (int, float)) for row in routing["provider_attempts"]))

    def test_finalizer_fallback_preserves_same_provider_provenance(self):
        router, adapter, artifact, selected, _attempts, diagnostic = self._run_single_role_with_provider_fallback(
            "finalizer", _final()
        )
        routing = diagnostic["provider_routing"]
        self.assertEqual([call[0] for call in adapter.calls], [1, 2, 3])
        self.assertEqual(selected.number, 3)
        self.assertEqual(artifact["schema"], "zen.autonomous_design.v0.1")
        self.assertEqual([row["slot_number"] for row in routing["provider_attempts"]], [1, 2, 3])
        self.assertEqual(routing["selected_successful_slot"], 3)
        self.assertTrue(routing["fallback_used"])

    def test_single_role_fallback_success_does_not_erase_prior_failures(self):
        _router, _adapter, _artifact, _selected, _attempts, diagnostic = self._run_single_role_with_provider_fallback(
            "researcher", _research()
        )
        attempts = diagnostic["provider_routing"]["provider_attempts"]
        self.assertEqual([row["failure_reason"] for row in attempts[:2]], ["HTTPError 503", "HTTPError 429"])
        self.assertEqual(attempts[2]["candidate_status"], "VALID_ROLE_OUTPUT")
        self.assertEqual(diagnostic["failure_class"], "SUCCESS")

    def test_single_role_fallback_diagnostics_never_include_credentials(self):
        for role_name, artifact in (("researcher", _research()), ("finalizer", _final())):
            _router, _adapter, _artifact, _selected, _attempts, diagnostic = self._run_single_role_with_provider_fallback(
                role_name, artifact
            )
            encoded = json.dumps(diagnostic)
            for secret in ("private-credential-1", "private-credential-2", "private-credential-3"):
                self.assertNotIn(secret, encoded)
            self.assertNotIn('"api_key":', encoded)

    def test_four_roles_execute_in_order_and_write_portable_artifacts(self):
        router, adapter = self._router([_research(), _draft(), _critic(), _final()])

        run = run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="four-roles")

        self.assertEqual([call[1].split(". ", 1)[0] for call in adapter.calls], [
            "ROLE: RESEARCHER", "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC", "ROLE: FINALIZER",
        ])
        self.assertEqual(run.run_path, Path(self.temp.name).resolve() / "projects" / "runs" / "four-roles")
        for role in ("researcher", "lighting_designer", "critic", "finalizer"):
            self.assertIsNotNone(read_step_artifact("four-roles", role))
        self.assertTrue((run.run_path / "final_design.json").is_file())

        provenance = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertTrue(provenance["GIT_HEAD"])
        self.assertEqual(len(provenance["CONTEXT_HASH"]), 64)
        self.assertEqual(len(provenance["FINAL_OUTPUT_HASH"]), 64)
        self.assertEqual(provenance["LOCAL_MODEL_USED"], "YES")
        self.assertEqual(provenance["CLOUD_REQUIRED"], "NO")
        self.assertEqual(provenance["CODEX_ARTISTIC_INTERVENTION"], "NONE")

    def test_same_local_provider_serves_every_role_and_cloud_is_not_required(self):
        cloud = ProviderSlot(1, "OPENAI_COMPATIBLE", "cloud", "https://example.test/v1", "cloud-secret", (), 5)
        local = ProviderSlot(2, "OPENAI_COMPATIBLE_LOCAL", "local", "http://127.0.0.1:8080/v1", "", (), 5)
        adapter = _SequenceAdapter([
            ProviderUnavailable("cloud unavailable"), _research(),
            ProviderUnavailable("cloud unavailable"), _draft(),
            ProviderUnavailable("cloud unavailable"), _critic(),
            ProviderUnavailable("cloud unavailable"), _final(),
        ])
        router = ProviderRouter("FALLBACK", (cloud, local), adapter)

        run = run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="local-only")

        self.assertEqual([call[0] for call in adapter.calls], [1, 2, 1, 2, 1, 2, 1, 2])
        state = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(state["LOCAL_MODEL_USED"], "YES")
        self.assertEqual(state["CLOUD_REQUIRED"], "NO")
        self.assertNotIn("cloud-secret", (run.run_path / "run.json").read_text(encoding="utf-8"))
        self.assertNotIn("cloud-secret", (run.run_path / "steps" / "researcher.json").read_text(encoding="utf-8"))

    def test_role_support_filtering_fails_closed_when_researcher_is_not_eligible(self):
        router, adapter = self._router([], roles=("LIGHTING_DESIGNER",))

        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="ineligible")

        self.assertEqual(adapter.calls, [])

    def test_interrupted_run_resumes_without_repeating_completed_step(self):
        first_router, first_adapter = self._router([
            _research(),
            ProviderUnavailable("interrupted"),
            ProviderUnavailable("interrupted"),
            ProviderUnavailable("interrupted"),
        ])
        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(first_router, request="synthetic request", repo_root=self.repo_root, run_id="resume")
        self.assertEqual(len(first_adapter.calls), 4)  # Researcher, then three bounded Designer attempts.

        resumed_router, resumed_adapter = self._router([_draft(), _critic(), _final()])
        run = run_multi_agent_design(resumed_router, request="synthetic request", repo_root=self.repo_root, run_id="resume")

        self.assertEqual(run.resumed_from, "lighting_designer")
        self.assertEqual(len(resumed_adapter.calls), 3)
        self.assertNotIn("ROLE: RESEARCHER", resumed_adapter.calls[0][1])

    def test_completed_run_is_not_repeated_without_explicit_restart(self):
        initial_router, _ = self._router([_research(), _draft(), _critic(), _final()])
        run_multi_agent_design(initial_router, request="synthetic request", repo_root=self.repo_root, run_id="complete")
        resume_router, adapter = self._router([])

        result = run_multi_agent_design(resume_router, request="synthetic request", repo_root=self.repo_root, run_id="complete")

        self.assertEqual(result.resumed_from, None)
        self.assertEqual(adapter.calls, [])

    def test_explicit_restart_archives_prior_artifacts_then_runs_every_role_again(self):
        initial_router, _ = self._router([_research(), _draft(), _critic(), _final()])
        run_multi_agent_design(initial_router, request="synthetic request", repo_root=self.repo_root, run_id="restart")
        restart_router, adapter = self._router([_research(), _draft(), _critic(), _final()])

        run = run_multi_agent_design(
            restart_router,
            request="synthetic request",
            repo_root=self.repo_root,
            run_id="restart",
            restart_run=True,
        )

        self.assertEqual(run.resumed_from, "researcher")
        self.assertEqual(len(adapter.calls), 4)
        self.assertTrue(any((run.run_path / "restart_archive").iterdir()))

    def test_invalid_role_json_retries_then_records_attempt_count(self):
        router, adapter = self._router(["not json", _research(), _draft(), _critic(), _final()])

        run = run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="retry")

        self.assertEqual(len(adapter.calls), 5)
        researcher = read_step_artifact("retry", "researcher")
        self.assertEqual(researcher["attempts"], 2)
        diagnostic = json.loads((run.run_path / "attempts" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(diagnostic["schema"], "zen.multi_agent_attempt_diagnostic.v0.1")
        self.assertEqual(diagnostic["response_characters"], len("not json"))
        context_diagnostic = json.loads((run.run_path / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(context_diagnostic["failure_class"], "OUTPUT_VALIDATION")
        self.assertIsInstance(context_diagnostic["provider_elapsed_seconds"], (int, float))

    def test_retry_prompt_preserves_uncertainty_and_avoids_artistic_invention(self):
        router, adapter = self._router(["not json", _research(), _draft(), _critic(), _final()])
        run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="retry-contract")
        retry_system = adapter.calls[1][1]
        self.assertIn("Preserve valid UNKNOWN", retry_system)
        self.assertIn("Do not invent color", retry_system)
        self.assertIn("Shorten prose before removing evidence or uncertainty", retry_system)
        self.assertIn("structural, not artistic invention", retry_system)

    def test_unknown_runtime_evidence_reference_fails_closed(self):
        invalid_research = _research() | {"evidence_refs": ["UNKNOWN_REF"]}
        router, _ = self._router([invalid_research, invalid_research, invalid_research])
        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="unknown-evidence")

    def test_researcher_source_resolution_failure_uses_bounded_retry_and_secret_safe_diagnostic(self):
        secret = "private-research-provider-key"
        invalid_research = _research() | {
            "sources": [{"source_id": "MODEL_INVENTED_SOURCE", "title": secret}],
        }
        adapter = _SequenceAdapter([invalid_research, _research(), _draft(), _critic(), _final()])
        router = ProviderRouter(
            "PRIMARY_ONLY",
            (self._local_slot(api_key=secret),),
            adapter,
        )

        run = run_multi_agent_design(
            router,
            request="synthetic request",
            repo_root=self.repo_root,
            run_id="research-source-validation-retry",
            max_role_attempts=2,
        )

        researcher = read_step_artifact("research-source-validation-retry", "researcher")
        self.assertEqual(researcher["attempts"], 2)
        self.assertEqual(researcher["artifact"]["resolved_sources"], [])
        attempt = json.loads((run.run_path / "attempts" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(attempt["failure_class"], "EVIDENCE_VALIDATION")
        self.assertEqual(attempt["secret_check"], "FAIL")
        self.assertNotIn("raw_response", attempt)
        self.assertNotIn(secret, json.dumps(attempt))
        diagnostic = json.loads((run.run_path / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        selected = diagnostic["provider_routing"]["provider_attempts"][-1]
        self.assertEqual(selected["role_output_validation"], "PASS")
        self.assertEqual(selected["evidence_validation"], "FAIL")
        self.assertEqual(selected["candidate_status"], "EVIDENCE_VALIDATION_FAILURE")
        self.assertEqual(diagnostic["RESEARCHER_SOURCE_CONTRACT_VALID"], "FAIL")
        self.assertEqual(diagnostic["RESEARCHER_CANONICAL_SOURCE_RESOLUTION"], "NOT_RUN")
        self.assertEqual(diagnostic["RESEARCHER_SOURCE_FAILURE_CLASS"], "NON_CANONICAL_SOURCE_SHAPE")
        self.assertIn("Copy source identity objects exactly from research_context.allowed_source_refs", adapter.calls[1][1])
        success = json.loads((run.run_path / "diagnostics" / "researcher-02.json").read_text(encoding="utf-8"))
        selected_success = success["provider_routing"]["provider_attempts"][-1]
        self.assertEqual(selected_success["evidence_validation"], "PASS")
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")

    def test_valid_research_source_and_knowledge_reference_are_resolved_by_runtime(self):
        context = build_designer_context(self.repo_root)
        researcher_payload = _role_context("researcher", request="synthetic request", context=context, completed={})
        pair = researcher_payload["research_context"]["allowed_source_refs"][0]
        research = _research() | {
            "sources": [pair],
            "evidence_refs": [pair["record_id"]],
        }
        router, _ = self._router([research, _draft(), _critic(), _final()])
        run = run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="valid-evidence")
        stored = read_step_artifact("valid-evidence", "researcher")["artifact"]
        self.assertEqual(stored["resolved_sources"][0]["source_id"], pair["source_id"])
        diagnostic = json.loads((run.run_path / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(diagnostic["RESEARCHER_SOURCE_CONTRACT_VALID"], "PASS")
        self.assertEqual(diagnostic["RESEARCHER_CANONICAL_SOURCE_RESOLUTION"], "PASS")
        self.assertEqual(diagnostic["RESEARCHER_EVIDENCE_REFS_VALID"], "PASS")
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")

    def test_researcher_without_selected_sources_accepts_empty_sources(self):
        context = build_designer_context(self.repo_root)
        context["canonical_knowledge_records"] = []
        context["evidence_ledger"] = {"entries": [], "available_verified_facts": []}
        payload = _role_context("researcher", request="no sources selected", context=context, completed={})
        allowed = payload["research_context"]["allowed_source_refs"]
        self.assertEqual(allowed, [])
        artifact = _validate_artifact_evidence(
            "researcher", _research(), context, allowed_source_refs=allowed
        )
        self.assertEqual(artifact["resolved_sources"], [])

    def test_researcher_contract_exposes_exact_selected_canonical_pairs(self):
        context = build_designer_context(self.repo_root)
        payload = _role_context("researcher", request="hierarchy and contrast", context=context, completed={})
        allowed = payload["research_context"]["allowed_source_refs"]
        metadata = payload["role_context_metadata"]
        selected_record_ids = set(metadata["selected_knowledge_ids"])
        selected_source_ids = set(metadata["selected_source_ids"])
        expected_pairs = {
            (record["source_id"], record["record_id"])
            for record in context["canonical_knowledge_records"]
            if record.get("record_id") in selected_record_ids
            and record.get("source_id")
        }
        self.assertTrue(allowed)
        self.assertTrue(all(set(pair) == {"source_id", "record_id"} for pair in allowed))
        self.assertTrue(all(pair["record_id"] in selected_record_ids for pair in allowed))
        self.assertTrue(all(pair["source_id"] in selected_source_ids for pair in allowed))
        self.assertEqual({(pair["source_id"], pair["record_id"]) for pair in allowed}, expected_pairs)
        prompt = ROLE_SYSTEM_PROMPTS["researcher"]
        self.assertIn('first key must be "schema" with exact value "zen.multi_agent_research.v0.1"', prompt)
        self.assertIn("Never put evidence_ref values, summaries, titles, URLs, or prose in sources", prompt)
        self.assertIn("Verified current Show facts belong in evidence_refs, not sources", prompt)

    def test_researcher_source_contract_rejects_noncanonical_shapes_and_pairs(self):
        allowed = [
            {"source_id": "CANONICAL-1", "record_id": "RECORD-1"},
            {"source_id": "CANONICAL-2", "record_id": "RECORD-2"},
        ]
        invalid_values = [
            ([{"evidence_ref": "CURRENT_SHOW:abc:fixture_inventory", "summary": "verified"}], "NON_CANONICAL_SOURCE_SHAPE"),
            (["CURRENT_SHOW:abc:fixture_inventory"], "NON_CANONICAL_SOURCE_SHAPE"),
            (["a source summary in prose"], "NON_CANONICAL_SOURCE_SHAPE"),
            ([{"source_id": "UNKNOWN", "record_id": "RECORD-1"}], "SOURCE_PAIR_NOT_ALLOWED"),
            ([{"source_id": "CANONICAL-1", "record_id": "UNKNOWN"}], "SOURCE_RECORD_MISMATCH"),
            ([{"source_id": "CANONICAL-1", "record_id": "RECORD-2"}], "SOURCE_RECORD_MISMATCH"),
            ([allowed[0], allowed[0]], "SOURCE_PAIR_NOT_ALLOWED"),
        ]
        for sources, expected_class in invalid_values:
            with self.subTest(sources=sources):
                with self.assertRaises(ResearchSourceContractError) as raised:
                    validate_research_source_contract(sources, allowed)
                self.assertEqual(raised.exception.classification, expected_class)
        self.assertEqual(validate_research_source_contract([], allowed), [])

    def test_invalid_researcher_sources_are_not_normalized_and_raw_response_is_preserved(self):
        invalid = _research() | {
            "sources": [{"evidence_ref": "CURRENT_SHOW:abc:fixture_inventory", "summary": "verified inventory"}],
        }
        raw_response = json.dumps(invalid)
        router, adapter = self._router([raw_response, _research(), _draft(), _critic(), _final()])
        run = run_multi_agent_design(
            router,
            request="source contract repair",
            repo_root=self.repo_root,
            run_id="research-source-raw-preserved",
            max_role_attempts=2,
        )
        first_attempt = json.loads((run.run_path / "attempts" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(first_attempt["raw_response"], raw_response)
        self.assertEqual(first_attempt["RESEARCHER_RAW_SOURCE_SHAPE"], "NON_CANONICAL_SOURCE_SHAPE")
        self.assertEqual(first_attempt["RESEARCHER_SOURCE_CONTRACT_VALID"], "FAIL")
        self.assertEqual(read_step_artifact("research-source-raw-preserved", "researcher")["attempts"], 2)
        self.assertIn("Do not use evidence_refs, summaries, titles, URLs, or prose as source identities", adapter.calls[1][1])

    def test_researcher_empty_sources_are_backward_compatible_with_bounded_diagnostics(self):
        router, adapter = self._router([_research(), _draft(), _critic(), _final()])
        run = run_multi_agent_design(router, request="no external source needed", repo_root=self.repo_root, run_id="empty-sources")
        payload = json.loads(adapter.calls[0][2])
        diagnostic = json.loads((run.run_path / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(read_step_artifact("empty-sources", "researcher")["artifact"]["sources"], [])
        self.assertEqual(diagnostic["RESEARCHER_ALLOWED_SOURCE_REF_COUNT"], len(payload["research_context"]["allowed_source_refs"]))
        self.assertEqual(diagnostic["RESEARCHER_OUTPUT_SOURCE_COUNT"], 0)
        self.assertEqual(diagnostic["RESEARCHER_SOURCE_CONTRACT_VALID"], "PASS")
        self.assertEqual(diagnostic["RESEARCHER_CANONICAL_SOURCE_RESOLUTION"], "PASS")
        self.assertNotIn("source_provenance", json.dumps(diagnostic))

    def test_role_context_uses_deterministic_knowledge_projection_without_blind_truncation(self):
        router, adapter = self._router([_research(), _draft(), _critic(), _final()])

        run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="bounded-context")

        researcher_payload = json.loads(adapter.calls[0][2])
        knowledge = researcher_payload["research_context"]["professional_lighting_design_knowledge"]
        self.assertEqual(knowledge["schema"], "zen.knowledge_retrieval_context.v0.1")
        self.assertTrue(knowledge["knowledge_refs"])
        self.assertEqual(len(knowledge["knowledge_refs"]), len(knowledge["records"]))
        self.assertNotIn("context_excerpt", json.dumps(knowledge))

    def test_each_role_retrieves_from_full_canonical_store_and_receives_scoped_context(self):
        context = build_designer_context(self.repo_root)
        canonical_count = len(context["canonical_knowledge_records"])
        self.assertGreaterEqual(canonical_count, 100)
        self.assertEqual(len(context["evidence_ledger"]["entries"]), canonical_count)
        self.assertEqual(canonical_count, len({item["record_id"] for item in context["canonical_knowledge_records"]}))
        completed = {"researcher": _research(), "lighting_designer": _draft(), "critic": _critic()}
        for role_name in ("researcher", "lighting_designer", "critic", "finalizer"):
            payload = _role_context(role_name, request="synthetic context-size regression", context=context, completed=completed)
            metadata = payload["role_context_metadata"]
            projected = payload["professional_lighting_design_knowledge"]
            self.assertLessEqual(metadata["selected_knowledge_count"], 8)
            self.assertEqual(metadata["selected_knowledge_count"], len(projected["records"]))
            self.assertEqual(metadata["selected_knowledge_ids"], projected["knowledge_refs"])
            self.assertLess(len(json.dumps(payload, ensure_ascii=False)), len(json.dumps(context, ensure_ascii=False)))
            self.assertNotEqual(len(payload["evidence_ledger"]["entries"]), len(context["evidence_ledger"]["entries"]))
            self.assertEqual(payload["evidence_ledger"]["available_verified_facts"], context["evidence_ledger"]["available_verified_facts"])
            if role_name == "researcher":
                source_ids = {source["source_id"] for source in payload["research_context"]["source_provenance"]["sources"]}
                self.assertTrue(source_ids <= set(metadata["selected_source_ids"]))

    def test_role_retrieval_does_not_depend_on_generic_projected_subset(self):
        context = build_designer_context(self.repo_root)
        context["categories"]["professional_lighting_design_knowledge"] = {"records": []}
        payload = _role_context(
            "researcher",
            request="visual hierarchy and negative space",
            context=context,
            completed={},
        )
        self.assertGreater(payload["role_context_metadata"]["selected_knowledge_count"], 0)
        self.assertTrue(payload["professional_lighting_design_knowledge"]["records"])

    def test_model_context_diagnostics_are_bounded_and_secret_free(self):
        router, _ = self._router([_research(), _draft(), _critic(), _final()])
        run = run_multi_agent_design(router, request="diagnostic request", repo_root=self.repo_root, run_id="context-diagnostics")
        for role_name in ("researcher", "lighting_designer", "critic", "finalizer"):
            diagnostic = json.loads((run.run_path / "diagnostics" / f"{role_name}-01.json").read_text(encoding="utf-8"))
            self.assertEqual(diagnostic["schema"], "zen.model_context_diagnostic.v0.1")
            self.assertLessEqual(diagnostic["selected_knowledge_count"], 8)
            self.assertGreater(diagnostic["payload_utf8_bytes"], 0)
            self.assertEqual(diagnostic["failure_class"], "SUCCESS")
            self.assertIsInstance(diagnostic["provider_elapsed_seconds"], (int, float))
            self.assertFalse(diagnostic["secrets_included"])
            self.assertNotIn("Authorization", json.dumps(diagnostic))

    def test_finalizer_projection_preserves_semantics_without_redundant_envelopes(self):
        context = build_designer_context(self.repo_root)
        research = _research() | {
            "transferable_design_observations": [{"observation": "layer depth", "evidence_refs": ["K-001"]}],
            "constraints": ["keep UNKNOWN"],
            "uncertainties": ["instrumentation UNKNOWN"],
            "evidence_refs": ["K-001"],
            "sources": [{"source_id": "SRC-001", "record_id": "K-001", "title": "must not be duplicated"}],
            "resolved_sources": [{"source_id": "SRC-001", "title": "canonical metadata", "url": "https://example.invalid"}],
            "provider": "secret-free-envelope",
            "artifact_hash": "redundant",
        }
        designer = _draft() | {
            "design_intent": {"purpose": "preserve contrast", "evidence_refs": ["K-001"]},
            "visual_strategy": {"keep": ["negative space"]},
            "uncertainties": ["stage target UNKNOWN"],
            "evidence_refs": ["K-001"],
            "provider": "redundant",
        }
        critic = _critic() | {
            "strengths": ["clear hierarchy"],
            "revision_requests": [{"request": "retain headroom", "evidence_refs": ["K-001"]}],
            "evidence_refs": ["K-001"],
            "run_diagnostics": {"payload": "redundant"},
        }
        payload = _role_context(
            "finalizer",
            request="projection test",
            context=context,
            completed={"researcher": research, "lighting_designer": designer, "critic": critic},
        )
        self.assertEqual(payload["research_artifact"]["evidence_refs"], ["K-001"])
        self.assertEqual(payload["research_artifact"]["sources"], [{"source_id": "SRC-001", "record_id": "K-001"}])
        self.assertEqual(payload["designer_draft"]["design_intent"], designer["design_intent"])
        self.assertEqual(payload["designer_draft"]["uncertainties"], designer["uncertainties"])
        self.assertEqual(payload["critic_artifact"]["revision_requests"], critic["revision_requests"])
        self.assertNotIn("resolved_sources", payload["research_artifact"])
        self.assertNotIn("provider", json.dumps(payload))
        self.assertNotIn("run_diagnostics", json.dumps(payload))
        self.assertNotIn("source_provenance", json.dumps(payload["finalization_context"]))

    def test_finalizer_projection_is_materially_smaller_than_legacy_shape(self):
        context = build_designer_context(self.repo_root)
        research = _research() | {
            "sources": [{"source_id": f"SRC-{i:03}", "record_id": f"K-{i:03}", "title": "duplicate metadata", "url": "https://example.invalid"} for i in range(20)],
            "resolved_sources": [{"source_id": f"SRC-{i:03}", "record_id": f"K-{i:03}", "title": "canonical", "url": "https://example.invalid", "publisher": "publisher"} for i in range(20)],
            "envelope_metadata": {"diagnostics": "x" * 6000},
        }
        designer = _draft() | {"envelope_metadata": {"diagnostics": "y" * 5000}}
        critic = _critic() | {"envelope_metadata": {"diagnostics": "z" * 5000}}
        completed = {"researcher": research, "lighting_designer": designer, "critic": critic}
        payload = _role_context("finalizer", request="synthetic 140-record context", context=context, completed=completed)
        legacy = {
            "user_request": "synthetic 140-record context",
            "research_artifact": research,
            "designer_draft": designer,
            "critic_artifact": critic,
            "finalization_context": {
                "fixture_technical_capability": context["categories"]["fixture_technical_capability"],
                "rig_spatial_visual_affordance": context["categories"]["rig_spatial_visual_affordance"],
                "operator_contract": context["categories"]["operator_contract"],
            },
            "evidence_ledger": context["evidence_ledger"],
            "source_registry": context["categories"]["source_provenance"],
        }
        old_bytes = len(json.dumps(legacy, ensure_ascii=False).encode("utf-8"))
        new_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        self.assertLess(new_bytes, old_bytes)
        self.assertLessEqual(new_bytes, 24000)
        canonical_count = len(context["canonical_knowledge_records"])
        self.assertGreaterEqual(canonical_count, 100)
        self.assertEqual(len(context["evidence_ledger"]["entries"]), canonical_count)

    def test_timeout_fails_fast_without_identical_retries_and_records_class(self):
        router, adapter = self._router([ProviderUnavailable("Provider slot 1 request failed: TimeoutError")])
        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(router, request="timeout", repo_root=self.repo_root, run_id="timeout-fast")
        self.assertEqual(len(adapter.calls), 1)
        root = Path(self.temp.name) / "projects" / "runs" / "timeout-fast"
        diagnostic = json.loads((root / "diagnostics" / "researcher-01.json").read_text(encoding="utf-8"))
        self.assertEqual(diagnostic["failure_class"], "TRANSPORT_TIMEOUT")
        self.assertIsInstance(diagnostic["provider_elapsed_seconds"], (int, float))
        self.assertFalse((root / "diagnostics" / "researcher-02.json").exists())

    def test_runtime_has_no_ma2_builder_or_resolver_import(self):
        import zen_ma2_agent.llm.multi_agent_runtime as runtime
        tree = ast.parse(inspect.getsource(runtime))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
            elif isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
        self.assertFalse(any("ma2" in name.casefold() or "builder" in name.casefold() or "resolver" in name.casefold() for name in imported))


    def test_parallel_designer_and_critic_candidates_reach_finalizer(self):
        class ParallelRoleAdapter:
            def __init__(self):
                self.calls = []

            def complete(self, slot, *, system, user):
                self.calls.append((slot.number, system, user))
                role = system.split(". ", 1)[0]
                payload = json.loads(user)
                if role == "ROLE: RESEARCHER":
                    return json.dumps(_research())
                if role == "ROLE: LIGHTING_DESIGNER":
                    value = _draft()
                    value["design_intent"] = {"provider_slot": slot.number}
                    return json.dumps(value)
                if role == "ROLE: CRITIC":
                    self.assert_candidate_count = len(payload.get("designer_candidates", []))
                    value = _critic()
                    value["revision_requests"] = [{"provider_slot": slot.number}]
                    return json.dumps(value)
                if role == "ROLE: FINALIZER":
                    self.finalizer_designer_count = len(payload.get("designer_candidates", []))
                    self.finalizer_critic_count = len(payload.get("critic_candidates", []))
                    return json.dumps(_final())
                raise AssertionError(role)

        adapter = ParallelRoleAdapter()
        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "local-a", "http://127.0.0.1:8080/v1", "", (), 5, priority=10, cost_class="LOCAL"),
            ProviderSlot(2, "OPENAI_COMPATIBLE_LOCAL", "local-b", "http://127.0.0.1:8081/v1", "", (), 5, priority=20, cost_class="LOCAL"),
        )
        router = ProviderRouter(
            "FREE_FIRST",
            slots,
            adapter,
            parallelism=2,
            parallel_roles=("LIGHTING_DESIGNER", "CRITIC"),
        )

        run = run_multi_agent_design(router, request="parallel synthetic request", repo_root=self.repo_root, run_id="parallel-candidates")

        designer = read_step_artifact("parallel-candidates", "lighting_designer")
        critic = read_step_artifact("parallel-candidates", "critic")
        self.assertEqual(len(designer["candidate_artifacts"]), 2)
        self.assertEqual(len(critic["candidate_artifacts"]), 2)
        self.assertEqual(adapter.assert_candidate_count, 2)
        self.assertEqual(adapter.finalizer_designer_count, 2)
        self.assertEqual(adapter.finalizer_critic_count, 2)
        state = json.loads((run.run_path / "run.json").read_text(encoding="utf-8"))
        execution = {item["role"]: item for item in state["role_execution"]}
        self.assertEqual(execution["lighting_designer"]["parallel_candidates"], 2)
        self.assertEqual(execution["critic"]["parallel_candidates"], 2)
        for role in ("lighting_designer", "critic"):
            provenance = execution[role]["parallel_runtime"]
            self.assertEqual(provenance["configured_parallelism"], 2)
            self.assertEqual(provenance["requested_successful_candidate_count"], 2)
            self.assertEqual(provenance["attempted_provider_slots"], [1, 2])
            self.assertEqual(provenance["accepted_provider_slots"], [1, 2])
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")
        self.assertFalse((run.run_path / "attempts").exists())

    def test_parallel_invalid_json_diagnostic_is_exact_and_valid_peer_is_accepted(self):
        response = "not-json"
        run, _ = self._run_parallel_validation_case("parallel-invalid-json-candidate", response)
        failure_path = run.run_path / "attempts" / "lighting_designer-parallel-slot01.json"
        self.assertTrue(failure_path.is_file())
        failed = json.loads(failure_path.read_text(encoding="utf-8"))
        self.assertEqual(failed["role"], "lighting_designer")
        self.assertEqual(failed["slot_number"], 1)
        self.assertEqual(failed["response_sha256"], hashlib.sha256(response.encode("utf-8")).hexdigest())
        self.assertEqual(failed["response_characters"], len(response))
        self.assertEqual(failed["validation_error_type"], "MultiAgentRunError")
        self.assertEqual(failed["validation_error"], "Provider response was not valid JSON.")
        self.assertEqual(failed["candidate_status"], "OUTPUT_VALIDATION_FAILURE")
        self.assertEqual(failed["secret_check"], "PASS")
        self.assertEqual(failed["raw_response"], response)
        self.assertEqual(failed["CODEX_ARTISTIC_INTERVENTION"], "NONE")

        parallel = json.loads((run.run_path / "diagnostics" / "lighting_designer-parallel.json").read_text(encoding="utf-8"))
        first = next(item for item in parallel["provider_attempts"] if item["slot_number"] == 1)
        self.assertEqual(first["validation_error_type"], failed["validation_error_type"])
        self.assertEqual(first["validation_error"], failed["validation_error"])
        self.assertEqual(parallel["parallel_runtime"]["accepted_provider_slots"], [2])
        candidates = read_step_artifact("parallel-invalid-json-candidate", "lighting_designer")["candidate_artifacts"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["provider"]["slot"], 2)
        self.assertFalse((run.run_path / "attempts" / "lighting_designer-parallel-slot02.json").exists())

    def test_parallel_wrong_schema_diagnostic_preserves_exact_validator_error(self):
        response = json.dumps({"schema": "wrong.role.schema", "design_intent": {}})
        run, _ = self._run_parallel_validation_case("parallel-wrong-schema-candidate", response)
        expected = "Role output schema must be zen.multi_agent_designer_draft.v0.1."
        failed = json.loads((run.run_path / "attempts" / "lighting_designer-parallel-slot01.json").read_text(encoding="utf-8"))
        self.assertEqual(failed["validation_error"], expected)
        self.assertEqual(failed["validation_error_type"], "MultiAgentRunError")
        parallel = json.loads((run.run_path / "diagnostics" / "lighting_designer-parallel.json").read_text(encoding="utf-8"))
        first = next(item for item in parallel["provider_attempts"] if item["slot_number"] == 1)
        self.assertEqual(first["validation_error"], expected)
        self.assertEqual(first["candidate_status"], "OUTPUT_VALIDATION_FAILURE")

    def test_parallel_failed_candidate_containing_api_key_never_persists_raw_response(self):
        secret = "private-candidate-key"
        response = json.dumps({"schema": "wrong.role.schema", "echo": secret})
        run, _ = self._run_parallel_validation_case(
            "parallel-secret-failed-candidate", response, failed_api_key=secret,
        )
        failure_path = run.run_path / "attempts" / "lighting_designer-parallel-slot01.json"
        failed = json.loads(failure_path.read_text(encoding="utf-8"))
        self.assertEqual(failed["secret_check"], "FAIL")
        self.assertEqual(failed["candidate_status"], "SECRET_REJECTION")
        self.assertNotIn("raw_response", failed)
        self.assertNotIn(secret, failure_path.read_text(encoding="utf-8"))
        parallel = json.loads((run.run_path / "diagnostics" / "lighting_designer-parallel.json").read_text(encoding="utf-8"))
        first = next(item for item in parallel["provider_attempts"] if item["slot_number"] == 1)
        self.assertEqual(first["secret_check"], "FAIL")
        self.assertNotIn(secret, json.dumps(parallel))

    def test_parallel_stage_diagnostics_survive_fallback_and_classify_failures(self):
        from collections import Counter
        from threading import Lock

        class DiagnosticAdapter:
            def __init__(self):
                self.calls = Counter()
                self.lock = Lock()

            def complete(self, slot, *, system, user):
                role = system.split(". ", 1)[0]
                with self.lock:
                    self.calls[(role, slot.number)] += 1
                    call_number = self.calls[(role, slot.number)]
                if role == "ROLE: RESEARCHER":
                    return json.dumps(_research())
                if role == "ROLE: LIGHTING_DESIGNER":
                    if slot.number == 1:
                        raise ProviderUnavailable("Provider slot 1 request failed: HTTPError 503 secret-value")
                    if slot.number == 2 and call_number == 1:
                        return "not-json"
                    draft = _draft()
                    if slot.number == 3:
                        draft["evidence_refs"] = ["UNKNOWN_PARALLEL_EVIDENCE"]
                    return json.dumps(draft)
                if role == "ROLE: CRITIC":
                    return json.dumps(_critic())
                if role == "ROLE: FINALIZER":
                    return json.dumps(_final())
                raise AssertionError(role)

        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE", "provider-1", "https://one.example.test/v1", "secret-one", ("LIGHTING_DESIGNER",), 5),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "provider-2", "https://two.example.test/v1", "secret-two", ("LIGHTING_DESIGNER",), 5),
            ProviderSlot(3, "OPENAI_COMPATIBLE", "provider-3", "https://three.example.test/v1", "secret-three", ("LIGHTING_DESIGNER",), 5),
            ProviderSlot(4, "OPENAI_COMPATIBLE_LOCAL", "support", "http://127.0.0.1:8080/v1", "", ("RESEARCHER", "CRITIC", "FINALIZER"), 5),
        )
        router = ProviderRouter(
            "FALLBACK", slots, DiagnosticAdapter(), parallelism=2,
            parallel_roles=("LIGHTING_DESIGNER", "CRITIC"),
        )

        run = run_multi_agent_design(
            router, request="diagnostic synthetic request", repo_root=self.repo_root,
            run_id="parallel-diagnostic-fallback", max_role_attempts=1,
        )

        diagnostic_root = run.run_path / "diagnostics"
        parallel_path = diagnostic_root / "lighting_designer-parallel.json"
        fallback_path = diagnostic_root / "lighting_designer-01.json"
        self.assertTrue(parallel_path.is_file())
        self.assertTrue(fallback_path.is_file())
        parallel = json.loads(parallel_path.read_text(encoding="utf-8"))
        fallback = json.loads(fallback_path.read_text(encoding="utf-8"))
        attempts = parallel["provider_attempts"]
        self.assertEqual([item["slot_number"] for item in attempts], [1, 2, 3])
        self.assertEqual(attempts[0]["candidate_status"], "TRANSPORT_FAILURE")
        self.assertEqual(attempts[0]["failure_reason"], "HTTPError 503")
        self.assertEqual(attempts[1]["role_output_validation"], "FAIL")
        self.assertEqual(attempts[1]["candidate_status"], "OUTPUT_VALIDATION_FAILURE")
        self.assertEqual(attempts[2]["role_output_validation"], "PASS")
        self.assertEqual(attempts[2]["evidence_validation"], "FAIL")
        self.assertEqual(attempts[2]["candidate_status"], "EVIDENCE_VALIDATION_FAILURE")
        self.assertEqual(parallel["parallel_runtime"]["attempted_provider_slots"], [1, 2, 3])
        self.assertEqual(parallel["parallel_runtime"]["accepted_provider_slots"], [])
        self.assertEqual(fallback["failure_class"], "SUCCESS")
        self.assertEqual(read_step_artifact("parallel-diagnostic-fallback", "lighting_designer")["attempts"], 1)
        self.assertEqual(run.final_design["schema"], "zen.autonomous_design.v0.1")
        for path in run.run_path.rglob("*"):
            if path.is_file():
                contents = path.read_text(encoding="utf-8")
                self.assertNotIn("secret-one", contents)
                self.assertNotIn("secret-two", contents)
                self.assertNotIn("secret-three", contents)
                self.assertNotIn("secret-value", contents)

    def test_parallel_secret_rejection_is_recorded_without_persisting_credential(self):
        class SecretAdapter:
            def complete(self, slot, *, system, user):
                role = system.split(". ", 1)[0]
                if role == "ROLE: RESEARCHER":
                    return json.dumps(_research())
                if role == "ROLE: LIGHTING_DESIGNER":
                    draft = _draft()
                    if slot.number == 1:
                        draft["design_intent"] = {"private_echo": slot.api_key}
                    return json.dumps(draft)
                if role == "ROLE: CRITIC":
                    return json.dumps(_critic())
                if role == "ROLE: FINALIZER":
                    return json.dumps(_final())
                raise AssertionError(role)

        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE", "provider-1", "https://one.example.test/v1", "credential-unique-one", ("LIGHTING_DESIGNER",), 5, priority=1, cost_class="FREE"),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "provider-2", "https://two.example.test/v1", "credential-unique-two", ("LIGHTING_DESIGNER",), 5, priority=2, cost_class="FREE"),
            ProviderSlot(3, "OPENAI_COMPATIBLE_LOCAL", "support", "http://127.0.0.1:8080/v1", "", ("RESEARCHER", "CRITIC", "FINALIZER"), 5),
        )
        router = ProviderRouter(
            "FREE_FIRST", slots, SecretAdapter(), parallelism=2,
            parallel_roles=("LIGHTING_DESIGNER", "CRITIC"),
        )

        run = run_multi_agent_design(
            router, request="secret diagnostic synthetic request", repo_root=self.repo_root,
            run_id="parallel-secret-diagnostic", max_role_attempts=1,
        )

        diagnostic = json.loads((run.run_path / "diagnostics" / "lighting_designer-parallel.json").read_text(encoding="utf-8"))
        attempts = diagnostic["provider_attempts"]
        self.assertEqual(attempts[0]["candidate_status"], "SECRET_REJECTION")
        self.assertEqual(attempts[0]["secret_check"], "FAIL")
        self.assertEqual(attempts[1]["candidate_status"], "VALID_CANDIDATE")
        self.assertEqual(diagnostic["parallel_runtime"]["accepted_provider_slots"], [2])
        for path in run.run_path.rglob("*"):
            if path.is_file():
                contents = path.read_text(encoding="utf-8")
                self.assertNotIn("credential-unique-one", contents)
                self.assertNotIn("credential-unique-two", contents)

    def test_invalid_final_schema_fails_closed_without_final_design_or_ma2_write(self):
        invalid_final = _final() | {"ma2_commands": ["forbidden"]}
        router, _ = self._router([_research(), _draft(), _critic(), invalid_final, invalid_final, invalid_final])

        with self.assertRaises(MultiAgentRunError):
            run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="invalid-final")

        root = Path(self.temp.name) / "projects" / "runs" / "invalid-final"
        self.assertFalse((root / "final_design.json").exists())
        failure = json.loads((root / "failure.json").read_text(encoding="utf-8"))
        self.assertEqual(failure["role"], "finalizer")
        self.assertEqual(failure["CODEX_ARTISTIC_INTERVENTION"], "NONE")


if __name__ == "__main__":
    unittest.main()
