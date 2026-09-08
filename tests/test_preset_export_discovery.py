import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from zen_ma2_agent.state.providers.group_membership import GroupMembershipProviderUnavailable
from zen_ma2_agent.state.providers.preset_export import PresetExportError, PresetExportProvider, preset_export_discovery


class ExportRuntime:
    def __init__(self, directory: Path, *, host: str = "127.0.0.1", xml: bytes = b"<Root><Opaque fixture='101' attribute='PAN' value='255'/></Root>"):
        self.preferences = {"ma2": {"host": host}}
        self.root = directory
        self.directory = directory
        self.xml = xml
        self.commands: list[tuple[str, str]] = []
        self.logs: list[tuple[str, dict]] = []

    @contextmanager
    def export_transaction(self):
        yield

    def export_preset_file(self, preset_ref: str, filename: str) -> str:
        self.commands.append((preset_ref, filename))
        (self.directory / filename).write_bytes(self.xml)
        return "Executing : Export Preset"

    def log(self, event: str, data: dict) -> None:
        self.logs.append((event, data))


class PresetExportDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-preset-export-")
        self.directory = Path(self.temp.name)
        self.settings = {"importexport_path": str(self.directory), "timeout_seconds": 1.0}

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, **kwargs):
        return PresetExportProvider(request_id_factory=lambda: "request0001", **kwargs)

    def test_unknown_well_formed_xml_creates_no_fixture_attribute_or_value_claim(self):
        result = preset_export_discovery("<Root><Opaque fixture='101' attribute='PAN' value='255'/></Root>", "2.21")
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["status"], "SCHEMA_UNVERIFIED")
        self.assertEqual(result["xml_discovery"]["attributes_by_element"]["Opaque"], ["attribute", "fixture", "value"])

    def test_export_uses_unique_agent_filename_and_cleans_importexport_file(self):
        runtime = ExportRuntime(self.directory)
        result = self.provider().export_and_discover(runtime, "2.21", self.settings)
        self.assertEqual(runtime.commands, [("2.21", "ZEN_AGENT_PRESET_2_21_request0001.xml")])
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["export"]["cleanup"], "AGENT_OWNED_TEMPORARY_FILE_REMOVED")
        self.assertFalse((self.directory / "ZEN_AGENT_PRESET_2_21_request0001.xml").exists())

    def test_explicit_retention_copies_then_cleans_the_importexport_file(self):
        runtime = ExportRuntime(self.directory)
        result = self.provider().export_and_discover(runtime, "2.21", self.settings, retain_export=True)
        retained = Path(result["export"]["retained_copy_path"])
        self.assertTrue(retained.is_file())
        self.assertFalse((self.directory / "ZEN_AGENT_PRESET_2_21_request0001.xml").exists())

    def test_malformed_xml_is_rejected_and_never_becomes_an_observation(self):
        runtime = ExportRuntime(self.directory, xml=b"<Root><Broken>")
        with self.assertRaisesRegex(PresetExportError, "MALFORMED"):
            self.provider(poll_seconds=.01).export_and_discover(runtime, "2.21", {**self.settings, "timeout_seconds": .1})
        self.assertIn("preset_export_diagnostic", [event for event, _data in runtime.logs])

    def test_timeout_is_reported_as_timeout_not_malformed_xml(self):
        class AdvancingClock:
            value = 0.0
            def __call__(self):
                current = self.value
                self.value += .2
                return current

        class NoFileRuntime(ExportRuntime):
            def export_preset_file(self, preset_ref, filename):
                self.commands.append((preset_ref, filename))
                return "Executing : Export Preset"

        runtime = NoFileRuntime(self.directory)
        provider = PresetExportProvider(request_id_factory=lambda: "request0001", monotonic_clock=AdvancingClock(), sleep=lambda _seconds: None)
        with self.assertRaisesRegex(PresetExportError, "EXPORT_FILE_TIMEOUT"):
            provider.export_and_discover(runtime, "2.21", {**self.settings, "timeout_seconds": .5})
        details = [data for event, data in runtime.logs if event == "preset_export_diagnostic"][-1]
        self.assertEqual(details["error"], "EXPORT_FILE_TIMEOUT")

    def test_remote_console_is_blocked_before_export(self):
        runtime = ExportRuntime(self.directory, host="10.0.0.5")
        with self.assertRaisesRegex(GroupMembershipProviderUnavailable, "REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM"):
            self.provider().export_and_discover(runtime, "2.21", self.settings)
        self.assertEqual(runtime.commands, [])

    def test_invalid_reference_is_rejected_before_export(self):
        with self.assertRaisesRegex(ValueError, "numeric type.id"):
            self.provider().export_and_discover(ExportRuntime(self.directory), "Position 21", self.settings)


if __name__ == "__main__":
    unittest.main()
