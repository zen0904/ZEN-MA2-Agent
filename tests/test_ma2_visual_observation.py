import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from zen_ma2_agent.ma2_visual_observation import (
    MA2Capture,
    MA2VisualObservationError,
    MA2VisualObservationService,
    MA2WindowInfo,
    OpenClawMA2VisionObserver,
    OpenClawVisionConfig,
)


class _Runner:
    def __init__(self, model_payload, *, returncode=0):
        self.model_payload = model_payload
        self.returncode = returncode
        self.command = None
        self.kwargs = None

    def __call__(self, command, **kwargs):
        self.command = list(command)
        self.kwargs = dict(kwargs)
        envelope = {
            "ok": True,
            "capability": "model.run",
            "transport": "local",
            "provider": "openai",
            "model": "gpt-5.6-sol",
            "attempts": [],
            "outputs": [{"text": json.dumps(self.model_payload), "mediaUrl": None}],
        }
        return subprocess.CompletedProcess(
            command,
            self.returncode,
            stdout=json.dumps(envelope),
            stderr="",
        )


class _Capture:
    def __init__(self, path: Path):
        self.path = path

    def capture(self, output_path: Path):
        output_path.write_bytes(b"fake-png")
        return MA2Capture(
            window=MA2WindowInfo(
                hwnd=123,
                pid=456,
                title="grandMA2 onPC",
                left=0,
                top=0,
                right=1016,
                bottom=631,
            ),
            image_path=output_path,
            sha256="a" * 64,
        )


class _Vision:
    def observe(self, image_path: Path):
        return {
            "is_grandma2": True,
            "capture_readable": True,
            "stage_view_visible": False,
            "visible_screen_or_panel": "Fixture / Position screen",
            "observations": ["Fixture controls are visible."],
            "limitations": ["Stage View is not visible."],
            "provider": "openai",
            "model": "gpt-5.6-sol",
            "transport": "local",
        }


class MA2VisualObservationTests(unittest.TestCase):
    def test_openclaw_vision_is_read_only_and_schema_bounded(self):
        runner = _Runner(
            {
                "is_grandma2": True,
                "capture_readable": True,
                "stage_view_visible": False,
                "panel": "Fixture / Position screen",
                "observations": ["Fixture controls are visible."],
                "limitations": ["Stage View is not visible."],
            }
        )
        provider = OpenClawMA2VisionObserver(
            OpenClawVisionConfig(executable="openclaw.cmd", agent="main"),
            runner=runner,
        )
        result = provider.observe(Path(r"C:\tmp\ma2.png"))

        self.assertTrue(result["is_grandma2"])
        self.assertFalse(result["stage_view_visible"])
        self.assertEqual(result["provider"], "openai")
        self.assertIn("--file", runner.command)
        self.assertIn("--local", runner.command)
        self.assertNotIn("zen.approve", " ".join(runner.command))
        self.assertNotIn("telnet", " ".join(runner.command).lower())

    def test_openclaw_vision_rejects_extra_model_fields(self):
        runner = _Runner(
            {
                "is_grandma2": True,
                "capture_readable": True,
                "stage_view_visible": False,
                "panel": "Fixture",
                "observations": [],
                "limitations": [],
                "raw_ma_command": "Fixture 1 At 100",
            }
        )
        provider = OpenClawMA2VisionObserver(
            OpenClawVisionConfig(executable="openclaw.cmd"),
            runner=runner,
        )
        with self.assertRaisesRegex(MA2VisualObservationError, "unexpected or missing"):
            provider.observe(Path(r"C:\tmp\ma2.png"))

    def test_service_keeps_visual_observations_non_authoritative(self):
        with tempfile.TemporaryDirectory(prefix="zen-ma2-visual-") as tmp:
            root = Path(tmp)
            service = MA2VisualObservationService(
                _Capture(root / "unused.png"),
                _Vision(),
                evidence_dir=root,
            )
            result = service.observe()

            self.assertEqual(result["schema"], "zen.ma2_visual_observation.v0.1")
            self.assertEqual(result["source_type"], "MACHINE_CAPTURED_MA2_WINDOW")
            self.assertEqual(result["show_binding_status"], "UNBOUND_VISUAL_OBSERVATION")
            self.assertEqual(result["vision"]["ma_write_authority"], "NONE")
            self.assertEqual(result["ma2_writes"], 0)
            observation = result["visual_observations"][0]
            self.assertEqual(observation["evidence_class"], "VISUAL_OBSERVATION")
            self.assertFalse(observation["verified_physical_fact"])
            self.assertEqual(observation["source_image_sha256"], "a" * 64)
            self.assertTrue((root / "latest_ma2_visual_observation.json").is_file())


if __name__ == "__main__":
    unittest.main()
