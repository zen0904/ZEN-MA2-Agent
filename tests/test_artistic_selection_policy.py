import unittest

from zen_ma2_agent.artistic_capabilities import (
    ARTISTIC_DIMENSIONS,
    ARTISTIC_SELECTION_POLICY_SCHEMA,
    artistic_selection_policy,
)
from zen_ma2_agent.designer.lean_design_mode import (
    assemble_compact_design_context,
    build_delta_revision_context,
)


class ArtisticSelectionPolicyTests(unittest.TestCase):
    def test_policy_exposes_full_repertoire_without_turning_it_into_a_quota(self):
        policy = artistic_selection_policy()
        self.assertEqual(policy["schema"], ARTISTIC_SELECTION_POLICY_SCHEMA)
        self.assertEqual(policy["repertoire_mode"], "FULL_VOCABULARY_NOT_CHECKLIST")
        self.assertEqual(policy["artistic_repertoire"], list(ARTISTIC_DIMENSIONS))
        self.assertEqual(policy["default_mechanism_state"], "OPTIONAL")
        self.assertTrue(policy["selection_requires_artistic_reason"])
        self.assertTrue(policy["deliberate_non_use_valid"])
        self.assertFalse(policy["resource_availability_implies_use"])
        self.assertIsNone(policy["mechanism_quota"])
        self.assertIn(
            "REVIEW_SHOULD_NOTICE_BOTH_UNJUSTIFIED_OMISSION_AND_GRATUITOUS_OVERUSE",
            policy["principles"],
        )

    def test_primary_and_delta_contexts_receive_the_same_policy(self):
        primary = assemble_compact_design_context(song_context={"song": "TEST"})
        delta = build_delta_revision_context(
            accepted_artistic_plan={"cues": [{"cue_number": 1, "label": "A", "actions": []}]},
            owner_revision_text="reduce density",
        )
        self.assertEqual(
            primary["context"]["artistic_selection_policy"],
            delta["context"]["artistic_selection_policy"],
        )
        self.assertEqual(
            primary["context"]["artistic_selection_policy"]["schema"],
            ARTISTIC_SELECTION_POLICY_SCHEMA,
        )


if __name__ == "__main__":
    unittest.main()
