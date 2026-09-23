import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.group_membership import GroupMembershipProviderUnavailable
from zen_ma2_agent.state.providers.sequence_export import (
    SequenceExportParseError,
    SequenceExportProvider,
    sequence_export_discovery,
)
from zen_ma2_agent.telnet_client import ConnectionState


SEQUENCE_XML = b'''<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA">
  <Sequ><Cue index="1"><Number number="4" sub_number="500"/>
    <CuePart index="0" name="Impact"/><CuePart index="1" name="Tail"/>
    <CueDatas>
      <CueData value_multipart_index="0" effect_multipart_index="0">
        <Channel fixture_id="101" channel_id="2" subfixture_id="1" attribute_name="Dimmer"/>
        <Value>42.5</Value><Fade>1.25</Fade><Delay>0.5</Delay>
        <Preset name="Dimmer Half"><No>1</No><No>101</No></Preset>
        <Effect name="Pulse"><No>1</No><No>9</No></Effect><EffectFlags>F</EffectFlags>
        <EffectRate>2.0</EffectRate><EffectLow>10</EffectLow>
        <EffectLowPreset><No>2</No><No>7</No></EffectLowPreset>
        <EffectHigh>90</EffectHigh><EffectHighPreset name="High"><No>2</No><No>8</No></EffectHighPreset>
        <EffectPhase>180</EffectPhase><EffectWidth>50</EffectWidth>
      </CueData>
      <CueData value_multipart_index="1" effect_multipart_index="1">
        <Channel fixture_id="101" channel_id="2" attribute_name="Color"/><Value>17</Value>
      </CueData>
    </CueDatas>
  </Cue></Sequ>
</MA>'''


class ExportRuntime:
    def __init__(self, directory: Path, xml: bytes = SEQUENCE_XML, host: str = "127.0.0.1"):
        self.preferences = {"ma2": {"host": host}}
        self.root = directory
        self.directory = directory
        self.xml = xml
        self.commands = []
        self.logs = []

    @contextmanager
    def export_transaction(self):
        yield

    def export_sequence_file(self, sequence_no, filename):
        self.commands.append((sequence_no, filename))
        (self.directory / filename).write_bytes(self.xml)
        return "Executing : Export Sequence"

    def log(self, event, data):
        self.logs.append((event, data))


class SequenceExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zen-sequence-export-")
        self.directory = Path(self.temp.name)
        self.settings = {"importexport_path": str(self.directory), "timeout_seconds": 1.0}

    def tearDown(self):
        self.temp.cleanup()

    def provider(self, **kwargs):
        return SequenceExportProvider(request_id_factory=lambda: "request0001", **kwargs)

    def test_parser_preserves_xsl_demonstrated_cue_content(self):
        result = sequence_export_discovery(SEQUENCE_XML, 5)
        self.assertEqual(result["status"], "VERIFIED")
        cue = result["cues"][0]
        self.assertEqual(cue["number"], {"number": "4", "sub_number": "500"})
        self.assertEqual(cue["parts"][0]["index"], "0")
        self.assertEqual(cue["parts"][0]["name"], "Impact")
        row = cue["parts"][0]["cue_data"][0]
        self.assertEqual(row["channel"], {"fixture_id": "101", "channel_id": "2", "subfixture_id": "1", "attribute_name": "Dimmer"})
        self.assertEqual(row["raw_values"]["Value"], "42.5")
        self.assertEqual(row["raw_values"]["Fade"], "1.25")
        self.assertEqual(row["raw_values"]["Delay"], "0.5")
        self.assertEqual(row["preset"]["no_components"], ["1", "101"])
        self.assertEqual(row["effect"]["display"], '1.9 "Pulse"')
        self.assertEqual(row["effect_low_preset"]["no_components"], ["2", "7"])
        self.assertEqual(row["effect"]["no_components"], ["1", "9"])
        self.assertEqual(row["raw_values"]["EffectPhase"], "180")

    def test_malformed_and_absent_cuedatas_are_explicit(self):
        with self.assertRaisesRegex(SequenceExportParseError, "MALFORMED"):
            sequence_export_discovery(b"<MA><Sequ>", 5)
        partial = sequence_export_discovery(b'<MA><Sequ><Cue><Number number="1"/><CuePart index="0" name="Only"/></Cue></Sequ></MA>', 5)
        self.assertEqual(partial["status"], "PARTIAL")
        unsupported = sequence_export_discovery(b"<MA><Group /></MA>", 5)
        self.assertEqual(unsupported["status"], "UNSUPPORTED")

    def test_provider_uses_exact_owned_name_and_cleans_only_that_file(self):
        foreign = self.directory / "keep-this.xml"
        foreign.write_text("foreign", encoding="utf-8")
        result = self.provider().export_and_discover(ExportRuntime(self.directory), 5, self.settings)
        self.assertEqual(result["export"]["filename"], "ZEN_AGENT_SEQUENCE_5_request0001.xml")
        self.assertFalse((self.directory / result["export"]["filename"]).exists())
        self.assertTrue(foreign.exists())

    def test_provider_remote_and_invalid_request_are_blocked(self):
        with self.assertRaisesRegex(GroupMembershipProviderUnavailable, "REMOTE_CONSOLE"):
            self.provider().export_and_discover(ExportRuntime(self.directory, host="10.0.0.5"), 5, self.settings)
        with self.assertRaisesRegex(ValueError, "positive sequence"):
            self.provider().export_and_discover(ExportRuntime(self.directory), True, self.settings)
        with self.assertRaisesRegex(SequenceExportParseError, "INVALID_EXPORT_REQUEST_ID"):
            SequenceExportProvider(request_id_factory=lambda: "bad/name").export_and_discover(ExportRuntime(self.directory), 5, self.settings)

    def test_malformed_export_is_retained_for_diagnostics(self):
        runtime = ExportRuntime(self.directory, xml=b"<MA><Sequ>")
        with self.assertRaisesRegex(SequenceExportParseError, "MALFORMED"):
            self.provider(poll_seconds=.01).export_and_discover(runtime, 5, {**self.settings, "timeout_seconds": .1})
        target = self.directory / "ZEN_AGENT_SEQUENCE_5_request0001.xml"
        self.assertTrue(target.exists())
        self.assertTrue(any(event == "sequence_export_diagnostic" for event, _data in runtime.logs))


class RuntimeSequenceCommandTests(unittest.TestCase):
    def test_runtime_validates_sequence_and_filename_before_execute(self):
        class Client:
            state = ConnectionState.READY
            def __init__(self): self.commands = []
            def execute(self, command): self.commands.append(command); return "ok"

        with tempfile.TemporaryDirectory(prefix="zen-runtime-") as folder:
            runtime = AgentRuntime(Path(folder))
            runtime.client = Client()
            self.assertEqual(runtime.export_sequence_file(5, "ZEN_AGENT_SEQUENCE_5_request0001.xml"), "ok")
            self.assertEqual(runtime.client.commands, ['Export Sequence 5 "ZEN_AGENT_SEQUENCE_5_request0001.xml" /nc'])
            with self.assertRaises(ValueError): runtime.export_sequence_file(True, "ZEN_AGENT_SEQUENCE_5_request0001.xml")
            with self.assertRaises(ValueError): runtime.export_sequence_file(0, "ZEN_AGENT_SEQUENCE_5_request0001.xml")
            with self.assertRaises(PermissionError): runtime.export_sequence_file(5, "foreign.xml")
            with self.assertRaises(PermissionError): runtime.export_sequence_file(5, 'ZEN_AGENT_SEQUENCE_5_x" /nc')


if __name__ == "__main__":
    unittest.main()
