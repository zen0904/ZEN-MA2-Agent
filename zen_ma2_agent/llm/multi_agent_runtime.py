"""Sequential, portable Local Multi-Agent runtime.

This module orchestrates bounded, structured LLM roles only.  It deliberately
does not import MA2 transport, Builder, or Resolver code: a validated final
design remains an experimental artifact until a separately approved path can
resolve it.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from uuid import uuid4

from ..portable import portable_state_path
from ..run_checkpoints import find_resume_point, read_step_artifact, write_step_artifact
from ..knowledge_store import project_records, resolve_research_sources, retrieve_records, validate_evidence_refs
from .autonomous_designer import (
    FORBIDDEN_KEYS,
    SCHEMA as FINAL_DESIGN_SCHEMA,
    DesignValidationError,
    build_designer_context,
    validate_design_output,
)
from .router import ProviderRouter, ProviderSlot, ProviderUnavailable


ROLE_SEQUENCE = ("researcher", "lighting_designer", "critic", "finalizer")
MAX_ROLE_ATTEMPTS = 3
RUN_SCHEMA = "zen.multi_agent_run.v0.1"
STEP_SCHEMA = "zen.multi_agent_step.v0.1"
FAILURE_SCHEMA = "zen.multi_agent_failure.v0.1"
ATTEMPT_SCHEMA = "zen.multi_agent_attempt_diagnostic.v0.1"
PARALLEL_CANDIDATE_ATTEMPT_SCHEMA = "zen.multi_agent_parallel_candidate_diagnostic.v0.1"


class MultiAgentRunError(RuntimeError):
    """Raised when a bounded role cannot produce a valid checkpoint."""


@dataclass(frozen=True)
class MultiAgentRun:
    run_id: str
    context_hash: str
    final_design: dict[str, object]
    run_path: Path
    resumed_from: str | None


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _run_path(run_id: str) -> Path:
    if not run_id or Path(run_id).name != run_id:
        raise ValueError("run_id must be a single portable directory name.")
    return portable_state_path("projects") / "runs" / run_id


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={repo_root}", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "UNKNOWN"


def _is_local(slot: ProviderSlot) -> bool:
    return slot.provider_type in ProviderSlot.LOCAL_TYPES


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(str(key).casefold() in FORBIDDEN_KEYS or _contains_forbidden_key(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def _parse_json(content: str) -> object:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise MultiAgentRunError("Provider response was not valid JSON.") from exc


def _validate_object(value: object, *, schema: str, required: tuple[str, ...]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise MultiAgentRunError("Role output must be a JSON object.")
    if value.get("schema") != schema:
        raise MultiAgentRunError(f"Role output schema must be {schema}.")
    missing = [field for field in required if field not in value]
    if missing:
        raise MultiAgentRunError("Role output missing required fields: " + ", ".join(missing))
    if _contains_forbidden_key(value):
        raise MultiAgentRunError("Role output contains a prohibited executable-command field.")
    if value.get("codex_artistic_intervention") not in (None, "NONE"):
        raise MultiAgentRunError("Role output must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    return value


def validate_research_artifact(value: object) -> dict[str, object]:
    return _validate_object(
        value,
        schema="zen.multi_agent_research.v0.1",
        required=("research_status", "subject", "sources", "transferable_design_observations", "constraints", "uncertainties"),
    )


def validate_designer_artifact(value: object) -> dict[str, object]:
    return _validate_object(
        value,
        schema="zen.multi_agent_designer_draft.v0.1",
        required=("design_intent", "visual_strategy", "resource_considerations", "uncertainties"),
    )


def validate_critic_artifact(value: object) -> dict[str, object]:
    return _validate_object(
        value,
        schema="zen.multi_agent_critic.v0.1",
        required=("strengths", "problems", "severity", "revision_requests"),
    )


ROLE_VALIDATORS: dict[str, Callable[[object], dict[str, object]]] = {
    "researcher": validate_research_artifact,
    "lighting_designer": validate_designer_artifact,
    "critic": validate_critic_artifact,
    "finalizer": validate_design_output,
}


ROLE_ROUTER_NAMES = {
    "researcher": "RESEARCHER",
    "lighting_designer": "LIGHTING_DESIGNER",
    "critic": "CRITIC",
    "finalizer": "FINALIZER",
}
ROLE_KNOWLEDGE_LIMIT = 8
FINALIZER_ROLE_KNOWLEDGE_LIMIT = 6

FINALIZER_RESEARCH_FIELDS = (
    "research_status",
    "subject",
    "transferable_design_observations",
    "constraints",
    "uncertainties",
    "evidence_refs",
    "sources",
)
FINALIZER_DESIGNER_FIELDS = (
    "design_intent",
    "visual_strategy",
    "resource_considerations",
    "uncertainties",
    "evidence_refs",
)
FINALIZER_CRITIC_FIELDS = (
    "strengths",
    "problems",
    "severity",
    "revision_requests",
    "evidence_refs",
)

RETRY_SAFETY_CONTRACT = (
    " Preserve valid UNKNOWN and uncertainty states. Do not invent facts to satisfy validation."
    " Do not invent color, position, intensity, fixture role, performer position, stage geometry, or source metadata."
    " Shorten prose before removing evidence or uncertainty. Preserve evidence_refs when still valid."
    " Validation repair must be structural, not artistic invention."
)


ROLE_SYSTEM_PROMPTS = {
    "researcher": (
        "ROLE: RESEARCHER. Build a compact, provenance-bearing Evidence Pack from only the supplied request and context. "
        "Do not fabricate live research or sources. When no retrieved source is supplied, use research_status OFFLINE_CACHED_CONTEXT. "
        "If evidence_refs or sources are included, use only identities present in the supplied evidence_ledger; never author canonical source metadata. "
        "Return one compact JSON object only. Its first key must be schema with exact value zen.multi_agent_research.v0.1, followed by fields research_status, subject, sources, "
        "transferable_design_observations, constraints, uncertainties, codex_artistic_intervention. "
        "Do not emit MA2, Telnet, Lua, shell, or executable commands. Set codex_artistic_intervention to NONE."
    ),
    "lighting_designer": (
        "ROLE: LIGHTING_DESIGNER. Produce a contextual design draft from the supplied request, evidence, and bounded Show context. "
        "Technical fixture capability is tool inventory, never a permanent artistic role. Preserve unknowns rather than inventing facts. "
        "Use evidence_refs only when they exist in the supplied evidence_ledger. "
        "Do not use fixture-name recipes or energy-to-fixture-count rules. Return one compact JSON object only. Its first key must be schema with exact value "
        "zen.multi_agent_designer_draft.v0.1, followed by fields design_intent, visual_strategy, resource_considerations, uncertainties, "
        "codex_artistic_intervention. Do not emit executable commands. Set codex_artistic_intervention to NONE."
    ),
    "critic": (
        "ROLE: CRITIC. Independently inspect the supplied draft against supplied constraints and identify strengths, problems with severity, "
        "and a severity classification with actionable revision_requests. Check unsupported features, repetitive/mechanical choices, weak hierarchy, missing negative space, "
        "Use evidence_refs only when they exist in the supplied evidence_ledger. "
        "handover/editability risks, and conflicts with known Show constraints. If designer_candidates is supplied, compare all candidates and identify the strongest valid elements rather than assuming the primary draft is best. Do not rubber-stamp the draft. Return one compact JSON object only. Its first key must be schema with exact value "
        "zen.multi_agent_critic.v0.1, followed by fields strengths, problems, severity, revision_requests, codex_artistic_intervention. "
        "Do not emit executable commands. Set codex_artistic_intervention to NONE."
    ),
    "finalizer": (
        "ROLE: FINALIZER. Produce the corrected final autonomous design using the supplied request, bounded context, research, draft, and critique. If designer_candidates or critic_candidates are supplied, synthesize only their strongest valid, evidence-supported elements; candidate presence does not make a claim true. "
        "Return exactly one compact JSON object. Its first key must be schema with exact value zen.autonomous_design.v0.1. Required fields are schema, design_intent, visual_strategy, "
        "virtual_rig, position_vocabulary, main_sequence, free_cue_layer, evidence_trace, codex_artistic_intervention. "
        "Retain uncertainty rather than inventing facts. Never emit MA2, Telnet, Lua, shell, or executable commands. "
        "Use evidence_refs only when they exist in the supplied evidence_ledger. "
        "Set codex_artistic_intervention to NONE."
    ),
}


def build_role_evidence_ledger(full_ledger: dict[str, object], selected_ids: list[str]) -> dict[str, object]:
    """Project the backend ledger for one role without weakening validation."""
    selected = set(selected_ids)
    entries = [
        entry for entry in full_ledger.get("entries", [])
        if isinstance(entry, dict) and (entry.get("kind") == "VERIFIED_FACT" or entry.get("evidence_ref") in selected)
    ]
    return {
        "schema": full_ledger.get("schema", "zen.evidence_ledger.v0.1"),
        "entries": sorted(entries, key=lambda item: str(item.get("evidence_ref", ""))),
        "available_verified_facts": full_ledger.get("available_verified_facts", []),
    }


def project_role_source_registry(full_registry: dict[str, object], selected_records: list[dict[str, object]]) -> dict[str, object]:
    """Expose only registry metadata referenced by a role's selected records."""
    selected_ids = {str(record.get("source_id")) for record in selected_records}
    sources = [source for source in full_registry.get("sources", []) if isinstance(source, dict) and source.get("source_id") in selected_ids]
    return {"schema": full_registry.get("schema", "zen.external_lighting_knowledge_source_registry.v0.1"), "registry_id": full_registry.get("registry_id", ""), "sources": sorted(sources, key=lambda item: str(item.get("source_id", "")))}


