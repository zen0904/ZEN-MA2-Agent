import json
import io
import unittest
from contextlib import redirect_stderr
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.translate_sequence_export import main as translate_file_main

from zen_ma2_agent.reverse_artistic_translator import (
    ReverseArtisticTranslationError,
    translate_sequence_evidence,
    translate_sequence_collection,
    translate_sequence_xml,
)
from zen_ma2_agent.state.providers.sequence_export import sequence_export_discovery


SEQUENCE_XML = b'''<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA">
  <Sequ>
    <Cue index="1"><Number number="1" sub_number="0"/><CuePart index="0" name="BUILD"/>
      <CueDatas>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="Dimmer"/><Value>35</Value><Fade>1.5</Fade></CueData>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="ColorRGB1"/><Preset><No>1</No><No>4</No><No>101</No></Preset></CueData>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="Pan"/><Effect><No>1</No><No>9</No></Effect></CueData>
      </CueDatas>
    </Cue>
    <Cue index="2"><Number number="2" sub_number="0"/><CuePart index="0" name="IMPACT"/>
      <CueDatas><CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="102" attribute_name="Dimmer"/><Value>100</Value></CueData></CueDatas>
    </Cue>
    <Cue index="3"><Number number="3" sub_number="0"/><CuePart index="0" name="BUILD_RETURN"/>
      <CueDatas>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="102" attribute_name="Dimmer"/><Value>45</Value><Fade>2</Fade></CueData>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="102" attribute_name="ColorRGB1"/><Preset><No>1</No><No>4</No><No>102</No></Preset></CueData>
        <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="102" attribute_name="Pan"/><Effect><No>1</No><No>10</No></Effect></CueData>
      </CueDatas>
    </Cue>
  </Sequ>
</MA>'''


