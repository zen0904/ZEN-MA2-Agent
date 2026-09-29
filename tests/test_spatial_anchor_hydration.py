import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from zen_ma2_agent.spatial_anchor_hydration import (
    GRAMMAR_ID,
    SpatialAnchorHydrationCapability,
    SpatialAnchorHydrationError,
    spatial_anchor_hydration_capability_is_verified,
)


class SpatialAnchorHydrationCapabilityTests(unittest.TestCase):
    def record(self, root: Path):
        return SpatialAnchorHydrationCapability(root).record_content_verified(
            preset_ref="2.900",
            preset_label="ZEN_SPATIAL_HYDRATE_PROBE",
            group_id=1,
            group_name="HYBRID",
            group_refs=["101", "102", "103", "104", "105", "106", "108", "107"],
            matched_channel_refs=[f"{n}.1" for n in range(101, 109)],
            sequence=9900,
            cue=1,
            sequence_export_sha256="a" * 64,
        )

    def test_records_and_loads_only_content_verified_hydration_grammar(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            value = self.record(root)
            self.assertEqual(value["grammar"], GRAMMAR_ID)
            self.assertTrue(spatial_anchor_hydration_capability_is_verified(value))
            loaded = SpatialAnchorHydrationCapability(root).load_verified()
            self.assertEqual(loaded["verification"]["cue_content_readback"], "VERIFIED")
            self.assertTrue(loaded["safety_boundary"]["slot_emptiness_is_per_target_evidence"])

    def test_metadata_only_or_bad_native_hash_never_becomes_verified(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            value = self.record(root)
            value["verification"]["cue_content_readback"] = "UNVERIFIED"
            self.assertFalse(spatial_anchor_hydration_capability_is_verified(value))
            path = SpatialAnchorHydrationCapability(root).path
            path.write_text(json.dumps(value), encoding="utf-8")
            self.assertIsNone(SpatialAnchorHydrationCapability(root).load_verified())
            with self.assertRaisesRegex(SpatialAnchorHydrationError, "SHA_INVALID"):
                SpatialAnchorHydrationCapability(root).record_content_verified(
                    preset_ref="2.900", preset_label="P", group_id=1, group_name="G",
                    group_refs=["101"], matched_channel_refs=["101.1"],
                    sequence=1, cue=1, sequence_export_sha256="bad",
                )

    def test_capability_does_not_claim_target_slot_emptiness(self):
        with TemporaryDirectory() as tmp:
            value = self.record(Path(tmp))
            self.assertNotIn("target_slot_empty", value["verification"])
            self.assertTrue(value["safety_boundary"]["capability_does_not_authorize_nonempty_preset_overwrite"])


if __name__ == "__main__":
    unittest.main()