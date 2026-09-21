from __future__ import annotations

import json
import io
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from zen_ma2_agent.llm.autonomous_designer import SCHEMA, DesignValidationError, validate_design_output
from zen_ma2_agent.llm.router import OpenAICompatibleHTTPAdapter, ProviderImageInput, ProviderRouter, ProviderSlot, ProviderUnavailable, load_provider_slots
from zen_ma2_agent.config import settings_path
from launcher.zen_portable_launcher import ma2_connectivity, provider_self_test


class _Adapter:
    def __init__(self, responses: dict[int, object]): self.responses = responses
    def complete(self, slot, *, system, user):
        value = self.responses[slot.number]
        if isinstance(value, Exception): raise value
        return value


class PortableLLMRouterTests(unittest.TestCase):
    def test_three_slots_and_fallback_do_not_expose_key(self):
        slots = tuple(ProviderSlot(i, "OPENAI_COMPATIBLE", "m", "https://example.test/v1", "secret", ("DESIGNER",), 10) for i in range(1, 4))
        router = ProviderRouter("FALLBACK", slots, _Adapter({1: ProviderUnavailable("down"), 2: "{}", 3: "never"}))
        content, chosen = router.complete(role="DESIGNER", system="s", user="u")
        self.assertEqual(content, "{}")
        self.assertEqual(chosen.number, 2)
        self.assertNotIn("secret", json.dumps(chosen.safe_identity()))

    def test_private_env_loads_three_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text("ZEN_PROVIDER_MODE=ROUTED\nZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE\nZEN_PROVIDER_1_MODEL=test\nZEN_PROVIDER_1_BASE_URL=https://example.test/v1\nZEN_PROVIDER_1_API_KEY=key\nZEN_PROVIDER_1_ROLES=DESIGNER\n", encoding="utf-8")
            mode, slots = load_provider_slots(path)
        self.assertEqual(mode, "ROUTED")
        self.assertTrue(slots[0].configured)
        self.assertFalse(slots[1].configured)

    def test_local_inference_timeout_can_be_configured_for_long_cpu_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text(
                "ZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE_LOCAL\n"
                "ZEN_PROVIDER_1_MODEL=test\n"
                "ZEN_PROVIDER_1_BASE_URL=http://127.0.0.1:8080/v1\n"
                "ZEN_PROVIDER_1_TIMEOUT_SECONDS=900\n",
                encoding="utf-8",
            )
            _, slots = load_provider_slots(path)
        self.assertEqual(slots[0].timeout_seconds, 900)


    def test_provider_pool_can_expand_beyond_three_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text(
                "ZEN_PROVIDER_MODE=FREE_FIRST\n"
                "ZEN_PROVIDER_SLOT_COUNT=8\n"
                "ZEN_PROVIDER_8_TYPE=OPENAI_COMPATIBLE\n"
                "ZEN_PROVIDER_8_MODEL=cloud-model\n"
                "ZEN_PROVIDER_8_BASE_URL=https://example.test/v1\n"
                "ZEN_PROVIDER_8_API_KEY=key\n"
                "ZEN_PROVIDER_8_COST_CLASS=FREE\n",
                encoding="utf-8",
            )
            mode, slots = load_provider_slots(path)
        self.assertEqual(mode, "FREE_FIRST")
        self.assertEqual(len(slots), 8)
        self.assertTrue(slots[7].configured)
        self.assertEqual(slots[7].cost_class, "FREE")

    def test_free_first_prefers_free_role_provider_then_local_fallback(self):
        free = ProviderSlot(
            2, "OPENAI_COMPATIBLE", "cloud", "https://example.test/v1", "key",
            ("CRITIC",), 10, priority=20, cost_class="FREE",
        )
        local = ProviderSlot(
            1, "OPENAI_COMPATIBLE_LOCAL", "local", "http://127.0.0.1:8080/v1", "",
            (), 10, priority=1, cost_class="LOCAL",
        )
        paid = ProviderSlot(
            3, "OPENAI_COMPATIBLE", "paid", "https://paid.example.test/v1", "key",
            ("CRITIC",), 10, priority=1, cost_class="PAID",
        )
        adapter = _Adapter({2: ProviderUnavailable("quota"), 1: "{}", 3: "never"})
        router = ProviderRouter("FREE_FIRST", (local, free, paid), adapter)
        content, chosen = router.complete(role="CRITIC", system="s", user="u")
        self.assertEqual(content, "{}")
        self.assertEqual(chosen.number, 1)

    def test_routed_uses_priority_within_role_specific_slots(self):
        slow = ProviderSlot(
            1, "OPENAI_COMPATIBLE", "a", "https://a.example.test/v1", "key",
            ("DESIGNER",), 10, priority=50,
        )
        preferred = ProviderSlot(
            2, "OPENAI_COMPATIBLE", "b", "https://b.example.test/v1", "key",
            ("DESIGNER",), 10, priority=10,
        )
        router = ProviderRouter("ROUTED", (slow, preferred), _Adapter({1: "wrong", 2: "ok"}))
        content, chosen = router.complete(role="DESIGNER", system="s", user="u")
        self.assertEqual(content, "ok")
        self.assertEqual(chosen.number, 2)

    def test_slot_can_disable_provider_specific_json_mode(self):
        slot = ProviderSlot(
            1, "OPENAI_COMPATIBLE", "test", "https://example.test/v1", "key",
            (), 10, response_format="NONE",
        )

        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self):
                return b'{"choices":[{"message":{"content":"{}"}}]}'

        captured = {}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=opener):
            content = OpenAICompatibleHTTPAdapter().complete(slot, system="s", user="u")
        self.assertEqual(content, "{}")
        self.assertNotIn("response_format", captured["body"])

    def test_unset_reasoning_effort_omits_parameter_and_preserves_existing_body(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"choices":[{"message":{"content":"{}"}}]}'

        captured = {}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        slot = ProviderSlot(
            1, "OPENAI_COMPATIBLE_LOCAL", "test", "http://127.0.0.1:8080/v1", "", (), 5,
            reasoning_effort=" ",
        )
        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=opener):
            OpenAICompatibleHTTPAdapter().complete(slot, system="s", user="u")
        self.assertEqual(
            captured["body"],
            {
                "model": "test",
                "messages": [
                    {"role": "system", "content": "s"},
                    {"role": "user", "content": "u"},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        self.assertNotIn("reasoning_effort", captured["body"])

    def test_private_config_loads_and_normalizes_reasoning_effort(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text(
                "ZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE_LOCAL\n"
                "ZEN_PROVIDER_1_MODEL=test\n"
                "ZEN_PROVIDER_1_BASE_URL=http://127.0.0.1:8080/v1\n"
                "ZEN_PROVIDER_1_REASONING_EFFORT=low\n",
                encoding="utf-8",
            )
            _, slots = load_provider_slots(path)
        self.assertEqual(slots[0].reasoning_effort, "LOW")
        self.assertEqual(slots[0].safe_identity()["reasoning_effort"], "LOW")

    def test_reasoning_effort_is_normalized_in_request(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"choices":[{"message":{"content":"{}"}}]}'

        slot = ProviderSlot(
            1, "OPENAI_COMPATIBLE_LOCAL", "test", "http://127.0.0.1:8080/v1", "", (), 5,
            reasoning_effort="LOW",
        )
        captured = {}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=opener):
            OpenAICompatibleHTTPAdapter().complete(slot, system="s", user="u")
        self.assertEqual(captured["body"]["reasoning_effort"], "low")

    def test_invalid_reasoning_effort_fails_private_config_loading(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text(
                "ZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE_LOCAL\n"
                "ZEN_PROVIDER_1_MODEL=test\n"
                "ZEN_PROVIDER_1_BASE_URL=http://127.0.0.1:8080/v1\n"
                "ZEN_PROVIDER_1_REASONING_EFFORT=EXTREME\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "reasoning effort"):
                load_provider_slots(path)

    def test_reasoning_effort_is_in_safe_identity_without_credentials(self):
        slot = ProviderSlot(
            1, "OPENAI_COMPATIBLE", "model", "https://example.test/v1", "credential-secret", (), 5,
            reasoning_effort="low",
        )
        identity = slot.safe_identity()
        self.assertEqual(identity["reasoning_effort"], "LOW")
        self.assertNotIn("credential-secret", json.dumps(identity))



    def test_portable_config_loads_parallelism_and_role_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "providers.private.env"
            path.write_text(
                "ZEN_PROVIDER_MODE=FREE_FIRST\n"
                "ZEN_PROVIDER_PARALLELISM=2\n"
                "ZEN_PROVIDER_PARALLEL_ROLES=LIGHTING_DESIGNER,CRITIC\n"
                "ZEN_PROVIDER_1_TYPE=OPENAI_COMPATIBLE_LOCAL\n"
                "ZEN_PROVIDER_1_MODEL=local\n"
                "ZEN_PROVIDER_1_BASE_URL=http://127.0.0.1:8080/v1\n",
                encoding="utf-8",
            )
            router = ProviderRouter.from_portable_config(path)
        self.assertEqual(router.parallelism, 2)
        self.assertEqual(router.parallel_limit("LIGHTING_DESIGNER"), 1)
        self.assertIn("CRITIC", router.parallel_roles)

    def test_parallel_fanout_returns_results_in_router_preference_order(self):
        class ParallelAdapter:
            def complete(self, slot, *, system, user):
                import time
                if slot.number == 1:
                    time.sleep(0.03)
                return f"slot-{slot.number}"

        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE", "a", "https://a.example.test/v1", "k", ("CRITIC",), 5, priority=10, cost_class="FREE"),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "b", "https://b.example.test/v1", "k", ("CRITIC",), 5, priority=20, cost_class="FREE"),
        )
        router = ProviderRouter("FREE_FIRST", slots, ParallelAdapter(), parallelism=2, parallel_roles=("CRITIC",))
        results = router.complete_parallel(role="CRITIC", system="s", user="u", limit=2)
        self.assertEqual([slot.number for _, slot in results], [1, 2])
        self.assertEqual([content for content, _ in results], ["slot-1", "slot-2"])

    def test_parallel_target_backfills_later_candidates_after_provider_failure(self):
        class BackfillAdapter:
            def __init__(self):
                self.calls = []

            def complete(self, slot, *, system, user):
                self.calls.append(slot.number)
                if slot.number == 1:
                    raise ProviderUnavailable("Provider slot 1 request failed: HTTPError 503 sensitive-value")
                return f"slot-{slot.number}"

        slots = tuple(
            ProviderSlot(number, "OPENAI_COMPATIBLE", f"model-{number}", "https://example.test/v1", f"key-{number}", ("CRITIC",), 5, priority=number, cost_class="FREE")
            for number in (1, 2, 3)
        )
        adapter = BackfillAdapter()
        router = ProviderRouter("FREE_FIRST", slots, adapter, parallelism=2, parallel_roles=("CRITIC",))

        results = router.complete_parallel(role="CRITIC", system="s", user="u", limit=2)

        self.assertEqual([slot.number for _content, slot in results], [2, 3])
        self.assertEqual(sorted(adapter.calls), [1, 2, 3])

    def test_parallel_attempt_details_are_bounded_and_secret_free(self):
        class FailureAdapter:
            def complete(self, slot, *, system, user):
                if slot.number == 1:
                    raise ProviderUnavailable("Provider slot 1 request failed: HTTPError 503 secret-value")
                return f"slot-{slot.number}"

        slots = tuple(
            ProviderSlot(number, "OPENAI_COMPATIBLE", f"model-{number}", "https://example.test/v1", f"secret-key-{number}", ("CRITIC",), 5, priority=number, cost_class="FREE")
            for number in (1, 2, 3)
        )
        router = ProviderRouter("FREE_FIRST", slots, FailureAdapter(), parallelism=2, parallel_roles=("CRITIC",))
        results, attempts = router.complete_parallel_with_diagnostics(role="CRITIC", system="s", user="u", limit=2)

        self.assertEqual([slot.number for _content, slot in results], [2, 3])
        self.assertEqual([item["slot_number"] for item in attempts], [1, 2, 3])
        self.assertEqual(attempts[0]["transport_status"], "FAILURE")
        self.assertEqual(attempts[0]["failure_class"], "TRANSPORT_FAILURE")
        self.assertEqual(attempts[0]["failure_reason"], "HTTPError 503")
        self.assertEqual([item["attempt_order"] for item in attempts], [1, 2, 3])
        encoded = json.dumps(attempts)
        self.assertNotIn("secret-key-", encoded)
        self.assertNotIn("secret-value", encoded)

    def test_parallel_limit_is_role_scoped(self):
        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE", "a", "https://a.example.test/v1", "k", (), 5, cost_class="FREE"),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "b", "https://b.example.test/v1", "k", (), 5, cost_class="FREE"),
        )
        router = ProviderRouter("FREE_FIRST", slots, _Adapter({1: "a", 2: "b"}), parallelism=2, parallel_roles=("CRITIC",))
        self.assertEqual(router.parallel_limit("CRITIC"), 2)
        self.assertEqual(router.parallel_limit("LIGHTING_DESIGNER"), 1)

    def test_provider_pool_readiness_is_key_free_and_reports_role_parallelism(self):
        slots = (
            ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "local", "http://127.0.0.1:8080/v1", "", ("LIGHTING_DESIGNER", "CRITIC"), 5, cost_class="LOCAL"),
            ProviderSlot(2, "OPENAI_COMPATIBLE", "free", "https://example.test/v1", "secret", ("LIGHTING_DESIGNER", "CRITIC"), 5, cost_class="FREE"),
        )
        router = ProviderRouter("FREE_FIRST", slots, _Adapter({1: "{}", 2: "{}"}), parallelism=2, parallel_roles=("LIGHTING_DESIGNER", "CRITIC"))
        diagnostic = router.pool_readiness(health_by_slot={1: True, 2: False}, failure_by_slot={2: "TRANSPORT_ERROR"})
        self.assertFalse(diagnostic["secrets_included"])
        self.assertEqual(diagnostic["roles"]["LIGHTING_DESIGNER"]["healthy_independent_slots"], 1)
        self.assertFalse(diagnostic["roles"]["LIGHTING_DESIGNER"]["parallelism_satisfied"])
        self.assertNotIn('"api_key":', json.dumps(diagnostic))
        self.assertNotIn("secret-token", json.dumps(diagnostic))
        self.assertEqual(diagnostic["slots"][1]["failure_class"], "TRANSPORT_ERROR")

    def test_provider_pool_unknown_health_does_not_claim_ready(self):
        slot = ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "local", "http://127.0.0.1:8080/v1", "", (), 5, cost_class="LOCAL")
        diagnostic = ProviderRouter("PRIMARY_ONLY", (slot,), _Adapter({1: "{}"})).pool_readiness()
        self.assertEqual(diagnostic["roles"]["CRITIC"]["status"], "UNKNOWN")
        self.assertEqual(diagnostic["slots"][0]["healthy"], "UNKNOWN")

    def test_design_rejects_raw_command_fields(self):
        output = {key: {} for key in ("design_intent", "visual_strategy", "virtual_rig", "position_vocabulary", "main_sequence", "free_cue_layer", "evidence_trace")}
        output |= {"schema": SCHEMA, "ma2_commands": ["Store Sequence 1"]}
        with self.assertRaises(DesignValidationError):
            validate_design_output(output)

    def _http_slot(self):
        return ProviderSlot(1, "OPENAI_COMPATIBLE_LOCAL", "test", "http://127.0.0.1:8080/v1", "", (), 5)

    def test_http_error_preserves_status_and_safe_json_summary(self):
        error = HTTPError(
            "http://127.0.0.1:8080/v1/chat/completions",
            413,
            "Payload Too Large",
            {},
            io.BytesIO(b'{"error":{"message":"context too large"}}'),
        )
        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=error):
            with self.assertRaises(ProviderUnavailable) as raised:
                OpenAICompatibleHTTPAdapter().complete(self._http_slot(), system="s", user="u")
        self.assertIn("HTTPError 413", str(raised.exception))
        self.assertIn("context too large", str(raised.exception))

    def test_http_error_summary_does_not_leak_secret_or_headers(self):
        error = HTTPError(
            "http://127.0.0.1:8080/v1/chat/completions",
            400,
            "Bad Request",
            {"Authorization": "Bearer secret-token"},
            io.BytesIO(b'{"error":{"message":"Authorization Bearer secret-token"}}'),
        )
        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=error):
            with self.assertRaises(ProviderUnavailable) as raised:
                OpenAICompatibleHTTPAdapter().complete(self._http_slot(), system="s", user="u")
        self.assertEqual(str(raised.exception), "Provider slot 1 request failed: HTTPError 400")
        self.assertNotIn("secret-token", str(raised.exception))

    def test_text_only_http_request_keeps_user_content_as_plain_text(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"choices":[{"message":{"content":"{}"}}]}'

        captured = {}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=opener):
            OpenAICompatibleHTTPAdapter().complete(self._http_slot(), system="s", user="u")
        self.assertEqual(captured["body"]["messages"], [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "u"},
        ])

    def test_multimodal_http_request_contains_verified_image_bytes_not_local_path(self):
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"provider-visual-evidence"
        evidence = ProviderImageInput("image/png", image_bytes, hashlib.sha256(image_bytes).hexdigest())

        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"choices":[{"message":{"content":"{}"}}]}'

        captured = {}
        def opener(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return Response()

        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=opener):
            OpenAICompatibleHTTPAdapter().complete_with_image(
                self._http_slot(), system="s", user="u", visual_evidence=evidence,
            )
        user_content = captured["body"]["messages"][1]["content"]
        self.assertEqual(user_content[0], {"type": "text", "text": "u"})
        self.assertEqual(user_content[1]["type"], "image_url")
        self.assertEqual(
            user_content[1]["image_url"]["url"],
            "data:image/png;base64," + __import__("base64").b64encode(image_bytes).decode("ascii"),
        )
        self.assertNotIn("local/path", json.dumps(captured["body"]))

    def test_http_error_non_string_detail_is_discarded(self):
        error = HTTPError(
            "http://127.0.0.1:8080/v1/chat/completions",
            500,
            "Server Error",
            {},
            io.BytesIO(b'{"error":{"message":{"Authorization":"secret-token"}}}'),
        )
        with patch("zen_ma2_agent.llm.router.urlopen", side_effect=error):
            with self.assertRaises(ProviderUnavailable) as raised:
                OpenAICompatibleHTTPAdapter().complete(self._http_slot(), system="s", user="u")
        self.assertEqual(str(raised.exception), "Provider slot 1 request failed: HTTPError 500")
        self.assertNotIn("secret-token", str(raised.exception))

    def test_design_requires_structured_fields(self):
        with self.assertRaises(DesignValidationError):
            validate_design_output({"schema": SCHEMA})

    def test_zen_home_redirects_preferences_outside_repository(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"ZEN_HOME": temp}, clear=False):
            self.assertEqual(settings_path(), Path(temp) / "config" / "settings.json")

    def test_ma2_connectivity_is_tcp_only_and_uses_portable_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            path.write_text('{"ma2":{"host":"127.0.0.1","port":30000}}', encoding="utf-8")
            closed = []
            class Connection:
                def close(self): closed.append(True)
            result = ma2_connectivity(path, lambda address, timeout: Connection())
        self.assertEqual(result["MA2_CONNECTIVITY"], "TCP_REACHABLE")
        self.assertTrue(closed)


