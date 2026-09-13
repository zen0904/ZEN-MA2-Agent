from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.llm.multi_agent_runtime import MultiAgentRunError, run_multi_agent_design
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

    def test_four_roles_execute_in_order_and_write_portable_artifacts(self):
        router, adapter = self._router([_research(), _draft(), _critic(), _final()])

        run = run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="four-roles")

        self.assertEqual([call[1].split(". ", 1)[0] for call in adapter.calls], [
            "ROLE: RESEARCHER", "ROLE: LIGHTING_DESIGNER", "ROLE: CRITIC", "ROLE: FINALIZER",
        ])
        self.assertEqual(run.run_path, Path(self.temp.name) / "projects" / "runs" / "four-roles")
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

    def test_local_role_context_is_bounded_with_a_full_value_hash(self):
        router, adapter = self._router([_research(), _draft(), _critic(), _final()])

        run_multi_agent_design(router, request="synthetic request", repo_root=self.repo_root, run_id="bounded-context")

        researcher_payload = json.loads(adapter.calls[0][2])
        knowledge = researcher_payload["research_context"]["professional_lighting_design_knowledge"]
        self.assertTrue(knowledge.get("truncated"))
        self.assertEqual(len(knowledge["full_value_sha256"]), 64)

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
