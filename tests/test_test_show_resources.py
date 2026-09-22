import unittest

from zen_ma2_agent.state.providers.show_pools import EffectProvider
from zen_ma2_agent.test_show_resources import (
    TemplateEffectSpec,
    allocate_template_effect_specs,
    reconcile_template_effect_specs,
    template_effect_commands,
    verify_template_effect_rows,
)


class TestShowResourcesTests(unittest.TestCase):
    def test_allocator_skips_existing_effect_ids(self):
        specs = allocate_template_effect_specs(
            [{"number": 1, "name": "Other"}, {"number": 3, "name": "Other2"}]
        )
        self.assertEqual([spec.effect_id for spec in specs], [2, 4, 5])

    def test_template_effect_commands_never_store_fixture_selection(self):
        spec = TemplateEffectSpec(2500, "FX_DIM_CHASE_SLOW", 30)
        commands = template_effect_commands(spec)
        self.assertEqual(commands[0], "ClearAll")
        self.assertEqual(commands[-1], "ClearAll")
        self.assertFalse(any(command.startswith(("Group ", "Fixture ")) for command in commands))
        self.assertFalse(any("Store Effect 1.2500.*" in command for command in commands))
        self.assertTrue(any('Assign Attribute "Dim"' in command for command in commands))


    def test_effect_detail_parser_uses_only_explicit_qty_evidence(self):
        provider = EffectProvider()

        template = provider.parse_template_detail(
            "Effect 1.2500.1\nQTY=None\nAttribute Dim\n"
        )
        self.assertEqual((template["status"], template["kind"]), ("VERIFIED", "TEMPLATE"))

        selective = provider.parse_template_detail(
            "Effect 1.2500.1\nQTY=8\nAttribute Dim\n"
        )
        self.assertEqual((selective["status"], selective["kind"]), ("VERIFIED", "SELECTIVE"))

        unknown = provider.parse_template_detail(
            "Effect 2500 FX_DIM_CHASE_SLOW\n"
        )
        self.assertEqual((unknown["status"], unknown["kind"]), ("UNKNOWN", None))

        mixed = provider.parse_template_detail(
            "QTY=None\nQTY=8\n"
        )
        self.assertEqual((mixed["status"], mixed["kind"]), ("UNKNOWN", None))

    def test_effect_detail_parser_accepts_real_ma2_tabular_qty_column(self):
        provider = EffectProvider()
        raw = """Executing : List Effect 1.2500.*
             QTY   Interleave  Attrib  Mode  Form   Rate  Speed     SpeedGroup  Dir  LowValue  HighValue  Phase         Width   Attack  Decay  Groups  Blocks  Wings  SingleShot
Effectline 1 None  None        DIM     Abs   Pwm 4  0.50  30.0 BPM              >    0.00      100.00     0.0 .. 360.0  100.00  0       0      1       None    None   No
"""
        parsed = provider.parse_template_detail(raw)
        self.assertEqual(parsed["status"], "VERIFIED")
        self.assertEqual(parsed["kind"], "TEMPLATE")
        self.assertEqual(parsed["qty_values"], ["NONE"])
        self.assertEqual(parsed["reason"], "ALL_EFFECT_LINES_QTY_NONE")

    def test_effect_detail_parser_marks_real_ma2_tabular_numeric_qty_selective(self):
        provider = EffectProvider()
        raw = """Executing : List Effect 1.2500.*
             QTY   Interleave  Attrib  Mode  Form
Effectline 1 8     None        DIM     Abs   Pwm
"""
        parsed = provider.parse_template_detail(raw)
        self.assertEqual(parsed["status"], "VERIFIED")
        self.assertEqual(parsed["kind"], "SELECTIVE")
        self.assertEqual(parsed["qty_values"], [8])
        self.assertEqual(parsed["reason"], "ALL_EFFECT_LINES_QTY_NUMERIC")

    def test_reconcile_reuses_only_exact_template_kind(self):
        specs, existing = reconcile_template_effect_specs([
            {"number": 88, "name": "FX_DIM_CHASE_SLOW", "kind": "TEMPLATE"},
        ])
        self.assertEqual(specs[0].effect_id, 88)
        self.assertIn(88, existing)

        with self.assertRaisesRegex(ValueError, "not verified TEMPLATE"):
            reconcile_template_effect_specs([
                {"number": 88, "name": "FX_DIM_CHASE_SLOW", "kind": "SELECTIVE"},
            ])

    def test_verifier_requires_exact_label_and_template_kind(self):
        spec = TemplateEffectSpec(88, "FX_DIM_CHASE_SLOW", 30)
        good = verify_template_effect_rows([
            {"number": 88, "name": "FX_DIM_CHASE_SLOW", "kind": "TEMPLATE"},
        ], [spec])
        self.assertTrue(good[88]["verified"])

        bad = verify_template_effect_rows([
            {"number": 88, "name": "FX_DIM_CHASE_SLOW", "kind": None},
        ], [spec])
        self.assertFalse(bad[88]["verified"])


if __name__ == "__main__":
    unittest.main()
