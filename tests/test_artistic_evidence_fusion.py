import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.fuse_artistic_evidence import main as fuse_file_main
from zen_ma2_agent.artistic_evidence_fusion import (
    ArtisticEvidenceFusionError,
    CONTEXT_EVIDENCE_SCHEMA,
    HYPOTHESIS_INPUT_SCHEMA,
    fuse_artistic_evidence,
)
from zen_ma2_agent.reverse_artistic_translator import translate_sequence_xml


SEQUENCE_XML = b'''<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA">
  <Sequ>
    <Cue index="1"><Number number="1" sub_number="0"/><CuePart index="0" name="HOOK_A"/><CueDatas>
      <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="Dimmer"/><Value>50</Value></CueData>
    </CueDatas></Cue>
    <Cue index="2"><Number number="2" sub_number="0"/><CuePart index="0" name="VERSE"/><CueDatas>
      <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="Dimmer"/><Value>20</Value></CueData>
    </CueDatas></Cue>
    <Cue index="3"><Number number="3" sub_number="0"/><CuePart index="0" name="HOOK_B"/><CueDatas>
      <CueData value_multipart_index="0" effect_multipart_index="0"><Channel fixture_id="101" attribute_name="Dimmer"/><Value>50</Value></CueData>
    </CueDatas></Cue>
  </Sequ>
</MA>'''


def context(evidence_id, source_type, observations, status="VERIFIED"):
    return {
        "schema": CONTEXT_EVIDENCE_SCHEMA,
        "read_only": True,
        "evidence_id": evidence_id,
        "source_type": source_type,
        "source_ref": f"offline/{evidence_id}.json",
        "status": status,
        "observations": observations,
    }