class LocalProviderNoApiKeyTests(unittest.TestCase):
    def test_local_type_is_configured_without_api_key(self):
        slot = ProviderSlot(
            number=1, provider_type="OPENAI_COMPATIBLE_LOCAL", model="local-model",
            base_url="http://127.0.0.1:1234/v1", api_key="", roles=(), timeout_seconds=45,
        )
        self.assertTrue(slot.configured)

    def test_cloud_type_still_requires_api_key(self):
        slot = ProviderSlot(
            number=1, provider_type="OPENAI_COMPATIBLE", model="gpt",
            base_url="https://api.example.com/v1", api_key="", roles=(), timeout_seconds=45,
        )
        self.assertFalse(slot.configured)


class PortableProviderSelfTestTests(unittest.TestCase):
    def test_scoped_multi_agent_slot_uses_an_eligible_probe_role(self):
        class ProbeAdapter:
            def __init__(self): self.calls = []
            def complete(self, slot, *, system, user):
                self.calls.append(slot.number)
                return '{"schema":"zen.provider_probe.v0.1","ready":true}'

        adapter = ProbeAdapter()
        slot = ProviderSlot(
            number=1, provider_type="OPENAI_COMPATIBLE_LOCAL", model="local-model",
            base_url="http://127.0.0.1:8080/v1", api_key="",
            roles=("RESEARCHER", "LIGHTING_DESIGNER", "CRITIC", "FINALIZER"), timeout_seconds=45,
        )
        router = ProviderRouter("PRIMARY_ONLY", (slot,), adapter)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "repo" / "ZEN-MA2-Agent" / ".git").mkdir(parents=True)
            with (
                patch("launcher.zen_portable_launcher.home", return_value=root),
                patch("launcher.zen_portable_launcher.repo", return_value=root / "repo" / "ZEN-MA2-Agent"),
                patch.object(ProviderRouter, "from_portable_config", return_value=router),
                patch("launcher.zen_portable_launcher._log"),
            ):
                result = provider_self_test()
        self.assertEqual(result["AUTONOMOUS_DESIGNER_AVAILABLE"], "YES")
        self.assertEqual(result["probe_role"], "RESEARCHER")
        self.assertEqual(adapter.calls, [1])


class ProviderRoleEligibilityTests(unittest.TestCase):
    def test_configured_role_is_case_insensitive_at_lookup(self):
        slot = ProviderSlot(
            number=1, provider_type="OPENAI_COMPATIBLE_LOCAL", model="local-model",
            base_url="http://127.0.0.1:8080/v1", api_key="", roles=("DESIGNER",), timeout_seconds=45,
        )
        self.assertTrue(slot.supports("designer"))

    def test_empty_roles_accept_any_role(self):
        slot = ProviderSlot(
            number=1, provider_type="OPENAI_COMPATIBLE_LOCAL", model="local-model",
            base_url="http://127.0.0.1:8080/v1", api_key="", roles=(), timeout_seconds=45,
        )
        self.assertTrue(slot.supports("CRITIC"))
