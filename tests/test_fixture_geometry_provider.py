import unittest
from pathlib import Path

from zen_ma2_agent.scanner import ShowScanner
from zen_ma2_agent.state.providers import FixtureGeometryProvider
from zen_ma2_agent.state.store import StateStore


SAMPLE = (Path(__file__).parent / "fixtures" / "ma2_fixture_list" / "ma2_3960_real_subfixtures.txt").read_text(encoding="utf-8")


class FixtureGeometryProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = FixtureGeometryProvider()

    def test_real_inventory_exposes_verified_single_and_multi_instance_seeds(self):
        seeds = {item.fixture_id: item for item in self.provider.parse_inventory(SAMPLE)}
        self.assertEqual((seeds[101].name, seeds[101].fixture_type, seeds[101].patch, seeds[101].instance_count), ("Hybrid 1", "2 ZEN BAW 20R Mode 2", "10.001", 1))
        self.assertEqual((seeds[701].patch, seeds[701].instance_count), ("21.001", 2))
        self.assertEqual(seeds[9999].patch, "(-)")

    def test_changed_xyz_rotation_and_sparse_fixture_identity_are_preserved(self):
        record = self.provider.parse_subfixture(SAMPLE, fixture_id=101, instance=1)
        self.assertEqual(record["fixture_ref"], "101.1")
        self.assertEqual(record["position"], {"x": -2.0, "y": 1.0, "z": 4.0})
        self.assertEqual(record["rotation"], {"x": 0.0, "y": 0.0, "z": 90.0})
        self.assertEqual((record["pan_dmx_invert"], record["tilt_dmx_invert"], record["pan_offset"], record["tilt_offset"]), ("Off", "Off", 0.0, 0.0))
        self.assertIsNone(self.provider.parse_subfixture("WARNING, NO OBJECTS FOUND FOR LIST", fixture_id=9999, instance=1))

    def test_multiple_subfixtures_never_collapse_to_the_parent_fixture(self):
        first = self.provider.parse_subfixture(SAMPLE, fixture_id=701, instance=1)
        second = self.provider.parse_subfixture(SAMPLE, fixture_id=701, instance=2)
        self.assertEqual((first["fixture_id"], first["subfixture_id"], first["fixture_ref"]), (701, 1, "701.1"))
        self.assertEqual((second["fixture_id"], second["subfixture_id"], second["fixture_ref"]), (701, 2, "701.2"))
        self.assertNotEqual(first["position"], second["position"])

    def test_show_profile_uses_geometry_only_when_fresh_and_explicit(self):
        state = StateStore()
        state.put("fixtures", [{"number": 101, "name": "Hybrid 1", "fixture_type": "2 ZEN BAW 20R Mode 2"}], source="ma2_telnet_list")
        record = self.provider.parse_subfixture(SAMPLE, fixture_id=101, instance=1)
        state.put("fixture_geometry", [record], source=self.provider.source, capability={"stage_geometry": "supported"})
        profile = ShowScanner().scan(state)
        geometry = profile["fixtures"][0]["stage_geometry"]
        self.assertEqual((geometry["x"], geometry["y"], geometry["z"], geometry["rot_z"]), (-2.0, 1.0, 4.0, 90.0))
        state.mark_stale("fixture_geometry")
        self.assertEqual(ShowScanner().scan(state)["fixtures"][0]["stage_geometry"]["status"], "STALE")


if __name__ == "__main__":
    unittest.main()
