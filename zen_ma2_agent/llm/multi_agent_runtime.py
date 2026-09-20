"""Sequential, portable Local Multi-Agent runtime.

This module orchestrates bounded, structured LLM roles only.  It deliberately
does not import MA2 transport, Builder, or Resolver code: a validated final
design remains an experimental artifact until a separately approved path can
resolve it.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import re
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
from .live_show_snapshot import (
    CurrentShowSnapshotInput,
    LiveShowSnapshotError,
    normalize_current_show_snapshot,
)


ROLE_SEQUENCE = ("researcher", "lighting_designer", "critic", "finalizer")
LIVE_SHOW_ROLE_SEQUENCE = (
    "researcher", "rig_designer", "position_designer", "lighting_designer", "critic", "finalizer",
)
MAX_ROLE_ATTEMPTS = 3
RUN_SCHEMA = "zen.multi_agent_run.v0.1"
STEP_SCHEMA = "zen.multi_agent_step.v0.1"
FAILURE_SCHEMA = "zen.multi_agent_failure.v0.1"
ATTEMPT_SCHEMA = "zen.multi_agent_attempt_diagnostic.v0.1"
PARALLEL_CANDIDATE_ATTEMPT_SCHEMA = "zen.multi_agent_parallel_candidate_diagnostic.v0.1"
RIG_DESIGN_SCHEMA = "zen.multi_agent_rig_design.v0.1"
POSITION_DESIGN_SCHEMA = "zen.multi_agent_position_design.v0.1"
RIG_DESIGN_REQUIRED_FIELDS = (
    "show_fingerprint",
    "spatial_strategy",
    "resource_assignments",
    "spatial_relationships",
    "constraints",
    "uncertainties",
    "codex_artistic_intervention",
)
POSITION_DESIGN_REQUIRED_FIELDS = (
    "show_fingerprint",
    "coordinate_system",
    "spatial_groups",
    "placements",
    "constraints",
    "uncertainties",
    "codex_artistic_intervention",
)


class MultiAgentRunError(RuntimeError):
    """Raised when a bounded role cannot produce a valid checkpoint."""


class EvidenceValidationError(MultiAgentRunError):
    """Raised when a structurally valid artifact violates canonical evidence."""


class ResearchEvidenceRefsValidationError(EvidenceValidationError):
    """Researcher evidence_refs do not resolve through the canonical ledger."""


class ResearchSourceContractError(EvidenceValidationError):
    """Researcher sources violate the backend-provided exact-pair contract."""

    def __init__(self, message: str, classification: str) -> None:
        super().__init__(message)
        self.classification = classification


class ResearchCanonicalSourceResolutionError(EvidenceValidationError):
    """Canonical source resolver rejected a structurally allowed source pair."""

    def __init__(self, message: str, classification: str = "CANONICAL_SOURCE_RESOLUTION_ERROR") -> None:
        super().__init__(message)
        self.classification = classification


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


def _empty_structural_normalization() -> dict[str, object]:
    return {"applied": False, "fields_added": []}


def normalize_role_envelope(
    role_name: str,
    value: object,
) -> tuple[object, dict[str, object]]:
    """Add only absent spatial-role schema metadata when the envelope is complete.

    This is deliberately narrower than validation.  It does not repair a
    malformed schema or synthesize any spatial/artistic field, and the normal
    role validator remains the authority after this projection.
    """
    contracts = {
        "rig_designer": (RIG_DESIGN_SCHEMA, RIG_DESIGN_REQUIRED_FIELDS),
        "position_designer": (POSITION_DESIGN_SCHEMA, POSITION_DESIGN_REQUIRED_FIELDS),
    }
    contract = contracts.get(role_name)
    audit = _empty_structural_normalization()
    if contract is None or not isinstance(value, dict) or "schema" in value:
        return value, audit
    schema, required = contract
    if any(field not in value for field in required):
        return value, audit
    if value.get("codex_artistic_intervention") != "NONE":
        return value, audit
    normalized = {"schema": schema, **value}
    return normalized, {
        "applied": True,
        "fields_added": ["schema"],
        "reason": "MISSING_ROLE_SCHEMA_METADATA",
        "schema_value": schema,
    }


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


_SPATIAL_FORBIDDEN_FIELDS = {
    "patch", "address", "dmx_address", "fixture_type", "fixture_type_id",
    "fixture_id_change", "fixture_type_change", "patch_change", "address_change",
    "new_fixture", "new_fixtures", "fixture_mutations", "identity_mutations",
}
_CONSOLE_COMMAND_RE = re.compile(
    r"^\s*(?:store|delete|assign|select|at|go|off|on|clearall|move3d|lua)\b"
    r"|^\s*fixture\s+\d+(?:\.\d+)?\s+(?:at|move3d|store|delete|assign)\b",
    re.IGNORECASE,
)


def _contains_spatial_command_or_mutation(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold() in _SPATIAL_FORBIDDEN_FIELDS
            or str(key).casefold() in FORBIDDEN_KEYS
            or _contains_spatial_command_or_mutation(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_spatial_command_or_mutation(child) for child in value)
    if isinstance(value, str):
        return value.lstrip().startswith("```") or bool(_CONSOLE_COMMAND_RE.match(value))
    return False


def _snapshot_identity_sets(snapshot: dict[str, object]) -> tuple[set[int], set[tuple[int, int]]]:
    fixtures = snapshot.get("fixture_inventory", [])
    fixture_ids = {
        int(item["fixture_id"])
        for item in fixtures
        if isinstance(item, dict) and isinstance(item.get("fixture_id"), int)
    }
    subfixture_refs = {
        (int(item["fixture_id"]), int(geometry["subfixture_id"]))
        for item in fixtures if isinstance(item, dict)
        for geometry in item.get("geometry", []) if isinstance(geometry, dict)
        and isinstance(item.get("fixture_id"), int)
        and isinstance(geometry.get("subfixture_id"), int)
    }
    return fixture_ids, subfixture_refs


def _validate_embedded_fixture_refs(
    value: object,
    *,
    fixture_ids: set[int],
    subfixture_refs: set[tuple[int, int]],
) -> None:
    if isinstance(value, dict):
        fixture_id = value.get("fixture_id")
        if fixture_id is not None:
            if isinstance(fixture_id, bool) or not isinstance(fixture_id, int) or fixture_id not in fixture_ids:
                raise MultiAgentRunError("Spatial artifact references an unknown fixture identity.")
            if fixture_id == 9999:
                raise MultiAgentRunError("Fixture 9999 is protected and unavailable for artistic use.")
            subfixture_id = value.get("subfixture_id")
            if subfixture_id is not None and (
                isinstance(subfixture_id, bool)
                or not isinstance(subfixture_id, int)
                or (fixture_id, subfixture_id) not in subfixture_refs
            ):
                raise MultiAgentRunError("Spatial artifact references an unknown fixture/subfixture identity.")
        for key in ("fixture_ids", "resource_ids"):
            rows = value.get(key)
            if rows is not None:
                if not isinstance(rows, list):
                    raise MultiAgentRunError(f"Spatial artifact {key} must be an array.")
                for item in rows:
                    if isinstance(item, bool) or not isinstance(item, int) or item not in fixture_ids:
                        raise MultiAgentRunError("Spatial artifact references an unknown fixture identity.")
                    if item == 9999:
                        raise MultiAgentRunError("Fixture 9999 is protected and unavailable for artistic use.")
        for child in value.values():
            _validate_embedded_fixture_refs(child, fixture_ids=fixture_ids, subfixture_refs=subfixture_refs)
    elif isinstance(value, list):
        for child in value:
            _validate_embedded_fixture_refs(child, fixture_ids=fixture_ids, subfixture_refs=subfixture_refs)


def validate_rig_design_artifact(value: object, snapshot: dict[str, object]) -> dict[str, object]:
    artifact = _validate_object(
        value,
        schema=RIG_DESIGN_SCHEMA,
        required=RIG_DESIGN_REQUIRED_FIELDS,
    )
    if artifact.get("codex_artistic_intervention") != "NONE":
        raise MultiAgentRunError("Rig design must set codex_artistic_intervention to NONE.")
    if artifact.get("show_fingerprint") != snapshot.get("show_fingerprint"):
        raise MultiAgentRunError("Rig design Show fingerprint does not match the live snapshot.")
    if not isinstance(artifact.get("spatial_strategy"), (str, dict)) or not artifact.get("spatial_strategy"):
        raise MultiAgentRunError("Rig design spatial_strategy must be a non-empty string or object.")
    for field in ("resource_assignments", "spatial_relationships", "constraints", "uncertainties"):
        if not isinstance(artifact.get(field), list):
            raise MultiAgentRunError(f"Rig design {field} must be an array.")
    if _contains_spatial_command_or_mutation(artifact):
        raise MultiAgentRunError("Rig design contains a prohibited command or Show identity/patch mutation field.")
    fixture_ids, subfixture_refs = _snapshot_identity_sets(snapshot)
    for assignment in artifact["resource_assignments"]:
        if not isinstance(assignment, dict) or not isinstance(assignment.get("resource_refs"), list):
            raise MultiAgentRunError("Each rig resource assignment must contain a resource_refs array.")
        for ref in assignment["resource_refs"]:
            if not isinstance(ref, dict) or "fixture_id" not in ref:
                raise MultiAgentRunError("Rig resource_refs must be fixture identity objects.")
            _validate_embedded_fixture_refs(ref, fixture_ids=fixture_ids, subfixture_refs=subfixture_refs)
    _validate_embedded_fixture_refs(artifact["spatial_relationships"], fixture_ids=fixture_ids, subfixture_refs=subfixture_refs)
    return artifact


def validate_position_design_artifact(value: object, snapshot: dict[str, object]) -> dict[str, object]:
    artifact = _validate_object(
        value,
        schema=POSITION_DESIGN_SCHEMA,
        required=POSITION_DESIGN_REQUIRED_FIELDS,
    )
    if artifact.get("codex_artistic_intervention") != "NONE":
        raise MultiAgentRunError("Position design must set codex_artistic_intervention to NONE.")
    fingerprint = snapshot.get("show_fingerprint")
    if artifact.get("show_fingerprint") != fingerprint:
        raise MultiAgentRunError("Position design Show fingerprint does not match the live snapshot.")
    if not isinstance(artifact.get("coordinate_system"), dict):
        raise MultiAgentRunError("Position design coordinate_system must be an object.")
    if artifact["coordinate_system"] != snapshot.get("coordinate_system"):
        raise MultiAgentRunError("Position design coordinate_system must exactly match the authoritative current Show metadata.")
    for field in ("spatial_groups", "placements", "constraints", "uncertainties"):
        if not isinstance(artifact.get(field), list):
            raise MultiAgentRunError(f"Position design {field} must be an array.")
    if _contains_spatial_command_or_mutation(artifact):
        raise MultiAgentRunError("Position design contains a prohibited command or Show identity/patch mutation field.")
    fixture_ids, subfixture_refs = _snapshot_identity_sets(snapshot)
    _validate_embedded_fixture_refs(artifact["spatial_groups"], fixture_ids=fixture_ids, subfixture_refs=subfixture_refs)
    seen: set[tuple[int, int]] = set()
    for placement in artifact["placements"]:
        if not isinstance(placement, dict):
            raise MultiAgentRunError("Position placements must be objects.")
        fixture_id = placement.get("fixture_id")
        subfixture_id = placement.get("subfixture_id")
        if (
            isinstance(fixture_id, bool) or not isinstance(fixture_id, int)
            or isinstance(subfixture_id, bool) or not isinstance(subfixture_id, int)
        ):
            raise MultiAgentRunError("Each placement must identify a fixture_id and subfixture_id.")
        if fixture_id == 9999:
            raise MultiAgentRunError("Fixture 9999 is protected and unavailable for placement.")
        ref = (fixture_id, subfixture_id)
        if ref not in subfixture_refs:
            raise MultiAgentRunError("Position placement references an unknown geometry-bearing fixture/subfixture.")
        if ref in seen:
            raise MultiAgentRunError("Position design contains duplicate placement references.")
        seen.add(ref)
        if placement.get("show_fingerprint") != fingerprint:
            raise MultiAgentRunError("Every placement must carry the matching current Show fingerprint.")
        xyz = placement.get("xyz")
        if not isinstance(xyz, dict):
            raise MultiAgentRunError("Every placement requires an XYZ object.")
        for axis in ("x", "y", "z"):
            number = xyz.get(axis)
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(float(number)):
                raise MultiAgentRunError(f"Placement XYZ.{axis} must be finite numeric data.")
        if "rotation" in placement:
            rotation = placement["rotation"]
            if not isinstance(rotation, dict):
                raise MultiAgentRunError("Placement rotation must be an object when present.")
            for axis in ("x", "y", "z"):
                number = rotation.get(axis)
                if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(float(number)):
                    raise MultiAgentRunError(f"Placement rotation.{axis} must be finite numeric data.")
    return artifact


def build_position_context(snapshot: dict[str, object]) -> dict[str, object]:
    """Build deterministic, placement-only context from a validated live snapshot.

    This is a model-facing projection, not a new source of Show truth. The
    normalized snapshot remains the backend validator's authority.
    """
    fingerprint = snapshot.get("show_fingerprint")
    coordinate_system = snapshot.get("coordinate_system")
    inventory = snapshot.get("fixture_inventory")
    if not isinstance(fingerprint, str) or not isinstance(coordinate_system, dict) or not isinstance(inventory, list):
        raise MultiAgentRunError("POSITION_DESIGNER requires a normalized current Show snapshot.")

    geometry_resources: list[dict[str, object]] = []
    protected_refs: list[dict[str, object]] = []
    for fixture in inventory:
        if not isinstance(fixture, dict):
            continue
        fixture_id = fixture.get("fixture_id")
        geometry = fixture.get("geometry", [])
        if not isinstance(geometry, list):
            continue
        for row in geometry:
            if not isinstance(row, dict):
                continue
            subfixture_id = row.get("subfixture_id")
            ref = {"fixture_id": fixture_id, "subfixture_id": subfixture_id}
            if fixture_id == 9999 or fixture.get("availability") == "PROTECTED_UNAVAILABLE":
                protected_refs.append(ref)
                continue
            resource: dict[str, object] = {
                **ref,
                "current_xyz": row.get("xyz"),
                "current_rotation": row.get("rotation"),
                "availability": fixture.get("availability", "UNKNOWN"),
            }
            geometry_resources.append(resource)

    geometry_resources.sort(key=lambda item: (int(item["fixture_id"]), int(item["subfixture_id"])))
    protected_refs.sort(key=lambda item: (int(item["fixture_id"]), int(item["subfixture_id"])))
    allowed_placement_refs = [
        {"fixture_id": item["fixture_id"], "subfixture_id": item["subfixture_id"]}
        for item in geometry_resources
    ]
    limitations = snapshot.get("limitations", [])
    return {
        "schema": "zen.position_context.v0.1",
        "show_fingerprint": fingerprint,
        "coordinate_system": dict(coordinate_system),
        "geometry_resources": geometry_resources,
        "allowed_placement_refs": allowed_placement_refs,
        "protected_refs": protected_refs,
        "limitations": list(limitations) if isinstance(limitations, list) else [],
    }


def _position_retry_contract(error: Exception) -> str:
    """Return a structure-only retry note for known Position contract failures."""
    message = str(error).casefold()
    if "not valid json" in message:
        instruction = "Return exactly one complete JSON object only. No Markdown, comments, prefix, suffix, or explanation."
    elif "coordinate_system must be an object" in message:
        instruction = "coordinate_system must be the exact object supplied in position_context.coordinate_system. Do not replace it with a string."
    elif "missing required fields" in message:
        instruction = "Return every required top-level field. Empty arrays are valid where appropriate; never omit required fields."
    else:
        return ""
    return (
        " POSITION_DESIGNER STRUCTURAL RETRY: " + instruction +
        " Preserve valid XYZ/artistic choices; do not alter them merely to satisfy structure."
    )


def validate_final_spatial_consistency(
    final_artifact: dict[str, object],
    position_artifact: dict[str, object],
    show_fingerprint: str,
) -> None:
    expected_reference = {
        "show_fingerprint": show_fingerprint,
        "position_artifact_sha256": _sha256(position_artifact),
    }
    if final_artifact.get("position_design_reference") != expected_reference:
        raise MultiAgentRunError("Finalizer position_design_reference does not identify the validated upstream Position Designer artifact.")
    expected = {
        (item["fixture_id"], item["subfixture_id"]): item["xyz"]
        for item in position_artifact.get("placements", []) if isinstance(item, dict)
    }

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if "fixture_id" in value and "subfixture_id" in value and "xyz" in value:
                key = (value.get("fixture_id"), value.get("subfixture_id"))
                if key not in expected or value.get("xyz") != expected[key]:
                    raise MultiAgentRunError("Final design geometry contradicts the upstream Position Designer artifact.")
                if value.get("show_fingerprint", show_fingerprint) != show_fingerprint:
                    raise MultiAgentRunError("Final design geometry references a different Show fingerprint.")
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(final_artifact.get("virtual_rig"))
    visit(final_artifact.get("position_vocabulary"))


ROLE_VALIDATORS: dict[str, Callable[[object], dict[str, object]]] = {
    "researcher": validate_research_artifact,
    "lighting_designer": validate_designer_artifact,
    "critic": validate_critic_artifact,
    "finalizer": validate_design_output,
}


ROLE_ROUTER_NAMES = {
    "researcher": "RESEARCHER",
    "rig_designer": "LIGHTING_DESIGNER",
    "position_designer": "LIGHTING_DESIGNER",
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

RESEARCH_SOURCE_RETRY_CONTRACT = (
    " Your previous sources value was invalid. Copy source identity objects exactly from research_context.allowed_source_refs, "
    "or return an empty sources array. Do not use evidence_refs, summaries, titles, URLs, or prose as source identities. "
    "Do not change valid observations merely to satisfy this repair."
)


ROLE_SYSTEM_PROMPTS = {
    "researcher": (
        "ROLE: RESEARCHER. Build a compact, provenance-bearing Evidence Pack from only the supplied request and context. "
        "Do not fabricate live research or sources. When no retrieved source is supplied, use research_status OFFLINE_CACHED_CONTEXT. "
        "Return exactly one JSON object. Its first key must be \"schema\" with exact value \"zen.multi_agent_research.v0.1\". "
        "Required fields are research_status, subject, sources, "
        "transferable_design_observations, constraints, uncertainties, codex_artistic_intervention. "
        "SOURCES CONTRACT: sources is an array. Every item must be copied exactly from research_context.allowed_source_refs as an object containing only source_id and record_id. "
        "Do not transform, summarize, reconstruct, or manufacture source identities or metadata. Never put evidence_ref values, summaries, titles, URLs, or prose in sources. "
        "If no allowed canonical source is needed, return \"sources\": []. "
        "EVIDENCE CONTRACT: evidence_refs is separate from sources. If used, copy exact evidence_ref strings from evidence_ledger[].evidence_ref. "
        "Verified current Show facts belong in evidence_refs, not sources. "
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
    "rig_designer": (
        "ROLE: RIG_DESIGNER. Create the upstream spatial/resource organization for this exact current Show before lighting design. "
        "Use only the supplied live Show snapshot and Researcher artifact. Fixture type and Group labels are identity evidence only, never artistic roles. "
        "Treat coordinate axes as UNKNOWN unless the supplied snapshot explicitly verifies semantics; do not infer stage-left/right or performer zones. "
        "Only reference real fixture/subfixture identities. Fixture 9999 is protected and unavailable. Do not claim unavailable fixture capabilities. "
        "Do not alter fixture identity, type, Patch, Address, or Stage geometry. Return exactly one JSON object. "
        "Its first key must be \"schema\" with exact value \"zen.multi_agent_rig_design.v0.1\". Then include the required fields "
        "show_fingerprint, spatial_strategy, resource_assignments, spatial_relationships, constraints, uncertainties, codex_artistic_intervention. "
        "Each resource_assignments item must contain resource_refs as objects with fixture_id and optional subfixture_id. "
        "Emit no MA2 commands, Lua, shell, or executable text. Set codex_artistic_intervention to NONE."
    ),
    "position_designer": (
        "ROLE: POSITION_DESIGNER. Turn the validated upstream Rig Designer artifact into concrete proposed test-show geometry; this is a proposal only, not a write. "
        "Use only geometry_resources and allowed_placement_refs from position_context plus the supplied Rig Designer artifact. "
        "The coordinate frame is backend metadata, not an artistic decision. Copy coordinate_system exactly from position_context.coordinate_system; do not infer or reinterpret its axis semantics. "
        "Fixture 9999 is protected and is never an available placement resource. "
        "Return exactly one top-level JSON object only. Its first key must be \"schema\" with exact value \"zen.multi_agent_position_design.v0.1\". "
        "Include every required top-level field with exactly these types: show_fingerprint (string), coordinate_system (object copied exactly from position_context.coordinate_system), "
        "spatial_groups (array), placements (array), constraints (array), uncertainties (array), codex_artistic_intervention (exactly \"NONE\"). "
        "Do not return coordinate_system as a string. Do not omit empty arrays. Do not return explanatory prose outside JSON, Markdown fences, or comments. "
        "Every placement item must contain only fixture_id (integer), subfixture_id (integer), show_fingerprint (string matching position_context.show_fingerprint), "
        "xyz (object with finite numeric x, y, z), and optional rotation (object with finite numeric x, y, z). "
        "Copy each placement identity exactly from position_context.allowed_placement_refs; never invent a fixture/subfixture identity. "
        "Keep placements compact: identity and geometry only, no per-placement essay and do not repeat the full Rig explanation. Put shared rationale concisely in spatial_groups, constraints, or uncertainties. "
        "Each spatial_groups item may express concise grouping intent and real fixture refs; choose any useful grouping or none, without inferring roles from labels/types. "
        "Do not include Patch, Address, fixture_type, fixture_type_change, fixture_id_change, Move3D, console_command, Lua, shell, or other executable content. "
        "Do not emit any MA2 commands or Show mutation instructions. Set codex_artistic_intervention to NONE."
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


def _project_allowed_source_refs(selected_records: list[dict[str, object]]) -> list[dict[str, str]]:
    """Expose only exact canonical identity pairs for the selected records."""
    return [
        {"source_id": str(record["source_id"]), "record_id": str(record["record_id"])}
        for record in selected_records
        if isinstance(record.get("source_id"), str)
        and record.get("source_id")
        and isinstance(record.get("record_id"), str)
        and record.get("record_id")
    ]


def validate_research_source_contract(
    sources: object,
    allowed_source_refs: object,
) -> list[dict[str, str]]:
    """Require Researcher citations to be exact backend-issued identity pairs."""
    if not isinstance(allowed_source_refs, list) or any(
        not isinstance(pair, dict)
        or set(pair) != {"source_id", "record_id"}
        or not isinstance(pair.get("source_id"), str)
        or not pair.get("source_id")
        or not isinstance(pair.get("record_id"), str)
        or not pair.get("record_id")
        for pair in allowed_source_refs
    ):
        raise MultiAgentRunError("Backend Researcher allowed_source_refs are malformed.")
    if not isinstance(sources, list):
        raise ResearchSourceContractError(
            "Researcher sources must be an array of exact canonical source identity objects.",
            "NON_CANONICAL_SOURCE_SHAPE",
        )
    if not sources:
        return []
    allowed_pairs = {(pair["source_id"], pair["record_id"]) for pair in allowed_source_refs}
    allowed_records_by_source: dict[str, set[str]] = {}
    for source_id, record_id in allowed_pairs:
        allowed_records_by_source.setdefault(source_id, set()).add(record_id)
    accepted: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in sources:
        if (
            not isinstance(item, dict)
            or set(item) != {"source_id", "record_id"}
            or not isinstance(item.get("source_id"), str)
            or not item.get("source_id")
            or not isinstance(item.get("record_id"), str)
            or not item.get("record_id")
        ):
            raise ResearchSourceContractError(
                "Researcher sources must contain only exact source_id/record_id objects from allowed_source_refs.",
                "NON_CANONICAL_SOURCE_SHAPE",
            )
        pair = (item["source_id"], item["record_id"])
        if pair in seen:
            raise ResearchSourceContractError(
                "Researcher sources contain a duplicate canonical identity pair.",
                "SOURCE_PAIR_NOT_ALLOWED",
            )
        seen.add(pair)
        if pair not in allowed_pairs:
            if pair[0] in allowed_records_by_source:
                raise ResearchSourceContractError(
                    "Researcher paired an allowed source_id with a different record_id.",
                    "SOURCE_RECORD_MISMATCH",
                )
            raise ResearchSourceContractError(
                "Researcher source identity pair is not present in allowed_source_refs.",
                "SOURCE_PAIR_NOT_ALLOWED",
            )
        accepted.append({"source_id": pair[0], "record_id": pair[1]})
    return accepted


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
                "allowed_source_refs": _project_allowed_source_refs(selected_records),
            }
        }
    live_snapshot = context.get("current_show_snapshot")
    if role_name == "rig_designer":
        if not isinstance(live_snapshot, dict):
            raise MultiAgentRunError("RIG_DESIGNER requires a validated current Show snapshot.")
        return common | {
            "current_show_snapshot": live_snapshot,
            "research_artifact": completed["researcher"],
            "owner_constraints": context.get("hard_constraints", []),
        }
    if role_name == "position_designer":
        if not isinstance(live_snapshot, dict):
            raise MultiAgentRunError("POSITION_DESIGNER requires a validated current Show snapshot.")
        return common | {
            "position_context": build_position_context(live_snapshot),
            "research_artifact": completed["researcher"],
            "rig_design_artifact": completed["rig_designer"],
            "owner_constraints": context.get("hard_constraints", []),
        }
    if role_name == "lighting_designer":
        lighting_payload = common | {
            "research_artifact": completed["researcher"],
            "design_context": {
                "fixture_technical_capability": categories.get("fixture_technical_capability", {}),
                "rig_spatial_visual_affordance": categories.get("rig_spatial_visual_affordance", {}),
                "operator_contract": categories.get("operator_contract", {}),
            },
        }
        if isinstance(live_snapshot, dict):
            lighting_payload |= {
                "current_show_snapshot": live_snapshot,
                "rig_design_artifact": completed["rig_designer"],
                "position_design_artifact": completed["position_designer"],
            }
        return lighting_payload
    if role_name == "critic":
        parallel_designers = candidate_sets.get("lighting_designer", [])
        critic_payload = common | {
            "research_artifact": completed["researcher"],
            "designer_draft": completed["lighting_designer"],
            "relevant_show_constraints": {
                "fixture_technical_capability": categories.get("fixture_technical_capability", {}),
                "rig_spatial_visual_affordance": categories.get("rig_spatial_visual_affordance", {}),
            },
        }
        if isinstance(live_snapshot, dict):
            critic_payload |= {
                "current_show_snapshot": live_snapshot,
                "rig_design_artifact": completed["rig_designer"],
                "position_design_artifact": completed["position_designer"],
            }
        return critic_payload | (
            {"designer_candidates": parallel_designers}
            if len(parallel_designers) > 1 else {}
        )
    parallel_designers = candidate_sets.get("lighting_designer", [])
    parallel_critics = candidate_sets.get("critic", [])
    finalizer_payload = common | {
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
    if isinstance(live_snapshot, dict):
        # Spatial artifacts are canonical upstream authority. Pass their
        # validated values unchanged; finalization may reference, not replace,
        # the Position Designer proposal.
        finalizer_payload |= {
            "current_show_snapshot": live_snapshot,
            "rig_design_artifact": completed["rig_designer"],
            "position_design_artifact": completed["position_designer"],
        }
    return finalizer_payload


def _read_completed_artifacts(
    run_id: str,
    role_sequence: tuple[str, ...] = ROLE_SEQUENCE,
    expected_show_fingerprint: str | None = None,
) -> dict[str, dict[str, object]]:
    completed: dict[str, dict[str, object]] = {}
    for role_name in role_sequence:
        envelope = read_step_artifact(run_id, role_name)
        if envelope is None:
            continue
        if not isinstance(envelope, dict):
            raise MultiAgentRunError(f"Checkpoint for {role_name} is malformed.")
        if envelope.get("current_show_fingerprint") != expected_show_fingerprint:
            raise MultiAgentRunError("Checkpoint Show fingerprint differs from this run input; use --restart-run to avoid mixing artifacts.")
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


def _validate_artifact_evidence(
    role_name: str,
    artifact: dict[str, object],
    context: dict[str, object],
    *,
    allowed_source_refs: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Bind every role's optional evidence refs to the canonical runtime ledger."""
    ledger = context.get("evidence_ledger", {})
    refs = artifact.get("evidence_refs", [])
    if refs is None:
        refs = []
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
        error_type = ResearchEvidenceRefsValidationError if role_name == "researcher" else EvidenceValidationError
        raise error_type(f"{role_name} evidence_refs must be a list of strings.")
    try:
        validate_evidence_refs(refs, ledger)
    except ValueError as exc:
        error_type = ResearchEvidenceRefsValidationError if role_name == "researcher" else EvidenceValidationError
        raise error_type(str(exc)) from exc
    if role_name == "researcher":
        # Validate exact backend-issued pairs before the full canonical resolver.
        # Provenance is never inferred, coerced, or silently repaired here.
        pairs = allowed_source_refs if allowed_source_refs is not None else []
        valid_sources = validate_research_source_contract(artifact.get("sources", []), pairs)
        try:
            artifact["resolved_sources"] = resolve_research_sources(
                sources=valid_sources,
                source_registry=context.get("categories", {}).get("source_provenance", {}),
                records=context.get("canonical_knowledge_records", []),
            )
        except (KeyError, TypeError, ValueError) as exc:
            classification = "SOURCE_RECORD_MISMATCH" if "identity mismatch" in str(exc) else "CANONICAL_SOURCE_RESOLUTION_ERROR"
            raise ResearchCanonicalSourceResolutionError(str(exc), classification) from exc
    return artifact


