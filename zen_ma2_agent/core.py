from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

from .events import EventBus
from .config import save_preferences
from .diagnostics import DiagnosticReport, ShowDiagnostics
from .build_identity import load_build_identity
from .extensions import ExtensionManager
from .network import internet_online
from .router import IntentRouter, ResponseType
from .runtime import AgentRuntime
from .skill_system import SkillError, SkillRegistry
from .state.providers import AdapterResponseError, AdapterUnsupported, CueProvider, EffectProvider, ExecutorProvider, ExportFileGroupMembershipProvider, FixtureGeometryProvider, FixtureProvider, FixtureTypeExportError, FixtureTypeExportProvider, GroupMembershipProvider, GroupMembershipProviderError, GroupMembershipProviderUnavailable, GroupProvider, LayoutExportProvider, LayoutInventoryProvider, LayoutObjectResolver, PageProvider, PresetProvider, SequenceExportParseError, SequenceExportProvider, SequenceProvider, TimecodeProvider, ZenStateAdapter, fixture_type_export_batch_binding, fixture_type_reference_from_list_label
from .state.store import StateStore
from .telnet_client import ConnectionState, MA2TelnetClient
from .workflow import WorkflowPlan
from .show_program import ROOT_PHASES, ROOT_CHILD_CONTEXT_KEY, MAX_CHILD_CONTEXT_BYTES, compose_show_program_child, set_show_program_state
from .effect_builder import EffectBuildError, EffectTargetAmbiguous, resolve_effect_spec
from .allocation import AllocationError, first_free_from_front
from .effect_resources import EffectCatalog, EffectRequirement, EffectRequirementError, EffectResourceResolver, apply_effect_references, show_identity
from .cue_effect_application import GRAMMAR_ID, CueEffectApplicationCapability, CueEffectApplicationError, CueEffectApplicationSpec, ma2_response_has_error, resolve_spec
from .geometry_clone import GeometryCloneAmbiguous, GeometryCloneError, GeometryCloneSpec, format_mapping, membership_fingerprint, resolve_geometry_clone_spec
from .timecode_offset import TimecodeOffsetError, fingerprint_timecode, resolve_timecode_offset_spec
from .geometry_test_environment import (
    DESTINATION_LABEL,
    GeometryTestEnvironmentError,
    GeometryTestGroupSpec,
    PRODUCTION_SHOW,
    SOURCE_LABEL,
    TEST_SHOW,
    test_mode_enabled,
)
from .models import Intent
from .designer import FirstSongDesigner
from .designer.lean_design_mode import assemble_compact_design_context
from .designer.lean_provider import LeanDesignIntelligence, LeanDesignProviderError, build_provider_resource_contract, compile_lean_artistic_intent, invoke_primary_design
from .designer.artistic_plan import ArtisticPlanCompileError
from .artistic_resources import build_artistic_resource_map
from .position_application_evidence import (
    PositionApplicationBindingStore, PositionEvidenceError, build_position_poc_preview,
)
from .position_raw_cue_poc import (
    build_position_raw_cue_preview, verify_raw_position_cue_content,
)
from .position_calibration import (
    build_position_calibration_preview,
    calibration_application_preview,
    verify_calibration_raw_content,
)
from .designer.report import write_real_song_design_report
from .builder import FirstSongBuildError, ShowPlanBuilder
from .song_analysis import SongAnalysisAdapter, validate_song_analysis
from .cue_content_verifier import CueContentVerificationError, verify_cue_content
from .test_show_evidence import (
    bounded_test_show_color_rows,
    derive_sheesh_test_dimmer_bindings,
    derive_sheesh_test_preset_bindings,
    test_show_palette_manifest,
)
from .test_show_resources import template_effect_labels


@dataclass
class ActionRecord:
    id: str
    workflow: WorkflowPlan
    status: str = "PENDING_APPROVAL"
    result: str | None = None

    @property
    def plan(self) -> dict[str, Any]:
        return self.workflow.as_dict()


