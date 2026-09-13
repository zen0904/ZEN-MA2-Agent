import unittest
from unittest.mock import patch

from zen_ma2_agent.builder.draft import ShowPlanBuilder
import zen_ma2_agent.protected_objects as protected_objects
from zen_ma2_agent.protected_objects import (
    PROTECTED_FIXTURE_IDS,
    PROTECTED_SEQUENCES,
    ProtectedObjectError,
    assert_fixture_allowed,
    assert_sequence_allowed,
)


class ProtectedObjectsTests(unittest.TestCase):
    def test_no_sequence_is_protected_by_default(self):
        # The active Show is disposable test data, so no Sequence is
        # protected right now -- only Fixture 9999 is held aside.
        self.assertEqual(PROTECTED_SEQUENCES, frozenset())

    def test_fixture_9999_is_protected(self):
        self.assertIn(9999, PROTECTED_FIXTURE_IDS)

    def test_assert_sequence_allowed_accepts_any_number_while_list_is_empty(self):
        for sequence in (201, 202, 204, 205, 901):
            assert_sequence_allowed(sequence)  # must not raise

    def test_assert_fixture_allowed_rejects_9999(self):
        with self.assertRaises(ProtectedObjectError):
            assert_fixture_allowed(9999)

    def test_assert_fixture_allowed_accepts_ordinary_fixture(self):
        assert_fixture_allowed(101)  # must not raise

    def test_sequence_allocator_skips_monkeypatched_protected_number(self):
        plan = {"active_sequence_range": [301, 303]}
        profile = {"sequences": []}
        with patch.object(protected_objects, "PROTECTED_SEQUENCES", frozenset({301})):
            self.assertEqual(ShowPlanBuilder._allocate_sequence(plan, profile), 302)


if __name__ == "__main__":
    unittest.main()
