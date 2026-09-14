import json
import unittest
from pathlib import Path

from zen_ma2_agent.visual_reference import validate_visual_reference


class VisualReferenceTests(unittest.TestCase):
    def test_metadata_only_reference_validates(self):
        payload = json.loads((Path(__file__).resolve().parents[1] / "data/visual_reference_foundation_001.json").read_text(encoding="utf-8"))
        value = validate_visual_reference(payload["references"][0])
        self.assertEqual(value["reference_kind"], "POSITIVE")
        self.assertEqual(value["review_status"], "HUMAN_CONFIRMED")
        self.assertEqual(value["media_origin"], "USER_PROVIDED_MEDIA")
        self.assertTrue(value["media_ref"].endswith(".mp4"))
        self.assertIsNone(value["source_url"])
        self.assertEqual(value["media_policy"], "METADATA_ONLY_NO_BINARY_MEDIA")
        self.assertIn("negative_space", value["transferable_concepts"])
        self.assertIn("intensity_headroom", value["transferable_concepts"])
        self.assertIn("Exact colors are not universal", value["non_transferable_specifics"])

    def test_binary_media_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_visual_reference({"schema": "zen.visual_reference.v0.1", "reference_id": "x", "title": "x", "source_url": "https://example.com", "publisher": "x", "retrieved_at": "2026-09-14", "reference_kind": "POSITIVE", "observations": ["x"], "transferable_concepts": ["x"], "non_transferable_specifics": [], "related_topics": [], "confidence": "LOW", "review_status": "NEEDS_REVIEW", "media_policy": "BINARY"})

    def test_web_reference_remains_supported(self):
        value = validate_visual_reference({"schema": "zen.visual_reference.v0.1", "reference_id": "web", "title": "Web", "source_url": "https://example.com/ref", "publisher": "Publisher", "retrieved_at": "2026-09-14", "reference_kind": "MIXED", "observations": ["bounded"], "transferable_concepts": ["contrast"], "non_transferable_specifics": [], "related_topics": [], "confidence": "LOW", "review_status": "NEEDS_REVIEW"})
        self.assertEqual(value["media_origin"], "EXTERNAL_WEB")

    def test_local_media_without_ref_or_url_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_visual_reference({"schema": "zen.visual_reference.v0.1", "reference_id": "local", "title": "Local", "source_url": None, "publisher": "x", "retrieved_at": "2026-09-14", "reference_kind": "POSITIVE", "observations": ["x"], "transferable_concepts": ["x"], "non_transferable_specifics": [], "related_topics": [], "confidence": "LOW", "review_status": "NEEDS_REVIEW"})


if __name__ == "__main__":
    unittest.main()
