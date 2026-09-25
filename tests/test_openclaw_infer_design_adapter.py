import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from zen_ma2_agent.llm.openclaw_infer_adapter import (
    OpenClawInferConfig,
    OpenClawInferLeanDesignIntelligence,
    load_openclaw_infer_design_intelligence,
)


class _Runner:
    def __init__(self, payload, *, returncode=0, stdout_prefix=""):
        self.payload = payload
        self.returncode = returncode
        self.stdout_prefix = stdout_prefix
        self.command = None
        self.kwargs = None
        self.input_path = None
        self.input_payload = None
        self.input_existed_during_call = False

    def __call__(self, command, **kwargs):
        self.command = list(command)
        self.kwargs = dict(kwargs)
        self.input_path = Path(command[2])
        self.input_existed_during_call = self.input_path.is_file()
        if self.input_existed_during_call:
            self.input_payload = json.loads(self.input_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(
            command,
            self.returncode,
            stdout=self.stdout_prefix + json.dumps(self.payload),
            stderr="",
        )


def _config():
    return OpenClawInferConfig(
        node_executable="node.exe",
        openclaw_root=r"C:\OpenClaw",
        openclaw_config_path=r"C:\Users\test\.openclaw\openclaw.json",
        agent="main",
        timeout_seconds=45,
    )


class OpenClawInferDesignAdapterTests(unittest.TestCase):
    def test_design_uses_sdk_file_handoff_and_returns_artistic_text(self):
        artistic = '{"cues":[{"label":"INTRO","fade":0,"actions":[{"group":1,"dimmer":50}]}]}'
        runner = _Runner(
            {
                "ok": True,
                "capability": "model.run",
                "transport": "sdk-local",
                "provider": "openai",
                "model": "gpt-5.6-sol",
                "outputs": [{"text": artistic, "mediaUrl": None}],
            }
        )
        provider = OpenClawInferLeanDesignIntelligence(_config(), runner=runner)

        result = provider.design(
            "make this song dramatic",
            {
                "verified_resource_contract": {
                    "group_resources": [{"group_id": 1}],
                }
            },
        )

        self.assertEqual(result, artistic)
        self.assertEqual(runner.command[0], "node.exe")
        self.assertTrue(runner.command[1].endswith("openclaw_sdk_infer.mjs"))
        self.assertEqual(runner.command[3], r"C:\OpenClaw")
        self.assertEqual(
            runner.command[4],
            r"C:\Users\test\.openclaw\openclaw.json",
        )
        self.assertEqual(runner.command[5], "main")
        self.assertTrue(runner.input_existed_during_call)
        self.assertIn("Never emit MA2 commands", runner.input_payload["system_prompt"])
        self.assertIn(
            '"request":"make this song dramatic"',
            runner.input_payload["user_prompt"],
        )
        self.assertIn('"group_id":1', runner.input_payload["user_prompt"])
        self.assertFalse(runner.input_path.exists())
        self.assertNotIn("make this song dramatic", " ".join(runner.command))
        self.assertEqual(provider.last_diagnostics["provider"], "openai")
        self.assertEqual(provider.last_diagnostics["model"], "gpt-5.6-sol")
        self.assertEqual(provider.last_diagnostics["transport"], "sdk-local")
        self.assertFalse(provider.last_diagnostics["tools_available_to_model"])

    def test_large_context_never_enters_windows_command_line(self):
        runner = _Runner(
            {
                "ok": True,
                "capability": "model.run",
                "transport": "sdk-local",
                "provider": "openai",
                "model": "gpt-5.6-sol",
                "outputs": [{"text": '{"cues":[]}', "mediaUrl": None}],
            }
        )
        provider = OpenClawInferLeanDesignIntelligence(_config(), runner=runner)
        provider.design("large context test", {"blob": "x" * 60000})

        self.assertGreater(len(runner.input_payload["user_prompt"]), 60000)
        self.assertLess(len(" ".join(runner.command)), 1000)
        self.assertNotIn("x" * 100, " ".join(runner.command))
        self.assertFalse(runner.input_path.exists())

    def test_provider_stdout_diagnostics_before_envelope_are_ignored(self):
        artistic = '{"cues":[]}'
        runner = _Runner(
            {
                "ok": True,
                "capability": "model.run",
                "transport": "sdk-local",
                "provider": "openai",
                "model": "gpt-5.6-sol",
                "outputs": [{"text": artistic, "mediaUrl": None}],
            },
            stdout_prefix=(
                "\x1b[33m[provider-transport-fetch]\x1b[39m start\n"
                "\x1b[33m[provider-transport-fetch]\x1b[39m response status=200\n"
            ),
        )
        provider = OpenClawInferLeanDesignIntelligence(_config(), runner=runner)
        self.assertEqual(provider.design("test", {}), artistic)

    def test_design_fails_closed_on_unexpected_transport(self):
        runner = _Runner(
            {
                "ok": True,
                "capability": "model.run",
                "transport": "gateway",
                "outputs": [{"text": '{"cues":[]}'}],
            }
        )
        provider = OpenClawInferLeanDesignIntelligence(_config(), runner=runner)
        with self.assertRaisesRegex(RuntimeError, "unexpected capability/transport"):
            provider.design("test", {})

    def test_factory_is_configuration_only_and_can_be_disabled(self):
        with patch.dict(os.environ, {"ZEN_OPENCLAW_INFER_ENABLED": "0"}, clear=False), patch(
            "zen_ma2_agent.llm.openclaw_infer_adapter._resolve_openclaw_executable"
        ) as resolve:
            self.assertIsNone(load_openclaw_infer_design_intelligence())
        resolve.assert_not_called()

    def test_factory_uses_resolved_openclaw_sdk_without_provider_probe(self):
        package_root = Path(r"C:\Tools\node_modules\openclaw")
        config_path = Path(r"C:\Users\test\.openclaw\openclaw.json")
        with patch.dict(
            os.environ,
            {
                "ZEN_OPENCLAW_INFER_ENABLED": "1",
                "ZEN_OPENCLAW_INFER_AGENT": "main",
                "ZEN_OPENCLAW_INFER_TIMEOUT_SECONDS": "75",
            },
            clear=False,
        ), patch(
            "zen_ma2_agent.llm.openclaw_infer_adapter._resolve_openclaw_executable",
            return_value=r"C:\Tools\openclaw.cmd",
        ), patch(
            "zen_ma2_agent.llm.openclaw_infer_adapter._resolve_node_executable",
            return_value=r"C:\Program Files\nodejs\node.exe",
        ), patch(
            "zen_ma2_agent.llm.openclaw_infer_adapter._resolve_openclaw_config_path",
            return_value=config_path,
        ), patch(
            "zen_ma2_agent.llm.openclaw_infer_adapter._resolve_openclaw_package_root",
            return_value=package_root,
        ) as resolve_root:
            provider = load_openclaw_infer_design_intelligence()

        self.assertIsNotNone(provider)
        resolve_root.assert_called_once_with(r"C:\Tools\openclaw.cmd")
        self.assertEqual(
            provider.config.node_executable,
            r"C:\Program Files\nodejs\node.exe",
        )
        self.assertEqual(provider.config.openclaw_root, str(package_root))
        self.assertEqual(provider.config.openclaw_config_path, str(config_path))
        self.assertEqual(provider.config.agent, "main")
        self.assertEqual(provider.config.timeout_seconds, 75.0)
        self.assertFalse(provider.safe_summary()["tools_available_to_model"])


if __name__ == "__main__":
    unittest.main()