def _project_artifact_fields(artifact: dict[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    """Select finalizer inputs without summarizing or rewriting their values."""
    return {field: artifact[field] for field in fields if field in artifact}


def _project_research_artifact(artifact: dict[str, object]) -> dict[str, object]:
    projected = _project_artifact_fields(artifact, FINALIZER_RESEARCH_FIELDS)
    sources = projected.get("sources")
    if isinstance(sources, list):
        # Source identity is sufficient downstream; canonical metadata remains
        # available to the backend resolver and is not duplicated in the prompt.
        projected["sources"] = [
            {key: item[key] for key in ("source_id", "record_id") if key in item}
            if isinstance(item, dict) else item
            for item in sources
        ]
    return projected


def _project_finalization_context(context: dict[str, object]) -> dict[str, object]:
    categories = context.get("categories", {})
    if not isinstance(categories, dict):
        categories = {}
    operator_contract = categories.get("operator_contract", {})
    if isinstance(operator_contract, dict):
        # Product narrative is not needed to finalize a typed design. Keep the
        # workflow and console handover constraints, while the full documents
        # remain available in backend context for validation/audit.
        operator_contract = {
            # The full MA2 intelligence document is backend knowledge, not a
            # required finalizer input.  Keeping the stable workflow contract
            # avoids duplicating console prose while preserving handover rules.
            key: operator_contract[key]
            for key in ("workflow_contract",)
            if key in operator_contract
        }
    return {
        "fixture_technical_capability": categories.get("fixture_technical_capability", {}),
        "rig_spatial_visual_affordance": categories.get("rig_spatial_visual_affordance", {}),
        "operator_contract": operator_contract,
    }


def _role_context(
    role_name: str,
    *,
    request: str,
    context: dict[str, object],
    completed: dict[str, dict[str, object]],
    candidate_sets: dict[str, list[dict[str, object]]] | None = None,
) -> dict[str, object]:
    candidate_sets = candidate_sets or {}
    categories = context.get("categories", {})
    # Retrieval is role-specific over the complete backend corpus.  The prior
    # generic 12-record seed is intentionally not used as a model-facing pool.
    canonical_records = context.get("canonical_knowledge_records", [])
    # Finalization already receives three upstream artifacts; keep its
    # selected knowledge smaller so the model-facing projection remains under
    # the established payload budget as the canonical store grows.
    role_limit = FINALIZER_ROLE_KNOWLEDGE_LIMIT if role_name == "finalizer" else ROLE_KNOWLEDGE_LIMIT
    selected_records = retrieve_records(canonical_records, role=ROLE_ROUTER_NAMES[role_name], request=request, current_context=context, limit=role_limit, max_records_per_topic=2)
    role_knowledge = project_records(selected_records)
    selected_ids = [str(item["record_id"]) for item in selected_records]
    full_registry = categories.get("source_provenance", {}) if isinstance(categories, dict) else {}
    role_registry = project_role_source_registry(full_registry, selected_records) if isinstance(full_registry, dict) else {"schema": "zen.external_lighting_knowledge_source_registry.v0.1", "registry_id": "", "sources": []}
    role_ledger = build_role_evidence_ledger(context.get("evidence_ledger", {}), selected_ids)
    knowledge_context = {
        "schema": "zen.knowledge_retrieval_context.v0.1",
        "records": role_knowledge,
        "knowledge_refs": selected_ids,
        "topic_diversity": sorted({item["topic"] for item in role_knowledge}),
    }
    common = {
        "user_request": request,
        "hard_constraints": context.get("hard_constraints", []),
        "evidence_boundary": context.get("evidence_boundary", {}),
        "evidence_ledger": role_ledger,
        "professional_lighting_design_knowledge": knowledge_context,
        "role_context_metadata": {
            "selected_knowledge_count": len(selected_records),
            "selected_knowledge_ids": selected_ids,
            "selected_topics": sorted({str(item["topic"]) for item in selected_records}),
            "selected_source_ids": sorted({str(item.get("source_id")) for item in selected_records}),
            "evidence_entry_count": len(role_ledger["entries"]),
        },
    }
    if role_name == "researcher":
        return common | {
            "research_context": {
                "professional_lighting_design_knowledge": knowledge_context,
                "source_provenance": role_registry,
            }
        }
    if role_name == "lighting_designer":
        return common | {
            "research_artifact": completed["researcher"],
            "design_context": {
                "fixture_technical_capability": categories.get("fixture_technical_capability", {}),
                "rig_spatial_visual_affordance": categories.get("rig_spatial_visual_affordance", {}),
                "operator_contract": categories.get("operator_contract", {}),
            },
        }
    if role_name == "critic":
        parallel_designers = candidate_sets.get("lighting_designer", [])
        return common | {
            "research_artifact": completed["researcher"],
            "designer_draft": completed["lighting_designer"],
            "relevant_show_constraints": {
                "fixture_technical_capability": categories.get("fixture_technical_capability", {}),
                "rig_spatial_visual_affordance": categories.get("rig_spatial_visual_affordance", {}),
            },
        } | (
            {"designer_candidates": parallel_designers}
            if len(parallel_designers) > 1 else {}
        )
    parallel_designers = candidate_sets.get("lighting_designer", [])
    parallel_critics = candidate_sets.get("critic", [])
    return common | {
        "research_artifact": _project_research_artifact(completed["researcher"]),
        "designer_draft": _project_artifact_fields(completed["lighting_designer"], FINALIZER_DESIGNER_FIELDS),
        "critic_artifact": _project_artifact_fields(completed["critic"], FINALIZER_CRITIC_FIELDS),
        "finalization_context": _project_finalization_context(context),
    } | (
        {
            "designer_candidates": [
                _project_artifact_fields(item, FINALIZER_DESIGNER_FIELDS)
                for item in parallel_designers
            ]
        } if len(parallel_designers) > 1 else {}
    ) | (
        {
            "critic_candidates": [
                _project_artifact_fields(item, FINALIZER_CRITIC_FIELDS)
                for item in parallel_critics
            ]
        } if len(parallel_critics) > 1 else {}
    )


def _read_completed_artifacts(run_id: str) -> dict[str, dict[str, object]]:
    completed: dict[str, dict[str, object]] = {}
    for role_name in ROLE_SEQUENCE:
        envelope = read_step_artifact(run_id, role_name)
        if envelope is None:
            continue
        artifact = envelope.get("artifact") if isinstance(envelope, dict) else None
        if isinstance(artifact, dict):
            completed[role_name] = artifact
    return completed


def _read_candidate_sets(run_id: str) -> dict[str, list[dict[str, object]]]:
    candidate_sets: dict[str, list[dict[str, object]]] = {}
    for role_name in ("lighting_designer", "critic"):
        envelope = read_step_artifact(run_id, role_name)
        if not isinstance(envelope, dict):
            continue
        raw = envelope.get("candidate_artifacts")
        if not isinstance(raw, list):
            continue
        artifacts = [
            item.get("artifact")
            for item in raw
            if isinstance(item, dict) and isinstance(item.get("artifact"), dict)
        ]
        if artifacts:
            candidate_sets[role_name] = artifacts
    return candidate_sets


def _validate_artifact_evidence(role_name: str, artifact: dict[str, object], context: dict[str, object]) -> dict[str, object]:
    """Bind every role's optional evidence refs to the canonical runtime ledger."""
    ledger = context.get("evidence_ledger", {})
    refs = artifact.get("evidence_refs", [])
    if refs is None:
        refs = []
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
        raise MultiAgentRunError(f"{role_name} evidence_refs must be a list of strings.")
    try:
        validate_evidence_refs(refs, ledger)
    except ValueError as exc:
        raise MultiAgentRunError(str(exc)) from exc
    if role_name == "researcher":
        try:
            artifact["resolved_sources"] = resolve_research_sources(
                sources=artifact.get("sources", []),
                source_registry=context.get("categories", {}).get("source_provenance", {}),
                records=context.get("canonical_knowledge_records", []),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MultiAgentRunError(str(exc)) from exc
    return artifact


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_run_state(path: Path, value: dict[str, object]) -> None:
    _write_json(path / "run.json", value)


def _read_run_state(path: Path) -> dict[str, object]:
    try:
        value = json.loads((path / "run.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _load_valid_final(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        return validate_design_output(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, DesignValidationError):
        return None


def _archive_for_restart(path: Path) -> None:
    """Preserve an explicit restart's prior evidence before regenerating it."""
    existing = [path / name for name in ("run.json", "steps", "final_design.json", "failure.json") if (path / name).exists()]
    if not existing:
        return
    archive = path / "restart_archive" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive.mkdir(parents=True, exist_ok=False)
    for item in existing:
        shutil.move(str(item), str(archive / item.name))


def _record_failure(path: Path, *, role_name: str, attempts: int, error: Exception) -> None:
    _write_json(path / "failure.json", {
        "schema": FAILURE_SCHEMA,
        "role": role_name,
        "attempts": attempts,
        "error_type": type(error).__name__,
        "message": str(error),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    })


def _record_attempt_diagnostic(
    path: Path,
    *,
    role_name: str,
    attempt: int,
    content: str,
    error: Exception,
    provider_elapsed_seconds: float | None = None,
    failure_class: str = "OUTPUT_VALIDATION",
) -> None:
    """Keep an agent-owned failed response for local validation diagnosis."""
    _write_json(path / "attempts" / f"{role_name}-{attempt:02}.json", {
        "schema": ATTEMPT_SCHEMA,
        "role": role_name,
        "attempt": attempt,
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_characters": len(content),
        "validation_error_type": type(error).__name__,
        "validation_error": str(error),
        "provider_elapsed_seconds": provider_elapsed_seconds,
        "failure_class": failure_class,
        "raw_response": content,
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    })


def _bounded_validation_error(error: Exception, *, api_key: str) -> str:
    message = str(error)
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return message[:500]


def _record_parallel_candidate_failure(
    path: Path,
    *,
    role_name: str,
    slot: ProviderSlot,
    content: str,
    error: Exception,
) -> tuple[bool, str]:
    """Persist one transport-successful parallel response rejected by its role validator."""
    secret_leaked = bool(slot.api_key and slot.api_key in content)
    validation_error = _bounded_validation_error(error, api_key=slot.api_key)
    diagnostic: dict[str, object] = {
        "schema": PARALLEL_CANDIDATE_ATTEMPT_SCHEMA,
        "role": role_name,
        "provider": slot.safe_identity(),
        "slot_number": slot.number,
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_characters": len(content),
        "validation_error_type": type(error).__name__,
        "validation_error": validation_error,
        "candidate_status": "SECRET_REJECTION" if secret_leaked else "OUTPUT_VALIDATION_FAILURE",
        "secret_check": "FAIL" if secret_leaked else "PASS",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    if not secret_leaked:
        diagnostic["raw_response"] = content
    _write_json(path / "attempts" / f"{role_name}-parallel-slot{slot.number:02}.json", diagnostic)
    return secret_leaked, validation_error


def _record_model_context_diagnostic(
    path: Path,
    *,
    role_name: str,
    attempt: int,
    system: str,
    user: str,
    payload: dict[str, object],
    provider_elapsed_seconds: float | None = None,
    failure_class: str = "PENDING",
    diagnostic_name: str | None = None,
) -> Path:
    metadata = payload.get("role_context_metadata", {})
    diagnostic_path = path / "diagnostics" / (diagnostic_name or f"{role_name}-{attempt:02}.json")
    _write_json(diagnostic_path, {
        "schema": "zen.model_context_diagnostic.v0.1",
        "role": role_name,
        "attempt": attempt,
        "selected_knowledge_count": metadata.get("selected_knowledge_count", 0) if isinstance(metadata, dict) else 0,
        "selected_knowledge_ids": metadata.get("selected_knowledge_ids", []) if isinstance(metadata, dict) else [],
        "selected_topics": metadata.get("selected_topics", []) if isinstance(metadata, dict) else [],
        "selected_source_ids": metadata.get("selected_source_ids", []) if isinstance(metadata, dict) else [],
        "evidence_entry_count": len(payload.get("evidence_ledger", {}).get("entries", [])) if isinstance(payload.get("evidence_ledger"), dict) else 0,
        "system_characters": len(system),
        "user_characters": len(user),
        "payload_utf8_bytes": len((system + user).encode("utf-8")),
        "provider_elapsed_seconds": provider_elapsed_seconds,
        "failure_class": failure_class,
        "secrets_included": False,
    })
    return diagnostic_path


def _update_model_context_diagnostic(path: Path, *, provider_elapsed_seconds: float, failure_class: str) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(value, dict):
        return
    value["provider_elapsed_seconds"] = round(provider_elapsed_seconds, 3)
    value["failure_class"] = failure_class
    _write_json(path, value)


def _write_single_role_provider_diagnostic(
    path: Path,
    *,
    role_name: str,
    router: ProviderRouter,
    provider_attempts: tuple[dict[str, object], ...],
    selected_slot: ProviderSlot | None,
    role_output_validation: str,
) -> None:
    """Persist sequential router fallback evidence beside the role attempt."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(value, dict):
        return
    eligible = router.candidates(ROLE_ROUTER_NAMES[role_name])
    rows: list[dict[str, object]] = []
    for attempt in provider_attempts:
        row = dict(attempt)
        if selected_slot is not None and row.get("slot_number") == selected_slot.number:
            row["role_output_validation"] = role_output_validation
            row["candidate_status"] = (
                "OUTPUT_VALIDATION_FAILURE"
                if role_output_validation == "FAIL"
                else "VALID_ROLE_OUTPUT"
            )
        rows.append(row)
    attempted_slots = [int(row["slot_number"]) for row in rows if isinstance(row.get("slot_number"), int)]
    first_eligible = eligible[0].number if eligible else None
    value["provider_routing"] = {
        "router_mode": router.mode,
        "role": ROLE_ROUTER_NAMES[role_name],
        "eligible_ordered_provider_candidates": [slot.safe_identity() for slot in eligible],
        "attempted_provider_slots": attempted_slots,
        "provider_attempts": rows,
        "selected_successful_slot": selected_slot.number if selected_slot is not None else None,
        "fallback_attempted": len(attempted_slots) > 1,
        "fallback_used": selected_slot is not None and selected_slot.number != first_eligible,
    }
    value["secrets_included"] = False
    _write_json(path, value)


def _failure_class(error: Exception) -> str:
    if isinstance(error, ProviderUnavailable):
        message = str(error).casefold()
        if any(marker in message for marker in ("timeouterror", "socket.timeout", "timed out", "timeout")):
            return "TRANSPORT_TIMEOUT"
        if any(marker in message for marker in ("urlerror", "connectionerror", "connection refused", "connection failed")):
            return "TRANSPORT_ERROR"
        return "PROVIDER_ERROR"
    return "OUTPUT_VALIDATION"


def _run_role(
    router: ProviderRouter,
    *,
    role_name: str,
    payload: dict[str, object],
    max_attempts: int,
    run_path: Path,
) -> tuple[dict[str, object], ProviderSlot, int]:
    validator = ROLE_VALIDATORS[role_name]
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        content = ""
        selected_slot: ProviderSlot | None = None
        provider_attempts: tuple[dict[str, object], ...] = ()
        system = ROLE_SYSTEM_PROMPTS[role_name]
        if last_error is not None:
            system += f" Previous attempt failed validation: {last_error}. Correct only the structural issue and return JSON only." + RETRY_SAFETY_CONTRACT
        diagnostic_path: Path | None = None
        started = time.monotonic()
        try:
            user = _canonical_json(payload)
            diagnostic_path = _record_model_context_diagnostic(
                run_path,
                role_name=role_name,
                attempt=attempt,
                system=system,
                user=user,
                payload=payload,
            )
            content, slot, provider_attempts = router.complete_with_diagnostics(
                role=ROLE_ROUTER_NAMES[role_name],
                system=system,
                user=user,
            )
            selected_slot = slot
            elapsed = time.monotonic() - started
            _update_model_context_diagnostic(path=diagnostic_path, provider_elapsed_seconds=elapsed, failure_class="SUCCESS")
            try:
                artifact = validator(_parse_json(content))
            except (MultiAgentRunError, DesignValidationError) as exc:
                _update_model_context_diagnostic(path=diagnostic_path, provider_elapsed_seconds=elapsed, failure_class="OUTPUT_VALIDATION")
                raise exc
            _write_single_role_provider_diagnostic(
                diagnostic_path,
                role_name=role_name,
                router=router,
                provider_attempts=provider_attempts,
                selected_slot=selected_slot,
                role_output_validation="PASS",
            )
            return artifact, slot, attempt
        except (ProviderUnavailable, MultiAgentRunError, DesignValidationError) as exc:
            elapsed = time.monotonic() - started
            if diagnostic_path is not None:
                classification = _failure_class(exc)
                _update_model_context_diagnostic(path=diagnostic_path, provider_elapsed_seconds=elapsed, failure_class=classification)
                if isinstance(exc, ProviderUnavailable):
                    provider_attempts = tuple(getattr(exc, "provider_attempts", ()))
                _write_single_role_provider_diagnostic(
                    diagnostic_path,
                    role_name=role_name,
                    router=router,
                    provider_attempts=provider_attempts,
                    selected_slot=selected_slot,
                    role_output_validation="FAIL" if selected_slot is not None and content else "NOT_RUN",
                )
            last_error = exc
            if content:
                _record_attempt_diagnostic(
                    run_path,
                    role_name=role_name,
                    attempt=attempt,
                    content=content,
                    error=exc,
                    provider_elapsed_seconds=elapsed,
                    failure_class=_failure_class(exc),
                )
            if _failure_class(exc) == "TRANSPORT_TIMEOUT":
                break
    assert last_error is not None
    failure = MultiAgentRunError(f"{role_name} failed after {attempt} attempts: {last_error}")
    failure.attempts = attempt
    raise failure from last_error


def _run_parallel_role_candidates(
    router: ProviderRouter,
    *,
    role_name: str,
    payload: dict[str, object],
    context: dict[str, object],
    run_path: Path,
    limit: int,
) -> tuple[list[tuple[dict[str, object], ProviderSlot]], dict[str, object]]:
    """Run one role on independent providers and retain valid candidates.

    This is candidate generation only. Every output still passes the same role
    validator and later evidence validation. If all parallel candidates fail,
    the caller falls back to the normal bounded retry path.
    """
    validator = ROLE_VALIDATORS[role_name]
    system = ROLE_SYSTEM_PROMPTS[role_name]
    user = _canonical_json(payload)
    started = time.monotonic()
    diagnostic_path = _record_model_context_diagnostic(
        run_path,
        role_name=role_name,
        attempt=1,
        system=system,
        user=user,
        payload=payload,
        diagnostic_name=f"{role_name}-parallel.json",
    )
    eligible_candidates = router.candidates(ROLE_ROUTER_NAMES[role_name])
    completions, provider_attempts = router.complete_parallel_with_diagnostics(
        role=ROLE_ROUTER_NAMES[role_name],
        system=system,
        user=user,
        limit=limit,
    )
    valid: list[tuple[dict[str, object], ProviderSlot]] = []
    for content, slot in completions:
        diagnostic = next(
            item for item in provider_attempts if item.get("slot_number") == slot.number
        )
        diagnostic["role_output_validation"] = "NOT_RUN"
        diagnostic["evidence_validation"] = "NOT_RUN"
        diagnostic["secret_check"] = "FAIL" if slot.api_key and slot.api_key in content else "PASS"
        diagnostic["candidate_status"] = "OUTPUT_VALIDATION_FAILURE"
        try:
            artifact = validator(_parse_json(content))
        except (MultiAgentRunError, DesignValidationError) as exc:
            diagnostic["role_output_validation"] = "FAIL"
            secret_leaked, validation_error = _record_parallel_candidate_failure(
                run_path,
                role_name=role_name,
                slot=slot,
                content=content,
                error=exc,
            )
            diagnostic["response_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            diagnostic["response_characters"] = len(content)
            diagnostic["validation_error_type"] = type(exc).__name__
            diagnostic["validation_error"] = validation_error
            diagnostic["secret_check"] = "FAIL" if secret_leaked else "PASS"
            if secret_leaked:
                diagnostic["candidate_status"] = "SECRET_REJECTION"
            continue
        diagnostic["role_output_validation"] = "PASS"
        secret_leaked = bool(slot.api_key and (slot.api_key in content or slot.api_key in _canonical_json(artifact)))
        diagnostic["secret_check"] = "FAIL" if secret_leaked else "PASS"
        try:
            _validate_artifact_evidence(role_name, artifact, context)
            diagnostic["evidence_validation"] = "PASS"
        except MultiAgentRunError:
            diagnostic["evidence_validation"] = "FAIL"
        if secret_leaked:
            diagnostic["candidate_status"] = "SECRET_REJECTION"
            continue
        if diagnostic["evidence_validation"] == "FAIL":
            diagnostic["candidate_status"] = "EVIDENCE_VALIDATION_FAILURE"
            continue
        diagnostic["candidate_status"] = "VALID_CANDIDATE"
        valid.append((artifact, slot))

    parallel_runtime: dict[str, object] = {
        "router_mode": router.mode,
        "configured_parallelism": router.parallelism,
        "parallel_role_scope": sorted(router.parallel_roles),
        "eligible_ordered_provider_candidates": [slot.safe_identity() for slot in eligible_candidates],
        "requested_successful_candidate_count": min(limit, len(eligible_candidates)),
        "attempted_provider_slots": [int(item["slot_number"]) for item in provider_attempts],
        "accepted_provider_slots": [slot.number for _artifact, slot in valid],
    }
    for diagnostic in provider_attempts:
        if diagnostic.get("transport_status") == "FAILURE":
            diagnostic["role_output_validation"] = "NOT_RUN"
            diagnostic["evidence_validation"] = "NOT_RUN"
            diagnostic["secret_check"] = "NOT_RUN"
            diagnostic["candidate_status"] = (
                "TRANSPORT_FAILURE"
                if diagnostic.get("failure_class") == "TRANSPORT_FAILURE"
                else "PROVIDER_ERROR"
            )
    _write_parallel_stage_diagnostic(
        diagnostic_path,
        parallel_runtime=parallel_runtime,
        provider_attempts=provider_attempts,
        provider_elapsed_seconds=time.monotonic() - started,
        failure_class=(
            "SUCCESS" if valid
            else "CANDIDATE_VALIDATION_FAILURE" if any(item.get("transport_status") == "SUCCESS" for item in provider_attempts)
            else "PROVIDER_TRANSPORT_FAILURE" if provider_attempts
            else "NO_PROVIDER_ATTEMPTS"
        ),
    )
    return valid, parallel_runtime


def _write_parallel_stage_diagnostic(
    path: Path,
    *,
    parallel_runtime: dict[str, object],
    provider_attempts: tuple[dict[str, object], ...],
    provider_elapsed_seconds: float,
    failure_class: str,
) -> None:
    try:
        diagnostic = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        diagnostic = {}
    if not isinstance(diagnostic, dict):
        diagnostic = {}
    diagnostic.update({
        "provider_elapsed_seconds": round(provider_elapsed_seconds, 3),
        "failure_class": failure_class,
        "parallel_runtime": parallel_runtime,
        "provider_attempts": list(provider_attempts),
        "secrets_included": False,
    })
    _write_json(path, diagnostic)


def _new_run_id() -> str:
    return f"zen-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:10]}"


def run_multi_agent_design(
    router: ProviderRouter,
    *,
    request: str,
    repo_root: Path,
    run_id: str | None = None,
    restart_run: bool = False,
    max_role_attempts: int = MAX_ROLE_ATTEMPTS,
) -> MultiAgentRun:
    """Execute or safely resume the four-role local design pipeline.

    Completed artifacts are never overwritten during a normal resume.  Passing
    ``restart_run=True`` is the explicit opt-in for regenerating an existing
    run id's checkpoints.
    """
    if not request.strip():
        raise ValueError("A non-empty user request is required.")
    if not 1 <= max_role_attempts <= MAX_ROLE_ATTEMPTS:
        raise ValueError(f"max_role_attempts must be from 1 to {MAX_ROLE_ATTEMPTS}.")

    run_id = run_id or _new_run_id()
    path = _run_path(run_id)
    path.mkdir(parents=True, exist_ok=True)
    if restart_run:
        _archive_for_restart(path)
    context = build_designer_context(repo_root)
    context_hash = _sha256(context)
    request_hash = _sha256({"user_request": request})
    final_path = path / "final_design.json"
    resume_point = find_resume_point(run_id, list(ROLE_SEQUENCE))
    previous_state = _read_run_state(path)
    if not restart_run and previous_state:
        if previous_state.get("REQUEST_HASH") not in (None, request_hash):
            raise MultiAgentRunError("Existing run id belongs to a different request; use a new run id or --restart-run.")
        if previous_state.get("CONTEXT_HASH") not in (None, context_hash) and resume_point is not None:
            raise MultiAgentRunError("Designer Context changed since this run started; use --restart-run to avoid mixing checkpoints.")
    if not restart_run and resume_point is None:
        final_design = _load_valid_final(final_path)
        if final_design is not None:
            return MultiAgentRun(run_id, context_hash, final_design, path, resumed_from=None)
        # A finalizer checkpoint without a valid final artifact is incomplete.
        resume_point = "finalizer"

    state: dict[str, object] = {
        "schema": RUN_SCHEMA,
        "RUN_ID": run_id,
        "GIT_HEAD": _git_head(repo_root),
        "CONTEXT_HASH": context_hash,
        "REQUEST_HASH": request_hash,
        "HOST_OS": platform.system(),
        "ROLE_EXECUTION_ORDER": list(ROLE_SEQUENCE),
        "role_execution": [] if restart_run else list(previous_state.get("role_execution", [])),
        "LOCAL_MODEL_USED": "NO",
        "CLOUD_REQUIRED": "NO",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_run_state(path, state)
    completed = {} if restart_run else _read_completed_artifacts(run_id)
    candidate_sets = {} if restart_run else _read_candidate_sets(run_id)
    started_from = ROLE_SEQUENCE[0] if restart_run else resume_point
    active_role = started_from or ROLE_SEQUENCE[0]

    try:
        for role_name in ROLE_SEQUENCE:
            if role_name in completed and not restart_run:
                continue
            active_role = role_name
            payload = _role_context(
                role_name,
                request=request,
                context=context,
                completed=completed,
                candidate_sets=candidate_sets,
            )
            parallel_results: list[tuple[dict[str, object], ProviderSlot]] = []
            parallel_runtime: dict[str, object] | None = None
            parallel_limit = router.parallel_limit(ROLE_ROUTER_NAMES[role_name])
            if role_name in {"lighting_designer", "critic"} and parallel_limit > 1:
                parallel_results, parallel_runtime = _run_parallel_role_candidates(
                    router,
                    role_name=role_name,
                    payload=payload,
                    context=context,
                    run_path=path,
                    limit=parallel_limit,
                )

            validated_candidates: list[tuple[dict[str, object], ProviderSlot]] = list(parallel_results)

            if validated_candidates:
                artifact, slot = validated_candidates[0]
                attempts = 1
                candidate_sets[role_name] = [candidate for candidate, _ in validated_candidates]
            else:
                artifact, slot, attempts = _run_role(
                    router,
                    role_name=role_name,
                    payload=payload,
                    max_attempts=max_role_attempts,
                    run_path=path,
                )
                artifact = _validate_artifact_evidence(role_name, artifact, context)
                if slot.api_key and slot.api_key in _canonical_json(artifact):
                    raise MultiAgentRunError("Role artifact contained a provider secret and was rejected.")
                validated_candidates = [(artifact, slot)]
                if role_name in {"lighting_designer", "critic"}:
                    candidate_sets[role_name] = [artifact]

            envelope = {
                "schema": STEP_SCHEMA,
                "role": role_name,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "attempts": attempts,
                "provider": slot.safe_identity(),
                "local_model": _is_local(slot),
                "artifact_hash": _sha256(artifact),
                "artifact": artifact,
                "candidate_artifacts": [
                    {
                        "provider": candidate_slot.safe_identity(),
                        "artifact_hash": _sha256(candidate),
                        "artifact": candidate,
                    }
                    for candidate, candidate_slot in validated_candidates
                ] if role_name in {"lighting_designer", "critic"} else [],
                "parallel_runtime": parallel_runtime,
                "CODEX_ARTISTIC_INTERVENTION": "NONE",
            }
            write_step_artifact(run_id, role_name, envelope)
            completed[role_name] = artifact
            state["LOCAL_MODEL_USED"] = "YES" if (
                state["LOCAL_MODEL_USED"] == "YES"
                or any(_is_local(candidate_slot) for _, candidate_slot in validated_candidates)
            ) else "NO"
            state["role_execution"] = list(state.get("role_execution", [])) + [{
                "role": role_name,
                "provider": slot.safe_identity(),
                "providers": [candidate_slot.safe_identity() for _, candidate_slot in validated_candidates],
                "parallel_candidates": len(validated_candidates),
                "parallel_runtime": parallel_runtime,
                "attempts": attempts,
                "artifact_hash": envelope["artifact_hash"],
            }]
            _write_run_state(path, state)

        final_design = completed["finalizer"]
        validate_design_output(final_design)
        _write_json(final_path, final_design)
        state |= {
            "status": "COMPLETE",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "FINAL_OUTPUT_HASH": _sha256(final_design),
            "CODEX_ARTISTIC_INTERVENTION": "NONE",
        }
        _write_run_state(path, state)
        return MultiAgentRun(run_id, context_hash, final_design, path, resumed_from=started_from)
    except (MultiAgentRunError, DesignValidationError, KeyError) as exc:
        state |= {"status": "FAILED", "failed_at": datetime.now(timezone.utc).isoformat()}
        _write_run_state(path, state)
        _record_failure(path, role_name=active_role, attempts=getattr(exc, "attempts", max_role_attempts), error=exc)
        raise MultiAgentRunError(str(exc)) from exc
