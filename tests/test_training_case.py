import unittest

from zen_ma2_agent.training_case import (
    TRAINING_CASE_SCHEMA,
    TRAINING_CASE_001,
    build_training_case_001,
    designer_context,
    validate_training_case,
)


class TrainingCaseTests(unittest.TestCase):
    def profile(self):
        groups = []
        fixtures = []
        for number, name in ((1, "HYBRID"), (2, "BEAM"), (3, "STROBE")):
            ids = [number * 100 + index for index in range(1, 9)]
            groups.append({"group_id": number, "name": name, "fixture_ids_in_selection_order": ids})
            fixtures.extend({"fixture_id": fixture_id, "fixture_type": f"TYPE_{number}"} for fixture_id in ids)
        return {"groups": groups, "fixtures": fixtures, "presets": [{"reference": "6.2"}], "effects": [{"effect_id": 3520}]}

    def test_case_schema_and_current_group_analysis_are_inferred(self):
        case = build_training_case_001(self.profile())
        self.assertEqual(case["schema"], TRAINING_CASE_SCHEMA)
        self.assertEqual(case["case_id"], TRAINING_CASE_001)
        self.assertEqual(case["case_type"], "RESOURCE_RICH_KPOP_ORIENTED")
        hybrid = case["fixture_groups"][0]
        self.assertEqual(hybrid["role_assignment"]["primary_role"], "AERIAL")
        self.assertEqual(hybrid["role_assignment"]["confidence"], "INFERRED_FROM_GROUP_IDENTITY")
        self.assertNotEqual(hybrid["role_assignment"]["primary_role"], hybrid["fixture_types"][0])

    def test_case_contains_general_lessons_and_case_specific_scope(self):
        case = build_training_case_001(self.profile())
        self.assertTrue(any(item["scope"] == "GENERALIZABLE_LESSON" for item in case["design_principles"]))
        self.assertTrue(any(item["scope"] == "CASE_SPECIFIC" for item in case["assumptions"]))
        self.assertIn("CASE_004_LED_ONLY", {item["case_id"] for item in case["future_cases"]})
        self.assertEqual(case["constraints"]["no_ma2_commands"], True)

    def test_designer_context_is_command_free_and_does_not_enable_writes(self):
        context = designer_context(build_training_case_001(self.profile()))
        self.assertEqual(context["status"], "KNOWLEDGE_ONLY")
        self.assertNotIn("commands", context)
        self.assertNotIn("command", str(context).lower())

    def test_validation_rejects_raw_command_and_invalid_role(self):
        case = build_training_case_001(self.profile())
        invalid = dict(case, commands=["Move3D Fixture 101"])
        with self.assertRaises(ValueError):
            validate_training_case(invalid)
        invalid_role = build_training_case_001(self.profile())
        invalid_role["fixture_groups"] = list(invalid_role["fixture_groups"])
        invalid_role["fixture_groups"][0] = dict(invalid_role["fixture_groups"][0])
        invalid_role["fixture_groups"][0]["role_assignment"] = dict(invalid_role["fixture_groups"][0]["role_assignment"], primary_role="MA2_COMMAND")
        with self.assertRaises(ValueError):
            validate_training_case(invalid_role)


if __name__ == "__main__":
    unittest.main()
