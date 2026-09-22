import unittest

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
            [{"number": 2500, "name": "Other"}, {"number": 2502, "name": "Other2"}]
        )
        self.assertEqual([spec.effect_id for spec in specs], [2501, 2503, 2504])

    def test_template_effect_commands_never_store_fixture_selection(self):
        spec = TemplateEffectSpec(2500, "FX_DIM_CHASE_SLOW", 30)
        commands = template_effect_commands(spec)
        self.assertEqual(commands[0], "ClearAll")
        self.assertEqual(commands[-1], "ClearAll")
        self.assertFalse(any(command.startswith(("Group ", "Fixture ")) for command in commands))
        self.assertFalse(any("Store Effect 1.2500.*" in command for command in commands))
        self.assertTrue(any('Assign Attribute "Dim"' in command for command in commands))

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
