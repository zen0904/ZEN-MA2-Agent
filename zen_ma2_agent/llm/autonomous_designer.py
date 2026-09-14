"""Actual-provider, structured-only autonomous Designer boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..knowledge_store import build_evidence_ledger, load_canonical_store, project_records, retrieve_records
from ..portable import portable_state_path
from .router import ProviderRouter, ProviderSlot


SCHEMA = "zen.autonomous_design.v0.1"
FORBIDDEN_KEYS = {"ma2_command", "ma2_commands", "telnet", "lua", "shell", "command", "commands", "raw_console_text"}


class DesignValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AutonomousDesignRun:
    run_id: str
    provider_slot: int
    provider_type: str
    model: str
    context_hash: str
    output_hash: str
    output: dict[str, object]


def _read_json(path: Path, limit: int = 30000) -> object:
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text[:limit])
    except (OSError, json.JSONDecodeError):
        return None


def _compact(value: object, limit: int = 6000) -> object:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(encoded) <= limit:
        return value
    return {"truncated": True, "sha256": hashlib.sha256(encoded.encode()).hexdigest(), "preview": encoded[:limit]}


def build_designer_context(repo_root: Path) -> dict[str, object]:
    """Bounded, provenance-preserving context; never a repository dump."""
    candidates = {
        "project_control": repo_root / "data" / "zen_project_control.json",
        "external_knowledge_pack": repo_root / "data" / "external_lighting_knowledge_pack_001.json",
        "external_source_registry": repo_root / "data" / "external_lighting_knowledge_source_registry_001.json",
        "current_show_visual_relationships": repo_root / "data" / "current_show_visual_relationships_001.json",
        "show_bound_color_evidence": repo_root / "data" / "zen_show_bound_color_preset_applicability_001.json",
        "show_bound_fixture_capability": repo_root / "data" / "ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json",
        "previous_sheesh_test_plan": repo_root / "data" / "zen_real_ma2_test_show_sheesh_001_plan.json",
    }
    documents = {
        "product_constitution": repo_root / "docs" / "ZEN_PRODUCT_CONSTITUTION.md",
        "workflow_contract": repo_root / "docs" / "ZEN_WORKFLOW_CONTRACT.md",
        "ma2_programming_intelligence": repo_root / "docs" / "MA2_PROGRAMMING_INTELLIGENCE.md",
    }
    data = {name: _compact(value) for name, path in candidates.items() if (value := _read_json(path)) is not None}
    docs = {name: path.read_text(encoding="utf-8")[:4500] for name, path in documents.items() if path.is_file()}
    external_knowledge_context = {"schema": "zen.knowledge_retrieval_context.v0.1", "runtime_mode": "SHADOW_ONLY", "records": [], "knowledge_refs": [], "topic_diversity": []}
    evidence_ledger = {"schema": "zen.evidence_ledger.v0.1", "entries": [], "available_verified_facts": []}
    canonical_knowledge_records: list[dict[str, object]] = []
    source_registry_for_context = data.get("external_source_registry", {})
    try:
        store = load_canonical_store(candidates["external_source_registry"], candidates["external_knowledge_pack"])
        # Keep the registry structurally complete for provenance validation; it
        # is compact metadata, not an unbounded source dump.
        source_registry_for_context = store["source_registry"]
        selected = retrieve_records(store["records"], role="LIGHTING_DESIGNER", request="lighting design", limit=12, max_records_per_topic=2)
        external_knowledge_context |= {
            "records": project_records(selected),
            "knowledge_refs": [item["record_id"] for item in selected],
            "topic_diversity": sorted({item["topic"] for item in selected}),
            "source_registry_ref": store["source_registry_ref"],
        }
        evidence_ledger = build_evidence_ledger(knowledge=store["records"]) | {"available_verified_facts": []}
        canonical_knowledge_records = list(store["records"])
    except (OSError, ValueError, json.JSONDecodeError):
        # The designer remains usable for diagnostics when the optional pack is unavailable.
        pass
    context = {
        "context_schema": "zen.designer_context.v0.1",
        "evidence_boundary": {
            "eligible": "verified/accepted evidence may inform a contextual design decision",
            "context_dependent": "may be considered only with its limitation retained",
            "not_authoritative": "unreviewed, rejected, or unavailable evidence cannot become a design rule",
        },
        "hard_constraints": [
            "Output typed JSON only; never console, telnet, Lua, shell, or MA2 command text.",
            "Fixture capability is not permanent artistic role identity.",
            "Do not fabricate unavailable song, venue, performance, or spatial information.",
            "Production Designer remains unchanged; this output is experimental until explicit approval.",
            "Fixture 9999 and protected existing objects are excluded.",
            "professional_lighting_design_knowledge is SHADOW_ONLY: reasoning and review context, never an action recipe or production rule.",
        ],
        "evidence_ledger": evidence_ledger,
        "canonical_knowledge_records": canonical_knowledge_records,
        "categories": {
            "fixture_technical_capability": {
                "fixture_type_binding": data.get("show_bound_fixture_capability", {}),
                "color_preset_evidence": data.get("show_bound_color_evidence", {}),
            },
            "rig_spatial_visual_affordance": data.get("current_show_visual_relationships", {}),
            "professional_lighting_design_knowledge": external_knowledge_context,
            "source_provenance": source_registry_for_context,
            "project_constraints": data.get("project_control", {}),
            "prior_case_artifacts": {"previous_sheesh_test_plan": data.get("previous_sheesh_test_plan", {})},
            "operator_contract": docs,
        },
    }
    return context


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(str(key).casefold() in FORBIDDEN_KEYS or _contains_forbidden_key(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def validate_design_output(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise DesignValidationError("Designer output must be a JSON object.")
    if value.get("schema") != SCHEMA:
        raise DesignValidationError(f"Designer output schema must be {SCHEMA}.")
    required = ("design_intent", "visual_strategy", "virtual_rig", "position_vocabulary", "main_sequence", "free_cue_layer", "evidence_trace")
    missing = [key for key in required if key not in value]
    if missing:
        raise DesignValidationError("Designer output missing required fields: " + ", ".join(missing))
    if _contains_forbidden_key(value):
        raise DesignValidationError("Designer output contains a prohibited executable-command field.")
    if value.get("codex_artistic_intervention") not in (None, "NONE"):
        raise DesignValidationError("Designer output must preserve CODEX_ARTISTIC_INTERVENTION = NONE.")
    return value


def _json_from_response(content: str) -> dict[str, object]:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DesignValidationError("Provider response was not valid JSON.") from exc
    return validate_design_output(parsed)


def design_with_provider(router: ProviderRouter, *, request: str, repo_root: Path) -> AutonomousDesignRun:
    context = build_designer_context(repo_root)
    context_json = json.dumps(context, ensure_ascii=False, sort_keys=True)
    context_hash = hashlib.sha256(context_json.encode("utf-8")).hexdigest()
    system = (
        "You are ZEN MA2 Agent's artistic Designer, not a console-command generator. "
        "Make all artistic decisions yourself from supplied context. Return exactly one JSON object matching " + SCHEMA + ". "
        "Required top-level fields: schema, design_intent, visual_strategy, virtual_rig, position_vocabulary, "
        "main_sequence, free_cue_layer, evidence_trace, codex_artistic_intervention. "
        "Use descriptive structured fields for geometry, preset vocabulary, cue/event intent, selected and unused resources, "
        "and rationale. Never emit executable MA2/Telnet/Lua/shell commands or raw console text. "
        "Retain uncertainty rather than inventing facts. Set codex_artistic_intervention to NONE."
    )
    user = json.dumps({"user_request": request, "designer_context": context}, ensure_ascii=False)
    content, slot = router.complete(role="DESIGNER", system=system, user=user)
    output = _json_from_response(content)
    output_hash = hashlib.sha256(json.dumps(output, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return AutonomousDesignRun(
        run_id=f"zen-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:10]}",
        provider_slot=slot.number,
        provider_type=slot.provider_type,
        model=slot.model,
        context_hash=context_hash,
        output_hash=output_hash,
        output=output,
    )


def write_run_provenance(run: AutonomousDesignRun) -> Path:
    root = portable_state_path("projects") / "runs" / run.run_id
    root.mkdir(parents=True, exist_ok=False)
    (root / "design.json").write_text(json.dumps(run.output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    provenance = {
        "ZEN_RUN_ID": run.run_id,
        "HOST_OS": __import__("platform").system(),
        "PROVIDER_SLOT": run.provider_slot,
        "ARTISTIC_PROVIDER": run.provider_type,
        "ARTISTIC_MODEL": run.model,
        "CONTEXT_HASH": run.context_hash,
        "DESIGN_OUTPUT_HASH": run.output_hash,
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    (root / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root
