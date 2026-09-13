import unittest

from zen_ma2_agent.protected_objects import (
    PROTECTED_FIXTURE_IDS,
    PROTECTED_SEQUENCES,
    ProtectedObjectError,
    assert_fixture_allowed,
    assert_sequence_allowed,
)


class ProtectedObjectsTests(unittest.TestCase):
    def test_known_protected_sequences_are_present(self):
        self.assertEqual(PROTECTED_SEQUENCES, frozenset({201, 202, 204, 205}))

    def test_fixture_9999_is_protected(self):
        self.assertIn(9999, PROTECTED_FIXTURE_IDS)

    def test_assert_sequence_allowed_rejects_protected_numbers(self):
        for sequence in PROTECTED_SEQUENCES:
            with self.assertRaises(ProtectedObjectError):
                assert_sequence_allowed(sequence)

    def test_assert_sequence_allowed_accepts_unprotected_numbers(self):
        assert_sequence_allowed(901)  # must not raise

    def test_assert_fixture_allowed_rejects_9999(self):
        with self.assertRaises(ProtectedObjectError):
            assert_fixture_allowed(9999)

    def test_assert_fixture_allowed_accepts_ordinary_fixture(self):
        assert_fixture_allowed(101)  # must not raise


if __name__ == "__main__":
    unittest.main()
