import unittest

from zen_ma2_agent.group_order_builder import GroupOrderBuildError, GroupOrderSpec


class GroupOrderBuilderTests(unittest.TestCase):
    def test_commands_are_deterministic_and_preserve_membership(self):
        spec = GroupOrderSpec.create(3, "BEAM", [201, 202, 203], [202, 201, 203])
        self.assertEqual(spec.commands(), (
            "ClearAll", "Fixture 202", "Fixture 201", "Fixture 203",
            "Store Group 3 /overwrite /nc", "ClearAll",
        ))
        self.assertFalse(spec.membership_changed)
        spec.verify([202, 201, 203])

    def test_subfixtures_and_order_mismatch_fail_closed(self):
        spec = GroupOrderSpec.create(7, "STROBE", ["701.1", "701.2"], ["701.2", "701.1"])
        self.assertIn("Fixture 701.2", spec.commands())
        with self.assertRaisesRegex(GroupOrderBuildError, "mismatch"):
            spec.verify(["701.1", "701.2"])

    def test_membership_change_and_protected_fixture_are_rejected(self):
        with self.assertRaisesRegex(GroupOrderBuildError, "membership"):
            GroupOrderSpec.create(1, "HYBRID", [101, 102], [101])
        with self.assertRaisesRegex(GroupOrderBuildError, "protected"):
            GroupOrderSpec.create(1, "HYBRID", [101, 9999], [101, 9999])


if __name__ == "__main__":
    unittest.main()
