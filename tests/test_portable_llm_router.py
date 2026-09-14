from __future__ import annotations

import json
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from zen_ma2_agent.llm.autonomous_designer import SCHEMA, DesignValidationError, validate_design_output
from zen_ma2_agent.llm.router import OpenAICompatibleHTTPAdapter, ProviderRouter, ProviderSlot, ProviderUnavailable, load_provider_slots
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
