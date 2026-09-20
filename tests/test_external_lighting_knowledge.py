import json
import unittest
from pathlib import Path

from zen_ma2_agent.external_lighting_knowledge import (
    CONTEXT_SCHEMA,
    PACK_SCHEMA,
    RECORD_SCHEMA,
    build_pack,
    build_shadow_knowledge_context,
    critique_ab002_density_limits,
    load_pack,
    validate_record,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external_lighting_knowledge_source_registry_001.json"
PACK = ROOT / "data" / "external_lighting_knowledge_pack_001.json"


class ExternalLightingKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.raw = json.loads(PACK.read_text(encoding="utf-8"))
        cls.pack = load_pack(REGISTRY, PACK)

    def test_pack_is_small_traceable_and_unpromoted(self):
        self.assertEqual(self.pack["schema"], PACK_SCHEMA)
        self.assertGreaterEqual(len(self.pack["records"]), 20)
        self.assertGreaterEqual(len(self.pack["records"]), 100)
        self.assertEqual(self.pack["runtime_wiring"], "NOT_RUN")
        self.assertEqual(self.pack["global_promotions"], [])
        source_ids = {source["source_id"] for source in self.pack["sources"]}
        self.assertTrue(all(record["source_id"] in source_ids for record in self.pack["records"]))
        record_ids = [record["record_id"] for record in self.pack["records"]]
        self.assertEqual(len(record_ids), len(set(record_ids)))
        self.assertTrue(all(record["promotion_state"] != "PROMOTED" for record in self.pack["records"]))
        self.assertTrue(all(record["knowledge_kind"] != "PRESCRIPTIVE_REQUIREMENT" for record in self.pack["records"]))
        self.assertTrue(all(len(record["normalized_claim"]) <= 500 and len(record["summary"]) <= 600 for record in self.pack["records"]))
        self.assertTrue(all("command" not in record and "full_text" not in record for record in self.pack["records"]))

    def test_records_preserve_descriptive_scope_and_provenance(self):
        record = self.pack["records"][0]
        self.assertEqual(record["schema"], RECORD_SCHEMA)
        self.assertEqual(record["knowledge_kind"], "DESCRIPTIVE")
        self.assertTrue(record["source_provenance"])
        self.assertTrue(record["exclusions"])

    def test_commands_and_long_copied_material_are_rejected(self):
        bad = dict(self.raw["records"][0])
        bad["command"] = "Store Cue 1"
        with self.assertRaises(ValueError):
            validate_record(bad)
        bad = dict(self.raw["records"][0], normalized_claim="x" * 501)
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_unknown_source_and_production_promotion_are_rejected(self):
        bad = dict(self.raw)
        bad["records"] = [dict(self.raw["records"][0], source_id="missing")]
        with self.assertRaises(ValueError):
            build_pack(self.registry, bad)

        bad = dict(self.raw, source_registry_ref="OTHER")
        with self.assertRaises(ValueError):
            build_pack(self.registry, bad)

        bad = dict(self.raw)
        bad["records"] = [dict(self.raw["records"][0], knowledge_kind="PRESCRIPTIVE_REQUIREMENT")]
        with self.assertRaises(ValueError):
            build_pack(self.registry, bad)

        case_record = next(item for item in self.raw["records"] if item["source_id"] == "PLASA_PARADISE_UNDER_THE_STARS")
        bad = dict(self.raw)
        bad["records"] = [dict(case_record, evidence_classification="GENERAL_DESIGN_KNOWLEDGE")]
        with self.assertRaises(ValueError):
            build_pack(self.registry, bad)
        bad = dict(self.raw)
        bad["records"] = [dict(self.raw["records"][0], promotion_state="PROMOTED")]
        with self.assertRaises(ValueError):
            build_pack(self.registry, bad)

    def test_shadow_context_and_ab002_critique_are_non_actioning(self):
        context = build_shadow_knowledge_context(self.pack, topics={"VISUAL_HIERARCHY", "RESOURCE_HEADROOM", "NEGATIVE_SPACE_RESTRAINT"})
        self.assertEqual(context["schema"], CONTEXT_SCHEMA)
        self.assertEqual(context["runtime_mode"], "SHADOW_ONLY")
        critique = critique_ab002_density_limits(context, observed_findings={"FINAL_COHORT_SATURATION_RISK", "GROUP_LEVEL_HOMOGENEITY_UNRESOLVED"})
        self.assertEqual(critique["action_changes"], [])
        self.assertTrue(critique["requires_show_specific_visual_evidence"])
        self.assertFalse(critique["production_designer_modified"])


if __name__ == "__main__":
    unittest.main()
