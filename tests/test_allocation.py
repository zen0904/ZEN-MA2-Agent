import unittest

from zen_ma2_agent.allocation import (
    AllocationError,
    first_free_executor,
    first_free_from_front,
)


class AllocationTests(unittest.TestCase):
    def test_first_free_from_front_skips_occupied_protected_and_foreign(self):
        self.assertEqual(
            first_free_from_front({1, 3}, protected={2}, start=1),
            4,
        )

    def test_first_free_from_front_fails_only_when_the_whole_range_is_unavailable(self):
        with self.assertRaises(AllocationError):
            first_free_from_front({1, 2}, protected={3}, start=1, end=3)

    def test_executor_allocation_advances_past_any_occupied_slot_on_the_page(self):
        inventory = 'Executor 2.001 "foreign"\nExecutor 2.002 "ZEN"\nExecutor 3.001 "other page"\n'
        self.assertEqual(first_free_executor(inventory, page=2), "2.003")


if __name__ == "__main__":
    unittest.main()