class ReverseArtisticTranslatorTests(unittest.TestCase):
    def test_cli_writes_new_utf8_json_without_overwriting(self):
        with TemporaryDirectory() as folder:
            source = Path(folder) / "sequence.xml"
            output = Path(folder) / "reference.json"
            source.write_bytes(SEQUENCE_XML)
            self.assertEqual(translate_file_main([str(source), "--sequence", "42", "--output", str(output)]), 0)
            raw = output.read_bytes()
            self.assertTrue(raw.startswith(b"{\n"))
            self.assertEqual(json.loads(raw.decode("utf-8"))["technical_structure"]["sequence_no"], 42)
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                translate_file_main([str(source), "--sequence", "42", "--output", str(output)])

    def test_translates_native_xml_to_descriptive_reference(self):
        result = translate_sequence_xml(SEQUENCE_XML, 42)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["translation_status"], "OBSERVED")
        self.assertEqual(result["technical_structure"]["sequence_no"], 42)
        self.assertEqual(result["technical_structure"]["numbered_cue_count"], 3)
        self.assertEqual(result["technical_structure"]["observed_dimensions"], {"COLOR": 2, "DIMMER": 3, "POSITION": 2})
        first = result["cue_semantics"][0]
        self.assertEqual(first["observable_layers"], {"EFFECT_REFERENCE": 1, "PRESET_REFERENCE": 1, "RAW_VALUE": 1})
        self.assertEqual(first["preset_references"], ["4.101"])
        self.assertEqual(first["effect_references"], ["9"])
        self.assertIn("1.4.101", [row["preset"] for row in first["observed_cue_data"]])
        self.assertEqual(first["observable_behaviors"], [{
            "type": "EFFECT_REFERENCE", "part_index": "0", "effect_id": "9",
            "fixture_refs": ["101"], "evidence_status": "OBSERVED_IN_CUE_DATA",
            "effect_playback_semantics": "NOT_CLAIMED",
        }])
        self.assertEqual(first["intent_status"], "NOT_INFERRED_FROM_SEQUENCE_XML")
        motifs = result["recurring_artistic_motifs"]
        self.assertEqual(motifs, [])
        reference = result["machine_readable_design_reference"]
        self.assertEqual(len(reference["cue_patterns"]), 3)
        self.assertEqual(reference["cue_patterns"][0]["content_fingerprint"], first["content_fingerprint"])
        self.assertEqual(reference["cue_patterns"][0]["observed_cue_data"][0]["channel"]["fixture_id"], "101")
        self.assertIn("MA2_WRITE_COMMANDS", reference["prohibited_inferences"])
        self.assertIn("REQUIRES_CURRENT_SHOW_RESOURCE_VALIDATION_BEFORE_ANY_REUSE", reference["use_constraints"])

    def test_recurrence_requires_same_targets_values_resources_and_parts(self):
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        repeated = deepcopy(discovery["cues"][0])
        repeated["number"] = {"number": "4", "sub_number": "0"}
        repeated["parts"][0]["name"] = "RETURN"
        discovery["cues"].append(repeated)
        result = translate_sequence_evidence(discovery)
        motifs = result["recurring_artistic_motifs"]
        self.assertEqual(len(motifs), 1)
        self.assertEqual(motifs[0]["cue_numbers"], ["1", "4"])
        self.assertEqual(motifs[0]["classification"], "RECURRING_STORED_CUE_CONTENT")

    def test_timing_only_row_is_not_raw_value_content(self):
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        discovery["cues"][0]["parts"][0]["cue_data"][0]["raw_values"] = {"Fade": "1.5"}
        result = translate_sequence_evidence(discovery)
        self.assertEqual(result["cue_semantics"][0]["observable_layers"].get("RAW_VALUE"), None)

    def test_position_behaviors_require_complete_pair_and_distinguish_preset(self):
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        cues = discovery["cues"]
        cues[0]["parts"][0]["cue_data"] = [
            {"channel": {"fixture_id": "101", "attribute_name": "PAN"}, "raw_values": {"Value": "20"}, "preset": None},
            {"channel": {"fixture_id": "101", "attribute_name": "TILT"}, "raw_values": {"Value": "30"}, "preset": None},
        ]
        cues[1]["parts"][0]["cue_data"] = [
            {"channel": {"fixture_id": "101", "attribute_name": "PAN"}, "raw_values": {"Value": "20"}, "preset": {"no_components": ["1", "2", "13"]}},
            {"channel": {"fixture_id": "101", "attribute_name": "TILT"}, "raw_values": {"Value": "30"}, "preset": {"no_components": ["1", "2", "13"]}},
        ]
        cues[2]["parts"][0]["cue_data"] = cues[0]["parts"][0]["cue_data"][:1]
        result = translate_sequence_evidence(discovery)
        self.assertEqual(result["cue_semantics"][0]["observable_behaviors"][0]["type"], "RAW_PAN_TILT")
        self.assertEqual(result["cue_semantics"][0]["observable_behaviors"][0]["raw_values"], {"PAN": "20", "TILT": "30"})
        self.assertEqual(result["cue_semantics"][1]["observable_behaviors"][0]["type"], "POSITION_PRESET_REFERENCE")
        self.assertEqual(result["cue_semantics"][1]["observable_behaviors"][0]["preset_reference"], "2.13")
        self.assertEqual(result["cue_semantics"][2]["observable_behaviors"], [])

    def test_collection_finds_cross_sequence_content_without_claiming_same_show(self):
        first = sequence_export_discovery(SEQUENCE_XML, 42)
        second = sequence_export_discovery(SEQUENCE_XML, 43)
        collection = translate_sequence_collection([first, second])
        self.assertEqual(len(collection["cross_sequence_motifs"]), 3)
        self.assertEqual(collection["source_relation"], "SAME_SHOW_NOT_VERIFIED_BY_SEQUENCE_XML")
        self.assertEqual(collection["cross_sequence_motifs"][0]["occurrences"][0]["sequence_no"], 42)
        second["status"] = "PARTIAL"
        self.assertEqual(translate_sequence_collection([first, second])["cross_sequence_motifs"], [])
        with self.assertRaisesRegex(ReverseArtisticTranslationError, "DUPLICATE_NUMBER"):
            translate_sequence_collection([first, first])

    def test_partial_discovery_stays_partial(self):
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        discovery["status"] = "PARTIAL"
        result = translate_sequence_evidence(discovery)
        self.assertEqual(result["translation_status"], "PARTIAL_EVIDENCE")
        self.assertEqual(result["technical_structure"]["source_integrity"], "PARTIAL")
        self.assertEqual(result["machine_readable_design_reference"]["source_evidence"]["integrity"], "PARTIAL")
        self.assertEqual(result["recurring_artistic_motifs"], [])

    def test_rejects_non_read_only_or_unverified_evidence(self):
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        discovery["read_only"] = False
        with self.assertRaisesRegex(ReverseArtisticTranslationError, "READ_ONLY"):
            translate_sequence_evidence(discovery)
        discovery = sequence_export_discovery(SEQUENCE_XML, 42)
        discovery["status"] = "UNSUPPORTED"
        with self.assertRaisesRegex(ReverseArtisticTranslationError, "NOT_TRANSLATABLE"):
            translate_sequence_evidence(discovery)

    def test_does_not_elevate_numeric_values_to_artistic_claims(self):
        result = translate_sequence_xml(SEQUENCE_XML, 42)
        first = result["cue_semantics"][0]
        self.assertNotIn("artistic_intent", first)
        self.assertEqual(first["timing_values"], {"fade": ["1.5"], "delay": []})
        self.assertNotIn("PATCH_ADDRESS_FIXTURE_IDENTITY_OR_TYPE", result["technical_structure"])


if __name__ == "__main__":
    unittest.main()
