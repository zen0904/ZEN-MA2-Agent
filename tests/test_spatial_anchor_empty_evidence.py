from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from zen_ma2_agent.spatial_anchor_empty_evidence import (
    SpatialAnchorEmptyEvidenceError,
    SpatialAnchorEmptyEvidenceStore,
    empty_evidence_matches_profile,
    verified_empty_refs,
)


def profile():
    return {
        "show_identity": {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "a" * 64, "confidence": "PARTIAL"},
        "presets": [
            {"preset_type": "POSITION", "reference": "2.1", "name": "HOME"},
            {"preset_type": "POSITION", "reference": "2.2", "name": "CENTER"},
        ],
    }


class SpatialAnchorEmptyEvidenceTests(unittest.TestCase):
    def record(self, root: Path):
        return SpatialAnchorEmptyEvidenceStore(root).record_verified(
            profile(),
            [
                {"reference": "2.1", "label": "HOME", "native_content_status": "EMPTY", "selected_fixture_refs": []},
                {"reference": "2.2", "label": "CENTER", "native_content_status": "EMPTY", "selected_fixture_refs": []},
            ],
            scratch_group=9901,
            verified_at="2026-09-29T07:00:00+00:00",
            nonempty_control={"preset_ref": "2.900", "selected_fixture_refs": ["101", "102"]},
            empty_control={"preset_ref": "2.901", "selected_fixture_refs": []},
        )

    def test_records_and_loads_show_bound_empty_slots(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = self.record(root)
            self.assertTrue(empty_evidence_matches_profile(profile(), evidence))
            self.assertEqual(verified_empty_refs(profile(), evidence), {"2.1", "2.2"})
            self.assertEqual(SpatialAnchorEmptyEvidenceStore(root).load_verified(profile())["scratch_group"], 9901)

    def test_show_or_label_drift_invalidates_evidence(self):
        with TemporaryDirectory() as tmp:
            evidence = self.record(Path(tmp))
            changed = profile()
            changed["show_identity"] = {"kind": "SCANNED_SHOW_PROFILE_FINGERPRINT", "value": "b" * 64, "confidence": "PARTIAL"}
            self.assertFalse(empty_evidence_matches_profile(changed, evidence))
            changed = profile()
            changed["presets"][1]["name"] = "CENTER_CHANGED"
            self.assertFalse(empty_evidence_matches_profile(changed, evidence))

    def test_nonempty_slot_or_bad_ab_control_is_rejected(self):
        with TemporaryDirectory() as tmp:
            store = SpatialAnchorEmptyEvidenceStore(Path(tmp))
            with self.assertRaisesRegex(SpatialAnchorEmptyEvidenceError, "SLOT_NOT_EMPTY"):
                store.record_verified(
                    profile(), [{"reference": "2.1", "label": "HOME", "native_content_status": "NONEMPTY", "selected_fixture_refs": ["101"]}],
                    scratch_group=9901, verified_at="x",
                    nonempty_control={"selected_fixture_refs": ["101"]}, empty_control={"selected_fixture_refs": []},
                )
            with self.assertRaisesRegex(SpatialAnchorEmptyEvidenceError, "AB_CONTROL_INVALID"):
                store.record_verified(
                    profile(), [{"reference": "2.1", "label": "HOME", "native_content_status": "EMPTY", "selected_fixture_refs": []}],
                    scratch_group=9901, verified_at="x",
                    nonempty_control={"selected_fixture_refs": []}, empty_control={"selected_fixture_refs": []},
                )


if __name__ == "__main__":
    unittest.main()
