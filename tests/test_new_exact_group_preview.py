import unittest
from datetime import datetime, timezone

from zen_ma2_agent.new_exact_group_preview import NewExactGroupPreviewError, preview_new_exact_group


class NewExactGroupPreviewTests(unittest.TestCase):
    def setUp(self):
        meta = {"status": "SUPPORTED", "stale": False, "updated_at": datetime.now(timezone.utc).isoformat()}
        self.profile = {
            "resources": {name: dict(meta) for name in ("groups", "fixtures", "fixture_geometry")},
            "groups": [{"group_id": 1}, {"group_id": 7}],
            "fixtures": [
                {"fixture_id": root, "stage_geometry": {"subfixtures": [{"subfixture_id": 1}, {"subfixture_id": 2}]}}
                for root in range(701, 709)
            ] + [{"fixture_id": 9999, "stage_geometry": {"subfixtures": [{"subfixture_id": 1}]}}],
        }
        self.refs = [f"{root}.2" for root in range(701, 709)]

    def test_preview_allocates_first_free_exact_group_without_execution(self):
        preview = preview_new_exact_group(self.profile, label="ZEN_TEST_ATOMIC_DIM_COLOR_EXACT", fixture_refs=self.refs)
        self.assertEqual(preview["group_id"], 2)
        self.assertEqual(preview["fixture_refs_in_selection_order"], self.refs)
        self.assertEqual(preview["commands"][1:9], [f"Fixture {ref}" for ref in self.refs])
        self.assertNotIn("/overwrite", " ".join(preview["commands"]))
        self.assertFalse(preview["executable"])
        self.assertTrue(preview["approval_required"])
        self.assertEqual(preview["future_readback_requirement"], "EXACT_RAW_EXPORT_GROUP_MEMBER_AND_ORDER_COMPARE")

    def test_preview_requires_fresh_group_inventory(self):
        self.profile["resources"]["groups"]["stale"] = True
        with self.assertRaisesRegex(NewExactGroupPreviewError, "Fresh read-only groups"):
            preview_new_exact_group(self.profile, label="ZEN_TEST_ATOMIC_DIM_COLOR_EXACT", fixture_refs=self.refs)
        self.profile["resources"]["groups"]["stale"] = False
        self.profile["resources"]["groups"]["updated_at"] = "2026-01-01T00:00:00Z"
        with self.assertRaisesRegex(NewExactGroupPreviewError, "Fresh read-only groups"):
            preview_new_exact_group(self.profile, label="ZEN_TEST_ATOMIC_DIM_COLOR_EXACT", fixture_refs=self.refs)

    def test_preview_rejects_unknown_parent_duplicate_and_fixture_9999(self):
        for refs in (["701"], ["701.3"], ["701.2", "701.2"], ["9999.1"]):
            with self.subTest(refs=refs), self.assertRaises(NewExactGroupPreviewError):
                preview_new_exact_group(self.profile, label="ZEN_TEST_ATOMIC_DIM_COLOR_EXACT", fixture_refs=refs)

    def test_preview_rejects_injected_label_and_malformed_inventory(self):
        with self.assertRaises(NewExactGroupPreviewError):
            preview_new_exact_group(self.profile, label='ZEN_TEST"; Delete Group 7', fixture_refs=self.refs)
        self.profile["groups"].append({"group_id": 7})
        with self.assertRaisesRegex(NewExactGroupPreviewError, "Duplicate Group IDs"):
            preview_new_exact_group(self.profile, label="ZEN_TEST_ATOMIC_DIM_COLOR_EXACT", fixture_refs=self.refs)


if __name__ == "__main__":
    unittest.main()