def _researcher_source_diagnostic_values(
    artifact: object,
    allowed_source_refs: object,
    *,
    error: Exception | None = None,
) -> dict[str, object]:
    """Return bounded source-contract diagnostics without registry contents."""
    allowed_count = len(allowed_source_refs) if isinstance(allowed_source_refs, list) else 0
    sources = artifact.get("sources") if isinstance(artifact, dict) else None
    output_count = len(sources) if isinstance(sources, list) else None
    if isinstance(sources, list) and not sources:
        raw_shape = "EMPTY_ARRAY"
    elif isinstance(sources, list) and all(
        isinstance(item, dict)
        and set(item) == {"source_id", "record_id"}
        and isinstance(item.get("source_id"), str)
        and isinstance(item.get("record_id"), str)
        for item in sources
    ):
        raw_shape = "CANONICAL_PAIR_ARRAY"
    elif isinstance(sources, list):
        raw_shape = "NON_CANONICAL_SOURCE_SHAPE"
    else:
        raw_shape = "MISSING_OR_NON_ARRAY"

    if isinstance(error, ResearchSourceContractError):
        source_contract, canonical_resolution = "FAIL", "NOT_RUN"
        failure_class = error.classification
        evidence_refs = "PASS"
    elif isinstance(error, ResearchCanonicalSourceResolutionError):
        source_contract, canonical_resolution = "PASS", "FAIL"
        failure_class = error.classification
        evidence_refs = "PASS"
    elif isinstance(error, ResearchEvidenceRefsValidationError):
        source_contract, canonical_resolution = "NOT_RUN", "NOT_RUN"
        failure_class = "INVALID_EVIDENCE_REFS"
        evidence_refs = "FAIL"
    elif error is not None:
        source_contract, canonical_resolution = "NOT_RUN", "NOT_RUN"
        failure_class = None
        evidence_refs = "NOT_RUN"
    else:
        source_contract, canonical_resolution = "PASS", "PASS"
        failure_class = None
        evidence_refs = "PASS"
    return {
        "RESEARCHER_ALLOWED_SOURCE_REF_COUNT": allowed_count,
        "RESEARCHER_OUTPUT_SOURCE_COUNT": output_count,
        "RESEARCHER_RAW_SOURCE_SHAPE": raw_shape,
        "RESEARCHER_SOURCE_CONTRACT_VALID": source_contract,
        "RESEARCHER_CANONICAL_SOURCE_RESOLUTION": canonical_resolution,
        "RESEARCHER_EVIDENCE_REFS_VALID": evidence_refs,
        "RESEARCHER_SOURCE_FAILURE_CLASS": failure_class,
    }


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
    existing = [
        path / name
        for name in ("run.json", "steps", "final_design.json", "failure.json", "diagnostics", "attempts")
        if (path / name).exists()
    ]
    if not existing:
        return
    archive = path / "restart_archive" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive.mkdir(parents=True, exist_ok=False)
    for item in existing:
        shutil.move(str(item), str(archive / item.name))


