import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from zen_ma2_agent.scanner import ShowScanner
from zen_ma2_agent.state.providers.fixture_type_export import (
    FixtureTypeExportError,
    FixtureTypeExportProvider,
    bind_local_profile_candidate,
    fixture_type_export_binding,
)
from zen_ma2_agent.state.providers.group_membership import GroupMembershipProviderUnavailable
from zen_ma2_agent.state.store import StateStore


def fixture_type_xml(*, index=2, name="ZEN BAW 20R", mode="Mode 2", channels=None):
    channels = channels or [
        '<ChannelType index="0" attribute="DIM" feature="DIMMER" preset="DIMMER" coarse="1" />',
        '<ChannelType index="1" attribute="COLORRGB1" feature="COLORRGB" preset="COLOR" coarse="2" />',
        '<ChannelType index="2" attribute="PAN" feature="POSITION" preset="POSITION" coarse="3" />',
        '<ChannelType index="3" attribute="TILT" feature="POSITION" preset="POSITION" coarse="4" />',
        '<ChannelType index="4" attribute="GOBO1" feature="GOBO1" preset="GOBO" coarse="5" />',
        '<ChannelType index="5" attribute="PRISM1" feature="PRISM" preset="BEAM" coarse="6" />',
        '<ChannelType index="6" attribute="ZOOM" feature="FOCUS" preset="FOCUS" coarse="7" />',
        '<ChannelType index="7" attribute="FOCUS" feature="FOCUS" preset="FOCUS" coarse="8" />',
        '<ChannelType index="8" attribute="FROST" feature="BEAM1" preset="BEAM" coarse="9" />',
        '<ChannelType index="9" attribute="SHUTTER" feature="SHUTTER" preset="BEAM" coarse="10" />',
    ]
    return ('<MA major_vers="3" minor_vers="9" stream_vers="60">'
            f'<FixtureType index="{index}" name="{name}" mode="{mode}"><Module>'
            + ''.join(channels) + '</Module></FixtureType></MA>').encode("utf-8")


class ExportRuntime:
    def __init__(self, directory: Path, *, host="127.0.0.1", xml=None):
        self.preferences = {"ma2": {"host": host}}
        self.root = directory
        self.directory = directory
        self.xml = xml or fixture_type_xml()
        self.commands = []
        self.logs = []

    @contextmanager
    def export_transaction(self):
        yield

    def export_fixture_type_file(self, fixture_type_id, filename):
        self.commands.append((fixture_type_id, filename))
        (self.directory / filename).write_bytes(self.xml)
        return "Executing : Export FixtureType"

    def log(self, event, data):
        self.logs.append((event, data))


class FixtureTypeExportBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-fixture-type-export-")
        self.directory = Path(self.temp.name)
        self.settings = {"importexport_path": str(self.directory), "timeout_seconds": 1.0}

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def provider(**kwargs):
        class Resolver:
            def __init__(self, directory):
                self.directory = directory
            def resolve_library(self, _configured):
                return self.directory
        return FixtureTypeExportProvider(Resolver(kwargs.pop("directory")), request_id_factory=lambda: "request0001", **kwargs)

    def test_exact_current_show_export_binds_identity_and_channels(self):
        result = fixture_type_export_binding(fixture_type_xml(), "2 ZEN BAW 20R Mode 2")
        self.assertEqual(result["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(result["fixture_type"], {
            "fixture_type_id": 2, "list_label": "2 ZEN BAW 20R Mode 2", "xml_index": 2,
            "name": "ZEN BAW 20R", "mode": "Mode 2",
            "ma_version": {"major": "3", "minor": "9", "stream": "60"},
        })
        self.assertEqual(result["capabilities"]["DIMMER"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(result["capabilities"]["POSITION"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(result["capabilities"]["PRISM"]["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(result["capabilities"]["PIXEL_SHAPE"]["status"], "UNCLASSIFIED_FROM_CHANNEL_INVENTORY")

    def test_mismatched_exported_id_or_label_never_becomes_capability_evidence(self):
        with self.assertRaisesRegex(FixtureTypeExportError, "ID_MISMATCH"):
            fixture_type_export_binding(fixture_type_xml(index=3), "2 ZEN BAW 20R Mode 2")
        with self.assertRaisesRegex(FixtureTypeExportError, "LABEL_MISMATCH"):
            fixture_type_export_binding(fixture_type_xml(name="Other"), "2 ZEN BAW 20R Mode 2")

    def test_ambiguous_or_channelless_xml_fails_closed(self):
        with self.assertRaisesRegex(FixtureTypeExportError, "COUNT_MISMATCH"):
            fixture_type_export_binding(b"<MA><FixtureType index='2'/><FixtureType index='2'/></MA>", "2 ZEN BAW 20R Mode 2")
        with self.assertRaisesRegex(FixtureTypeExportError, "CHANNELS_NOT_PRESENT"):
            fixture_type_export_binding(b"<MA><FixtureType index='2' name='ZEN BAW 20R' mode='Mode 2'/></MA>", "2 ZEN BAW 20R Mode 2")

    def test_local_candidate_requires_exact_structural_channel_definition_match(self):
        show_bound = fixture_type_export_binding(fixture_type_xml(), "2 ZEN BAW 20R Mode 2")
        equivalent = fixture_type_xml(index=99, name="Library BAW", mode="Other Mode")
        self.assertEqual(bind_local_profile_candidate(show_bound, equivalent)["status"], "LOCAL_PROFILE_CANDIDATE_BOUND")
        changed = fixture_type_xml(channels=['<ChannelType index="0" attribute="DIM" feature="DIMMER" preset="DIMMER" coarse="99" />'])
        self.assertEqual(bind_local_profile_candidate(show_bound, changed)["status"], "LOCAL_PROFILE_CANDIDATE_UNBOUND")

    def test_provider_exports_exact_type_to_owned_file_then_cleans_it(self):
        runtime = ExportRuntime(self.directory)
        result = self.provider(directory=self.directory).export_and_bind(runtime, "2 ZEN BAW 20R Mode 2", self.settings)
        self.assertEqual(runtime.commands, [(2, "ZEN_AGENT_FT_2_request0001.xml")])
        self.assertEqual(result["status"], "SHOW_BOUND_VERIFIED")
        self.assertEqual(result["export"]["cleanup"], "AGENT_OWNED_TEMPORARY_FILE_REMOVED")
        self.assertFalse((self.directory / "ZEN_AGENT_FT_2_request0001.xml").exists())

    def test_remote_console_is_blocked_before_export(self):
        runtime = ExportRuntime(self.directory, host="10.0.0.8")
        with self.assertRaisesRegex(GroupMembershipProviderUnavailable, "REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM"):
            self.provider(directory=self.directory).export_and_bind(runtime, "2 ZEN BAW 20R Mode 2", self.settings)
        self.assertEqual(runtime.commands, [])

    def test_scanner_retains_optional_show_bound_profiles_without_breaking_fixture_contract(self):
        state = StateStore()
        state.put("fixtures", [{"number": 101, "name": "Hybrid 1", "fixture_type": "2 ZEN BAW 20R Mode 2"}], source="ma2_telnet_list")
        bound = fixture_type_export_binding(fixture_type_xml(), "2 ZEN BAW 20R Mode 2")
        state.put("fixture_type_profiles", [bound], source="ma2_export_fixture_type_xml")
        profile = ShowScanner().scan(state)
        self.assertEqual(profile["fixture_type_profiles"], [bound])
        self.assertEqual(profile["known_limits"]["fixture_type_structure"], "SUPPORTED")


if __name__ == "__main__":
    unittest.main()