class ArtisticEvidenceFusionTests(unittest.TestCase):
    def setUp(self):
        self.translation = translate_sequence_xml(SEQUENCE_XML, 901)
        self.song = context("song-001", "SONG_STRUCTURE", [{
            "observation_id": "hook-sections",
            "kind": "SECTION_BOUNDARY",
            "claim": "Supplied song analysis labels Cue anchors 1 and 3 as HOOK.",
            "cue_refs": ["1", "3"],
            "tags": ["HOOK"],
            "confidence": "HIGH",
        }])
        self.timing = context("time-001", "TIMING_TIMECODE", [{
            "observation_id": "cue-one-anchor",
            "kind": "TIMECODE_ANCHOR",
            "claim": "Supplied timecode maps Cue 1 to 00:14.000.",
            "cue_refs": ["1"],
            "tags": [],
            "temporal_evidence": {"timecode": "00:14.000", "start_seconds": 14.0},
            "confidence": "HIGH",
        }])
        self.visual = context("visual-001", "STAGE_VIEW_VISUAL", [{
            "observation_id": "frame-001",
            "kind": "FRAME_OBSERVATION",
            "claim": "Supplied Stage View frame records a visible state at its documented timestamp.",
            "cue_refs": ["2"],
            "tags": ["FRAME"],
            "confidence": "MEDIUM",
        }])

    def test_separates_fact_inference_and_hypothesis_with_traceability(self):
        hypothesis = {
            "schema": HYPOTHESIS_INPUT_SCHEMA,
            "read_only": True,
            "hypotheses": [{
                "hypothesis_id": "possible-hook-reuse",
                "statement": "The repeated stored content may support a recurring hook treatment.",
                "evidence_refs": [
                    "sequence:901:motif:CONTENT_" + self.translation["recurring_artistic_motifs"][0]["motif_id"].split("CONTENT_", 1)[1],
                    "context:song-001:observation:hook-sections",
                ],
            }],
        }
        result = fuse_artistic_evidence(self.translation, [self.visual, self.timing, self.song], hypothesis)
        self.assertTrue(result["read_only"])
        self.assertEqual(result["source_sequence"]["sequence_no"], 901)
        self.assertEqual(set(result["layers"]), {"FACT", "INFERENCE", "HYPOTHESIS"})
        self.assertTrue(any(item["classification"] == "EXACT_RECURRING_STORED_CUE_CONTENT" for item in result["layers"]["FACT"]))
        cue_one = next(item for item in result["layers"]["FACT"] if item["finding_id"] == "FACT_SEQUENCE_901_CUE_1")
        self.assertEqual(cue_one["observed"]["cue_parts"][0]["name"], "HOOK_A")
        timing_fact = next(item for item in result["layers"]["FACT"] if item["classification"] == "SUPPLIED_TIMING_TIMECODE_OBSERVATION")
        self.assertEqual(timing_fact["temporal_evidence"]["timecode"], "00:14.000")
        tag_inference = next(item for item in result["layers"]["INFERENCE"] if item["classification"] == "EXACT_CONTENT_RECURRENCE_WITH_SHARED_CONTEXT_TAG")
        self.assertEqual(tag_inference["confidence"], "MEDIUM")
        self.assertIn("context:song-001:observation:hook-sections", tag_inference["evidence_refs"])
        self.assertTrue(all(item["evidence_refs"] and item["confidence"] in {"LOW", "MEDIUM", "HIGH"} for item in result["layers"]["INFERENCE"]))
        output_hypothesis = result["layers"]["HYPOTHESIS"][0]
        self.assertEqual(output_hypothesis["confidence"], "LOW")
        self.assertIn("NOT_A_FACT", output_hypothesis["limits"])
        self.assertIn("NATIVE_XML_TO_VISUAL_OUTPUT_FACT", result["prohibited_promotions"])

    def test_partial_context_downgrades_correlation_confidence(self):
        result = fuse_artistic_evidence(self.translation, [context("audio-001", "AUDIO_ANALYSIS", [{
            "observation_id": "accent",
            "kind": "ACCENT",
            "claim": "Supplied audio analysis detects an accent at the Cue 1 anchor.",
            "cue_refs": ["1"],
            "tags": ["ACCENT"],
            "confidence": "HIGH",
        }], status="PARTIAL")])
        inference = result["layers"]["INFERENCE"][0]
        self.assertEqual(inference["confidence"], "LOW")
        supplied_fact = next(item for item in result["layers"]["FACT"] if item["classification"] == "SUPPLIED_AUDIO_ANALYSIS_OBSERVATION")
        self.assertEqual(supplied_fact["confidence"], "LOW")

    def test_unlinked_context_is_not_correlated_to_a_cue(self):
        unlinked = context("audio-002", "AUDIO_ANALYSIS", [{
            "observation_id": "unknown-anchor",
            "kind": "ACCENT",
            "claim": "Supplied audio analysis has an unmapped accent.",
            "cue_refs": ["99"],
            "tags": ["ACCENT"],
            "confidence": "HIGH",
        }])
        result = fuse_artistic_evidence(self.translation, [unlinked])
        self.assertEqual(result["layers"]["INFERENCE"], [])
        self.assertTrue(any(item["classification"] == "SUPPLIED_AUDIO_ANALYSIS_OBSERVATION" for item in result["layers"]["FACT"]))

    def test_rejects_writable_or_untraceable_inputs(self):
        writable = dict(self.song)
        writable["read_only"] = False
        with self.assertRaisesRegex(ArtisticEvidenceFusionError, "READ_ONLY"):
            fuse_artistic_evidence(self.translation, [writable])
        invalid_hypothesis = {
            "schema": HYPOTHESIS_INPUT_SCHEMA,
            "read_only": True,
            "hypotheses": [{
                "hypothesis_id": "bad-ref",
                "statement": "Untraceable.",
                "evidence_refs": ["not-a-real-reference"],
            }],
        }
        with self.assertRaisesRegex(ArtisticEvidenceFusionError, "EVIDENCE_REF"):
            fuse_artistic_evidence(self.translation, [self.song], invalid_hypothesis)

    def test_cli_writes_new_utf8_json_without_overwriting(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            reference = root / "reference.json"
            source = root / "song.json"
            output = root / "fusion.json"
            reference.write_text(json.dumps(self.translation), encoding="utf-8")
            source.write_text(json.dumps(self.song), encoding="utf-8")
            self.assertEqual(fuse_file_main([str(reference), "--context", str(source), "--output", str(output)]), 0)
            raw = output.read_bytes()
            self.assertTrue(raw.startswith(b"{"))
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertEqual(json.loads(raw.decode("utf-8"))["schema"], "zen.artistic_evidence_fusion.v0.1")
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                fuse_file_main([str(reference), "--context", str(source), "--output", str(output)])


if __name__ == "__main__":
    unittest.main()