def _bind_current_show_context(
    context: dict[str, object],
    snapshot: dict[str, object],
) -> dict[str, object]:
    """Make the supplied snapshot current truth and isolate mismatched cache."""
    bound = dict(context)
    categories = dict(bound.get("categories", {}))
    fingerprint = str(snapshot["show_fingerprint"])
    categories["fixture_technical_capability"] = {
        "status": "UNKNOWN_FOR_CURRENT_FINGERPRINT",
        "show_fingerprint": fingerprint,
        "capabilities": [],
        "reason": snapshot["technical_capabilities"]["reason"],
    }
    categories["rig_spatial_visual_affordance"] = {
        "status": "LIVE_GEOMETRY_ONLY",
        "show_fingerprint": fingerprint,
        "coordinate_system": snapshot["coordinate_system"],
        "fixture_count": snapshot["fixture_count"],
        "geometry_record_count": snapshot["geometry_record_count"],
        "group_count": snapshot["group_count"],
        "semantic_positions": "NONE_VERIFIED",
    }
    # These cached inputs can belong to a different Show. Keep their existence
    # as backend diagnostics only; do not let them appear as current facts.
    categories["prior_case_artifacts"] = {
        "status": "EXCLUDED_FROM_CURRENT_SHOW_CONTEXT",
        "reason": "Cached case artifacts are not fingerprint-bound to this live snapshot.",
    }
    bound["categories"] = categories
    bound["current_show_snapshot"] = snapshot

    ledger = dict(bound.get("evidence_ledger", {}))
    entries = list(ledger.get("entries", []))
    source = {
        "type": "PHASE_A_SAVED_READ_ONLY_CURRENT_SHOW_SNAPSHOT",
        "show_fingerprint": fingerprint,
        "source_artifact_hash": snapshot["source_artifact_hash"],
    }
    facts = [
        ("fixture_inventory", f"The read-only current Show snapshot records {snapshot['fixture_count']} fixtures and {snapshot['group_count']} Groups."),
        ("fixture_geometry", f"The read-only current Show snapshot records {snapshot['geometry_record_count']} fixture/subfixture geometry entries; axis semantics remain UNKNOWN."),
        ("technical_capability_status", "No current-fingerprint verified fixture capability profiles are available to this run."),
    ]
    for name, summary in facts:
        entries.append({
            "evidence_ref": f"CURRENT_SHOW:{fingerprint}:{name}",
            "kind": "VERIFIED_FACT",
            "source": source,
            "summary": summary,
        })
    ledger["entries"] = sorted(entries, key=lambda item: str(item.get("evidence_ref", "")))
    ledger["available_verified_facts"] = [
        *ledger.get("available_verified_facts", []),
        *[ref for ref, _ in ((f"CURRENT_SHOW:{fingerprint}:{name}", summary) for name, summary in facts)],
    ]
    bound["evidence_ledger"] = ledger
    return bound


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
    api_key: str = "",
    provider_elapsed_seconds: float | None = None,
    failure_class: str = "OUTPUT_VALIDATION",
    structural_normalization: dict[str, object] | None = None,
    researcher_diagnostics: dict[str, object] | None = None,
) -> None:
    """Keep an agent-owned failed response for local validation diagnosis."""
    secret_leaked = bool(api_key and api_key in content)
    diagnostic: dict[str, object] = {
        "schema": ATTEMPT_SCHEMA,
        "role": role_name,
        "attempt": attempt,
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_characters": len(content),
        "validation_error_type": type(error).__name__,
        "validation_error": _bounded_validation_error(error, api_key=api_key),
        "provider_elapsed_seconds": provider_elapsed_seconds,
        "failure_class": failure_class,
        "structural_normalization": structural_normalization or _empty_structural_normalization(),
        "secret_check": "FAIL" if secret_leaked else "PASS",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    if not secret_leaked:
        diagnostic["raw_response"] = content
    if researcher_diagnostics:
        diagnostic.update(researcher_diagnostics)
    _write_json(path / "attempts" / f"{role_name}-{attempt:02}.json", diagnostic)


def _record_structural_normalization_diagnostic(
    path: Path,
    *,
    role_name: str,
    attempt: int,
    content: str,
    api_key: str,
    provider_elapsed_seconds: float,
    structural_normalization: dict[str, object],
) -> None:
    """Audit a successful metadata-only normalization without altering raw evidence."""
    secret_leaked = bool(api_key and api_key in content)
    diagnostic: dict[str, object] = {
        "schema": ATTEMPT_SCHEMA,
        "role": role_name,
        "attempt": attempt,
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_characters": len(content),
        "validation_error_type": None,
        "validation_error": None,
        "provider_elapsed_seconds": round(provider_elapsed_seconds, 3),
        "failure_class": "SUCCESS",
        "candidate_status": "STRUCTURALLY_NORMALIZED_VALID_ROLE_OUTPUT",
        "structural_normalization": structural_normalization,
        "secret_check": "FAIL" if secret_leaked else "PASS",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    if not secret_leaked:
        diagnostic["raw_response"] = content
    _write_json(path / "attempts" / f"{role_name}-{attempt:02}.json", diagnostic)


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
    diagnostic: dict[str, object] = {
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
        "structural_normalization": _empty_structural_normalization(),
        "secrets_included": False,
    }
    if role_name == "researcher":
        research_context = payload.get("research_context", {})
        allowed_source_refs = research_context.get("allowed_source_refs", []) if isinstance(research_context, dict) else []
        diagnostic.update(_researcher_source_diagnostic_values({}, allowed_source_refs))
        diagnostic["RESEARCHER_SOURCE_CONTRACT_VALID"] = "NOT_RUN"
        diagnostic["RESEARCHER_CANONICAL_SOURCE_RESOLUTION"] = "NOT_RUN"
        diagnostic["RESEARCHER_EVIDENCE_REFS_VALID"] = "NOT_RUN"
    _write_json(diagnostic_path, diagnostic)
    return diagnostic_path


def _update_model_context_diagnostic(
    path: Path,
    *,
    provider_elapsed_seconds: float,
    failure_class: str,
    extra: dict[str, object] | None = None,
) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(value, dict):
        return
    value["provider_elapsed_seconds"] = round(provider_elapsed_seconds, 3)
    value["failure_class"] = failure_class
    if extra:
        value.update(extra)
    _write_json(path, value)


def _update_structural_normalization_diagnostic(
    path: Path,
    structural_normalization: dict[str, object],
) -> None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(value, dict):
        return
    value["structural_normalization"] = structural_normalization
    _write_json(path, value)


def _read_structural_normalization_diagnostic(
    path: Path,
    *,
    role_name: str,
    attempt: int,
) -> dict[str, object]:
    diagnostic_path = path / "diagnostics" / f"{role_name}-{attempt:02}.json"
    try:
        value = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_structural_normalization()
    normalization = value.get("structural_normalization") if isinstance(value, dict) else None
    return normalization if isinstance(normalization, dict) else _empty_structural_normalization()


def _write_single_role_provider_diagnostic(
    path: Path,
    *,
    role_name: str,
    router: ProviderRouter,
    provider_attempts: tuple[dict[str, object], ...],
    selected_slot: ProviderSlot | None,
    role_output_validation: str,
    evidence_validation: str = "NOT_RUN",
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
            row["evidence_validation"] = evidence_validation
            row["candidate_status"] = (
                "EVIDENCE_VALIDATION_FAILURE"
                if role_output_validation == "PASS" and evidence_validation == "FAIL"
                else "OUTPUT_VALIDATION_FAILURE"
                if role_output_validation == "FAIL"
                else "VALID_ROLE_OUTPUT"
            )
        rows.append(row)
    attempted_slots = [int(row["slot_number"]) for row in rows if isinstance(row.get("slot_number"), int)]
    first_eligible = eligible[0].number if eligible else None
    value["provider_routing"] = {
        "router_mode": router.mode,
        "role": ROLE_ROUTER_NAMES[role_name],
        "semantic_role": role_name.upper(),
        "provider_capability_role": ROLE_ROUTER_NAMES[role_name],
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
    if isinstance(error, EvidenceValidationError):
        return "EVIDENCE_VALIDATION"
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
    validator: Callable[[object], dict[str, object]] | None = None,
    system_prompt: str | None = None,
    evidence_validation_enabled: bool = False,
) -> tuple[dict[str, object], ProviderSlot, int]:
    validator = validator or ROLE_VALIDATORS[role_name]
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        content = ""
        parsed: object | None = None
        selected_slot: ProviderSlot | None = None
        provider_attempts: tuple[dict[str, object], ...] = ()
        structural_normalization = _empty_structural_normalization()
        system = system_prompt or ROLE_SYSTEM_PROMPTS[role_name]
        if last_error is not None:
            system += f" Previous attempt failed validation: {last_error}. Correct only the structural issue and return JSON only." + RETRY_SAFETY_CONTRACT
            if role_name == "position_designer":
                system += _position_retry_contract(last_error)
            if role_name == "researcher" and isinstance(
                last_error,
                (ResearchSourceContractError, ResearchCanonicalSourceResolutionError),
            ):
                system += RESEARCH_SOURCE_RETRY_CONTRACT
        research_context = payload.get("research_context", {})
        allowed_source_refs = (
            research_context.get("allowed_source_refs", [])
            if isinstance(research_context, dict)
            else []
        )
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
                parsed = _parse_json(content)
                if role_name == "researcher":
                    source_diagnostics = _researcher_source_diagnostic_values(parsed, allowed_source_refs)
                    source_diagnostics.update({
                        "RESEARCHER_SOURCE_CONTRACT_VALID": "NOT_RUN",
                        "RESEARCHER_CANONICAL_SOURCE_RESOLUTION": "NOT_RUN",
                        "RESEARCHER_EVIDENCE_REFS_VALID": "NOT_RUN",
                    })
                    _update_model_context_diagnostic(
                        path=diagnostic_path,
                        provider_elapsed_seconds=elapsed,
                        failure_class="SUCCESS",
                        extra=source_diagnostics,
                    )
                normalized, structural_normalization = normalize_role_envelope(role_name, parsed)
                _update_structural_normalization_diagnostic(diagnostic_path, structural_normalization)
                artifact = validator(normalized)
            except (MultiAgentRunError, DesignValidationError) as exc:
                researcher_diagnostics = (
                    _researcher_source_diagnostic_values(parsed, allowed_source_refs, error=exc)
                    if role_name == "researcher" and parsed is not None
                    else None
                )
                _update_model_context_diagnostic(
                    path=diagnostic_path,
                    provider_elapsed_seconds=elapsed,
                    failure_class="OUTPUT_VALIDATION",
                    extra=researcher_diagnostics,
                )
                raise exc
            if role_name == "researcher":
                researcher_diagnostics = _researcher_source_diagnostic_values(parsed, allowed_source_refs)
                _update_model_context_diagnostic(
                    path=diagnostic_path,
                    provider_elapsed_seconds=elapsed,
                    failure_class="SUCCESS",
                    extra=researcher_diagnostics,
                )
            _write_single_role_provider_diagnostic(
                diagnostic_path,
                role_name=role_name,
                router=router,
                provider_attempts=provider_attempts,
                selected_slot=selected_slot,
                role_output_validation="PASS",
                evidence_validation="PASS" if evidence_validation_enabled else "NOT_RUN",
            )
            if structural_normalization["applied"]:
                _record_structural_normalization_diagnostic(
                    run_path,
                    role_name=role_name,
                    attempt=attempt,
                    content=content,
                    api_key=selected_slot.api_key,
                    provider_elapsed_seconds=elapsed,
                    structural_normalization=structural_normalization,
                )
            return artifact, slot, attempt
        except (ProviderUnavailable, MultiAgentRunError, DesignValidationError) as exc:
            elapsed = time.monotonic() - started
            researcher_diagnostics = (
                _researcher_source_diagnostic_values(parsed, allowed_source_refs, error=exc)
                if role_name == "researcher" and parsed is not None
                else None
            )
            if diagnostic_path is not None:
                classification = _failure_class(exc)
                _update_model_context_diagnostic(
                    path=diagnostic_path,
                    provider_elapsed_seconds=elapsed,
                    failure_class=classification,
                    extra=researcher_diagnostics,
                )
                if isinstance(exc, ProviderUnavailable):
                    provider_attempts = tuple(getattr(exc, "provider_attempts", ()))
                _write_single_role_provider_diagnostic(
                    diagnostic_path,
                    role_name=role_name,
                    router=router,
                    provider_attempts=provider_attempts,
                    selected_slot=selected_slot,
                    role_output_validation=(
                        "PASS" if isinstance(exc, EvidenceValidationError)
                        else "FAIL" if selected_slot is not None and content
                        else "NOT_RUN"
                    ),
                    evidence_validation="FAIL" if isinstance(exc, EvidenceValidationError) else "NOT_RUN",
                )
            last_error = exc
            if content:
                _record_attempt_diagnostic(
                    run_path,
                    role_name=role_name,
                    attempt=attempt,
                    content=content,
                    error=exc,
                    api_key=selected_slot.api_key if selected_slot is not None else "",
                    provider_elapsed_seconds=elapsed,
                    failure_class=_failure_class(exc),
                    structural_normalization=structural_normalization,
                    researcher_diagnostics=researcher_diagnostics,
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
    system_prompt: str | None = None,
) -> tuple[list[tuple[dict[str, object], ProviderSlot]], dict[str, object]]:
    """Run one role on independent providers and retain valid candidates.

    This is candidate generation only. Every output still passes the same role
    validator and later evidence validation. If all parallel candidates fail,
    the caller falls back to the normal bounded retry path.
    """
    validator = ROLE_VALIDATORS[role_name]
    system = system_prompt or ROLE_SYSTEM_PROMPTS[role_name]
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
        "semantic_role": role_name.upper(),
        "provider_capability_role": ROLE_ROUTER_NAMES[role_name],
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
    current_show_snapshot: CurrentShowSnapshotInput | dict[str, object] | None = None,
) -> MultiAgentRun:
    """Execute or safely resume the conditional multi-agent design pipeline.

    Completed artifacts are never overwritten during a normal resume.  Passing
    ``current_show_snapshot`` activates the six-role upstream spatial path.
    Passing ``restart_run=True`` is the explicit opt-in for regenerating an
    existing run id's checkpoints.
    """
    if not request.strip():
        raise ValueError("A non-empty user request is required.")
    if not 1 <= max_role_attempts <= MAX_ROLE_ATTEMPTS:
        raise ValueError(f"max_role_attempts must be from 1 to {MAX_ROLE_ATTEMPTS}.")

    context = build_designer_context(repo_root)
    normalized_snapshot: dict[str, object] | None = None
    show_fingerprint: str | None = None
    if current_show_snapshot is not None:
        try:
            normalized_snapshot = normalize_current_show_snapshot(current_show_snapshot)
        except (LiveShowSnapshotError, TypeError, ValueError) as exc:
            raise MultiAgentRunError(f"Current Show snapshot rejected: {exc}") from exc
        show_fingerprint = str(normalized_snapshot["show_fingerprint"])
        context = _bind_current_show_context(context, normalized_snapshot)
    role_sequence = LIVE_SHOW_ROLE_SEQUENCE if normalized_snapshot is not None else ROLE_SEQUENCE
    context_hash = _sha256(context)
    request_hash = _sha256({"user_request": request})
    run_id = run_id or _new_run_id()
    path = _run_path(run_id)
    path.mkdir(parents=True, exist_ok=True)
    if restart_run:
        _archive_for_restart(path)
    if normalized_snapshot is not None:
        _write_json(path / "normalized_current_show_snapshot.json", normalized_snapshot)
    final_path = path / "final_design.json"
    resume_point = find_resume_point(run_id, list(role_sequence))
    previous_state = _read_run_state(path)
    step_dir = path / "steps"
    checkpoint_files = sorted(step_dir.glob("*.json")) if step_dir.is_dir() else []
    has_checkpoints = bool(checkpoint_files)
    if not restart_run and previous_state:
        if previous_state.get("REQUEST_HASH") not in (None, request_hash):
            raise MultiAgentRunError("Existing run id belongs to a different request; use a new run id or --restart-run.")
        if has_checkpoints:
            if previous_state.get("CURRENT_SHOW_FINGERPRINT") != show_fingerprint:
                raise MultiAgentRunError("Existing checkpoints belong to a different current Show fingerprint; use --restart-run to avoid mixing artifacts.")
            prior_order = previous_state.get("ROLE_EXECUTION_ORDER")
            if prior_order != list(role_sequence):
                raise MultiAgentRunError("Existing checkpoints were produced with a different role order; use --restart-run to avoid mixing artifacts.")
            if previous_state.get("CONTEXT_HASH") != context_hash:
                raise MultiAgentRunError("Designer Context changed since this run started; use --restart-run to avoid mixing checkpoints.")
    if not restart_run and has_checkpoints:
        checkpoint_roles = [item.stem for item in checkpoint_files]
        if any(role not in role_sequence for role in checkpoint_roles):
            raise MultiAgentRunError("Existing checkpoints contain roles outside this run's execution order; use --restart-run.")
        checkpoint_role_set = set(checkpoint_roles)
        expected_prefix = list(role_sequence[:len(checkpoint_roles)])
        if [role for role in role_sequence if role in checkpoint_role_set] != expected_prefix:
            raise MultiAgentRunError("Existing checkpoints are not a completed prefix of this role order; refusing an unsafe resume.")
    if not restart_run and resume_point is None:
        final_design = _load_valid_final(final_path)
        if final_design is not None:
            if normalized_snapshot is not None:
                position_envelope = read_step_artifact(run_id, "position_designer")
                position_artifact = position_envelope.get("artifact") if isinstance(position_envelope, dict) else None
                if not isinstance(position_artifact, dict):
                    raise MultiAgentRunError("Completed live-Show run is missing its canonical Position Designer checkpoint.")
                validate_final_spatial_consistency(final_design, position_artifact, show_fingerprint or "")
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
        "ROLE_EXECUTION_ORDER": list(role_sequence),
        "CURRENT_SHOW_FINGERPRINT": show_fingerprint,
        "CURRENT_SHOW_SNAPSHOT_SOURCE_HASH": normalized_snapshot.get("source_artifact_hash") if normalized_snapshot else None,
        "LIVE_SHOW_SNAPSHOT_IN_CONTEXT": "YES" if normalized_snapshot else "NO",
        "CURRENT_SHOW_CAPABILITY_STATUS": normalized_snapshot.get("technical_capabilities", {}).get("status") if normalized_snapshot else "NOT_SUPPLIED",
        "role_execution": [] if restart_run else list(previous_state.get("role_execution", [])),
        "LOCAL_MODEL_USED": "NO",
        "CLOUD_REQUIRED": "NO",
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
        "status": "RUNNING",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    completed = {} if restart_run else _read_completed_artifacts(
        run_id,
        role_sequence,
        expected_show_fingerprint=show_fingerprint,
    )
    candidate_sets = {} if restart_run else _read_candidate_sets(run_id)
    _write_run_state(path, state)
    started_from = role_sequence[0] if restart_run else resume_point
    active_role = started_from or role_sequence[0]

    try:
        for role_name in role_sequence:
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
            system_prompt = ROLE_SYSTEM_PROMPTS[role_name]
            if normalized_snapshot is not None and role_name == "lighting_designer":
                system_prompt += (
                    " For this live-Show case, treat the supplied validated Rig Designer and Position Designer artifacts as upstream authority. "
                    "Begin lighting reasoning after the spatial proposal; do not replace or silently rewrite its geometry. "
                    "FixtureType and Group labels are identity only, not artistic roles."
                )
            elif normalized_snapshot is not None and role_name == "critic":
                system_prompt += (
                    " For this live-Show case, inspect the exact Researcher, Rig Designer, Position Designer, and Lighting Designer artifacts. "
                    "Check spatial/resource conflicts, unsupported capability, forced novelty, hierarchy/negative-space weakness, "
                    "and operator/editability concerns. Critique without inventing replacement geometry or treating Group/FixtureType labels as roles."
                )
            parallel_limit = router.parallel_limit(ROLE_ROUTER_NAMES[role_name])
            if role_name in {"lighting_designer", "critic"} and parallel_limit > 1:
                parallel_results, parallel_runtime = _run_parallel_role_candidates(
                    router,
                    role_name=role_name,
                    payload=payload,
                    context=context,
                    run_path=path,
                    limit=parallel_limit,
                    system_prompt=system_prompt,
                )

            validated_candidates: list[tuple[dict[str, object], ProviderSlot]] = list(parallel_results)
            structural_normalization = _empty_structural_normalization()

            if validated_candidates:
                artifact, slot = validated_candidates[0]
                attempts = 1
                candidate_sets[role_name] = [candidate for candidate, _ in validated_candidates]
            else:
                role_validator: Callable[[object], dict[str, object]] | None = None
                if role_name == "rig_designer" and normalized_snapshot is not None:
                    role_validator = lambda value: validate_rig_design_artifact(value, normalized_snapshot)
                elif role_name == "position_designer" and normalized_snapshot is not None:
                    role_validator = lambda value: validate_position_design_artifact(value, normalized_snapshot)
                elif role_name == "finalizer" and normalized_snapshot is not None:
                    position_artifact = completed.get("position_designer")
                    if not isinstance(position_artifact, dict):
                        raise MultiAgentRunError("Finalizer requires the validated Position Designer artifact.")
                    reference = {
                        "show_fingerprint": show_fingerprint,
                        "position_artifact_sha256": _sha256(position_artifact),
                    }
                    system_prompt += (
                        " This live-Show run has canonical upstream spatial authority. Include a top-level position_design_reference "
                        "exactly equal to " + _canonical_json(reference) + ". Do not replace or restate different fixture geometry. "
                        "If virtual_rig or position_vocabulary includes exact fixture/subfixture XYZ, it must match the upstream Position Designer artifact."
                    )

                    def validate_live_final(value: object) -> dict[str, object]:
                        final = validate_design_output(value)
                        validate_final_spatial_consistency(final, position_artifact, show_fingerprint or "")
                        return final

                    role_validator = validate_live_final
                schema_validator = role_validator or ROLE_VALIDATORS[role_name]

                def validate_role_with_evidence(value: object) -> dict[str, object]:
                    validated = schema_validator(value)
                    researcher_context = payload.get("research_context", {})
                    allowed_refs = (
                        researcher_context.get("allowed_source_refs", [])
                        if role_name == "researcher" and isinstance(researcher_context, dict)
                        else None
                    )
                    return _validate_artifact_evidence(
                        role_name,
                        validated,
                        context,
                        allowed_source_refs=allowed_refs,
                    )

                artifact, slot, attempts = _run_role(
                    router,
                    role_name=role_name,
                    payload=payload,
                    max_attempts=max_role_attempts,
                    run_path=path,
                    validator=validate_role_with_evidence,
                    system_prompt=system_prompt,
                    evidence_validation_enabled=True,
                )
                structural_normalization = _read_structural_normalization_diagnostic(
                    path,
                    role_name=role_name,
                    attempt=attempts,
                )
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
                "structural_normalization": structural_normalization,
                "current_show_fingerprint": show_fingerprint,
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
                "structural_normalization": structural_normalization,
                "attempts": attempts,
                "artifact_hash": envelope["artifact_hash"],
            }]
            _write_run_state(path, state)

        final_design = completed["finalizer"]
        validate_design_output(final_design)
        if normalized_snapshot is not None:
            validate_final_spatial_consistency(final_design, completed["position_designer"], show_fingerprint or "")
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
