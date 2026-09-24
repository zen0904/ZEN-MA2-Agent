"""Non-executable Builder PoC.

This preserves the existing ActionPlan model while refusing to invent MA2
syntax for a plan whose Fixture/Preset/Effect semantics are not yet readable.
"""
from __future__ import annotations

import re
from typing import Any

from ..allocation import AllocationError, first_free_executor, first_free_from_front
from ..designer.schema import validate_show_plan
from ..ma_text import validate_ma_text
from ..models import Intent
from .. import protected_objects
from ..workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan
from ..cue_effect_application import cue_effect_capability_is_content_verified


class FirstSongBuildError(ValueError):
    pass


class ShowPlanBuilder:
    def draft(self, plan: dict[str, Any], profile: dict[str, Any]) -> WorkflowPlan:
        plan = validate_show_plan(plan)
        task = Task("show-plan-draft", "Build Show Plan Draft", Intent("build_show_plan_draft", {"cue_count": len(plan["cues"])}, "ZEN_SHOW_PLAN"), "builder.show_plan")
        unresolved: list[str] = []
        group_ids = {item.get("group_id") for item in profile.get("groups", [])}
        effect_ids = {item.get("effect_id") for item in profile.get("effects", [])}
        for cue in plan["cues"]:
            intent = cue.get("intent", {})
            group = intent.get("group_id")
            effect = intent.get("effect_id")
            if group is not None and group not in group_ids:
                unresolved.append(f"Cue {cue['id']}: Group {group}")
            if effect is not None and effect not in effect_ids:
                unresolved.append(f"Cue {cue['id']}: Effect {effect}")
        details = "All currently referenced pool IDs are present." if not unresolved else "Unresolved references: " + "; ".join(unresolved)
        return WorkflowPlan(
            task,
            (Subtask("validate", "Validate design intent and known references", "Planning"), Subtask("draft", "Prepare non-executable implementation draft", "Planning")),
            (SkillGraphNode("root", "builder.show_plan", "Show Plan Draft"),),
            (),
            "SAFE",
            "Show Plan Draft Only\n\nNo MA2 commands were generated. " + details,
            (),
            "No MA2 execution; implementation requires verified fixture, preset, and effect-value providers.",
            "No rollback required because this draft sends no MA2 command.",
            False,
        )

    def build_first_song(self, plan: dict[str, Any], profile: dict[str, Any]) -> WorkflowPlan:
        """Resolve a typed first-song plan into a narrow approved MA2 workflow.

        It is intentionally limited to selecting a scanned Group, calling a
        scanned Preset, setting Dimmer, and storing/labelling Cue metadata in
        a newly allocated Sequence.  No arbitrary command field reaches here.
        """
        plan = validate_show_plan(plan)
        sequence = self._allocate_sequence(plan, profile)
        label = self._sequence_label_for_build(
            str(plan.get("song") or "SONG"),
            sequence,
            profile,
        )
        target_executor = self._allocate_executor(plan, profile)
        group_ids = {item.get("group_id") for item in profile.get("groups", [])}
        preset_refs = {item.get("reference") for item in profile.get("presets", []) if item.get("reference")}
        preset_types = {
            item.get("reference"): str(item.get("preset_type") or "").upper()
            for item in profile.get("presets", [])
            if item.get("reference")
        }
        effect_ids = {item.get("effect_id") for item in profile.get("effects", []) if item.get("effect_id")}
        steps = []
        # A first-song build necessarily uses the Programmer. The explicit
        # ClearAll at both boundaries guarantees no build values persist; the
        # Preview exposes this state impact before approval.
        steps.append(("clear-before", "Clear Programmer before Agent-owned cue build", "ClearAll"))
        labelled = False
        referenced_groups, referenced_presets, referenced_effects = set(), set(), set()
        capability = plan.get("effect_application_capability")
        effect_application_verified = cue_effect_capability_is_content_verified(capability)
        effect_application_blocked: list[int] = []
        for cue in plan["cues"]:
            cue_no, cue_label, fade = cue["cue_number"], cue["label"], float(cue["fade"])
            validate_ma_text(str(cue_label), field=f"cue[{cue_no}].label")
            indexed_actions = list(enumerate(cue["actions"], start=1))
            # Real-MA2 Sequence 901 content evidence shows that the Atomic 3000
            # multi-instance Group 7 stores Color Preset 4.112 reliably when
            # Color preset values enter the Programmer before direct Dimmer
            # values.  Sequence 5 and 7 both lost that same Preset when the
            # canonical action order was Dimmer then Color.  ShowPlan actions
            # are declarative typed state, so only verified COLOR Preset calls
            # are normalized ahead of the remaining actions; original action
            # indexes and the canonical plan are preserved for verification.
            color_preset_actions = [
                item for item in indexed_actions
                if item[1].get("operation") == "CALL_PRESET"
                and str(
                    item[1].get("preset_type")
                    or preset_types.get(item[1].get("preset_ref"))
                    or ""
                ).upper() == "COLOR"
            ]
            remaining_actions = [item for item in indexed_actions if item not in color_preset_actions]
            for index, action in [*color_preset_actions, *remaining_actions]:
                target = action["target"]
                group = target.get("ref")
                if target.get("type") != "group" or group not in group_ids:
                    raise FirstSongBuildError(f"Cue {cue_no} references an unavailable scanned Group.")
                if action["operation"] == "CALL_PRESET":
                    reference = action.get("preset_ref")
                    if reference not in preset_refs:
                        raise FirstSongBuildError(f"Cue {cue_no} references an unavailable scanned Preset {reference}.")
                    steps.extend(((f"cue-{cue_no}-select-{index}", f"Select scanned Group {group}", f"Group {group}"), (f"cue-{cue_no}-preset-{index}", f"Call scanned Preset {reference}", f"At Preset {reference}")))
                    referenced_groups.add(group); referenced_presets.add(reference)
                elif action["operation"] == "SET_DIMMER":
                    level = action.get("level")
                    if not isinstance(level, int) or not 0 <= level <= 100:
                        raise FirstSongBuildError(f"Cue {cue_no} has an invalid Dimmer level.")
                    steps.extend(((f"cue-{cue_no}-select-{index}", f"Select scanned Group {group}", f"Group {group}"), (f"cue-{cue_no}-dimmer-{index}", f"Set Dimmer {level}%", f"At {level}")))
                    referenced_groups.add(group)
                elif action["operation"] == "CALL_EFFECT":
                    reference = action.get("effect_ref")
                    if not isinstance(reference, dict) or not isinstance(reference.get("id"), int) or reference["id"] not in effect_ids:
                        raise FirstSongBuildError(f"Cue {cue_no} references an unresolved Effect resource.")
                    referenced_groups.add(group)
                    referenced_effects.add(reference["id"])
                    if effect_application_verified:
                        steps.extend(((f"cue-{cue_no}-select-{index}", f"Select scanned Group {group}", f"Group {group}"), (f"cue-{cue_no}-effect-{index}", f"Call content-verified Effect {reference['id']} via At Effect", f"At Effect {reference['id']}")))
                    else:
                        effect_application_blocked.append(reference["id"])
                else:
                    raise FirstSongBuildError(f"Cue {cue_no} has unsupported operation {action['operation']}.")
            command = f'Store Cue {cue_no} Sequence {sequence} "{cue_label}" Fade {fade:g} /nc'
            steps.append((f"cue-{cue_no}-store", f"Store Agent-owned Cue {cue_no} {cue_label}", command))
            if not labelled:
                steps.append(("label-sequence", "Label new Agent-owned Sequence", f'Label Sequence {sequence} "{label}" /nc'))
                labelled = True
        if target_executor is not None:
            steps.append(("assign-executor", f"Assign Sequence {sequence} to Page 2 Executor", f"Assign Sequence {sequence} At Executor {target_executor} /nc"))
            validate_ma_text(label, field="sequence.label")
            steps.append(("label-executor", "Label the owned target Executor", f'Label Executor {target_executor} "{label}" /nc'))
        steps.append(("clear-after", "Clear Agent build Programmer values", "ClearAll"))
        action_steps = tuple(ActionStep(step_id, title, "command", command, "MODIFY") for step_id, title, command in steps)
        effect_line = "Effects: none" if not referenced_effects else (
            "Effects: resolved references " + ", ".join(map(str, sorted(referenced_effects))) + ("; effect-pool call grammar verified by isolated real-MA2 POC." if effect_application_verified else "; EFFECT_APPLICATION_UNVERIFIED — no Cue Effect MA2 commands were generated.")
        )
        preview_title = "ZEN AI REAL SONG BUILD PREVIEW" if plan.get("designer", {}).get("input_kind") == "SONG_ANALYSIS" else "ZEN AI SHOW BUILD PREVIEW"
        cue_preview = []
        for cue in plan["cues"]:
            effect = next((action.get("effect_ref") for action in cue["actions"] if action.get("operation") == "CALL_EFFECT"), None)
            effect_text = "NONE" if not isinstance(effect, dict) else f"{effect.get('label') or 'Effect'} (ID: {effect.get('id')})"
            cue_preview.append(f"Cue {cue['cue_number']} — {cue['label']} | Energy {float(cue.get('design_energy', 0)):.2f} | Fade {float(cue['fade']):g} | Effect: {effect_text}")
        preview = "\n".join([
            preview_title, "", f"Song: {plan['song']}", f"Target Sequence: {sequence}", f"New label: {label}", f"Generated Cues: {len(plan['cues'])}", "",
            "Cue design:", *[f"- {line}" for line in cue_preview], "", "Resources:",
            f"Groups: {', '.join(map(str, sorted(referenced_groups)))}", f"Presets: {', '.join(sorted(referenced_presets)) or 'NONE'}", effect_line,
            "New Effects to create: NONE", f"Geometry usage: {'neutral numeric geometry available' if plan.get('designer', {}).get('uses_neutral_geometry') else 'FALLBACK — no fresh geometry profile required for this safe Group build'}",
            f"Warnings: {'; '.join(plan.get('warnings') or ['None'])}", "Effect application: " + ("REAL_MACHINE_CONTENT_VERIFIED" if effect_application_verified else "EFFECT_APPLICATION_UNVERIFIED"),
            "Existing production objects modified: NONE", f"Will create: Sequence {sequence}; Cues {len(plan['cues'])}", "", "Safety: MODIFY", "Approval required.", "", "Generated MA2 commands:", *[f"- {command}" for _, _, command in steps],
        ])
        effect_application = "EFFECT_APPLICATION_UNVERIFIED" if effect_application_blocked else "REAL_MACHINE_CONTENT_VERIFIED" if referenced_effects else "NOT_REQUESTED"
        intent = Intent("build_first_song", {"song": plan["song"], "sequence": sequence, "sequence_label": label, "target_executor": plan.get("target_executor"), "cue_count": len(plan["cues"]), "cue_labels": [cue["label"] for cue in plan["cues"]], "cues": plan["cues"], "referenced_groups": sorted(referenced_groups), "referenced_presets": sorted(referenced_presets), "referenced_effects": sorted(referenced_effects), "effect_application": effect_application, "warnings": plan.get("warnings", [])}, "ZEN_SHOW_PLAN")
        executable = not effect_application_blocked
        verification = "Verify Sequence/Cue metadata and exported Cue content. Raw Dimmer/Color Preset content is readable; Effect application is executable only from REAL_MACHINE_CONTENT_VERIFIED capability evidence."
        if effect_application_blocked:
            verification = "EFFECT_APPLICATION_UNVERIFIED: typed Effect references were resolved, but no content-level Sequence Export evidence proves that the Effect is stored in the Cue. No Sequence commands may run."
        return WorkflowPlan(Task("first-song-build", "Build First Song", intent, "show.builder", ("groups", "presets", "effects", "sequences")), (Subtask("resolve", "Resolve scanned resources and unused Sequence", "Planning"), Subtask("preview", "Preview Agent-owned Sequence build", "Planning"), Subtask("execute", "Execute approved cue build", "Execution"), Subtask("verify", "Verify Sequence/Cue metadata", "Verification")), (SkillGraphNode("root", "show.builder", "First Song Builder"),), action_steps, "MODIFY", preview, ("PREVIEW",), verification, f"Narrow rollback: Delete Sequence {sequence} only after exact Agent-owned label verification.", executable)

    @staticmethod
    def _allocate_sequence(plan: dict[str, Any], profile: dict[str, Any]) -> int:
        limits = plan.get("active_sequence_range")
        if not isinstance(limits, list) or len(limits) != 2:
            raise FirstSongBuildError("Plan has no explicit active Sequence range.")
        used = [item.get("number") for item in profile.get("sequences", []) if isinstance(item, dict)]
        try:
            return first_free_from_front(
                used,
                protected=protected_objects.PROTECTED_SEQUENCES,
                start=int(limits[0]),
                end=int(limits[1]),
            )
        except AllocationError as exc:
            raise FirstSongBuildError("BLOCKED: no unused Sequence is available in the active range.") from exc

    @classmethod
    def _allocate_executor(cls, plan: dict[str, Any], profile: dict[str, Any]) -> str | None:
        requested = cls._executor_address(plan.get("target_executor"))
        if requested is None:
            return None
        page = int(requested.split(".", 1)[0])
        try:
            # Executor numbers are ZEN-owned operational metadata.  A supplied
            # address selects a Page only; allocation always begins at 001.
            return cls._executor_address(
                first_free_executor(profile.get("executors", []), page=page)
            )
        except AllocationError as exc:
            raise FirstSongBuildError("BLOCKED: no unused Executor is available on the target Page.") from exc

    @staticmethod
    def narrow_rollback_command(sequence: int, label: str, observed_sequence: dict[str, Any] | None) -> str:
        """Return the only permitted recovery command after exact ownership proof.

        This deliberately does *not* execute anything.  A caller must still
        create a separate DANGEROUS ActionPlan and obtain explicit approval.
        """
        if (
            isinstance(sequence, int)
            and sequence > 0
            and isinstance(label, str)
            and label.startswith("ZEN_AI_TEST_")
            and isinstance(observed_sequence, dict)
            and observed_sequence.get("number") == sequence
            and observed_sequence.get("name") == label
        ):
            return f"Delete Sequence {sequence} /nc"
        raise FirstSongBuildError("Narrow rollback blocked: exact Agent-owned Sequence identity was not read back.")

    @staticmethod
    def _sequence_label(song: str) -> str:
        safe = "".join(character if character.isalnum() or character in "_-" else "_" for character in song.upper()).strip("_")
        return f"ZEN_AI_TEST_{safe[:40] or 'SONG'}"

    @classmethod
    def _sequence_label_for_build(
        cls,
        song: str,
        sequence: int,
        profile: dict[str, Any],
    ) -> str:
        """Return a deterministic Agent-owned label without reusing another Sequence's label.

        Song identity is artistic/task metadata; Sequence labels are operational
        metadata owned by ZEN.  A prior A/B or smoke build may legitimately use
        the base song label, so a new unused Sequence gets a Sequence-number
        suffix instead of blocking or forcing another provider call.
        """
        base = cls._sequence_label(song)
        existing = {
            str(item.get("name"))
            for item in profile.get("sequences", [])
            if isinstance(item, dict) and item.get("name")
        }
        if base not in existing:
            return base
        suffix = f"_SEQ{sequence}"
        max_base = max(1, 52 - len(suffix))
        candidate = f"{base[:max_base]}{suffix}"
        if candidate not in existing:
            return candidate
        for ordinal in range(2, 1000):
            extra = f"_{ordinal}"
            max_base = max(1, 52 - len(suffix) - len(extra))
            candidate = f"{base[:max_base]}{suffix}{extra}"
            if candidate not in existing:
                return candidate
        raise FirstSongBuildError("BLOCKED: no unique Agent-owned Sequence label could be allocated.")

    @staticmethod
    def _executor_address(value: object) -> str | None:
        """Validate a display target (for example ``2.001``) and return MA2's
        canonical page.executor address (``2.1``). Pages are pre-existing;
        this builder never creates or changes a Page.
        """
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise FirstSongBuildError("target_executor must be a display string such as 2.001.")
        match = re.fullmatch(r"([1-9]\d*)\.(0*[1-9]\d*)", value.strip())
        if not match:
            raise FirstSongBuildError("target_executor must use page.executor form such as 2.001.")
        page, executor = int(match.group(1)), int(match.group(2))
        if page < 1 or executor < 1:
            raise FirstSongBuildError("target_executor must address positive Page and Executor numbers.")
        return f"{page}.{executor}"
