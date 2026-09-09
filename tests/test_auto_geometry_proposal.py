import unittest

from zen_ma2_agent.geometry import AutoGeometryProposer, WRITE_PLAN_SCHEMA, state_change_guard, validate_write_plan


def fixture(fixture_id, fixture_type="MH", subfixtures=(1,)):
    return {
        "fixture_id": fixture_id,
        "name": f"Fixture {fixture_id}",
        "fixture_type": fixture_type,
        "stage_geometry": {
            "patch": f"10.{fixture_id:03d}",
            "subfixtures": [{"subfixture_id": value} for value in subfixtures],
        },
    }


def profile():
    groups = []
    fixtures = []
    for group_id in range(1, 8):
        ids = [group_id * 100 + index for index in range(1, 9)]
        groups.append({"group_id": group_id, "name": f"G{group_id}", "fixture_ids_in_selection_order": ids})
        fixtures.extend(fixture(value, "TYPE_A" if group_id % 2 else "TYPE_B") for value in ids)
    fixtures.append(fixture(9999, "TYPE_A", (1, 2)))
    return {"show_identity": {"value": "show-a"}, "groups": groups, "fixtures": fixtures}


class AutoGeometryProposalTests(unittest.TestCase):
    def test_three_candidates_preserve_order_and_even_center_gap(self):
        proposal = AutoGeometryProposer().build(profile(), {"geometry": {"status": "GEOMETRY_UNINITIALIZED"}})
        self.assertEqual([item["id"] for item in proposal["candidates"]], ["A_LAYERED_ROWS", "B_FIXTURE_FAMILY_STAGING", "C_COMPACT_SYMMETRIC"])
        group = proposal["candidates"][0]["groups"][0]
        self.assertEqual(group["fixture_ids_in_selection_order"], list(range(101, 109)))
        self.assertEqual(group["x_positions"], [-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5])
        self.assertEqual([(item["fixture_a"], item["fixture_b"]) for item in group["mirror_pairs"]], [(101, 108), (102, 107), (103, 106), (104, 105)])
        self.assertEqual(group["inner"], [104, 105])
        self.assertEqual(group["outer"], [108, 101])
        self.assertTrue(group["center"]["between_fixtures"])

    def test_ungrouped_fixture_is_excluded_and_subfixtures_inherit_root_target(self):
        proposal = AutoGeometryProposer().build(profile(), {"geometry": {"status": "GEOMETRY_UNINITIALIZED"}})
        self.assertEqual([item["fixture_id"] for item in proposal["ungrouped_fixtures"]], [9999])
        self.assertNotIn(9999, {item["fixture_ref"]["fixture_id"] for item in proposal["typed_write_plan"]["operations"]})
        operation = next(item for item in proposal["typed_write_plan"]["operations"] if item["fixture_ref"]["fixture_id"] == 101)
        self.assertEqual(operation["fixture_ref"]["subfixture_ids"], [1])
        multi = dict(profile())
        multi["fixtures"] = list(multi["fixtures"])
        multi["fixtures"][0] = fixture(101, "TYPE_A", (1, 2))
        proposal_multi = AutoGeometryProposer().build(multi, {"geometry": {"status": "GEOMETRY_UNINITIALIZED"}})
        operation_multi = next(item for item in proposal_multi["typed_write_plan"]["operations"] if item["fixture_ref"]["fixture_id"] == 101)
        self.assertEqual(operation_multi["fixture_ref"]["subfixture_ids"], [1, 2])

    def test_overlap_is_reported_and_conflicting_fixture_is_not_written(self):
        value = profile()
        value["groups"] = list(value["groups"])
        value["groups"][1] = dict(value["groups"][1])
        value["groups"][1]["fixture_ids_in_selection_order"] = [201, 202, 203, 204, 205, 206, 207, 101]
        proposal = AutoGeometryProposer().build(value, {"geometry": {"status": "GEOMETRY_UNINITIALIZED"}})
        self.assertEqual(proposal["group_membership_overlap"], [{"fixture_id": 101, "groups": [1, 2]}])
        self.assertNotIn(101, {item["fixture_ref"]["fixture_id"] for item in proposal["typed_write_plan"]["operations"]})

    def test_typed_write_plan_and_state_change_guard(self):
        proposal = AutoGeometryProposer().build(profile(), {"geometry": {"status": "GEOMETRY_UNINITIALIZED"}})
        plan = proposal["typed_write_plan"]
        self.assertEqual(plan["schema"], WRITE_PLAN_SCHEMA)
        validate_write_plan(plan)
        invalid = dict(plan, commands=["Move3D Fixture 101"])
        with self.assertRaises(ValueError):
            validate_write_plan(invalid)
        self.assertEqual(state_change_guard(current_status="GEOMETRY_READY", baseline_identity="show-a", current_identity="show-a")["status"], "STATE_CHANGED_SINCE_PREVIEW")
        self.assertEqual(state_change_guard(current_status="GEOMETRY_UNINITIALIZED", baseline_identity="show-a", current_identity="show-b")["status"], "STATE_CHANGED_SINCE_PREVIEW")
        self.assertFalse(state_change_guard(current_status="GEOMETRY_UNINITIALIZED", baseline_identity="show-a", current_identity="show-a")["allowed"])


if __name__ == "__main__":
    unittest.main()
