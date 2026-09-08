import json
import unittest
from pathlib import Path

from zen_ma2_agent.geometry import GEOMETRY_ALGORITHM_VERSION, GeometryNormalizer
from zen_ma2_agent.state.providers.fixture_geometry import FixtureGeometryProvider


FIXTURE = Path(__file__).parent / "fixtures" / "ma2_fixture_geometry" / "signed_axis_numeric_readback.json"


def record(fixture_id, x, y=0, z=5, fixture_type="MH", subfixture_id=1):
    return {"fixture_id": fixture_id, "subfixture_id": subfixture_id, "fixture_type": fixture_type, "position": {"x": x, "y": y, "z": z}}


class GeometryNormalizerTests(unittest.TestCase):
    def setUp(self):
        self.normalizer = GeometryNormalizer(tolerance=0.05)

    def test_sanitized_real_machine_signed_axis_evidence_has_exact_numeric_readback(self):
        evidence = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["semantic_labels"], "UNVERIFIED_NO_STAGE_VIEW_EVIDENCE")
        self.assertTrue(all(item["match"] for item in evidence["cases"].values()))
        self.assertEqual(evidence["cases"]["x_positive"]["actual"]["x"], 4.0)
        self.assertEqual(evidence["cases"]["z_negative"]["actual"]["z"], 2.0)

    def test_normalizes_per_relevant_set_and_preserves_zero_range_axis(self):
        analysis = self.normalizer.analyze([record(101, -8), record(102, 0), record(103, 8)])
        values = {item["fixture_id"]: item for item in analysis["records"]}
        self.assertEqual(values[101]["normalized"], {"horizontal": -1.0, "depth": 0.0, "height": 0.0})
        self.assertEqual(values[103]["normalized"]["horizontal"], 1.0)
        self.assertEqual(analysis["axis_ranges"]["y"]["span"], 0.0)

    def test_deterministic_numeric_order_is_not_named_stage_left_without_axis_evidence(self):
        analysis = self.normalizer.analyze([record(104, 8), record(101, -8), record(102, -4), record(103, 4)])
        values = {item["fixture_id"]: item for item in analysis["records"]}
        self.assertEqual(values[101]["relationships"]["horizontal_index"], 0)
        self.assertEqual(values[104]["relationships"]["horizontal_index"], 3)
        self.assertEqual(values[101]["relationships"]["x_side"], "X_NEGATIVE_SIDE")

    def test_even_count_center_is_between_fixtures(self):
        analysis = self.normalizer.analyze([record(101, -2), record(102, 2)])
        center = analysis["nearest_to_x_center"]
        self.assertTrue(center["between_fixtures"])
        self.assertEqual({entry["fixture_id"] for entry in center["fixture_subfixtures"]}, {101, 102})

    def test_odd_count_center_selects_center_fixture(self):
        analysis = self.normalizer.analyze([record(101, -2), record(102, 0), record(103, 2)])
        center = analysis["nearest_to_x_center"]
        self.assertFalse(center["between_fixtures"])
        self.assertEqual(center["fixture_subfixtures"], [{"fixture_id": 102, "subfixture_id": 1}])

    def test_mirror_pair_respects_y_z_and_fixture_type_confidence(self):
        analysis = self.normalizer.analyze([record(101, -8, 2, 6, "MH"), record(108, 8, 2, 6, "MH"), record(201, -4, 2, 6, "A"), record(202, 4, 2, 6, "B")])
        values = {item["fixture_id"]: item for item in analysis["records"]}
        self.assertEqual(values[101]["relationships"]["symmetry_pair"]["fixture_id"], 108)
        self.assertTrue(values[101]["relationships"]["symmetry_pair"]["fixture_type_compatible"])
        self.assertEqual(values[201]["relationships"]["symmetry_pair"]["fixture_id"], 202)
        self.assertFalse(values[201]["relationships"]["symmetry_pair"]["fixture_type_compatible"])

    def test_subfixture_identity_is_part_of_derived_record(self):
        analysis = self.normalizer.analyze([record(701, -1, subfixture_id=1), record(701, 1, subfixture_id=2)])
        self.assertEqual([(item["fixture_id"], item["subfixture_id"]) for item in analysis["records"]], [(701, 1), (701, 2)])

    def test_row_and_layer_clustering_obeys_configurable_tolerance(self):
        analysis = self.normalizer.analyze([record(101, -1, 2, 6), record(102, 1, 2.03, 6.01), record(201, 0, -2, 3)])
        values = {item["fixture_id"]: item for item in analysis["records"]}
        self.assertEqual(values[101]["relationships"]["row_id"], values[102]["relationships"]["row_id"])
        self.assertNotEqual(values[101]["relationships"]["row_id"], values[201]["relationships"]["row_id"])
        self.assertEqual(analysis["algorithm_version"], GEOMETRY_ALGORITHM_VERSION)

    def test_verified_raw_patch_parser_retains_authoritative_text(self):
        self.assertEqual(FixtureGeometryProvider.parse_patch("10.001"), {"raw_patch": "10.001", "universe": 10, "address": 1, "parse_status": "VERIFIED_LIST_FORMAT"})
        self.assertEqual(FixtureGeometryProvider.parse_patch("(-)")["parse_status"], "UNPARSED")


if __name__ == "__main__":
    unittest.main()
