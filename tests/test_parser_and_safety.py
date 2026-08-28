import unittest

from zen_ma2_agent.models import SafetyLevel
from zen_ma2_agent.parser import ParseError, parse
from zen_ma2_agent.safety import build_plan, classify


class ParserAndSafetyTests(unittest.TestCase):
    def setUp(self):
        self.preferences = {"blackout_command_template": None}

    def test_select_group(self):
        plan = build_plan(parse("選 Group BEAM"), self.preferences)
        self.assertEqual(plan.command, 'Group "BEAM"')
        self.assertEqual(plan.safety, SafetyLevel.SAFE)

    def test_beam_intensity_requires_preview(self):
        plan = build_plan(parse("Beam 亮 30%"), self.preferences)
        self.assertEqual(plan.command, 'Group "BEAM"; At 30')
        self.assertEqual(plan.safety, SafetyLevel.MODIFY)
        self.assertTrue(plan.executable)

    def test_sequence_and_fixture_range(self):
        self.assertEqual(build_plan(parse("Go Sequence 5"), self.preferences).command, "Go Sequence 5")
        self.assertEqual(build_plan(parse("選 Fixture 1 到 10"), self.preferences).command, "Fixture 1 Thru 10")

    def test_blackout_remains_unconfigured(self):
        plan = build_plan(parse("Blackout"), self.preferences)
        self.assertFalse(plan.executable)
        self.assertEqual(plan.safety, SafetyLevel.DANGEROUS)

    def test_invalid_fixture_range_and_danger(self):
        with self.assertRaises(ParseError):
            parse("選 Fixture 10 到 1")
        self.assertEqual(classify("Delete Sequence 1"), SafetyLevel.DANGEROUS)


if __name__ == "__main__":
    unittest.main()
