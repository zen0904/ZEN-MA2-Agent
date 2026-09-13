from __future__ import annotations

import json
import unittest
from pathlib import Path

from zen_ma2_agent.benchmark import score_structural, validate_benchmark_case

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        payload = json.loads((ROOT / "data/benchmark_cases_001.json").read_text(encoding="utf-8"))
        cls.cases = payload["cases"]

    def test_cases_validate_and_score_deterministically(self):
        case = validate_benchmark_case(self.cases[0])
        output = {"schema": "zen.autonomous_design.v0.1", "uncertainties": ["harmony"], "evidence_refs": ["KNOW_1"]}
        first = score_structural(case, output, known_evidence_refs=["KNOW_1"], retrieved_topics=["VISUAL_HIERARCHY"], retry_count=1, runtime_seconds=2.0)
        second = score_structural(case, output, known_evidence_refs=["KNOW_1"], retrieved_topics=["VISUAL_HIERARCHY"], retry_count=1, runtime_seconds=2.0)
        self.assertEqual(first, second)
        self.assertTrue(first["metrics"]["schema_valid"])
        self.assertTrue(first["metrics"]["uncertainty_preservation"])
        self.assertEqual(first["metrics"]["knowledge_retrieval_coverage"], 0.5)

    def test_forbidden_commands_unknown_sources_and_role_locking_are_visible(self):
        case = self.cases[1]
        output = {"ma2_commands": ["Store"], "evidence_refs": ["FAKE"], "permanent_role": "WASH"}
        result = score_structural(case, output, known_evidence_refs=[])
        self.assertEqual(result["metrics"]["forbidden_command_count"], 1)
        self.assertEqual(result["metrics"]["unknown_source_count"], 1)
        self.assertEqual(result["metrics"]["fixture_role_locking"], True)


if __name__ == "__main__":
    unittest.main()
