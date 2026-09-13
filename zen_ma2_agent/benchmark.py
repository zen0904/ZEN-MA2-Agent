"""Deterministic structural benchmark primitives (no artistic grading)."""
from __future__ import annotations

from typing import Any, Iterable

SCHEMA = "zen.benchmark_case.v0.1"
RESULT_SCHEMA = "zen.benchmark_result.v0.1"
FORBIDDEN_KEYS = {"ma2_command", "ma2_commands", "telnet", "lua", "shell", "raw_console_text", "command"}


def validate_benchmark_case(case: dict[str, Any]) -> dict[str, Any]:
    required = {"schema", "case_id", "title", "expected_constraints", "evidence_availability", "forbidden_assumptions", "validation_targets"}
    if not isinstance(case, dict) or case.get("schema") != SCHEMA or not required <= set(case):
        raise ValueError("Benchmark case schema or required fields are invalid.")
    if not isinstance(case["validation_targets"], list):
        raise ValueError("Benchmark validation_targets must be a list.")
    return case


def _count_forbidden(value: Any) -> int:
    if isinstance(value, dict):
        return sum((1 if str(key).casefold() in FORBIDDEN_KEYS else 0) + _count_forbidden(child) for key, child in value.items())
    if isinstance(value, list):
        return sum(_count_forbidden(child) for child in value)
    return 0


def score_structural(case: dict[str, Any], output: Any, *, known_evidence_refs: Iterable[str] = (), retrieved_topics: Iterable[str] = (), retry_count: int = 0, runtime_seconds: float | None = None) -> dict[str, Any]:
    case = validate_benchmark_case(case)
    known = set(known_evidence_refs)
    refs = output.get("evidence_refs", []) if isinstance(output, dict) else []
    refs = refs if isinstance(refs, list) else []
    expected_schema = case.get("expected_output_schema")
    schema_valid = isinstance(output, dict) and (expected_schema is None or output.get("schema") == expected_schema)
    topics = set(retrieved_topics)
    expected_topics = {str(item) for item in case.get("expected_topics", [])}
    coverage = (len(topics & expected_topics) / len(expected_topics)) if expected_topics else (1.0 if topics else 0.0)
    uncertainties = isinstance(output, dict) and any(key in output for key in ("uncertainties", "unknowns", "unknown_context"))
    role_locking = isinstance(output, dict) and ("permanent_role" in output or output.get("fixture_role_locking") is True)
    result = {
        "schema": RESULT_SCHEMA,
        "case_id": case["case_id"],
        "metrics": {
            "schema_valid": bool(schema_valid),
            "forbidden_command_count": _count_forbidden(output),
            "unknown_source_count": sum(1 for ref in refs if ref not in known),
            "unsupported_fact_count": len(output.get("unsupported_facts", [])) if isinstance(output, dict) and isinstance(output.get("unsupported_facts", []), list) else 0,
            "uncertainty_preservation": bool(uncertainties),
            "fixture_role_locking": bool(role_locking),
            "evidence_reference_integrity": all(ref in known for ref in refs),
            "knowledge_retrieval_coverage": coverage,
            "knowledge_topic_diversity": len(topics),
            "retry_count": retry_count,
            "runtime": runtime_seconds,
            "output_size": len(str(output)),
        },
    }
    return result
