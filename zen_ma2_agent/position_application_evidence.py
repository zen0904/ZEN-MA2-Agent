"""Exact, readback-backed Position Preset application evidence.

Discovery and preview never create applicability. Only a future approved probe
whose Sequence Export proves Position channels for every exact selected member
can produce a binding. No MA transport or execution lives in this module.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from .allocation import first_free_from_front
from .protected_objects import PROTECTED_SEQUENCES
from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


SCHEMA = "zen.position_preset_application_binding.v0.1"
PREVIEW_SCHEMA = "zen.position_application_poc_preview.v0.1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REF = re.compile(r"([1-9]\d*)(?:\.([1-9]\d*))?\Z")
_PRESET = re.compile(r"2\.([1-9]\d*)\Z")
_POSITION_ATTRIBUTES = frozenset({"PAN", "TILT"})


class PositionEvidenceError(ValueError):
    pass


class PositionApplicationPocSkill:
    """Approval-aware wrapper for the existing exact, deterministic POC plan.

    No transport is available from this skill. AgentCore alone owns execution
    after a second, fresh read-only identity check at approval time.
    """

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        return (self.manifest.enabled and intent.kind == "verify_position_application"
                and state.has(self.manifest.required_state))

    def create_task(self, intent: Intent) -> Task:
        return Task("position-application-poc", "Position Application POC", intent,
                    self.manifest.id, self.manifest.required_state)

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        preview = task.intent.parameters.get("position_preview")
        if not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA:
            raise PositionEvidenceError("POSITION_POC_PREVIEW_INVALID")
        commands = preview.get("candidate_commands")
        if not isinstance(commands, list) or len(commands) != 6:
            raise PositionEvidenceError("POSITION_POC_COMMAND_PLAN_INVALID")
        steps = tuple(ActionStep(f"step-{index}", title, "command", command, "MODIFY",
                                 depends_on=(f"step-{index-1}",) if index > 1 else ())
                      for index, (title, command) in enumerate(zip((
                          "Clear programmer", "Select exact verified Group", "Apply exact Position Preset",
                          "Store one new Cue", "Label new Agent-owned Sequence", "Clear programmer",
                      ), commands), start=1))
        summary = json.dumps({key: preview[key] for key in (
            "preview_id", "show_identity", "group", "preset", "sequence",
            "typed_action", "candidate_commands", "expected_readback", "rollback_scope",
        )}, sort_keys=True, ensure_ascii=True, indent=2)
        return WorkflowPlan(task, (
            Subtask("fresh-verify", "Fresh read-only Show, Group, Preset and Sequence check", "Planning"),
            Subtask("preview", "Human review of exact bounded plan", "Planning"),
            Subtask("execute", "Approved one-Cue probe only", "Execution"),
            Subtask("readback", "Native Sequence Export exact PAN/TILT evidence", "Verification"),
        ), (SkillGraphNode("root", self.manifest.id, "Position Application POC"),),
            steps, "MODIFY", "POSITION APPLICATION POC — PREVIEW ONLY\n" + summary,
            ("PREVIEW",), f"Exact Cue 1 PAN/TILT Preset {preview['preset']['reference']} content for every exact member; no foreign member",
            preview["rollback_scope"], True, "PREVIEW", "READY")

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        preview = plan.task.intent.parameters.get("position_preview")
        if (plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY"
                or not isinstance(preview, dict) or preview.get("schema") != PREVIEW_SCHEMA
                or plan.commands != tuple(preview.get("candidate_commands") or ())
                or preview.get("sequence", {}).get("executor", "INVALID") is not None):
            raise PositionEvidenceError("POSITION_POC_WORKFLOW_INVALID")
        sequence = preview["sequence"]["id"]
        group = preview["group"]["id"]
        reference = preview["preset"]["reference"]
        label = preview["sequence"]["label"]
        if (not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1
                or sequence in PROTECTED_SEQUENCES or not isinstance(group, int) or group < 1
                or not isinstance(reference, str) or not _PRESET.fullmatch(reference)
                or not isinstance(label, str) or not re.fullmatch(r"ZEN_POSITION_APPLICATION_POC_SEQ[1-9]\d*", label)
                or preview.get("sequence", {}).get("cue") != 1
                or plan.commands != (
                    "ClearAll", f"Group {group}", f"At Preset {reference}",
                    f'Store Cue 1 Sequence {sequence} "POSITION_APPLICATION_POC" Fade 0 /nc',
                    f'Label Sequence {sequence} "{label}" /nc', "ClearAll",
                ) or any(not command.isascii() for command in plan.commands)):
            raise PositionEvidenceError("POSITION_POC_COMMAND_PLAN_INVALID")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise PositionEvidenceError("POSITION_POC_SKILL_MISMATCH")
        self.validate(approved_plan, None)
        return approved_plan.commands


def _group(profile: Mapping[str, Any], group_id: int) -> Mapping[str, Any]:
    for group in profile.get("groups", []):
        if isinstance(group, Mapping) and group.get("group_id") == group_id:
            return group
    raise PositionEvidenceError("CURRENT_GROUP_NOT_FOUND")


def _exact_refs(group: Mapping[str, Any]) -> list[str]:
    membership = group.get("membership")
    refs = group.get("fixture_refs_in_selection_order")
    if (not isinstance(membership, Mapping) or membership.get("status") != "SUPPORTED"
            or membership.get("source") not in {"ma2_export_xml", "ma2_group_export_xml"}
            or not isinstance(refs, list) or not refs
            or any(not isinstance(ref, str) or not _REF.fullmatch(ref) for ref in refs)
            or len(refs) != len(set(refs))
            or any(ref == "9999" or ref.startswith("9999.") for ref in refs)):
        raise PositionEvidenceError("EXACT_GROUP_MEMBERSHIP_UNAVAILABLE")
    return refs


def _preset(profile: Mapping[str, Any], reference: str) -> Mapping[str, Any]:
    if not isinstance(reference, str) or not _PRESET.fullmatch(reference):
        raise PositionEvidenceError("POSITION_PRESET_REF_INVALID")
    for preset in profile.get("presets", []):
        if (isinstance(preset, Mapping) and preset.get("reference") == reference
                and preset.get("preset_type") == "POSITION"
                and isinstance(preset.get("name"), str) and preset["name"]):
            return preset
    raise PositionEvidenceError("POSITION_PRESET_IDENTITY_UNAVAILABLE")


def _position_capability(profile: Mapping[str, Any], refs: list[str]) -> None:
    fixtures = {item.get("fixture_id"): item for item in profile.get("fixtures", []) if isinstance(item, Mapping)}
    types = {
        item.get("fixture_type", {}).get("list_label"): item
        for item in profile.get("fixture_type_profiles", [])
        if isinstance(item, Mapping) and isinstance(item.get("fixture_type"), Mapping)
        and item.get("status") == "SHOW_BOUND_VERIFIED"
    }
    for ref in refs:
        root = int(ref.split(".", 1)[0])
        fixture = fixtures.get(root)
        if not isinstance(fixture, Mapping):
            raise PositionEvidenceError("GROUP_FIXTURE_IDENTITY_UNAVAILABLE")
        profile_row = types.get(fixture.get("fixture_type"))
        capability = (profile_row or {}).get("capabilities", {}).get("POSITION", {})
        if not isinstance(capability, Mapping) or capability.get("status") != "SHOW_BOUND_VERIFIED":
            raise PositionEvidenceError("POSITION_TECHNICAL_CAPABILITY_UNVERIFIED")
        # A parent selection is unambiguous only for a single-instance body.
        geometry = fixture.get("stage_geometry")
        subfixtures = geometry.get("subfixtures") if isinstance(geometry, Mapping) else None
        if "." not in ref and (not isinstance(subfixtures, list) or len(subfixtures) != 1):
            raise PositionEvidenceError("MULTI_INSTANCE_PARENT_SELECTION_AMBIGUOUS")
        if "." in ref and (not isinstance(subfixtures, list) or int(ref.split(".", 1)[1]) not in
                               {row.get("subfixture_id") for row in subfixtures if isinstance(row, Mapping)}):
            raise PositionEvidenceError("EXACT_SUBFIXTURE_NOT_VERIFIED")


def _identity(profile: Mapping[str, Any]) -> dict[str, Any]:
    identity = profile.get("show_identity")
    if (not isinstance(identity, Mapping) or identity.get("kind") != "SCANNED_SHOW_PROFILE_FINGERPRINT"
            or not isinstance(identity.get("value"), str) or not _SHA256.fullmatch(identity["value"])):
        raise PositionEvidenceError("CURRENT_SHOW_IDENTITY_UNAVAILABLE")
    return dict(identity)


def _fresh_resources(profile: Mapping[str, Any], *, include_sequences: bool) -> bool:
    resources = profile.get("resources")
    required = ["groups", "group_membership", "fixtures", "fixture_geometry", "fixture_type_profiles", "presets"]
    if include_sequences:
        required.append("sequences")
    return bool(isinstance(resources, Mapping) and all(
        isinstance(resources.get(key), Mapping) and resources[key].get("status") == "SUPPORTED"
        for key in required
    ))


def build_position_poc_preview(profile: Mapping[str, Any], *, group_id: int, preset_ref: str) -> dict[str, Any]:
    """Build a deterministic, non-executable Preview from fresh read-only state."""
    identity = _identity(profile)
    group = _group(profile, group_id)
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    preset = _preset(profile, preset_ref)
    if not _fresh_resources(profile, include_sequences=True):
        raise PositionEvidenceError("FRESH_READ_ONLY_STATE_REQUIRED")
    sequences = profile.get("sequences")
    if not isinstance(sequences, list):
        raise PositionEvidenceError("SEQUENCE_INVENTORY_UNAVAILABLE")
    occupied = {item.get("number") for item in sequences if isinstance(item, Mapping)}
    sequence = first_free_from_front(occupied, protected=PROTECTED_SEQUENCES, start=1, end=9999)
    label = f"ZEN_POSITION_APPLICATION_POC_SEQ{sequence}"
    if label in {item.get("name") for item in sequences if isinstance(item, Mapping)}:
        raise PositionEvidenceError("AGENT_OWNED_SEQUENCE_LABEL_COLLISION")
    proposal = {
        "schema": PREVIEW_SCHEMA,
        "status": "PREVIEW_ONLY_NOT_REGISTERED_FOR_APPROVAL",
        "executable": False,
        "show_identity": identity,
        "group": {"id": group_id, "name": group.get("name"), "exact_refs": refs},
        "preset": {"reference": preset_ref, "type": "POSITION", "label": preset["name"]},
        "sequence": {"id": sequence, "label": label, "cue": 1, "executor": None},
        "typed_action": {"operation": "CALL_PRESET", "target": {"type": "group", "ref": group_id}, "preset_ref": preset_ref, "preset_type": "POSITION"},
        "candidate_commands": [
            "ClearAll", f"Group {group_id}", f"At Preset {preset_ref}",
            f'Store Cue 1 Sequence {sequence} "POSITION_APPLICATION_POC" Fade 0 /nc',
            f'Label Sequence {sequence} "{label}" /nc', "ClearAll",
        ],
        "approval": "FUTURE_INTERACTIVE_OWNER_APPROVAL_REQUIRED; NO_EXECUTION_PATH_IN_THIS_PREVIEW",
        "expected_readback": "Exact Sequence Export Cue 1 PAN/TILT Preset reference on every exact Group member, no foreign member",
        "rollback_scope": f"Only newly created Agent-owned Sequence {sequence}, after exact identity readback; no automatic Delete",
        "ma2_writes": 0,
    }
    canonical = json.dumps(proposal, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    proposal["preview_id"] = hashlib.sha256(canonical).hexdigest()[:16]
    return proposal


def _row_ref(channel: Mapping[str, Any]) -> str | None:
    fixture, sub = channel.get("fixture_id"), channel.get("subfixture_id")
    if not str(fixture).isdigit() or int(fixture) < 1:
        return None
    if sub is None or sub == "":
        return str(int(fixture))
    if not str(sub).isdigit() or int(sub) < 1:
        return None
    return f"{int(fixture)}.{int(sub)}"


def _preset_matches(row: Mapping[str, Any], reference: str) -> bool:
    preset = row.get("preset")
    parts = preset.get("no_components") if isinstance(preset, Mapping) else None
    return bool(isinstance(parts, list) and len(parts) >= 2
                and all(isinstance(x, str) and x.isdigit() for x in parts[-2:])
                and tuple(map(int, parts[-2:])) == tuple(map(int, reference.split("."))))


def _expected_channel_refs(profile: Mapping[str, Any], refs: list[str]) -> set[str]:
    fixtures = {item.get("fixture_id"): item for item in profile.get("fixtures", []) if isinstance(item, Mapping)}
    expected: set[str] = set()
    for ref in refs:
        if "." in ref:
            expected.add(ref)
        else:
            subfixtures = fixtures[int(ref)]["stage_geometry"]["subfixtures"]
            expected.add(f"{ref}.{subfixtures[0]['subfixture_id']}")
    return expected


def derive_position_application_binding(
    profile: Mapping[str, Any], preview: Mapping[str, Any], discovery: Mapping[str, Any],
) -> dict[str, Any]:
    """Future post-approval proof: exact Cue content, not command acceptance."""
    if not _fresh_resources(profile, include_sequences=True):
        raise PositionEvidenceError("FRESH_READ_ONLY_STATE_REQUIRED")
    if preview.get("schema") != PREVIEW_SCHEMA or preview.get("show_identity") != _identity(profile):
        raise PositionEvidenceError("PREVIEW_SHOW_IDENTITY_DRIFT")
    group_id = (preview.get("group") or {}).get("id")
    reference = (preview.get("preset") or {}).get("reference")
    group = _group(profile, group_id)
    refs = _exact_refs(group)
    _position_capability(profile, refs)
    preset = _preset(profile, reference)
    if (preview["group"].get("exact_refs") != refs or preview["group"].get("name") != group.get("name")
            or preview["preset"].get("label") != preset.get("name")
            or preview["preset"].get("type") != "POSITION"):
        raise PositionEvidenceError("PREVIEW_RESOURCE_IDENTITY_DRIFT")
    sequence = (preview.get("sequence") or {}).get("id")
    if (discovery.get("schema") != "zen.sequence_export_discovery.v0.1"
            or discovery.get("status") != "VERIFIED" or discovery.get("sequence_no") != sequence):
        raise PositionEvidenceError("SEQUENCE_CONTENT_UNVERIFIED")
    sha = (discovery.get("xml_discovery") or {}).get("sha256")
    if not isinstance(sha, str) or not _SHA256.fullmatch(sha):
        raise PositionEvidenceError("SEQUENCE_EXPORT_SHA_UNAVAILABLE")
    cues = discovery.get("cues")
    matching = [cue for cue in cues if isinstance(cue, Mapping) and isinstance(cue.get("number"), Mapping)
                and cue["number"].get("number") == "1" and cue["number"].get("sub_number") in (None, "", "0")]
    if len(matching) != 1:
        raise PositionEvidenceError("POC_CUE_NOT_EXACTLY_VERIFIED")
    rows = [row for part in matching[0].get("parts", []) if isinstance(part, Mapping)
            for row in part.get("cue_data", []) if isinstance(row, Mapping)]
    hits: dict[str, set[str]] = {}
    for row in rows:
        channel = row.get("channel")
        if not isinstance(channel, Mapping) or str(channel.get("attribute_name") or "").upper() not in _POSITION_ATTRIBUTES:
            continue
        if not _preset_matches(row, reference):
            continue
        ref = _row_ref(channel)
        if ref is None:
            raise PositionEvidenceError("POSITION_CHANNEL_IDENTITY_UNAVAILABLE")
        hits.setdefault(ref, set()).add(str(channel["attribute_name"]).upper())
    # Parent Group refs can map to the only verified subfixture of that body.
    expected = _expected_channel_refs(profile, refs)
    if set(hits) != expected or any(not attrs for attrs in hits.values()):
        raise PositionEvidenceError("POSITION_PRESET_CUE_CONTENT_MISMATCH")
    return {
        "schema": SCHEMA, "status": "REAL_MACHINE_CONTENT_VERIFIED",
        "show_identity": _identity(profile), "group_id": group_id,
        "group_name": group.get("name"), "fixture_refs": sorted(refs),
        "reference": reference, "preset_type": "POSITION", "preset_label": preset["name"],
        "source": "MA2_POSITION_APPLICATION_POC_SEQUENCE_EXPORT",
        "evidence": {"sequence": sequence, "cue": 1, "sequence_export_sha256": sha,
                     "matched_channel_refs": sorted(hits),
                     "observed_attributes_by_ref": {ref: sorted(attrs) for ref, attrs in sorted(hits.items())},
                     "ma2_version_family": "grandMA2_3.9"},
    }


def position_binding_matches_profile(profile: Mapping[str, Any], binding: Mapping[str, Any]) -> bool:
    """Fail closed on every resource-identity or provenance drift."""
    try:
        if not _fresh_resources(profile, include_sequences=False):
            return False
        if (binding.get("schema") != SCHEMA or binding.get("status") != "REAL_MACHINE_CONTENT_VERIFIED"
                or binding.get("source") != "MA2_POSITION_APPLICATION_POC_SEQUENCE_EXPORT"
                or binding.get("show_identity") != _identity(profile)
                or binding.get("preset_type") != "POSITION"):
            return False
        group = _group(profile, binding.get("group_id"))
        refs = _exact_refs(group)
        _position_capability(profile, refs)
        preset = _preset(profile, binding.get("reference"))
        evidence = binding.get("evidence")
        return bool(
            binding.get("group_name") == group.get("name")
            and binding.get("fixture_refs") == sorted(refs)
            and binding.get("preset_label") == preset.get("name")
            and isinstance(evidence, Mapping)
            and evidence.get("cue") == 1
            and isinstance(evidence.get("sequence"), int) and evidence["sequence"] > 0
            and isinstance(evidence.get("sequence_export_sha256"), str)
            and _SHA256.fullmatch(evidence["sequence_export_sha256"])
            and evidence.get("ma2_version_family") == "grandMA2_3.9"
            and evidence.get("matched_channel_refs") == sorted(_expected_channel_refs(profile, refs))
            and isinstance(evidence.get("observed_attributes_by_ref"), Mapping)
            and set(evidence["observed_attributes_by_ref"]) == _expected_channel_refs(profile, refs)
            and all(isinstance(attrs, list) and attrs and set(attrs) <= _POSITION_ATTRIBUTES
                    for attrs in evidence["observed_attributes_by_ref"].values())
        )
    except (PositionEvidenceError, KeyError, TypeError, ValueError):
        return False


class PositionApplicationBindingStore:
    """Local evidence cache; current Show facts remain authoritative."""

    def __init__(self, root: Path):
        self.path = root / "data" / "ZEN_POSITION_APPLICATION_BINDINGS.json"

    def has_candidates(self) -> bool:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return bool(isinstance(data, dict)
                    and data.get("schema") == "zen.position_application_binding_catalog.v0.1"
                    and isinstance(data.get("bindings"), list) and data["bindings"])

    def load_verified(self, profile: Mapping[str, Any]) -> list[dict[str, Any]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(data, dict) or data.get("schema") != "zen.position_application_binding_catalog.v0.1":
            return []
        rows = data.get("bindings")
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict) and position_binding_matches_profile(profile, row)]

    def record_after_readback(
        self, profile: Mapping[str, Any], preview: Mapping[str, Any], discovery: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Persist only an independently verified native Cue content match."""
        binding = derive_position_application_binding(profile, preview, discovery)
        rows = self.load_verified(profile)
        rows = [row for row in rows if (row.get("group_id"), row.get("reference")) !=
                (binding["group_id"], binding["reference"])]
        rows.append(binding)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"schema": "zen.position_application_binding_catalog.v0.1",
                                         "bindings": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return binding