class AgentCore:
    """Single backend control boundary used by OpenClaw and headless ZEN services."""
    CHAT_ROW_LIMIT = 30

    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        group_membership_provider: GroupMembershipProvider | None = None,
        design_intelligence_provider: LeanDesignIntelligence | None = None,
        sequence_export_provider: SequenceExportProvider | None = None,
    ):
        self.runtime = runtime or AgentRuntime()
        self.build_identity = load_build_identity(self.runtime.root)
        self.events = EventBus()
        self.chat: list[dict[str, Any]] = []
        self.actions: dict[str, ActionRecord] = {}
        self.state = StateStore()
        self.group_membership_provider = group_membership_provider or ExportFileGroupMembershipProvider()
        self.design_intelligence_provider = design_intelligence_provider
        self.sequence_export_provider = (
            sequence_export_provider
            if sequence_export_provider is not None
            else SequenceExportProvider()
            if self.runtime.client_factory is MA2TelnetClient
            else None
        )
        self.fixture_type_export_provider = FixtureTypeExportProvider()
        self.layout_export_provider = LayoutExportProvider()
        self.skills = SkillRegistry(self.runtime.root)
        self.skills.discover()
        self.router = IntentRouter()
        self.extensions = ExtensionManager(self.runtime.root)
        self.progress = "Idle"
        self._last_state = ""
        self._active_action_id: str | None = None
        self._root_workflow_status: dict[str, Any] = {"state": "IDLE", "phase": "DONE", "action_id": None}
        self._internet_status = False
        self._internet_checked_at = 0.0
        self._effect_page = 0
        self.diagnostics = ShowDiagnostics()
        self.effect_catalog = EffectCatalog(self.runtime.root)
        self.effect_resources = EffectResourceResolver(self.effect_catalog)
        self.cue_effect_application_capability = CueEffectApplicationCapability(self.runtime.root)
        self.position_application_bindings = PositionApplicationBindingStore(self.runtime.root)
        self.last_diagnostics: DiagnosticReport | None = None
        self.last_chat_routing: dict[str, Any] | None = None
        self._isolated_geometry_test_loaded = False
        self.runtime.log("startup", {"build_identity": self.build_identity, "runtime_root": str(self.runtime.root)})

    def root_workflow_status(self) -> dict[str, Any]:
        return dict(self._root_workflow_status)

    def snapshot(self) -> dict[str, Any]:
        ma2 = self.runtime.preferences["ma2"]
        mode = self.runtime.preferences.get("internet_access", "AUTO")
        if mode == "OFFLINE":
            online = False
        elif mode == "ONLINE":
            online = True
        else:
            if monotonic() - self._internet_checked_at > 5:
                self._internet_status = internet_online()
                self._internet_checked_at = monotonic()
            online = self._internet_status
        return {
            "connection": {"state": self.runtime.state.value, "ready": self.runtime.ready, "status": self.runtime.status_text(), "host": ma2["host"], "port": ma2["port"], "user": self.runtime.client.authenticated_user if self.runtime.client else None},
            "internet": "ONLINE" if online else "OFFLINE",
            "progress": self.progress,
            "chat": list(self.chat[-40:]),
            "actions": [{"id": item.id, "status": item.status, "result": item.result, **item.plan} for item in self.actions.values()],
            "state_browser": self.state.summary(),
            "diagnostics": self.last_diagnostics.as_dict() if self.last_diagnostics else None,
            "skills": self.skills.list(),
            "proposals": [proposal.summary() for proposal in self.extensions.proposals.values()],
        }

    def scan_show_profile(self, output_path: Path | None = None) -> dict[str, Any]:
        """Export the current read-only StateStore as a ZEN show-profile draft.

        This method performs no refresh and never talks to the MA2 transport;
        callers choose explicitly when to collect State through existing
        allow-listed providers before scanning.
        """
        from .scanner import ShowScanner

        scanner = ShowScanner()
        profile = scanner.write(self.state, output_path) if output_path else scanner.scan(self.state)
        self.runtime.log("show_profile_scan", {"read_only": True, "output_path": str(output_path) if output_path else None})
        return profile

    def preview_first_song(self, song_input: dict[str, Any]) -> dict[str, Any]:
        """Create a typed first-song ActionPlan through the shared Core boundary."""
        return self._preview_designer_input(song_input, analysis=None)

    def preview_song_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Use structured song analysis as the only new upstream build input.

        The resulting plan deliberately follows the same Designer → Builder →
        shared approval route as the verified manual first-song PoC.
        """
        normalized = validate_song_analysis(analysis)
        return self._preview_designer_input(SongAnalysisAdapter().to_designer_input(normalized), analysis=normalized)

    def preview_cue_effect_application_poc(self, effect_id: int = 3520) -> dict[str, Any]:
        """Prepare the sole isolated real-machine Cue Effect grammar probe.

        This is a Core API for the packaged test bridge/verifier, not a
        natural-language raw-command escape hatch. Every resource is refreshed
        before the shared ActionPlan is queued for approval.
        """
        if not isinstance(effect_id, int) or effect_id < 1:
            raise CueEffectApplicationError("Cue Effect POC requires a positive Effect number.")
        self.refresh_state("effects")
        # A full inventory confirms the surrounding pool; this exact List is
        # the final freshness proof for the one Effect we are about to call.
        direct_effects = EffectProvider().parse(self.runtime.read_state(f"List Effect {effect_id}"))
        raw_effect = next((item for item in direct_effects if item.get("number") == effect_id), None)
        # StateStore keeps native Pool rows (`number`); the typed POC model
        # intentionally uses the Designer-facing `effect_id` vocabulary.
        effect = ({"effect_id": raw_effect.get("number"), "name": raw_effect.get("name")} if raw_effect else None)
        catalog_entry = next((item for item in self.effect_catalog.load().get("entries", []) if item.get("effect_id") == effect_id), None)
        target = ((catalog_entry or {}).get("requirement") or {}).get("target_ref")
        if not isinstance(target, int):
            raise CueEffectApplicationError("STALE_EFFECT_RESOURCE: Effect catalog target is unavailable.")
        self.refresh_state("groups")
        groups = self.state.get("groups")
        group = next((item for item in (groups.values if groups else []) if item.get("number") == target), None)
        membership_result = self.refresh_state("group_membership", group_no=target)
        membership = next((item for item in membership_result.get("values", []) if item.get("group_no") == target), None)
        self.refresh_state("sequences")
        sequences = self.state.get("sequences")
        spec = resolve_spec(effect=effect, catalog_entry=catalog_entry, group=group, membership=membership, sequences=list(sequences.values if sequences else []))
        intent = Intent("verify_cue_effect_application", {"cue_effect_spec": spec.summary()}, "CUE_EFFECT_APPLICATION_POC")
        workflow = self.skills.plan_intent(intent, self.state, self.runtime.preferences)
        self.runtime.log("cue_effect_application_preview", {"effect": effect_id, "target_group": spec.target_group, "sequence": spec.sequence, "cue": spec.cue_number, "grammar": GRAMMAR_ID})
        return self._queue_workflow(workflow)

    def _fresh_position_poc_profile(self, *, group_id: int, preset_ref: str) -> dict[str, Any]:
        """Read the exact POC resources from MA2, never from a cached preview."""
        if (isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1
                or not isinstance(preset_ref, str) or not re.fullmatch(r"2\.[1-9]\d*", preset_ref)):
            raise PositionEvidenceError("POSITION_POC_TARGET_INVALID")
        if not self.runtime.ready:
            raise PositionEvidenceError("MA2_CONNECTION_NOT_READY")
        for resource in ("groups", "fixtures", "fixture_geometry", "sequences", "presets"):
            result = self.refresh_state(resource)
            if result["status"] != "available":
                raise PositionEvidenceError(f"FRESH_{resource.upper()}_READ_FAILED: {result.get('error')}")
        groups = self.state.get("groups")
        for row in groups.values if groups else []:
            result = self.refresh_state("group_membership", group_no=row["number"])
            if result["status"] != "available":
                raise PositionEvidenceError(f"EXACT_GROUP_{row['number']}_READ_FAILED: {result.get('error')}")
        result = self.refresh_state("fixture_type_profiles")
        if result["status"] != "available":
            raise PositionEvidenceError(f"FIXTURE_TYPE_PROFILES_READ_FAILED: {result.get('error')}")
        # The pool inventory is not the final identity authority for the
        # selected Position object. The exact direct read must agree.
        direct = PresetProvider().parse(self.runtime.read_state(f"List Preset {preset_ref}"), "POSITION")
        profile = self.scan_show_profile()
        self._recover_bounded_test_show_evidence(profile)
        candidates = [row for row in profile["presets"] if row.get("reference") == preset_ref]
        if (len(candidates) != 1 or len(direct) != 1
                or direct[0].get("reference") != preset_ref
                or direct[0].get("preset_type") != "POSITION"
                or direct[0].get("name") != candidates[0].get("name")):
            raise PositionEvidenceError("POSITION_PRESET_DIRECT_IDENTITY_MISMATCH")
        return profile

    def _fresh_position_poc_preview(self, *, group_id: int, preset_ref: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Rebuild the exact POC from current read-only MA2 state, never cache."""
        profile = self._fresh_position_poc_profile(group_id=group_id, preset_ref=preset_ref)
        return profile, build_position_poc_preview(profile, group_id=group_id, preset_ref=preset_ref)

    def preview_position_application_poc(
        self, *, expected_show_fingerprint: str, group_id: int,
        expected_group_name: str, expected_exact_refs: list[str],
        preset_ref: str, expected_preset_label: str,
    ) -> dict[str, Any]:
        """Register one exact owner-reviewable Position Action; never execute."""
        if (not isinstance(expected_show_fingerprint, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_show_fingerprint)
                or isinstance(group_id, bool) or not isinstance(group_id, int) or group_id < 1
                or not isinstance(expected_group_name, str) or not expected_group_name
                or not isinstance(expected_exact_refs, list) or not expected_exact_refs
                or not isinstance(expected_preset_label, str) or not expected_preset_label):
            raise PositionEvidenceError("POSITION_POC_EXPECTED_IDENTITY_INVALID")
        _profile, preview = self._fresh_position_poc_preview(group_id=group_id, preset_ref=preset_ref)
        if preview["show_identity"]["value"] != expected_show_fingerprint:
            raise PositionEvidenceError("POSITION_POC_SHOW_FINGERPRINT_DRIFT")
        if (preview["group"]["name"] != expected_group_name
                or preview["group"]["exact_refs"] != expected_exact_refs):
            raise PositionEvidenceError("POSITION_POC_GROUP_IDENTITY_DRIFT")
        if preview["preset"]["label"] != expected_preset_label:
            raise PositionEvidenceError("POSITION_POC_PRESET_IDENTITY_DRIFT")
        workflow = self.skills.plan_intent(
            Intent("verify_position_application", {"position_preview": preview}, "POSITION_APPLICATION_POC"),
            self.state, self.runtime.preferences,
        )
        result = self._queue_workflow(workflow)
        action_id = result["action"]["id"]
        self._root_workflow_status = {"state": "READY", "phase": "PREVIEW", "action_id": action_id}
        result["action"].update({"root_state": "READY", "current_phase": "PREVIEW",
                                 "phase": "PREVIEW", "action_id": action_id,
                                 "preview_id": preview["preview_id"]})
        self.runtime.log("position_application_poc_preview", {
            "action_id": action_id, "preview_id": preview["preview_id"],
            "show_identity": preview["show_identity"], "group": group_id,
            "preset": preset_ref, "sequence": preview["sequence"]["id"], "ma2_writes": 0,
        })
        return result

    def _ensure_position_poc_state_unchanged(self, action: ActionRecord) -> dict[str, Any]:
        """Approval-time revalidation; a new free slot never rewrites approval."""
        approved = action.workflow.task.intent.parameters.get("position_preview")
        if not isinstance(approved, dict):
            raise PositionEvidenceError("POSITION_POC_APPROVED_PREVIEW_MISSING")
        profile, current = self._fresh_position_poc_preview(
            group_id=approved["group"]["id"], preset_ref=approved["preset"]["reference"])
        if current != approved:
            raise PositionEvidenceError("POSITION_POC_STALE_APPROVED_PREVIEW")
        self.skills.get("position.application_poc")
        return profile

    def _fresh_position_raw_profile(self, *, group_id: int) -> dict[str, Any]:
        """Refresh the raw probe's exact Show facts without relying on a Preset."""
        if group_id != 1 or isinstance(group_id, bool) or not self.runtime.ready:
            raise PositionEvidenceError("RAW_POSITION_POC_TARGET_OR_CONNECTION_INVALID")
        for resource in ("groups", "fixtures", "fixture_geometry", "sequences", "presets"):
            result = self.refresh_state(resource)
            if result["status"] != "available":
                raise PositionEvidenceError(f"FRESH_{resource.upper()}_READ_FAILED: {result.get('error')}")
        groups = self.state.get("groups")
        for row in groups.values if groups else []:
            result = self.refresh_state("group_membership", group_no=row["number"])
            if result["status"] != "available":
                raise PositionEvidenceError(f"EXACT_GROUP_{row['number']}_READ_FAILED: {result.get('error')}")
        result = self.refresh_state("fixture_type_profiles")
        if result["status"] != "available":
            raise PositionEvidenceError(f"FIXTURE_TYPE_PROFILES_READ_FAILED: {result.get('error')}")
        profile = self.scan_show_profile()
        self._recover_bounded_test_show_evidence(profile)
        return profile

    def _fresh_position_raw_preview(self, *, group_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
        profile = self._fresh_position_raw_profile(group_id=group_id)
        return profile, build_position_raw_cue_preview(profile, group_id=group_id)

    def preview_position_raw_cue_poc(
        self, *, expected_show_fingerprint: str, group_id: int,
        expected_group_name: str, expected_exact_refs: list[str],
    ) -> dict[str, Any]:
        """Register an approval-aware Raw Pan/Tilt Cue proof; Preview sends no writes."""
        if (not isinstance(expected_show_fingerprint, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_show_fingerprint)
                or group_id != 1 or isinstance(group_id, bool)
                or not isinstance(expected_group_name, str) or not expected_group_name
                or not isinstance(expected_exact_refs, list) or not expected_exact_refs
                or any(not isinstance(ref, str) for ref in expected_exact_refs)):
            raise PositionEvidenceError("RAW_POSITION_POC_EXPECTED_IDENTITY_INVALID")
        _profile, preview = self._fresh_position_raw_preview(group_id=group_id)
        if preview["show_identity"]["value"] != expected_show_fingerprint:
            raise PositionEvidenceError("RAW_POSITION_POC_SHOW_FINGERPRINT_DRIFT")
        if (preview["group"]["name"] != expected_group_name
                or preview["group"]["exact_refs"] != expected_exact_refs):
            raise PositionEvidenceError("RAW_POSITION_POC_GROUP_IDENTITY_DRIFT")
        workflow = self.skills.plan_intent(
            Intent("verify_position_raw_cue", {"position_raw_preview": preview}, "POSITION_RAW_CUE_POC"),
            self.state, self.runtime.preferences,
        )
        result = self._queue_workflow(workflow)
        action_id = result["action"]["id"]
        self._root_workflow_status = {"state": "READY", "phase": "PREVIEW", "action_id": action_id}
        result["action"].update({"root_state": "READY", "current_phase": "PREVIEW",
                                 "phase": "PREVIEW", "action_id": action_id,
                                 "preview_id": preview["preview_id"]})
        self.runtime.log("position_raw_cue_poc_preview", {
            "action_id": action_id, "preview_id": preview["preview_id"],
            "show_identity": preview["show_identity"], "group": group_id,
            "sequence": preview["sequence"]["id"], "ma2_writes": 0,
        })
        return result

    def _ensure_position_raw_state_unchanged(self, action: ActionRecord) -> dict[str, Any]:
        """Approval-time fresh check; never silently switch Sequence candidates."""
        approved = action.workflow.task.intent.parameters.get("position_raw_preview")
        if not isinstance(approved, dict):
            raise PositionEvidenceError("RAW_POSITION_POC_APPROVED_PREVIEW_MISSING")
        profile, current = self._fresh_position_raw_preview(group_id=approved["group"]["id"])
        if current != approved:
            raise PositionEvidenceError("RAW_POSITION_POC_STALE_APPROVED_PREVIEW")
        self.skills.get("position.raw_cue_poc")
        return profile

    def _fresh_position_calibration_preview(
        self, *, group_id: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        profile = self._fresh_position_raw_profile(group_id=group_id)
        return profile, build_position_calibration_preview(profile, group_id=group_id)

    def preview_position_calibration(
        self, *, expected_show_fingerprint: str, group_id: int,
        expected_group_name: str, expected_exact_refs: list[str],
    ) -> dict[str, Any]:
        """Register one efficient Raw + Preset Position calibration Action."""
        if (not isinstance(expected_show_fingerprint, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_show_fingerprint)
                or group_id != 1 or isinstance(group_id, bool)
                or not isinstance(expected_group_name, str) or not expected_group_name
                or not isinstance(expected_exact_refs, list) or not expected_exact_refs
                or any(not isinstance(ref, str) for ref in expected_exact_refs)):
            raise PositionEvidenceError("POSITION_CALIBRATION_EXPECTED_IDENTITY_INVALID")
        _profile, preview = self._fresh_position_calibration_preview(group_id=group_id)
        if preview["show_identity"]["value"] != expected_show_fingerprint:
            raise PositionEvidenceError("POSITION_CALIBRATION_SHOW_FINGERPRINT_DRIFT")
        if (preview["group"]["name"] != expected_group_name
                or preview["group"]["exact_refs"] != expected_exact_refs):
            raise PositionEvidenceError("POSITION_CALIBRATION_GROUP_IDENTITY_DRIFT")
        workflow = self.skills.plan_intent(
            Intent(
                "verify_position_calibration",
                {"position_calibration_preview": preview},
                "POSITION_CALIBRATION",
            ),
            self.state, self.runtime.preferences,
        )
        result = self._queue_workflow(workflow)
        action_id = result["action"]["id"]
        self._root_workflow_status = {
            "state": "READY", "phase": "PREVIEW", "action_id": action_id,
        }
        result["action"].update({
            "root_state": "READY", "current_phase": "PREVIEW",
            "phase": "PREVIEW", "action_id": action_id,
            "preview_id": preview["preview_id"],
        })
        self.runtime.log("position_calibration_preview", {
            "action_id": action_id,
            "preview_id": preview["preview_id"],
            "show_identity": preview["show_identity"],
            "expected_postwrite_show_identity": preview["expected_postwrite_show_identity"],
            "group": group_id,
            "preset": preview["preset"]["reference"],
            "sequence": preview["sequence"]["id"],
            "ma2_writes": 0,
        })
        return result

    def _ensure_position_calibration_state_unchanged(
        self, action: ActionRecord,
    ) -> dict[str, Any]:
        approved = action.workflow.task.intent.parameters.get(
            "position_calibration_preview"
        )
        if not isinstance(approved, dict):
            raise PositionEvidenceError("POSITION_CALIBRATION_APPROVED_PREVIEW_MISSING")
        profile, current = self._fresh_position_calibration_preview(
            group_id=approved["group"]["id"]
        )
        if current != approved:
            raise PositionEvidenceError("POSITION_CALIBRATION_STALE_APPROVED_PREVIEW")
        self.skills.get("position.calibration")
        return profile

    def _preview_designer_input(self, song_input: dict[str, Any], *, analysis: dict[str, Any] | None) -> dict[str, Any]:
        # A First Song/Effect-resource resolution needs pool identities, not a
        # full Subfixture geometry sweep. Geometry remains available from a
        # prior scan but must not turn an Effect-only Preview into hundreds of
        # unrelated List Fixture reads.
        for resource, kwargs in (("groups", {}), ("fixtures", {}), ("presets", {"sequence": "ALL"}), ("effects", {}), ("sequences", {}), ("executors", {})):
            self.refresh_state(resource, **kwargs)
        data_dir = self.runtime.root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        profile = self.scan_show_profile(data_dir / "ZEN_SHOW_PROFILE.json")
        if analysis is not None:
            (data_dir / "ZEN_SONG_ANALYSIS.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        show_plan = FirstSongDesigner().design(song_input, profile)
        effect_requirements = show_plan.get("effect_requirements") or {}
        if effect_requirements:
            resolutions = {
                str(identifier): self.effect_resources.resolve(requirement, profile=profile)
                for identifier, requirement in effect_requirements.items()
            }
            creation = next((item for item in resolutions.values() if item.status == "CREATE_REQUIRED"), None)
            if creation:
                workflow = self._plan_effect_requirement(creation, profile, show_plan)
                self.runtime.log("effect_resource_resolution", {"status": creation.status, "requirement": creation.requirement.summary(), "show_identity": show_identity(profile)})
                return self._queue_workflow(workflow)
            unresolved = [item for item in resolutions.values() if item.status != "EXISTING_MATCH"]
            if unresolved:
                details = "; ".join(f"{item.requirement.semantic_label}: {item.status}" for item in unresolved)
                raise EffectRequirementError("Effect resource resolution is blocked: " + details)
            show_plan = apply_effect_references(show_plan, resolutions)
            # The catalog is never sufficient on its own.  A full inventory is
            # fresh enough for matching, then every chosen resource gets a
            # direct List proof before it may enter an executable Show Plan.
            self._fresh_verify_effect_references(show_plan)
            # Only a completed isolated real-machine POC can enable the
            # compiler-side CALL_EFFECT grammar. Designer remains entirely
            # declarative and never receives this transport detail.
            capability = self.cue_effect_application_capability.load_verified()
            if capability:
                show_plan["effect_application_capability"] = capability
            self.runtime.log("effect_resource_resolution", {"status": "EXISTING_MATCH", "requirements": [item.summary() for item in resolutions.values()], "show_identity": show_identity(profile)})
        (data_dir / "ZEN_SHOW_PLAN.json").write_text(json.dumps(show_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_real_song_design_report(show_plan, profile, self.runtime.root / "ZEN_REAL_SONG_DESIGN_REPORT.md")
        context = {key: profile.get(key, []) for key in ("groups", "presets", "effects", "sequences", "executors")}
        workflow = self.skills.plan_intent(Intent("build_first_song", {"first_song_spec": {"show_plan": show_plan, "profile": context}}, "ZEN_SHOW_PLAN"), self.state, self.runtime.preferences)
        self.runtime.log("song_analysis_preview" if analysis is not None else "first_song_preview", {"song": show_plan["song"], "cue_count": len(show_plan["cues"]), "sequence_range": show_plan["active_sequence_range"], "analysis_schema": analysis.get("schema") if analysis else None})
        return self._queue_workflow(workflow)

    def _queue_workflow(self, workflow: WorkflowPlan) -> dict[str, Any]:
        """Store a prepared workflow in the same approval registry as Chat plans."""
        if not workflow.executable:
            message = workflow.preview_note + "\n\nExecution: Disabled — " + workflow.verification_strategy
            self.chat.append({"role": "assistant", "kind": ResponseType.ACTION_PLAN.value, "text": message})
            self.progress = "Idle"
            self.events.emit("plan", self.snapshot())
            return {"type": ResponseType.ACTION_PLAN.value, "message": message, "action": {"id": None, "status": "PREVIEW_ONLY", **workflow.as_dict()}}
        action_id = uuid.uuid4().hex[:12]
        if self._active_action_id:
            previous = self.actions.get(self._active_action_id)
            if previous and previous.status == "PENDING_APPROVAL":
                previous.status = "CANCELLED"
        record = ActionRecord(action_id, workflow)
        self.actions[action_id] = record
        self._active_action_id = action_id
        self.chat.append({"role": "assistant", "kind": ResponseType.ACTION_PLAN.value, "text": workflow.preview_note, "action_id": action_id})
        self.progress = "Waiting for approval"
        self.events.emit("plan", self.snapshot())
        return {"type": ResponseType.ACTION_PLAN.value, "message": workflow.preview_note, "action": {"id": action_id, "status": record.status, **record.plan}}

    def tick(self) -> None:
        self.runtime.poll_connection()
        state = self.runtime.status_text()
        if state != self._last_state:
            self._last_state = state
            self.events.emit("connection", self.snapshot())

    def connect(self, host: str, port: object, username: str, password: str = "") -> str:
        response = self.runtime.connect(host, port, username, password)
        self.events.emit("connection", self.snapshot())
        return response

    def disconnect(self) -> None:
        self.runtime.disconnect()
        for resource in self.state.RESOURCES:
            self.state.mark_stale(resource)
        self.events.emit("connection", self.snapshot())

    def set_internet_access(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"AUTO", "OFFLINE", "ONLINE"}:
            raise ValueError("Internet access must be AUTO, OFFLINE, or ONLINE.")
        self.runtime.preferences["internet_access"] = mode
        save_preferences(self.runtime.preferences, self.runtime.root)
        self.events.emit("internet", self.snapshot())

    def refresh_state(self, resource: str, *, group_no: int | None = None, layout_no: int | None = None, sequence: int | None = None) -> dict[str, Any]:
        """Refresh a named read-only state resource through an allow-listed provider."""
        self.progress = f"Reading MA2 {resource.title()}"
        try:
            if resource == "groups":
                provider = GroupProvider()
                snapshot = self.state.put_groups(provider.parse(self.runtime.read_state(provider.command)))
            elif resource == "fixtures":
                provider = FixtureProvider()
                snapshot = self.state.put_fixtures(provider.parse(self.runtime.read_state(provider.command)))
            elif resource == "fixture_geometry":
                if not self.state.get("fixtures"):
                    self.refresh_state("fixtures")
                provider = FixtureGeometryProvider()
                values, capability = provider.collect(self.runtime)
                snapshot = self.state.put(resource, values, source=provider.source, capability=capability)
            elif resource == "fixture_type_profiles":
                if not self.state.get("fixtures"):
                    self.refresh_state("fixtures")
                fixtures = self.state.get("fixtures")
                labels = sorted({str(item.get("fixture_type") or "").strip() for item in (fixtures.values if fixtures else []) if str(item.get("fixture_type") or "").strip()})
                if not labels:
                    raise FixtureTypeExportError("FIXTURE_TYPE_LIST_ID_UNAVAILABLE")

                # The current Show fingerprint deliberately excludes FixtureType
                # profiles, so it is safe to compare before/after this read-only
                # export batch without the batch changing its own identity.
                identity_before = self.scan_show_profile().get("show_identity")
                values = []
                for label in labels:
                    try:
                        values.append(self.fixture_type_export_provider.export_and_bind(self.runtime, label, self.runtime.preferences.get("state_adapter")))
                    except (FixtureTypeExportError, GroupMembershipProviderUnavailable) as exc:
                        # A FixtureType failure must not erase already captured
                        # Show-bound records from the same fresh run.  It is an
                        # explicit, fail-closed per-type result, never a
                        # capability inferred from a similar local profile.
                        try:
                            identity = fixture_type_reference_from_list_label(label)
                        except FixtureTypeExportError:
                            identity = {"list_label": label}
                        values.append({
                            "schema": "zen.fixture_type_channel_profile.v0.1",
                            "read_only": True,
                            "status": "UNSUPPORTED" if isinstance(exc, GroupMembershipProviderUnavailable) else "PARTIAL",
                            "source": self.fixture_type_export_provider.source,
                            "fixture_type": identity,
                            "failure_reason": str(exc),
                            "export_diagnostic": getattr(exc, "diagnostic", None),
                            "export": getattr(exc, "export", None),
                        })

                identity_after = self.scan_show_profile().get("show_identity")
                compound_status = "NOT_ATTEMPTED"
                compound_failure_reason = None
                if identity_before == identity_after:
                    try:
                        values = fixture_type_export_batch_binding(values, show_identity_match="MATCH")
                        compound_status = "SHOW_BOUND_VERIFIED"
                    except FixtureTypeExportError as exc:
                        # Preserve the strict per-type results. Compound identity
                        # is an additional proof path, never a fallback guess.
                        compound_status = "PARTIAL"
                        compound_failure_reason = str(exc)
                else:
                    compound_status = "PARTIAL"
                    compound_failure_reason = "CURRENT_SHOW_IDENTITY_MISMATCH"

                verified_count = sum(item.get("status") == "SHOW_BOUND_VERIFIED" for item in values)
                capability = self.fixture_type_export_provider.capabilities(self.runtime, self.runtime.preferences.get("state_adapter")) | {
                    "binding_status": "SHOW_BOUND_VERIFIED" if verified_count == len(values) else "PARTIAL" if verified_count else "UNSUPPORTED",
                    "verified_fixture_type_count": verified_count,
                    "unresolved_fixture_type_count": len(values) - verified_count,
                    "compound_identity_status": compound_status,
                    "compound_identity_failure_reason": compound_failure_reason,
                }
                snapshot = self.state.put(resource, values, source=self.fixture_type_export_provider.source, capability=capability)
            elif resource == "sequences":
                provider = SequenceProvider()
                snapshot = self.state.put("sequences", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list")
            elif resource == "presets":
                provider = PresetProvider(); preset_type = "ALL" if sequence is None else str(sequence).upper()
                values = provider.parse(self.runtime.read_state(provider.command(preset_type)), preset_type)
                existing = self.state.get("presets")
                # `List Preset All` supersedes every cached pool row; retaining
                # typed rows here duplicates state on each full scan and makes
                # a session fingerprint depend on refresh count.
                retained = [] if preset_type == "ALL" else [item for item in (existing.values if existing else []) if item.get("preset_type") != preset_type]
                snapshot = self.state.put("presets", [*retained,*values], source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "effects":
                provider=EffectProvider(); values=provider.parse(self.runtime.read_state(provider.command)); diagnostics=provider.diagnostics(values); self.runtime.log("effect_inventory_diagnostic", diagnostics); snapshot=self.state.put("effects", values, source="ma2_telnet_list", capability={"requires_local_filesystem":False,"diagnostics":diagnostics})
            elif resource == "timecodes":
                provider = TimecodeProvider()
                snapshot = self.state.put("timecodes", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability=provider.capability())
            elif resource == "pages":
                provider=PageProvider(); snapshot=self.state.put("pages", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "executors":
                provider=ExecutorProvider(); snapshot=self.state.put("executors", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "cues":
                if not isinstance(sequence, int) or sequence < 1:
                    raise ValueError("Cue inventory requires a positive sequence number.")
                provider = CueProvider()
                cues = provider.parse(self.runtime.read_state(provider.command(sequence)), sequence)
                existing = self.state.get("cues")
                retained = [item for item in (existing.values if existing else []) if item.get("sequence") != sequence]
                snapshot = self.state.put("cues", [*retained, *cues], source="ma2_telnet_list")
            elif resource == "layouts" and layout_no is None:
                provider = LayoutInventoryProvider()
                snapshot = self.state.put("layouts", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list")
            elif resource == "group_membership":
                if not isinstance(group_no, int) or isinstance(group_no, bool) or group_no < 1:
                    raise ValueError("Group membership requires a positive group number.")
                value = self.group_membership_provider.get_group_membership(
                    self.runtime,
                    group_no,
                    self.runtime.preferences.get("state_adapter"),
                )
                snapshot = self.state.upsert(resource, "group_no", value, source=self.group_membership_provider.source)
            elif resource == "layout_items":
                if not isinstance(layout_no, int) or isinstance(layout_no, bool) or layout_no < 1: raise ValueError("Layout requires a positive number.")
                value=self.layout_export_provider.get_layout(self.runtime, layout_no, self.runtime.preferences.get("state_adapter"))
                snapshot=self.state.upsert(resource,"layout",value,source=self.layout_export_provider.source,capability=self.layout_export_provider.capabilities(self.runtime,self.runtime.preferences.get("state_adapter")))
            elif resource in {"selection", "programmer"}:
                adapter = ZenStateAdapter()
                request, parser = self._adapter_state_request(resource, group_no=group_no, layout_no=layout_no)
                settings = self.runtime.preferences.get("state_adapter")
                output = self.runtime.read_adapter_state(
                    plugin_slot=adapter.plugin_slot(settings),
                    request=request.wire,
                    timeout_seconds=adapter.timeout_seconds(settings),
                )
                value = parser(adapter, output, request)
                snapshot = self.state.put(resource, [value], source=adapter.source)
            else:
                raise ValueError(f"State resource is not implemented: {resource}")
        except AdapterUnsupported as exc:
            snapshot = self.state.record_error(resource, str(exc), source=ZenStateAdapter.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "UNSUPPORTED", "error": snapshot.error}
        except AdapterResponseError as exc:
            snapshot = self.state.record_error(resource, str(exc), source=ZenStateAdapter.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "ERROR", "error": snapshot.error}
        except GroupMembershipProviderUnavailable as exc:
            source = self.fixture_type_export_provider.source if resource == "fixture_type_profiles" else self.group_membership_provider.source
            snapshot = self.state.record_error(resource, f"UNSUPPORTED {exc}", source=source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "UNSUPPORTED", "error": snapshot.error}
        except GroupMembershipProviderError as exc:
            source = self.fixture_type_export_provider.source if resource == "fixture_type_profiles" else self.group_membership_provider.source
            snapshot = self.state.record_error(resource, str(exc), source=source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "ERROR", "error": snapshot.error}
        self.progress = "Idle"
        self.events.emit("state", self.snapshot())
        return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "available"}

    @staticmethod
    def _adapter_state_request(resource: str, *, group_no: int | None, layout_no: int | None) -> tuple[Any, Any]:
        if resource == "selection":
            return ZenStateAdapter.request("selection"), lambda adapter, output, request: adapter.unsupported_resource(output, request)
        if resource == "programmer":
            return ZenStateAdapter.request("programmer"), lambda adapter, output, request: adapter.unsupported_resource(output, request)
        raise ValueError(f"No adapter request for state resource: {resource}")

    def request_group_membership(self, group_no: int) -> dict[str, Any]:
        groups = self.state.get("groups")
        if not groups or groups.stale or groups.error:
            self.refresh_state("groups")
        result = self.refresh_state("group_membership", group_no=group_no)
        result["group"] = next((item for item in result["values"] if item.get("group_no") == group_no), None)
        return result

    def get_selection(self) -> dict[str, Any]:
        result = self._unsupported_inspect_result("selection")
        result["selection"] = result["values"][0] if result["values"] else None
        return result

    def get_programmer_summary(self) -> dict[str, Any]:
        result = self._unsupported_inspect_result("programmer")
        result["programmer"] = result["values"][0] if result["values"] else None
        return result

    def _unsupported_inspect_result(self, resource: str) -> dict[str, Any]:
        """Return an explicit read-only capability gap without probing MA2.

        grandMA2 3.9's verified Lua API has no non-mutating accessor for the
        current fixture selection or Programmer's active values.  Never fall
        back to selecting fixtures, creating temporary objects, or clearing the
        Programmer merely to answer an inspect request.
        """
        details = {
            "selection": {
                "error": "UNSUPPORTED selection: no verified non-mutating MA2 3.9 accessor exposes current fixture members.",
                "capability": {"selection_presence": "unsupported", "selection_members": "unsupported", "subfixtures": "unsupported"},
            },
            "programmer": {
                "error": "UNSUPPORTED programmer: no verified non-mutating MA2 3.9 accessor exposes Programmer presence, members, attributes, or values.",
                "capability": {"programmer_presence": "unsupported", "programmer_members": "unsupported", "programmer_attributes": "unsupported", "programmer_values": "unsupported"},
            },
        }[resource]
        snapshot = self.state.record_error(resource, details["error"], source="ma2_3_9_verified_api_gap", capability=details["capability"])
        self.progress = "Idle"
        self.events.emit("state", self.snapshot())
        return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "UNSUPPORTED", "error": snapshot.error, "capability": snapshot.capability}

    def set_skill_enabled(self, skill_id: str, enabled: bool) -> dict[str, Any]:
        manifest = self.skills.set_enabled(skill_id, enabled)
        self.events.emit("skills", self.snapshot())
        return manifest.summary()

    def propose_skill(self, name: str, intent: str, required_state: list[str], safety: str) -> dict[str, Any]:
        proposal = self.extensions.propose(name, intent, required_state, safety)
        self.events.emit("proposal", self.snapshot())
        return proposal.summary()

    def install_skill_proposal(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.extensions.install(proposal_id)
        self.skills.discover()
        self.events.emit("skills", self.snapshot())
        return proposal.summary()

    def handle_request(self, text: str, source: str = "desktop") -> dict[str, Any]:
        """Shared Desktop/Mobile natural-language routing entrypoint."""
        self.chat.append({"role": "user", "source": source, "text": text})
        self.progress = "Understanding request"
        self.events.emit("progress", {"stage": self.progress})
        route = self.router.route(text, self.skills)
        self.last_chat_routing = {
            "CHAT_INPUT": text,
            "ROUTER_INTENT": route.intent.kind if route.intent else None,
            "ROUTER_PARAMETERS": route.intent.parameters if route.intent else None,
            "ROUTER_HANDLER": "state_answer" if route.response_type is ResponseType.ANSWER else route.response_type.value,
            "PROVIDER": self._provider_for_intent(route.intent),
        }
        self.runtime.log("chat_routing", self.last_chat_routing)
        if route.response_type is ResponseType.NEEDS_CLARIFICATION:
            return self._respond(ResponseType.NEEDS_CLARIFICATION, "I understand this needs an MA2 workflow, but need a target or action. For example: ‘選 Group HYBRID’, ‘有哪些 Group’, or ‘複製 Group 1 到 2’.")
        if route.response_type is ResponseType.NOT_IMPLEMENTED:
            assert route.intent and route.capability
            message = (f"Request: {route.normalized_text}\nIntent: {route.intent.kind}\n"
                       f"Matched capability: {route.capability.name}\nStatus: NOT IMPLEMENTED\n"
                       f"Safety: {route.capability.safety}\n"
                       f"Proposed next step: Enable, install, or implement the {route.capability.name} workflow.")
            return self._respond(ResponseType.NOT_IMPLEMENTED, message, intent=route.intent, capability=route.capability.id)
        if route.response_type is ResponseType.ANSWER:
            assert route.intent
            return self._answer_state(route.intent)
        try:
            assert route.intent
            workflow = self._plan_routed_intent(route.intent)
            self.runtime.log("workflow_preview", workflow.as_dict())
        except (EffectTargetAmbiguous, GeometryCloneAmbiguous) as exc:
            return self._respond(ResponseType.NEEDS_CLARIFICATION, str(exc), intent=route.intent)
        except (SkillError, ConnectionError, EffectBuildError, GeometryCloneError, TimecodeOffsetError, GeometryTestEnvironmentError, ValueError) as exc:
            return self._respond(ResponseType.ERROR, str(exc) or "Unable to prepare a safe workflow.", intent=route.intent)
        if not workflow.executable:
            message = workflow.preview_note + "\n\nExecution: Disabled pending safe real-machine Clone write validation."
            self.chat.append({"role": "assistant", "kind": ResponseType.ACTION_PLAN.value, "text": message})
            self.progress = "Idle"
            self.events.emit("plan", self.snapshot())
            return {"type": ResponseType.ACTION_PLAN.value, "message": message, "action": {"id": None, "status": "PREVIEW_ONLY", **workflow.as_dict()}}
        action_id = uuid.uuid4().hex[:12]
        if self._active_action_id:
            previous = self.actions.get(self._active_action_id)
            if previous and previous.status == "PENDING_APPROVAL":
                previous.status = "CANCELLED"
        record = ActionRecord(action_id, workflow)
        self.actions[action_id] = record
        self._active_action_id = action_id
        response = workflow.preview_note if workflow.task.skill_id in {"effects.builder", "timecode.offset", "clone.geometry", "geometry.test_environment"} else "Workflow plan ready for review." if workflow.executable else workflow.preview_note
        self.chat.append({"role": "assistant", "kind": ResponseType.ACTION_PLAN.value, "text": response, "action_id": action_id})
        self.progress = "Waiting for approval"
        self.events.emit("plan", self.snapshot())
        return {"type": ResponseType.ACTION_PLAN.value, "message": response, "action": {"id": action_id, "status": record.status, **record.plan}}

    def _collect_lean_design_profile(self) -> dict[str, Any]:
        """Build the normalized read-only profile used by the lean Designer."""
        if self.runtime.ready:
            for resource, kwargs in (
                ("groups", {}),
                ("fixtures", {}),
                ("presets", {"sequence": "ALL"}),
                ("effects", {}),
                ("sequences", {}),
                ("executors", {}),
            ):
                self.refresh_state(resource, **kwargs)
            if self.position_application_bindings.has_candidates():
                # Exact parent/subfixture applicability needs geometry identity.
                # Ordinary shows without Position evidence avoid this extra scan.
                self.refresh_state("fixture_geometry")
            groups = self.state.get("groups")
            for item in (groups.values if groups else []):
                number = item.get("number")
                if isinstance(number, int) and not isinstance(number, bool) and number > 0:
                    self.refresh_state("group_membership", group_no=number)
            # Fixture-type capability is useful to the resource map but remains
            # read-only and fail-closed when native export is unavailable.
            try:
                self.refresh_state("fixture_type_profiles")
            except (FixtureTypeExportError, GroupMembershipProviderUnavailable, GroupMembershipProviderError):
                pass

        profile = self.scan_show_profile()
        if not profile.get("groups") or not profile.get("fixtures"):
            raise ValueError(
                "Read-only show discovery is required before lean design can continue."
            )
        return profile

    def _recover_bounded_test_show_evidence(
        self,
        profile: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Recover only the already-proven SHEESH Test Show resource evidence.

        This path is deliberately narrow. It performs fresh exact Preset reads
        only for the committed Build 001 Color manifest, then delegates all
        Sequence identity and exact Group-membership checks to the existing
        fail-closed evidence adapters.
        """
        plan_path = self.runtime.root / "data" / "zen_real_ma2_test_show_sheesh_001_plan.json"
        if not plan_path.is_file():
            return [], []
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return [], []
        if not isinstance(plan, dict):
            return [], []

        readbacks: dict[str, str] = {}
        if self.runtime.ready:
            for reference in test_show_palette_manifest(plan):
                try:
                    readbacks[reference] = self.runtime.read_state(f"List Preset {reference}")
                except (ConnectionError, PermissionError, ValueError):
                    continue

        rows = bounded_test_show_color_rows(plan, readbacks)
        if rows:
            merged = {
                str(item.get("reference") or ""): item
                for item in profile.get("presets", [])
                if isinstance(item, dict) and item.get("reference")
            }
            for row in rows:
                merged[row["reference"]] = row
            profile["presets"] = list(merged.values())
            profile["show_identity"] = show_identity(profile)

        preset_recovery = derive_sheesh_test_preset_bindings(profile, plan)
        dimmer_recovery = derive_sheesh_test_dimmer_bindings(profile, plan)
        preset_bindings = [
            item
            for item in preset_recovery.get("bindings", [])
            if isinstance(item, dict)
        ]
        dimmer_bindings = [
            item
            for item in dimmer_recovery.get("bindings", [])
            if isinstance(item, dict)
        ]
        self.runtime.log(
            "bounded_test_show_evidence_recovery",
            {
                "preset_status": preset_recovery.get("status"),
                "preset_binding_count": len(preset_bindings),
                "dimmer_status": dimmer_recovery.get("status"),
                "dimmer_binding_count": len(dimmer_bindings),
                "bounded_color_readback_count": len(rows),
                "show_identity": profile.get("show_identity"),
            },
        )
        return preset_bindings, dimmer_bindings

    def _recover_bounded_template_effect_inventory(
        self,
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Promote only reserved Test Show template Effects from fresh QTY proof."""
        if not self.runtime.ready:
            return []
        reserved = {label.upper() for label in template_effect_labels()}
        provider = EffectProvider()
        evidence: list[dict[str, Any]] = []
        for row in profile.get("effects", []) if isinstance(profile.get("effects"), list) else []:
            if not isinstance(row, dict):
                continue
            label = str(row.get("name") or "").strip().upper()
            effect_id = row.get("effect_id")
            if (
                label not in reserved
                or isinstance(effect_id, bool)
                or not isinstance(effect_id, int)
                or effect_id < 1
            ):
                continue
            try:
                raw = self.runtime.read_state(f"List Effect 1.{effect_id}.*")
            except (ConnectionError, PermissionError, ValueError):
                continue
            detail = provider.parse_template_detail(raw)
            evidence.append({
                "effect_id": effect_id,
                "name": row.get("name"),
                "detail": detail,
            })
            if detail.get("status") == "VERIFIED" and detail.get("kind") == "TEMPLATE":
                row["kind"] = "TEMPLATE"
                row["template_detail"] = detail
        self.runtime.log(
            "bounded_template_effect_recovery",
            {
                "candidate_count": len(evidence),
                "verified_template_count": sum(
                    1
                    for item in evidence
                    if isinstance(item.get("detail"), dict)
                    and item["detail"].get("status") == "VERIFIED"
                    and item["detail"].get("kind") == "TEMPLATE"
                ),
                "show_identity": profile.get("show_identity"),
            },
        )
        return evidence

    def _plan_lean_design_child(self, root: WorkflowPlan, request: str) -> WorkflowPlan:
        """Run one injected artistic call, compile it, then reuse show.builder."""
        if self.design_intelligence_provider is None:
            raise ValueError("No design intelligence provider is configured.")

        profile = self._collect_lean_design_profile()
        effect_application = self.cue_effect_application_capability.load_verified()
        preset_bindings, dimmer_bindings = self._recover_bounded_test_show_evidence(profile)
        # A cached Position proof is useful only with fresh exact current-Show
        # identity and direct current Preset ref/type/label readback. This
        # never creates an application binding or touches MA2 Show state.
        for binding in self.position_application_bindings.load_verified(profile):
            reference = binding["reference"]
            try:
                current = PresetProvider().parse(self.runtime.read_state(f"List Preset {reference}"), "POSITION")
            except (ConnectionError, PermissionError, ValueError):
                continue
            if (len(current) == 1 and current[0].get("reference") == reference
                    and current[0].get("preset_type") == "POSITION"
                    and current[0].get("name") == binding["preset_label"]):
                preset_bindings.append(binding)
        self._recover_bounded_template_effect_inventory(profile)
        resource_map = build_artistic_resource_map(
            profile,
            preset_bindings=preset_bindings,
            dimmer_bindings=dimmer_bindings,
            effect_catalog_entries=self.effect_catalog.load().get("entries", []),
            effect_application_capability=effect_application,
        )
        compact = assemble_compact_design_context(
            song_context={"song": request, "brief": request},
            groups=profile.get("groups", []),
            presets=profile.get("presets", []),
            effects=profile.get("effects", []),
            capability_profiles=profile.get("fixture_type_profiles", []),
            artistic_resource_map=resource_map,
        )
        design_context = dict(compact["context"])
        design_context["verified_resource_contract"] = build_provider_resource_contract(resource_map)

        provider_output = invoke_primary_design(self.design_intelligence_provider, request, design_context)
        compiled, audit = compile_lean_artistic_intent(
            provider_output,
            request=request,
            resource_map=resource_map,
            active_sequence_range=(301, 400),
            target_executor="2.001",
        )
        if effect_application and any(
            action.get("operation") == "CALL_EFFECT"
            for cue in compiled.get("cues", [])
            for action in cue.get("actions", [])
            if isinstance(action, dict)
        ):
            compiled["effect_application_capability"] = effect_application

        builder_profile = {
            key: profile.get(key, [])
            for key in ("groups", "presets", "effects", "sequences", "executors")
        }
        child = self.skills.plan_intent(
            Intent(
                "build_first_song",
                {"first_song_spec": {"show_plan": compiled, "profile": builder_profile}},
                "LEAN_SINGLE_DESIGNER",
            ),
            self.state,
            self.runtime.preferences,
        )
        self.runtime.log(
            "lean_design",
            {
                "provider": "injected",
                "primary_call_count": 1,
                "audit": audit,
                "context_hash": compact["context_hash"],
            },
        )
        return compose_show_program_child(root, child)

    def _plan_routed_intent(self, intent: Intent) -> WorkflowPlan:
        """Plan one already-routed intent through the existing safe child planners."""
        if intent.kind == "build_dimmer_chase":
            return self._plan_effect_builder(intent)
        if intent.kind == "offset_timecode":
            return self._plan_timecode_offset(intent)
        if intent.kind == "timecode_test_setup":
            return self._plan_timecode_test_setup(intent)
        if intent.kind == "geometry_test_setup_groups":
            return self._plan_geometry_test_groups(intent)
        if intent.kind == "geometry_test_load_show":
            return self.skills.plan_intent(intent, self.state, self.runtime.preferences)
        if intent.kind == "geometry_test_restore_show":
            if not self._isolated_geometry_test_loaded:
                raise GeometryTestEnvironmentError(
                    "Production restore is available only after this process loaded the isolated Geometry test show."
                )
            return self.skills.plan_intent(intent, self.state, self.runtime.preferences)
        if intent.kind == "geometry_clone":
            return self._plan_geometry_clone(intent)
        return self.skills.plan_intent(intent, self.state, self.runtime.preferences)

    def program_show_request(self, request: str, source: str = "operator") -> dict[str, Any]:
        """Plan the normal root workflow without executing it."""
        if not isinstance(request, str) or not request.strip() or len(request) > 2048:
            raise ValueError("request must be a non-empty bounded string")

        root_intent = Intent("program_show", {"request": request}, request)
        root = self.skills.plan_intent(root_intent, self.state, self.runtime.preferences)
        route = self.router.route(request, self.skills)

        if route.response_type is ResponseType.NEEDS_CLARIFICATION:
            if self.design_intelligence_provider is None:
                workflow = set_show_program_state(root, "NEEDS_INTELLIGENCE", "The request needs bounded design intelligence before a child workflow can be selected.", phase="UNDERSTAND")
            else:
                try:
                    workflow = self._plan_lean_design_child(root, request)
                except (FirstSongBuildError, SkillError, ArtisticPlanCompileError, LeanDesignProviderError, ValueError) as exc:
                    workflow = set_show_program_state(root, "NEEDS_RESEARCH", str(exc) or "Lean design could not be safely compiled.", phase="RESEARCH_IF_NEEDED")
        elif route.response_type is ResponseType.NOT_IMPLEMENTED:
            workflow = set_show_program_state(
                root,
                "NEEDS_RESEARCH",
                "The request matches a known capability that is not currently executable.",
                phase="RESEARCH_IF_NEEDED",
            )
        elif route.response_type is ResponseType.ANSWER:
            workflow = set_show_program_state(
                root,
                "NEEDS_INPUT",
                "This request resolves to a read-only query; use the read-only operator tools.",
                phase="DISCOVER",
            )
        else:
            assert route.intent is not None
            try:
                child = self._plan_routed_intent(route.intent)
                workflow = compose_show_program_child(root, child)
            except (EffectTargetAmbiguous, GeometryCloneAmbiguous) as exc:
                workflow = set_show_program_state(root, "NEEDS_INPUT", str(exc), phase="RESOLVE")
            except (SkillError, ConnectionError, EffectBuildError, GeometryCloneError, TimecodeOffsetError, GeometryTestEnvironmentError, ValueError) as exc:
                workflow = set_show_program_state(
                    root,
                    "NEEDS_INPUT",
                    str(exc) or "Unable to prepare a safe child workflow.",
                    phase="DISCOVER",
                )

        self._root_workflow_status = {
            "state": workflow.root_state or ("READY" if workflow.executable else "NEEDS_INPUT"),
            "phase": workflow.current_phase or ROOT_PHASES[0],
            "action_id": None,
        }
        self.runtime.log("root_workflow", workflow.as_dict())

        if not workflow.executable:
            self.events.emit("plan", self.snapshot())
            return {
                "type": ResponseType.ACTION_PLAN.value,
                "message": workflow.preview_note,
                "action": {"id": None, "status": "ROOT_WORKFLOW", **workflow.as_dict()},
            }

        action_id = uuid.uuid4().hex[:12]
        if self._active_action_id and self.actions.get(self._active_action_id):
            self.actions[self._active_action_id].status = "CANCELLED"
        record = ActionRecord(action_id, workflow)
        self.actions[action_id] = record
        self._active_action_id = action_id
        self._root_workflow_status.update(
            {"state": "PENDING_APPROVAL", "phase": "PREVIEW", "action_id": action_id}
        )
        self.progress = "Waiting for approval"
        self.events.emit("plan", self.snapshot())
        return {
            "type": ResponseType.ACTION_PLAN.value,
            "message": workflow.preview_note,
            "action": {"id": action_id, "status": record.status, **record.plan},
        }

    def preview_action(self, action_id: str | None = None) -> dict[str, Any]:
        selected = action_id or self._active_action_id
        if not selected or selected not in self.actions:
            return {"status": "NO_PREVIEW", "action": None}
        record = self.actions[selected]
        action = {"id": record.id, **record.plan}
        if record.workflow.task.intent.kind in {"verify_position_application", "verify_position_raw_cue"}:
            key = ("position_preview" if record.workflow.task.intent.kind == "verify_position_application"
                   else "position_raw_preview")
            preview = record.workflow.task.intent.parameters[key]
            action.update({"action_id": record.id, "preview_id": preview["preview_id"],
                           "phase": "PREVIEW" if record.status == "PENDING_APPROVAL" else record.status})
        return {"status": record.status, "action": action}

    def _plan_effect_builder(self, intent: Any) -> WorkflowPlan:
        """Refresh only the inventories needed to bind a safe EffectSpec."""
        parameters = intent.parameters
        target_type = parameters.get("target_type")
        if target_type in {"group_number", "group_name"}:
            groups = self.state.get("groups")
            if not groups or groups.stale or groups.error:
                self.refresh_state("groups")
        elif target_type == "fixture_number":
            fixtures = self.state.get("fixtures")
            if not fixtures or fixtures.stale or fixtures.error:
                self.refresh_state("fixtures")
        else:
            raise EffectBuildError("Dimmer Chase requires a Group name, Group number, or Fixture number.")
        effects = self.state.get("effects")
        if not effects or effects.stale or effects.error:
            self.refresh_state("effects")
        groups = self.state.get("groups")
        fixtures = self.state.get("fixtures")
        effects = self.state.get("effects")
        spec = resolve_effect_spec(
            intent,
            groups=list(groups.values if groups else []),
            fixtures=list(fixtures.values if fixtures else []),
            effects=list(effects.values if effects else []),
        )
        bound = Intent(intent.kind, {**intent.parameters, "effect_spec": spec.summary()}, intent.source_text)
        return self.skills.plan_intent(bound, self.state, self.runtime.preferences)

    def _plan_effect_requirement(self, resolution: Any, profile: dict[str, Any], show_plan: dict[str, Any]) -> WorkflowPlan:
        """Make Effect creation its own approved phase before a Sequence build.

        The continuation is deliberately explicit: after verification the
        caller re-previews the typed song plan.  This avoids treating approval
        for a new Effect as approval for all later Cue writes.
        """
        if resolution.status != "CREATE_REQUIRED" or not resolution.effect_spec:
            raise EffectRequirementError("Effect creation requires a resolved CREATE_REQUIRED specification.")
        spec = resolution.effect_spec
        identity = show_identity(profile)
        intent = Intent("build_dimmer_chase", {
            "effect_spec": spec.summary(),
            "effect_requirement": resolution.requirement.summary(),
            "effect_catalog_context": {"show_identity": identity, "song": show_plan.get("song")},
        }, "EffectResourceResolver")
        return self.skills.plan_intent(intent, self.state, self.runtime.preferences)

    def _plan_timecode_offset(self, intent: Any) -> WorkflowPlan:
        """Bind only fresh, read-only Timecode inventory into an OffsetSpec."""
        self.refresh_state("timecodes")
        timecodes = self.state.get("timecodes")
        spec = resolve_timecode_offset_spec(intent, list(timecodes.values if timecodes else []))
        bound = Intent(intent.kind, {**intent.parameters, "timecode_offset_spec": spec.summary()}, intent.source_text)
        return self.skills.plan_intent(bound, self.state, self.runtime.preferences)

    def _plan_geometry_clone(self, intent: Any) -> WorkflowPlan:
        """Bind only fresh Group inventory and export-backed membership to Clone."""
        spec = self._resolve_geometry_clone_spec(intent)
        isolated_test = (
            self._isolated_geometry_test_loaded
            and test_mode_enabled()
            and spec.source_group_name == SOURCE_LABEL
            and spec.destination_group_name == DESTINATION_LABEL
        )
        bound = Intent(intent.kind, {**intent.parameters, "geometry_clone_spec": spec.summary(), "isolated_test_show": isolated_test}, intent.source_text)
        return self.skills.plan_intent(bound, self.state, self.runtime.preferences)

    def _resolve_geometry_clone_spec(self, intent: Any) -> GeometryCloneSpec:
        self.refresh_state("groups")
        groups_snapshot = self.state.get("groups")
        groups = list(groups_snapshot.values if groups_snapshot else [])
        # Resolve identity before exporting; ambiguous names never select a Group.
        parameters = intent.parameters
        from .geometry_clone import _resolve_group
        source = _resolve_group(groups, number=parameters.get("source_group_number"), name=parameters.get("source_group_name"), role="source")
        destination = _resolve_group(groups, number=parameters.get("destination_group_number"), name=parameters.get("destination_group_name"), role="destination")
        memberships: dict[int, dict[str, Any]] = {}
        try:
            for group_no in (int(source["number"]), int(destination["number"])):
                result = self.refresh_state("group_membership", group_no=group_no)
                if result.get("status") != "available":
                    raise GeometryCloneError("Cannot build Geometry Clone because Group Membership state is not fresh.")
                member = next((item for item in result["values"] if item.get("group_no") == group_no), None)
                if not member:
                    raise GeometryCloneError("Cannot build Geometry Clone because Group Membership state is not fresh.")
                memberships[group_no] = member
        except (GroupMembershipProviderError, GroupMembershipProviderUnavailable, ConnectionError, ValueError) as exc:
            raise GeometryCloneError(f"Cannot build Geometry Clone because Group Membership state is not fresh: {exc}") from exc
        return resolve_geometry_clone_spec(intent, groups=groups, memberships=memberships)

    def _plan_timecode_test_setup(self, intent: Any) -> WorkflowPlan:
        """Only the explicit packaged verifier can reach this test setup intent."""
        self.refresh_state("timecodes")
        requested = intent.parameters.get("timecode_number")
        if not isinstance(requested, int) or isinstance(requested, bool) or requested < 1:
            raise TimecodeOffsetError("Test Timecode setup requires a positive number.")
        current = self.state.get("timecodes")
        occupied = [
            item.get("timecode_number")
            for item in (current.values if current else [])
            if isinstance(item, dict)
        ]
        try:
            number = first_free_from_front(occupied, start=1)
        except AllocationError as exc:
            raise TimecodeOffsetError("No safe free Timecode slot remains.") from exc
        bound = Intent(
            intent.kind,
            {
                **intent.parameters,
                "requested_timecode_number": requested,
                "timecode_number": number,
            },
            intent.source_text,
        )
        return self.skills.plan_intent(bound, self.state, self.runtime.preferences)

    def _plan_geometry_test_groups(self, intent: Any) -> WorkflowPlan:
        """Bind two fresh Fixture identities into an isolated-only Group setup."""
        if not (test_mode_enabled() and self._isolated_geometry_test_loaded):
            raise GeometryTestEnvironmentError("Geometry test Group setup requires an approved isolated Test Show load in this process.")
        source, destination = intent.parameters.get("source_fixture"), intent.parameters.get("destination_fixture")
        if not isinstance(source, int) or not isinstance(destination, int) or source < 1 or destination < 1 or source == destination:
            raise GeometryTestEnvironmentError("Geometry test Group setup requires two distinct positive Fixture IDs.")
        self.refresh_state("groups")
        groups = self.state.get("groups")
        occupied_groups = [
            item.get("number")
            for item in (groups.values if groups else [])
            if isinstance(item, dict)
        ]
        try:
            source_group = first_free_from_front(occupied_groups, start=1)
            destination_group = first_free_from_front([*occupied_groups, source_group], start=1)
        except AllocationError as exc:
            raise GeometryTestEnvironmentError("No two safe free Group slots remain in the isolated Test Show.") from exc
        self.refresh_state("fixtures")
        fixtures = self.state.get("fixtures")
        numbers = {item.get("number") for item in (fixtures.values if fixtures else [])}
        missing = [number for number in (source, destination) if number not in numbers]
        if missing:
            raise GeometryTestEnvironmentError(f"Test Fixture inventory does not contain: {', '.join(map(str, missing))}.")
        bound = Intent(
            intent.kind,
            {
                **intent.parameters,
                "geometry_test_group_spec": GeometryTestGroupSpec(
                    source,
                    destination,
                    source_group,
                    destination_group,
                ).summary(),
            },
            intent.source_text,
        )
        return self.skills.plan_intent(bound, self.state, self.runtime.preferences)

    def submit_request(self, text: str, source: str = "desktop") -> dict[str, Any]:
        """Backward-compatible alias; all callers should use handle_request."""
        return self.handle_request(text, source)

    def _respond(self, response_type: ResponseType, message: str, **extra: Any) -> dict[str, Any]:
        self.chat.append({"role": "assistant", "kind": response_type.value, "text": message})
        self.progress = "Idle"
        self.runtime.log("chat_response", {"RESPONSE_TYPE": response_type.value, "message": message})
        self.events.emit("chat", self.snapshot())
        return {"type": response_type.value, "message": message, "action": None, **extra}

    def _answer_state(self, intent: Any) -> dict[str, Any]:
        try:
            kind, parameters = intent.kind, intent.parameters
            if kind == "geometry_clone_mapping":
                spec = self._resolve_geometry_clone_spec(intent)
                return self._respond(ResponseType.ANSWER, format_mapping(spec, preview=False), intent=intent, state={"resource": "group_membership", "status": "available"})
            if kind == "diagnose_show":
                report = self.run_show_diagnostics()
                return self._respond(ResponseType.ANSWER, self._format_diagnostics(report), intent=intent, diagnostics=report.as_dict())
            if kind == "diagnose_show_details":
                report = self.last_diagnostics or self.run_show_diagnostics()
                return self._respond(ResponseType.ANSWER, self._format_diagnostics(report, detailed=True), intent=intent, diagnostics=report.as_dict())
            if kind == "diagnose_show_filter":
                report = self.last_diagnostics or self.run_show_diagnostics()
                return self._respond(ResponseType.ANSWER, self._format_diagnostics(report, detailed=True, **parameters), intent=intent, diagnostics=report.as_dict())
            if kind == "effect_next_page":
                current = self.state.get("effects")
                if not current or current.stale or current.error:
                    self.refresh_state("effects")
                    current = self.state.get("effects")
                if not current:
                    return self._respond(ResponseType.NEEDS_CLARIFICATION, "Ask for Effects first.", intent=intent)
                self._effect_page += 1
                result = {"resource": "effects", "count": len(current.values), "values": current.values, "status": "available"}
                return self._respond(ResponseType.ANSWER, self._format_state_answer(intent, result), intent=intent, state=result)
            if kind == "state_group_membership_name":
                groups = self.state.get("groups")
                if not groups or groups.stale or groups.error:
                    self.refresh_state("groups")
                    groups = self.state.get("groups")
                wanted = parameters["group_name"].casefold()
                group = next((item for item in (groups.values if groups else []) if item["name"].casefold() == wanted), None)
                if not group:
                    return self._respond(ResponseType.NEEDS_CLARIFICATION, f"No Group named {parameters['group_name']} is available in the current Group inventory.", intent=intent)
                result = self.request_group_membership(group["number"])
            elif kind == "state_group_membership":
                result = self.request_group_membership(parameters["group_no"])
            elif kind in {"layout_items_query", "layout_all_objects_query"}:
                result = self.refresh_state("layout_items", layout_no=parameters["layout_no"])
            elif kind == "state_selection":
                result = self.get_selection()
            elif kind == "state_programmer":
                result = self.get_programmer_summary()
            elif kind == "state_cues":
                result = self.refresh_state("cues", sequence=parameters["sequence"])
            elif kind in {"state_presets", "preset_list"}:
                result = self.refresh_state("presets", sequence=parameters["preset_type"])
            elif kind in {"state_effects", "effect_list", "effect_lookup"}:
                result = self.refresh_state("effects")
                if kind == "effect_list": self._effect_page = 0
            elif kind == "state_timecodes":
                result = self.refresh_state("timecodes")
            elif kind == "state_timecode_events":
                self.refresh_state("timecodes")
                return self._respond(ResponseType.ANSWER, "UNSUPPORTED: grandMA2 3.9 Timecode event/track readback has no verified non-mutating provider. Timecode inventory remains available.", intent=intent, state={"resource": "timecodes", "status": "UNSUPPORTED"})
            elif kind in {"state_sequence_executors", "sequence_executor_lookup", "page_executor_list"}: result = self.refresh_state("executors")
            else:
                result = self.refresh_state(kind.removeprefix("state_"))
        except GeometryCloneAmbiguous as exc:
            return self._respond(ResponseType.NEEDS_CLARIFICATION, str(exc), intent=intent)
        except (ConnectionError, PermissionError, GeometryCloneError, ValueError) as exc:
            return self._respond(ResponseType.ERROR, str(exc), intent=intent)
        if result["status"] != "available":
            return self._respond(ResponseType.ANSWER, result.get("error") or f"{result['resource']} is unavailable.", intent=intent, state=result)
        if kind == "layout_items_query" and parameters.get("object_name"):
            return self._respond(ResponseType.ANSWER, self._format_layout_group_answer(parameters["object_name"], result), intent=intent, state=result)
        return self._respond(ResponseType.ANSWER, self._format_state_answer(intent, result), intent=intent, state=result)

    def run_show_diagnostics(self) -> DiagnosticReport:
        """Refresh supported read-only state, then evaluate deterministic findings."""
        self.progress = "Reading Show State"
        for resource in ("groups", "fixtures", "layouts", "presets", "effects", "sequences", "pages", "executors"):
            self._diagnostic_refresh(resource, sequence="ALL" if resource == "presets" else None)
        groups = self.state.get("groups")
        for group in (groups.values if groups and not groups.error else []):
            self._diagnostic_refresh("group_membership", group_no=group.get("number"))
        layouts = self.state.get("layouts")
        for layout in (layouts.values if layouts and not layouts.error else []):
            self._diagnostic_refresh("layout_items", layout_no=layout.get("layout"))
        sequences = self.state.get("sequences")
        sequence_values = sequences.values if sequences and not sequences.error else []
        for sequence in sequence_values:
            self._diagnostic_refresh("cues", sequence=sequence.get("number"))
        if not sequence_values:
            self.state.put("cues", [], source="ma2_telnet_list")
        self.last_diagnostics = self.diagnostics.evaluate(self.state)
        self.runtime.log("diagnostics", self.last_diagnostics.as_dict())
        self.progress = "Idle"
        self.events.emit("diagnostics", self.snapshot())
        return self.last_diagnostics

    def _diagnostic_refresh(self, resource: str, **kwargs: Any) -> None:
        """Diagnostics retains typed provider errors instead of failing as a whole."""
        try:
            self.refresh_state(resource, **kwargs)
        except Exception as exc:  # Individual state failure is a diagnostic finding.
            self.state.record_error(resource, str(exc) or exc.__class__.__name__, source="diagnostics_refresh")

    @staticmethod
    def _format_diagnostics(report: DiagnosticReport, *, detailed: bool = False, severity: str | None = None, category: str | None = None) -> str:
        findings = list(report.findings)
        if severity:
            findings = [item for item in findings if item.severity == severity]
        if category:
            findings = [item for item in findings if item.category == category]
        counts = report.counts
        lines = ["Show Diagnostics", "", f"Status: {report.status}", "", f"Errors: {counts['ERROR']}", f"Warnings: {counts['WARNING']}", f"Info: {counts['INFO']}"]
        if detailed or severity or category:
            lines.extend(["", "Findings:"])
            if findings:
                lines.extend(f"[{item.severity}] {item.summary}" + (f"\n  Details: {item.details}" if detailed else "") for item in findings)
            else:
                lines.append("No matching findings.")
        else:
            warnings = [item for item in findings if item.severity in {"ERROR", "WARNING"}][:3]
            if warnings:
                lines.extend(["", "Warnings:"])
                lines.extend(f"{index}. {item.summary}" for index, item in enumerate(warnings, 1))
        lines.extend(["", "Capabilities:"])
        lines.extend(f"- {item['name']}: {item['status'].title()}" for item in report.capabilities)
        if not detailed and not severity and not category:
            lines.extend(["", "Type: 「顯示詳細診斷」 to show full findings."])
        return "\n".join(lines)

    def _format_state_answer(self, intent: Any, result: dict[str, Any]) -> str:
        values = result["values"]
        kind = intent.kind
        if kind in {"state_groups", "state_fixtures", "state_sequences"}:
            return AgentCore._format_rows(f"{result['resource'].title()} ({result['count']})", values, lambda item: f"{item['number']}: {item['name']}")
        if kind == "state_timecodes":
            return AgentCore._format_rows(f"Timecodes ({result['count']})", values, lambda item: f"{item['timecode_number']}: {item['name']}")
        if kind == "state_layouts":
            return f"Layouts ({result['count']})\n" + ("\n".join(f"{item['layout']}: {item.get('name', '')}" for item in values) or "No entries returned.")
        if kind in {"state_group_membership", "state_group_membership_name"}:
            group_no = intent.parameters.get("group_no")
            group = next((item for item in values if group_no is None or item.get("group_no") == group_no), values[-1] if values else None)
            return f"Group {group['group_no']} {group['name']}\nFixtures ({len(group['fixtures'])}): " + ", ".join(str(item) for item in group["fixtures"])
        if kind == "layout_items_query":
            layout = next(item for item in values if item["layout"] == intent.parameters["layout_no"])
            fixture_geometry = layout.get("fixture_geometry", {})
            if fixture_geometry.get("status") != "available":
                return f"Layout {layout['layout']} {layout.get('name', '')}\n{fixture_geometry.get('reason', 'Fixture layout data is unavailable.')}\nVisible CObjects: {len(layout['items'])}."
            lighting = LayoutObjectResolver.lighting_items(layout)
            other_count = len(layout["items"]) - len(lighting)
            rows = [AgentCore._format_layout_item(item) for item in lighting]
            empty = "Empty layout.\n" if not layout["items"] else ""
            return f"Layout {layout['layout']} {layout.get('name', '')}\n{empty}Fixtures: {len(lighting)}\n" + ("\n".join(rows) if rows else "No fixture entries returned.") + f"\nOther objects: {other_count}"
        if kind == "layout_all_objects_query":
            layout = next(item for item in values if item["layout"] == intent.parameters["layout_no"])
            return AgentCore._format_rows(f"Layout {layout['layout']} {layout.get('name', '')} Objects ({len(layout['items'])})", layout["items"], AgentCore._format_layout_item)
        if kind == "state_selection":
            selection = values[0]
            return "Selected Fixtures: " + (", ".join(str(item) for item in selection["fixtures"]) or "none")
        if kind == "state_programmer":
            programmer = values[0]
            return "Programmer: " + ("active values present" if programmer["has_active_values"] else "empty")
        if kind == "state_cues":
            sequence_cues = [item for item in values if item.get("sequence") == intent.parameters["sequence"]]
            return f"Sequence {intent.parameters['sequence']} Cues ({len(sequence_cues)})\n" + ("\n".join(f"{item['number']}: {item['name']}" for item in sequence_cues) or "No cues returned.")
        if kind in {"state_presets", "preset_list"}: return AgentCore._format_rows(f"{intent.parameters['preset_type'].title()} Presets ({len(values)})", values, lambda item: f"{item['number']}: {item['name']}")
        if kind in {"state_effects", "effect_list", "effect_next_page"}: return self._format_effect_rows(values)
        if kind == "effect_lookup":
            item=next((item for item in values if item["number"]==intent.parameters["effect"]),None); return f"Effect {intent.parameters['effect']}: {item['name']}" if item else f"Effect {intent.parameters['effect']} not found."
        if kind in {"state_sequence_executors", "sequence_executor_lookup"}:
            rows=[item for item in values if item.get("assignment_type")=="sequence" and item.get("assignment")==intent.parameters["sequence"]]
            return f"Sequence {intent.parameters['sequence']} Executors ({len(rows)})\n" + ("\n".join(f"{item['location']}: {item.get('label') or ''}" for item in rows) or "No executor assignment returned.")
        if kind == "page_executor_list":
            rows=[item for item in values if item.get("page")==intent.parameters["page"]]; return f"Page {intent.parameters['page']} Executors ({len(rows)})\n" + ("\n".join(f"{item['location']}: {item.get('label') or ''}" for item in rows) or "No executor assignment returned.")
        return f"{result['resource'].title()} ({result['count']})"

    @classmethod
    def _format_rows(cls, heading: str, values: list[dict[str, Any]], render: Any) -> str:
        rows = [render(item) for item in values[:cls.CHAT_ROW_LIMIT]]
        shown = f"Showing first {cls.CHAT_ROW_LIMIT}\n" if len(values) > cls.CHAT_ROW_LIMIT else ""
        return f"{heading}\n{shown}" + ("\n".join(rows) if rows else "No entries returned.")

    @staticmethod
    def _format_effect(item: dict[str, Any]) -> str:
        label = str(item.get("name") or "").strip()
        return f"{item['number']} (unlabeled)" if not label or label == str(item["number"]) else f"{item['number']}: {label}"

    def _format_effect_rows(self, values: list[dict[str, Any]]) -> str:
        if not values:
            self._effect_page = 0
            return "Effects (0)\nNo entries returned."
        first = self._effect_page * self.CHAT_ROW_LIMIT
        if first >= len(values):
            self._effect_page = max(0, (len(values) - 1) // self.CHAT_ROW_LIMIT)
            return f"Effects ({len(values)})\nNo further Effect entries."
        page = values[first:first + self.CHAT_ROW_LIMIT]
        showing = f"Showing first {self.CHAT_ROW_LIMIT}" if first == 0 else f"Showing {first + 1}-{first + len(page)}"
        hint = "\nNext page: 下一頁\nInspect: Effect <number> 是什麼？\nSearch: 搜尋 Effect 名稱" if first + len(page) < len(values) else ""
        return f"Effects ({len(values)})\n{showing}\n" + "\n".join(self._format_effect(item) for item in page) + hint

    @staticmethod
    def _format_layout_item(item: dict[str, Any]) -> str:
        reference = item["reference"] if item["type"] != "unknown" else f"unresolved {item.get('reference_tokens', [])}"
        name = str(item.get("name") or "").strip()
        if item["type"] in {"preset", "group"} and name:
            name = re.sub(rf"\s+{re.escape(str(reference))}$", "", name).strip()
        label = f' "{name}"' if name else ""
        return f"{str(item['type']).title()} {reference}{label}: x={item['x']}, y={item['y']}"

    def _format_layout_group_answer(self, group_name: str, result: dict[str, Any]) -> str:
        groups = self.state.get("groups")
        if not groups or groups.stale or groups.error:
            self.refresh_state("groups"); groups = self.state.get("groups")
        group = next((item for item in (groups.values if groups else []) if item["name"].casefold() == group_name.casefold()), None)
        if not group:
            return f"No Group named {group_name} is available in the current Group inventory."
        membership = self.request_group_membership(group["number"])
        if membership["status"] != "available" or not membership.get("group"):
            return membership.get("error") or f"Group {group_name} membership is unavailable."
        fixtures = set(membership["group"]["fixtures"])
        layout = next(item for item in result["values"] if item["layout"] == result["values"][-1]["layout"])
        matching = [item for item in LayoutObjectResolver.lighting_items(layout) if item["reference"] in fixtures]
        if not matching:
            group_items = [item for item in layout["items"] if item["type"] == "group" and item["reference"] == group["number"]]
            if group_items:
                item = group_items[0]
                return f'Group {group["number"]} "{group["name"]}" is in Layout {layout["layout"]} at x={item["x"]}, y={item["y"]}.\nNo individual {group["name"]} fixture items are present.'
            return f"{group_name} has no resolved fixture items in Layout {layout['layout']}."
        return f"{group_name} in Layout {layout['layout']}\n" + "\n".join(self._format_layout_item(item) for item in matching[:self.CHAT_ROW_LIMIT])

    @staticmethod
    def _provider_for_intent(intent: Any | None) -> str | None:
        if intent is None:
            return None
        providers = {
            "diagnose_show": "ShowDiagnostics",
            "diagnose_show_details": "ShowDiagnostics",
            "diagnose_show_filter": "ShowDiagnostics",
            "layout_items_query": "LayoutExportProvider",
            "layout_all_objects_query": "LayoutExportProvider",
            "state_layouts": "LayoutInventoryProvider",
            "preset_list": "PresetProvider",
            "effect_list": "EffectProvider",
            "effect_next_page": "EffectProvider",
            "effect_lookup": "EffectProvider",
            "sequence_executor_lookup": "ExecutorProvider",
            "page_executor_list": "ExecutorProvider",
            "state_selection": "SelectionInspectCapability",
            "state_programmer": "ProgrammerInspectCapability",
            "build_dimmer_chase": "EffectBuilderSkill",
            "state_timecodes": "TimecodeProvider",
            "state_timecode_events": "TimecodeProvider",
            "offset_timecode": "TimecodeOffsetSkill",
            "timecode_test_setup": "TimecodeOffsetSkill",
            "geometry_test_load_show": "GeometryTestEnvironmentSkill",
            "geometry_test_restore_show": "GeometryTestEnvironmentSkill",
            "geometry_test_setup_groups": "GeometryTestEnvironmentSkill",
            "geometry_clone": "GeometryCloneSkill",
            "geometry_clone_mapping": "GeometryCloneSkill",
        }
        return providers.get(intent.kind)

    def cancel_action(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            return False
        action.status = "CANCELLED"
        if self._active_action_id == action_id:
            self._active_action_id = None
        if action.workflow.task.intent.kind in {"verify_position_application", "verify_position_raw_cue"}:
            self._root_workflow_status.update({"state": "CANCELLED", "phase": "DONE", "action_id": action_id})
        self.progress = "Idle"
        self.events.emit("plan", self.snapshot())
        return True

    def _effective_execution_context(self, action: ActionRecord) -> tuple[str, Intent]:
        """Resolve the child execution identity for a composed show.program action."""
        workflow = action.workflow
        if workflow.task.skill_id != "show.program":
            return workflow.task.skill_id, workflow.task.intent
        if not workflow.executable:
            raise ValueError("Non-executable show.program workflow cannot be approved.")
        context = workflow.continuation_context
        if not isinstance(context, dict):
            raise ValueError("Executable show.program workflow has no continuation context.")
        child = context.get(ROOT_CHILD_CONTEXT_KEY)
        if not isinstance(child, dict) or set(child) != {"skill_id", "intent_kind", "parameters", "source_text"}:
            raise ValueError("Executable show.program workflow has invalid child execution context.")
        skill_id = child.get("skill_id")
        intent_kind = child.get("intent_kind")
        parameters = child.get("parameters")
        source_text = child.get("source_text")
        if not isinstance(skill_id, str) or not skill_id or len(skill_id) > 128:
            raise ValueError("show.program child skill id is invalid.")
        if not isinstance(intent_kind, str) or not intent_kind or len(intent_kind) > 128:
            raise ValueError("show.program child intent kind is invalid.")
        if not isinstance(parameters, dict):
            raise ValueError("show.program child intent parameters are invalid.")
        if not isinstance(source_text, str) or len(source_text) > 2048:
            raise ValueError("show.program child source text is invalid.")
        try:
            encoded = json.dumps(child, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("show.program child execution context is not JSON-safe.") from exc
        if len(encoded) > MAX_CHILD_CONTEXT_BYTES:
            raise ValueError("show.program child execution context is too large.")
        if not any(node.skill_id == skill_id and node.skill_id != "show.program" for node in workflow.skill_graph):
            raise ValueError("show.program child execution context does not match its Skill graph.")
        capability = self.skills.get(skill_id)
        if intent_kind not in capability.intents:
            raise ValueError("show.program child execution context does not match the child Skill intent.")
        return skill_id, Intent(intent_kind, dict(parameters), source_text)

    def approve_action(self, action_id: str, *, danger_confirmed: bool = False) -> dict[str, Any]:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            raise ValueError("Action is not awaiting approval.")
        if action_id != self._active_action_id:
            raise ValueError("This preview is no longer the active action.")
        execution_skill_id, execution_intent = self._effective_execution_context(action)
        if not self.runtime.ready:
            raise PermissionError("MA2 must be READY before an approved action can execute.")
        if action.workflow.safety == "DANGEROUS" and not danger_confirmed:
            raise PermissionError("Dangerous actions require a second confirmation.")
        if execution_intent.kind == "offset_timecode":
            self._ensure_timecode_state_unchanged(action)
        elif execution_intent.kind == "geometry_clone":
            self._ensure_geometry_clone_state_unchanged(action)
        elif execution_intent.kind == "verify_position_application":
            self._ensure_position_poc_state_unchanged(action)
        elif execution_intent.kind == "verify_position_raw_cue":
            self._ensure_position_raw_state_unchanged(action)
        elif execution_intent.kind == "verify_position_calibration":
            self._ensure_position_calibration_state_unchanged(action)
        action.status = "APPROVED"
        self.progress = "Executing"
        self.events.emit("progress", {"stage": self.progress})
        try:
            intent_kind = execution_intent.kind
            if intent_kind == "verify_cue_effect_application":
                result = self._execute_cue_effect_application_poc(action)
            elif intent_kind == "verify_position_application":
                result = self._execute_position_application_poc(action)
            elif intent_kind == "verify_position_raw_cue":
                result = self._execute_position_raw_cue_poc(action)
            elif intent_kind == "verify_position_calibration":
                result = self._execute_position_calibration(action)
            else:
                commands = self.skills.approved_commands(action.workflow.task.skill_id, action.workflow)
                results = self.runtime.execute_approved_commands(commands)
                result = "\n".join(item for item in results if item) or "Approved MA2 workflow commands sent"
            if intent_kind.startswith("geometry_test_") and re.search(r"(?:\berror\b|\billegal\b|\bfailed\b)", result, re.I):
                raise GeometryTestEnvironmentError("MA2 reported an error while executing the approved workflow.")
            if intent_kind == "geometry_test_load_show":
                self._isolated_geometry_test_loaded = True
                for resource in self.state.RESOURCES:
                    self.state.mark_stale(resource)
                result += f"\nVerification: Test Show \"{TEST_SHOW}\" load command completed. Refresh its Fixture inventory before any setup."
            elif intent_kind == "geometry_test_restore_show":
                self._isolated_geometry_test_loaded = False
                for resource in self.state.RESOURCES:
                    self.state.mark_stale(resource)
                result += f"\nVerification: Production Show \"{PRODUCTION_SHOW}\" restore command completed. Refresh production state."
            elif intent_kind == "geometry_test_setup_groups":
                result = self._verify_geometry_test_groups(action, result)
            elif execution_skill_id == "effects.builder":
                result = self._verify_effect_builder(action, result)
            elif intent_kind == "offset_timecode":
                result = self._verify_timecode_offset(action, result)
            elif intent_kind == "geometry_clone":
                result = self._verify_geometry_clone(action, result)
            elif intent_kind == "build_first_song":
                result = self._verify_first_song(action, result)
            action.status, action.result = "EXECUTED", result
            self._active_action_id = None
            if action.workflow.task.skill_id == "show.program":
                self._root_workflow_status.update({"state": "EXECUTED", "phase": "VERIFY_ACTUAL_CONTENT", "action_id": action_id})
            elif intent_kind in {
                "verify_position_application", "verify_position_raw_cue",
                "verify_position_calibration",
            }:
                self._root_workflow_status.update({"state": "EXECUTED", "phase": "DONE", "action_id": action_id})
            self.chat.append({"role": "assistant", "kind": "result", "text": action.result, "action_id": action_id})
            self.progress = "Verifying"
        except Exception as exc:
            action.status, action.result = "FAILED", str(exc)
            self._active_action_id = None
            if action.workflow.task.skill_id == "show.program":
                self._root_workflow_status.update(
                    {"state": "FAILED", "phase": "SELF_HEAL_IF_NEEDED", "action_id": action_id}
                )
            elif execution_intent.kind in {
                "verify_position_application", "verify_position_raw_cue",
                "verify_position_calibration",
            }:
                self._root_workflow_status.update({"state": "FAILED", "phase": "DONE", "action_id": action_id})
            self.progress = "Idle"
            self.events.emit("error", {"message": str(exc)})
            raise
        self.events.emit("execution", self.snapshot())
        return {"id": action.id, "status": action.status, "result": action.result}

    def _execute_position_application_poc(self, action: ActionRecord) -> str:
        """Future explicit-approval path; never called by Preview registration.

        The native Cue export is the sole binding authority. A partial new
        Sequence is retained for manual, identity-checked recovery; no Delete
        or automatic rollback command is generated.
        """
        preview = action.workflow.task.intent.parameters["position_preview"]
        commands = self.skills.approved_commands(action.workflow.task.skill_id, action.workflow)
        if len(commands) != 6:
            raise PositionEvidenceError("POSITION_POC_APPROVED_COMMAND_PLAN_INVALID")
        responses: list[str] = []
        try:
            for command in commands[:5]:
                response = self.runtime.execute_approved_commands((command,))[0]
                responses.append(response)
                if ma2_response_has_error(response):
                    raise PositionEvidenceError(f"POSITION_POC_MA_COMMAND_REJECTED: {command}: {response}")
            sequence = preview["sequence"]["id"]
            label = preview["sequence"]["label"]
            self.verify_first_song_metadata(
                sequence, label, [{"cue_number": 1, "label": "POSITION_APPLICATION_POC", "fade": 0}],
            )
            if self.sequence_export_provider is None:
                raise PositionEvidenceError("POSITION_POC_SEQUENCE_EXPORT_UNAVAILABLE")
            discovery = self.sequence_export_provider.export_and_discover(
                self.runtime, sequence, self.runtime.preferences.get("state_adapter"), retain_export=True,
            )
            # The stable scanned identity excludes the newly created Sequence,
            # but all Group/Preset/fixture evidence is checked again here.
            profile = self._fresh_position_poc_profile(
                group_id=preview["group"]["id"], preset_ref=preview["preset"]["reference"])
            if profile["show_identity"] != preview["show_identity"]:
                raise PositionEvidenceError("POSITION_POC_POSTWRITE_SHOW_IDENTITY_DRIFT")
            binding = self.position_application_bindings.record_after_readback(profile, preview, discovery)
            self.runtime.log("position_application_poc_verified", {
                "action_id": action.id, "sequence": sequence, "group": preview["group"]["id"],
                "preset": preview["preset"]["reference"],
                "sequence_export_sha256": binding["evidence"]["sequence_export_sha256"],
            })
            return f"Position application content VERIFIED for Sequence {sequence}; binding recorded."
        except Exception as exc:
            self.runtime.log("position_application_poc_failed", {
                "action_id": action.id, "sequence": preview["sequence"]["id"],
                "error": str(exc), "automatic_delete": False,
            })
            raise
        finally:
            try:
                self.runtime.execute_approved_commands((commands[-1],))
            except Exception as clear_exc:
                self.runtime.log("position_application_poc_clear_failed", {"error": str(clear_exc)})

    def _execute_position_raw_cue_poc(self, action: ActionRecord) -> str:
        """Execute only after explicit approval; retain failed new Sequence evidence."""
        preview = action.workflow.task.intent.parameters["position_raw_preview"]
        commands = self.skills.approved_commands(action.workflow.task.skill_id, action.workflow)
        if len(commands) != 7:
            raise PositionEvidenceError("RAW_POSITION_POC_APPROVED_COMMAND_PLAN_INVALID")
        try:
            for command in commands[:-1]:
                response = self.runtime.execute_approved_commands((command,))[0]
                if ma2_response_has_error(response):
                    raise PositionEvidenceError(f"RAW_POSITION_POC_MA_COMMAND_REJECTED: {command}: {response}")
            sequence = preview["sequence"]["id"]
            self.verify_first_song_metadata(
                sequence, preview["sequence"]["label"],
                [{"cue_number": 1, "label": "POSITION_RAW_POC", "fade": 0}],
            )
            if self.sequence_export_provider is None:
                raise PositionEvidenceError("RAW_POSITION_POC_SEQUENCE_EXPORT_UNAVAILABLE")
            discovery = self.sequence_export_provider.export_and_discover(
                self.runtime, sequence, self.runtime.preferences.get("state_adapter"), retain_export=True,
            )
            profile = self._fresh_position_raw_profile(group_id=preview["group"]["id"])
            proof = verify_raw_position_cue_content(profile, preview, discovery)
            self.runtime.log("position_raw_cue_content_verified", {
                "action_id": action.id, "sequence": sequence,
                "sequence_export_sha256": proof["sequence_export_sha256"],
                "position_application_binding_recorded": False,
            })
            return f"RAW_POSITION_CUE_CONTENT_VERIFIED for Sequence {sequence}; no Position binding recorded."
        except Exception as exc:
            self.runtime.log("position_raw_cue_poc_failed", {
                "action_id": action.id, "sequence": preview["sequence"]["id"],
                "error": str(exc), "automatic_delete": False,
            })
            raise
        finally:
            try:
                self.runtime.execute_approved_commands((commands[-1],))
            except Exception as clear_exc:
                self.runtime.log("position_raw_cue_poc_clear_failed", {"error": str(clear_exc)})

    def _execute_position_calibration(self, action: ActionRecord) -> str:
        """Run one approved raw + newly created Preset Position calibration."""
        preview = action.workflow.task.intent.parameters["position_calibration_preview"]
        commands = self.skills.approved_commands(
            action.workflow.task.skill_id, action.workflow
        )
        if len(commands) != 16:
            raise PositionEvidenceError("POSITION_CALIBRATION_APPROVED_COMMAND_PLAN_INVALID")
        responses: list[str] = []
        try:
            # Phase A: prove/store the raw Cue, then deliberately reactivate
            # PAN/TILT before creating the Preset.  Real MA2 evidence showed
            # Store Cue cannot be treated as preserving Preset-storable active
            # programmer state.
            for command in commands[:10]:
                response = self.runtime.execute_approved_commands((command,))[0]
                responses.append(response)
                if ma2_response_has_error(response):
                    raise PositionEvidenceError(
                        f"POSITION_CALIBRATION_MA_COMMAND_REJECTED: {command}: {response}"
                    )

            preset_ref = preview["preset"]["reference"]
            preset_label = preview["preset"]["label"]
            direct = PresetProvider().parse(
                self.runtime.read_state(f"List Preset {preset_ref}"), "POSITION"
            )
            if (
                len(direct) != 1
                or direct[0].get("reference") != preset_ref
                or direct[0].get("preset_type") != "POSITION"
                or direct[0].get("name") != preset_label
            ):
                raise PositionEvidenceError(
                    "POSITION_CALIBRATION_CREATED_PRESET_IDENTITY_UNVERIFIED"
                )

            # Phase B is unreachable until the exact new Preset identity exists.
            for command in commands[10:-1]:
                response = self.runtime.execute_approved_commands((command,))[0]
                responses.append(response)
                if ma2_response_has_error(response):
                    raise PositionEvidenceError(
                        f"POSITION_CALIBRATION_MA_COMMAND_REJECTED: {command}: {response}"
                    )

            sequence = preview["sequence"]["id"]
            self.verify_first_song_metadata(
                sequence,
                preview["sequence"]["label"],
                [
                    {"cue_number": 1, "label": "RAW_POSITION", "fade": 0},
                    {"cue_number": 2, "label": "PRESET_POSITION", "fade": 0},
                ],
            )
            if self.sequence_export_provider is None:
                raise PositionEvidenceError(
                    "POSITION_CALIBRATION_SEQUENCE_EXPORT_UNAVAILABLE"
                )
            discovery = self.sequence_export_provider.export_and_discover(
                self.runtime,
                sequence,
                self.runtime.preferences.get("state_adapter"),
                retain_export=True,
            )

            profile = self._fresh_position_raw_profile(
                group_id=preview["group"]["id"]
            )
            if profile.get("show_identity") != preview.get(
                "expected_postwrite_show_identity"
            ):
                raise PositionEvidenceError(
                    "POSITION_CALIBRATION_POSTWRITE_SHOW_IDENTITY_DRIFT"
                )
            candidates = [
                row for row in profile.get("presets", [])
                if row.get("reference") == preset_ref
            ]
            if (
                len(candidates) != 1
                or candidates[0].get("preset_type") != "POSITION"
                or candidates[0].get("name") != preset_label
            ):
                raise PositionEvidenceError(
                    "POSITION_CALIBRATION_POSTWRITE_PRESET_IDENTITY_UNVERIFIED"
                )

            raw_proof = verify_calibration_raw_content(
                profile, preview, discovery
            )
            application_preview = calibration_application_preview(
                profile, preview
            )
            binding = self.position_application_bindings.record_after_readback(
                profile, application_preview, discovery
            )
            self.runtime.log(
                "position_calibration_verified",
                {
                    "action_id": action.id,
                    "sequence": sequence,
                    "preset": preset_ref,
                    "raw_status": raw_proof["status"],
                    "application_status": binding["status"],
                    "sequence_export_sha256": raw_proof[
                        "sequence_export_sha256"
                    ],
                    "cleanup_after_verified": False,
                },
            )
            return (
                "RAW_POSITION_CUE_CONTENT_VERIFIED; "
                f"POSITION_APPLICATION={binding['status']}; "
                f"Preset {preset_ref} binding recorded from Sequence {sequence} Cue 2."
            )
        except Exception as exc:
            self.runtime.log(
                "position_calibration_failed",
                {
                    "action_id": action.id,
                    "sequence": preview["sequence"]["id"],
                    "preset": preview["preset"]["reference"],
                    "error": str(exc),
                    "automatic_delete": False,
                },
            )
            raise
        finally:
            try:
                self.runtime.execute_approved_commands((commands[-1],))
            except Exception as clear_exc:
                self.runtime.log(
                    "position_calibration_clear_failed",
                    {"error": str(clear_exc)},
                )

    def _execute_cue_effect_application_poc(self, action: ActionRecord) -> str:
        """Execute the POC in a guarded two-phase sequence.

        Store/label are unreachable until the Effect call returns without a
        recognised MA2 error. ClearAll is attempted on every exit path.
        """
        raw = self._effective_execution_context(action)[1].parameters.get("cue_effect_spec")
        if not isinstance(raw, dict):
            raise CueEffectApplicationError("Cue Effect POC verification metadata is incomplete.")
        try:
            spec = CueEffectApplicationSpec(**raw)
        except TypeError as exc:
            raise CueEffectApplicationError("Cue Effect POC verification metadata is malformed.") from exc
        commands = self.skills.approved_commands(action.workflow.task.skill_id, action.workflow)
        if len(commands) != 6:
            raise CueEffectApplicationError("Cue Effect POC has an invalid approved command count.")
        responses: list[str] = []
        try:
            for command in commands[:3]:
                response = self.runtime.execute_approved_commands((command,))[0]
                responses.append(response)
                if ma2_response_has_error(response):
                    raise CueEffectApplicationError(f"MA2 rejected Cue Effect application candidate {command!r}: {response or 'no feedback'}")
            for command in commands[3:5]:
                response = self.runtime.execute_approved_commands((command,))[0]
                responses.append(response)
                if ma2_response_has_error(response):
                    raise CueEffectApplicationError(f"MA2 rejected approved Cue storage command {command!r}: {response or 'no feedback'}")
            verification = self.verify_first_song_metadata(
                spec.sequence,
                spec.sequence_label,
                [{"cue_number": spec.cue_number, "label": spec.cue_label, "fade": 0}],
            )
            content_text, content_report = self._verify_first_song_cue_content(
                {
                    "sequence": spec.sequence,
                    "cues": [{
                        "cue_number": spec.cue_number,
                        "label": spec.cue_label,
                        "fade": 0,
                        "actions": [{
                            "operation": "CALL_EFFECT",
                            "target": {"type": "group", "ref": spec.target_group},
                            "effect_ref": {"id": spec.effect_id, "label": spec.effect_label},
                        }],
                    }],
                }
            )
            if content_report is None:
                capability = self.cue_effect_application_capability.record(spec)
            else:
                capability = self.cue_effect_application_capability.record_content_verified(
                    spec,
                    sequence_export_sha256=str(content_report.get("source_xml_sha256") or ""),
                )
            self.runtime.log(
                "cue_effect_application_verification",
                {
                    "status": capability["status"],
                    "grammar": capability["grammar"],
                    "effect": spec.effect_id,
                    "target_group": spec.target_group,
                    "sequence": spec.sequence,
                    "cue": spec.cue_number,
                    "application": capability["verification"]["application"],
                    "cue_content_effect_readback": capability["verification"]["cue_content_readback"],
                    "sequence_export_sha256": (
                        content_report.get("source_xml_sha256")
                        if isinstance(content_report, dict)
                        else None
                    ),
                    "responses": responses,
                },
            )
            return (
                "\n".join(item for item in responses if item)
                + "\n"
                + verification
                + "\n"
                + content_text
                + "\nEffect application capability: "
                + capability["status"]
                + "."
            )
        except Exception as exc:
            self.runtime.log("cue_effect_application_verification", {"status": "FAILED", "effect": spec.effect_id, "target_group": spec.target_group, "sequence": spec.sequence, "cue": spec.cue_number, "error": str(exc), "responses": responses})
            raise
        finally:
            try:
                clear_response = self.runtime.execute_approved_commands((commands[-1],))[0]
                self.runtime.log("cue_effect_application_clear", {"sequence": spec.sequence, "response": clear_response})
            except Exception as clear_exc:
                self.runtime.log("cue_effect_application_clear", {"sequence": spec.sequence, "error": str(clear_exc)})

    def _verify_first_song(self, action: ActionRecord, execution_result: str) -> str:
        data = self._effective_execution_context(action)[1].parameters
        sequence, label = data.get("sequence"), data.get("sequence_label")
        expected_labels = data.get("cue_labels")
        if not isinstance(sequence, int) or not isinstance(label, str) or not isinstance(expected_labels, list):
            raise FirstSongBuildError("First Song verification metadata is incomplete.")
        metadata = self.verify_first_song_metadata(sequence, label, data.get("cues", []), expected_labels)
        target_executor = data.get("target_executor")
        if target_executor:
            address = ShowPlanBuilder._executor_address(target_executor)
            if address is None:
                raise FirstSongBuildError("First Song target Executor metadata is invalid during verification.")
            executor_output = self.runtime.read_state("List Executor")
            if not re.search(rf"(?:Executor|Exec)\s+{re.escape(address)}\b", executor_output, re.I) or not re.search(rf"(?:Sequence\s*=\s*Seq|Sequence)\s*{sequence}\b", executor_output, re.I) or label not in executor_output:
                raise FirstSongBuildError(f"Verification failed: Page/Executor {target_executor} is not assigned to the owned Sequence.")
            metadata += f"\nExecutor {target_executor} assignment verified."
        effect_lines = self._fresh_verify_effect_references({"cues": data.get("cues", [])})
        preset_refs = set(data.get("referenced_presets") or [])
        preset_lines = self._fresh_verify_preset_references(preset_refs)
        details = []
        if effect_lines:
            details.append("Effect references verified: " + "; ".join(effect_lines))
        if preset_lines:
            details.append("Preset references verified by exact fresh List lookup: " + "; ".join(preset_lines))
        content_text, _content_report = self._verify_first_song_cue_content(data)
        details.append(content_text)
        return execution_result + "\n" + metadata + ("\n" + "\n".join(details) if details else "")

    def _verify_first_song_cue_content(self, data: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
        """Compare approved Cue actions with fresh native Sequence Export content."""
        provider = self.sequence_export_provider
        if provider is None:
            return (
                "Verification: PARTIAL — Cue-content Sequence Export is unavailable in this runtime.",
                None,
            )
        sequence = data.get("sequence")
        cues = data.get("cues")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1 or not isinstance(cues, list):
            raise FirstSongBuildError("Cue-content verification metadata is incomplete.")

        groups: set[int] = set()
        for cue in cues:
            if not isinstance(cue, dict):
                raise FirstSongBuildError("Cue-content verification received an invalid Cue.")
            for action in cue.get("actions", []):
                target = action.get("target") if isinstance(action, dict) else None
                group = target.get("ref") if isinstance(target, dict) else None
                if isinstance(group, bool) or not isinstance(group, int) or group < 1:
                    raise FirstSongBuildError("Cue-content verification received an invalid Group target.")
                groups.add(group)

        settings = self.runtime.preferences.get("state_adapter", {})
        memberships: dict[int, list[int]] = {}
        try:
            for group in sorted(groups):
                item = self.group_membership_provider.get_group_membership(self.runtime, group, settings)
                members = item.get("fixtures")
                if not isinstance(members, list):
                    raise FirstSongBuildError(
                        f"Cue-content verification Group {group} membership is not parseable."
                    )
                memberships[group] = [
                    value for value in members
                    if isinstance(value, int) and not isinstance(value, bool) and value > 0
                ]
            discovery = provider.export_and_discover(
                self.runtime, sequence, settings, retain_export=True
            )
        except GroupMembershipProviderUnavailable as exc:
            self.runtime.log(
                "cue_content_verification",
                {"status": "PARTIAL", "reason": str(exc), "sequence": sequence},
            )
            return (
                "Verification: PARTIAL — Cue-content export/membership provider is unavailable.",
                None,
            )
        except (GroupMembershipProviderError, SequenceExportParseError, OSError) as exc:
            raise FirstSongBuildError(f"Cue-content verification readback failed: {exc}") from exc

        try:
            report = verify_cue_content({"cues": cues}, discovery, memberships)
        except CueContentVerificationError as exc:
            raise FirstSongBuildError(
                f"Cue-content verification could not compare the approved plan: {exc}"
            ) from exc

        self.runtime.log("cue_content_verification", report)
        if report.get("status") != "VERIFIED":
            mismatches: list[str] = []
            for cue in report.get("cues", []):
                if not isinstance(cue, dict):
                    continue
                for action in cue.get("actions", []):
                    if isinstance(action, dict) and action.get("status") != "VERIFIED":
                        mismatches.append(
                            f"Cue {cue.get('cue_number')} action {action.get('action_index')} "
                            f"{action.get('operation')}: {action.get('reason')}"
                        )
                if cue.get("status") != "VERIFIED" and not cue.get("actions"):
                    mismatches.append(f"Cue {cue.get('cue_number')}: {cue.get('reason')}")
            detail = "; ".join(mismatches[:8]) or "stored Cue content differs from the approved plan"
            raise FirstSongBuildError(f"Cue-content verification mismatch: {detail}")

        return (
            "Cue-content verification: VERIFIED — every approved Dimmer/Preset/Effect action "
            "has matching fresh Sequence Export evidence for every current Group member. "
            f"Source SHA-256: {report.get('source_xml_sha256') or 'UNAVAILABLE'}.",
            report,
        )

    def _fresh_verify_preset_references(self, references: set[str] | list[str]) -> list[str]:
        """Prove each referenced Preset by exact read-only List lookup.

        A broad `List Preset All` is inventory context, not an existence proof:
        grandMA2 can omit rows that an exact `List Preset <ref>` returns.
        """
        verified: list[str] = []
        provider = PresetProvider()
        for reference in sorted({str(item) for item in references if str(item).strip()}):
            if not re.fullmatch(r"[1-9]\d*\.[1-9]\d*", reference):
                raise FirstSongBuildError(
                    f"Verification failed: referenced Preset has invalid identity: {reference}"
                )
            raw = self.runtime.read_state(f"List Preset {reference}")
            upper = raw.upper()
            if "OBJECT DOES NOT EXIST" in upper or "NO OBJECTS FOUND" in upper:
                raise FirstSongBuildError(
                    f"Verification failed: referenced Preset is no longer present: {reference}"
                )
            rows = provider.parse(raw, "ALL")
            found = next(
                (item for item in rows if str(item.get("reference") or "") == reference),
                None,
            )
            if found is None:
                raise FirstSongBuildError(
                    f"Verification failed: referenced Preset read-back was not parseable: {reference}"
                )
            label = str(found.get("name") or "").strip()
            verified.append(f"{reference}" + (f" — {label}" if label else ""))
        return verified

    def _fresh_verify_effect_references(self, show_plan: dict[str, Any]) -> list[str]:
        """Prove every typed Effect reference by exact read-only List lookup."""
        references: dict[int, str] = {}
        for cue in show_plan.get("cues", []):
            for action in cue.get("actions", []):
                if action.get("operation") != "CALL_EFFECT":
                    continue
                reference = action.get("effect_ref")
                if not isinstance(reference, dict) or not isinstance(reference.get("id"), int) or not isinstance(reference.get("label"), str):
                    raise EffectRequirementError("Resolved Show Plan Effect reference is incomplete.")
                effect_id, label = reference["id"], reference["label"]
                previous = references.setdefault(effect_id, label)
                if previous != label:
                    raise EffectRequirementError(f"Resolved Show Plan Effect {effect_id} has conflicting labels.")
        verified: list[str] = []
        for effect_id, expected_label in sorted(references.items()):
            values = EffectProvider().parse(self.runtime.read_state(f"List Effect {effect_id}"))
            found = next((item for item in values if item.get("number") == effect_id), None)
            if not found or found.get("name") != expected_label:
                raise EffectRequirementError(f"STALE_EFFECT_RESOURCE: Effect {effect_id} no longer matches its approved label.")
            verified.append(f"{effect_id} — {expected_label}")
        return verified

    def verify_first_song_metadata(self, sequence: int, label: str, expected_cues: list[dict[str, Any]], expected_labels: list[str] | None = None) -> str:
        """Read only the exact known Cue metadata after an approved build.

        `List Cue <number> Part 0 Sequence <number>` is the verified MA2
        detail path.  It never changes selection or Programmer state.
        """
        if not isinstance(sequence, int) or not isinstance(label, str) or not isinstance(expected_cues, list):
            raise FirstSongBuildError("First Song verification metadata is incomplete.")
        labels = expected_labels if isinstance(expected_labels, list) else [cue.get("label") for cue in expected_cues]
        if len(labels) != len(expected_cues):
            raise FirstSongBuildError("First Song verification labels are incomplete.")
        self.refresh_state("sequences")
        sequences = self.state.get("sequences")
        found = next((item for item in (sequences.values if sequences else []) if item.get("number") == sequence), None)
        if not found or found.get("name") != label:
            raise FirstSongBuildError("Verification failed: Agent-owned Sequence label was not read back exactly.")
        provider = CueProvider()
        cues = []
        for expected in expected_cues:
            number = expected.get("cue_number")
            if not isinstance(number, int) or number < 1:
                raise FirstSongBuildError("Verification failed: approved Cue number is invalid.")
            response = self.runtime.read_state(provider.detail_command(sequence, number))
            cue = provider.parse_detail(response, sequence, number)
            if cue is None:
                raise FirstSongBuildError(f"Verification failed: Cue {number} detail was not read back.")
            cues.append(cue)
        self.state.put("cues", cues, source="ma2_telnet_list_detail")
        actual_labels = [item.name for item in cues]
        if len(cues) != len(labels) or actual_labels != labels:
            raise FirstSongBuildError("Verification failed: Cue count or labels do not match the approved plan.")
        fades = [item.fade for item in cues]
        expected_fades = [float(cue.get("fade")) for cue in expected_cues]
        if any(value is None for value in fades) or fades != expected_fades:
            raise FirstSongBuildError("Verification failed: Cue Fade values do not match the approved plan.")
        self.runtime.log("first_song_verification", {"sequence": sequence, "label": label, "cue_count": len(cues), "cue_labels": actual_labels, "fades": fades, "cue_content": "NOT_CHECKED_IN_METADATA_STAGE"})
        return f"Metadata verification: VERIFIED — Sequence {sequence} {label}; {len(cues)} Cue labels and Fades verified."

    def _verify_geometry_test_groups(self, action: ActionRecord, execution_result: str) -> str:
        raw = self._effective_execution_context(action)[1].parameters.get("geometry_test_group_spec")
        try:
            spec = (
                GeometryTestGroupSpec(
                    int(raw["source_fixture"]),
                    int(raw["destination_fixture"]),
                    int(raw["source_group"]),
                    int(raw["destination_group"]),
                )
                if isinstance(raw, dict)
                else None
            )
            if not spec:
                raise GeometryTestEnvironmentError("Test Group setup metadata is incomplete.")
            self.refresh_state("groups")
            groups = self.state.get("groups")
            expected_names = {
                spec.source_group: SOURCE_LABEL,
                spec.destination_group: DESTINATION_LABEL,
            }
            for number, name in expected_names.items():
                group = next(
                    (
                        item
                        for item in (groups.values if groups else [])
                        if item.get("number") == number and item.get("name") == name
                    ),
                    None,
                )
                if not group:
                    raise GeometryTestEnvironmentError(
                        f"Group {number} was not returned with its expected test-only label."
                    )
            expected_members = {
                spec.source_group: spec.source_fixture,
                spec.destination_group: spec.destination_fixture,
            }
            for number, fixture in expected_members.items():
                refreshed = self.refresh_state("group_membership", group_no=number)
                member = next(
                    (item for item in refreshed["values"] if item.get("group_no") == number),
                    None,
                )
                if not member or list(member.get("fixtures") or []) != [fixture]:
                    raise GeometryTestEnvironmentError(
                        f"Group {number} does not contain exactly Fixture {fixture}."
                    )
            return (
                execution_result
                + f"\nVerification: PASSED — Group {spec.source_group} contains Fixture {spec.source_fixture}; "
                + f"Group {spec.destination_group} contains Fixture {spec.destination_fixture}."
            )
        except Exception as exc:
            self.runtime.log("geometry_test_group_verification", {"status": "FAILED", "error": str(exc)})
            raise GeometryTestEnvironmentError(
                f"Verification failed — isolated Geometry test Groups could not be verified: {exc}"
            ) from exc

    def _ensure_timecode_state_unchanged(self, action: ActionRecord) -> None:
        raw = self._effective_execution_context(action)[1].parameters.get("timecode_offset_spec", {})
        number, expected = raw.get("timecode_number"), raw.get("state_fingerprint")
        if not isinstance(number, int) or not isinstance(expected, str):
            raise TimecodeOffsetError("STATE_CHANGED_SINCE_PREVIEW: Timecode preview metadata is incomplete.")
        refreshed = self.refresh_state("timecodes")
        current = next((item for item in refreshed["values"] if item.get("timecode_number") == number), None)
        if not current or fingerprint_timecode(current) != expected:
            raise TimecodeOffsetError("STATE_CHANGED_SINCE_PREVIEW: Timecode inventory changed; create a new Preview before executing.")

    def _ensure_geometry_clone_state_unchanged(self, action: ActionRecord) -> None:
        raw = self._effective_execution_context(action)[1].parameters.get("geometry_clone_spec", {})
        try:
            spec = GeometryCloneSpec.from_summary(raw)
            expected = {
                spec.source_group_number: spec.source_membership_fingerprint,
                spec.destination_group_number: spec.destination_membership_fingerprint,
            }
            for group_no, fingerprint in expected.items():
                refreshed = self.refresh_state("group_membership", group_no=group_no)
                current = next((item for item in refreshed["values"] if item.get("group_no") == group_no), None)
                if not current or membership_fingerprint(current) != fingerprint:
                    raise GeometryCloneError("STATE_CHANGED_SINCE_PREVIEW")
        except (GeometryCloneError, GroupMembershipProviderError, GroupMembershipProviderUnavailable, ConnectionError, ValueError) as exc:
            message = str(exc) or "Group Membership could not be refreshed."
            if not message.startswith("STATE_CHANGED_SINCE_PREVIEW"):
                message = "STATE_CHANGED_SINCE_PREVIEW: " + message
            raise GeometryCloneError(message) from exc

    def _verify_geometry_clone(self, action: ActionRecord, execution_result: str) -> str:
        raw = self._effective_execution_context(action)[1].parameters.get("geometry_clone_spec", {})
        try:
            spec = GeometryCloneSpec.from_summary(raw)
            if re.search(r"(?:\berror\b|illegal)", execution_result, re.I):
                self.runtime.log("geometry_clone_verification", {"status": "FAILED", "reason": "MA2 command feedback reported an error", "source_group": spec.source_group_number, "destination_group": spec.destination_group_number})
                return execution_result + "\nVerification: FAILED — MA2 Clone command feedback reported an error."
            memberships: dict[int, dict[str, Any]] = {}
            for group_no in (spec.source_group_number, spec.destination_group_number):
                refreshed = self.refresh_state("group_membership", group_no=group_no)
                member = next((item for item in refreshed["values"] if item.get("group_no") == group_no), None)
                if not member:
                    raise GeometryCloneError(f"Group {group_no} membership was not returned after Clone.")
                memberships[group_no] = member
            unchanged = (
                membership_fingerprint(memberships[spec.source_group_number]) == spec.source_membership_fingerprint
                and membership_fingerprint(memberships[spec.destination_group_number]) == spec.destination_membership_fingerprint
            )
            fixtures = self.refresh_state("fixtures")
            fixture_numbers = {item.get("number") for item in fixtures["values"]}
            destination_exists = all(fixture in fixture_numbers for fixture in spec.destination_members)
            if not unchanged or not destination_exists:
                self.runtime.log("geometry_clone_verification", {"status": "FAILED", "membership_unchanged": unchanged, "destination_fixtures_exist": destination_exists, "source_group": spec.source_group_number, "destination_group": spec.destination_group_number})
                return execution_result + "\nVerification: FAILED — Group membership changed unexpectedly or a destination Fixture is no longer present."
            self.runtime.log("geometry_clone_verification", {"status": "PARTIAL", "membership_unchanged": True, "destination_fixtures_exist": True, "source_group": spec.source_group_number, "destination_group": spec.destination_group_number, "pair_count": len(spec.pairs), "internal_clone_data": "UNSUPPORTED"})
            return execution_result + f"\nVerification: PARTIAL — {len(spec.pairs)} native MA2 Clone commands returned without an error; source/destination Group membership is unchanged and destination Fixtures still exist. Internal cloned fixture data has no verified read-back provider."
        except Exception as exc:
            self.runtime.log("geometry_clone_verification", {"status": "PARTIAL", "error": str(exc)})
            return execution_result + f"\nVerification: PARTIAL — Clone commands were sent, but post-Clone read-back failed: {exc}"

    def _verify_timecode_offset(self, action: ActionRecord, execution_result: str) -> str:
        raw = self._effective_execution_context(action)[1].parameters.get("timecode_offset_spec", {})
        number = raw.get("timecode_number")
        try:
            result = self.refresh_state("timecodes")
            found = next((item for item in result["values"] if item.get("timecode_number") == number), None)
            if not found:
                self.runtime.log("timecode_offset_verification", {"timecode_number": number, "status": "FAILED", "reason": "Timecode not returned by List Timecode"})
                return execution_result + f"\nVerification: FAILED — Timecode {number} was not returned by List Timecode."
            expected_ms = raw.get("offset_ms")
            actual_ms = found.get("offset_ms")
            exact = isinstance(expected_ms, int) and actual_ms == expected_ms
            status = "VERIFIED" if exact else "PARTIAL"
            self.runtime.log("timecode_offset_verification", {"timecode_number": number, "status": status, "exists": True, "expected_offset_ms": expected_ms, "actual_offset_ms": actual_ms, "event_readback": "UNSUPPORTED"})
            if exact:
                return execution_result + f"\nVerification: VERIFIED — Timecode {number} Offset read back as +{expected_ms / 1000:.3f} s. Event-level time read-back is unavailable."
            return execution_result + f"\nVerification: PARTIAL — Timecode {number} remains present, but Offset read-back was unavailable or mismatched (expected {expected_ms} ms; returned {actual_ms})."
        except Exception as exc:
            self.runtime.log("timecode_offset_verification", {"timecode_number": number, "status": "PARTIAL", "error": str(exc)})
            return execution_result + f"\nVerification: PARTIAL — offset command was sent, but Timecode inventory re-read failed: {exc}"

    def _verify_effect_builder(self, action: ActionRecord, execution_result: str) -> str:
        """Perform the explicit read-only, necessarily partial v1 verification."""
        spec = self._effective_execution_context(action)[1].parameters.get("effect_spec", {})
        number = spec.get("effect_number")
        expected_name = str(spec.get("name") or "")
        if not isinstance(number, int):
            return execution_result + "\nVerification: partial — Effect number was unavailable."
        try:
            provider = EffectProvider()
            output = self.runtime.read_state(f"List Effect {number}")
            rows = provider.parse(output)
            found = next((item for item in rows if item.get("number") == number), None)
            if not found:
                self.runtime.log("effect_builder_verification", {"effect_number": number, "status": "FAILED", "reason": "Effect not returned by List Effect <number>", "output": output})
                return execution_result + f"\nVerification: FAILED — Effect {number} was not returned by List Effect {number}."
            actual_name = str(found.get("name") or "")
            label_verified = actual_name == expected_name
            self.state.upsert("effects", "number", found, source="ma2_telnet_list")
            self.runtime.log("effect_builder_verification", {"effect_number": number, "status": "PARTIAL", "exists": True, "expected_name": expected_name, "actual_name": actual_name, "label_verified": label_verified})
            requirement_raw = self._effective_execution_context(action)[1].parameters.get("effect_requirement")
            context = self._effective_execution_context(action)[1].parameters.get("effect_catalog_context")
            if label_verified and isinstance(requirement_raw, dict) and isinstance(context, dict) and isinstance(context.get("show_identity"), dict):
                requirement = EffectRequirement.from_dict(requirement_raw)
                entry = self.effect_catalog.record(
                    requirement=requirement,
                    effect_id=number,
                    label=actual_name,
                    identity=context["show_identity"],
                    verification={"object": "VERIFIED", "label": "VERIFIED", "parameters": "PARTIAL"},
                )
                self.runtime.log("effect_catalog_recorded", {"effect_id": number, "label": actual_name, "ownership": entry["ownership"], "show_identity": context["show_identity"]})
            label = "label matches" if label_verified else f"label not exposed/matched (returned: {actual_name or 'none'})"
            catalog_note = " Agent-owned catalog metadata saved." if label_verified and isinstance(requirement_raw, dict) and isinstance(context, dict) else ""
            return execution_result + f"\nVerification: PARTIAL — Effect {number} exists; {label}. Parameter verification is not exposed by EffectProvider." + catalog_note
        except Exception as exc:
            self.runtime.log("effect_builder_verification", {"effect_number": number, "status": "PARTIAL", "error": str(exc)})
            return execution_result + f"\nVerification: PARTIAL — Effect commands were sent, but read-back failed: {exc}"
