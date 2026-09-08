"""Non-executable Builder PoC.

This preserves the existing ActionPlan model while refusing to invent MA2
syntax for a plan whose Fixture/Preset/Effect semantics are not yet readable.
"""
from __future__ import annotations

from typing import Any

from ..designer.schema import validate_show_plan
from ..models import Intent
from ..workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


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
        label = self._sequence_label(str(plan.get("song") or "SONG"))
        if any(item.get("name") == label for item in profile.get("sequences", [])):
            raise FirstSongBuildError("BLOCKED: an existing Sequence already has this Agent-owned label; refusing an ambiguous build.")
        group_ids = {item.get("group_id") for item in profile.get("groups", [])}
        preset_refs = {item.get("reference") for item in profile.get("presets", []) if item.get("reference")}
        steps = []
        # A first-song build necessarily uses the Programmer. The explicit
        # ClearAll at both boundaries guarantees no build values persist; the
        # Preview exposes this state impact before approval.
        steps.append(("clear-before", "Clear Programmer before Agent-owned cue build", "ClearAll"))
        labelled = False
        referenced_groups, referenced_presets = set(), set()
        for cue in plan["cues"]:
            cue_no, cue_label, fade = cue["cue_number"], cue["label"], float(cue["fade"])
            for index, action in enumerate(cue["actions"], start=1):
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
                else:
                    raise FirstSongBuildError(f"Cue {cue_no} has unsupported operation {action['operation']}.")
            command = f'Store Cue {cue_no} Sequence {sequence} "{cue_label}" Fade {fade:g} /nc'
            steps.append((f"cue-{cue_no}-store", f"Store Agent-owned Cue {cue_no} {cue_label}", command))
            if not labelled:
                steps.append(("label-sequence", "Label new Agent-owned Sequence", f'Label Sequence {sequence} "{label}" /nc'))
                labelled = True
        steps.append(("clear-after", "Clear Agent build Programmer values", "ClearAll"))
        action_steps = tuple(ActionStep(step_id, title, "command", command, "MODIFY") for step_id, title, command in steps)
        preview = "\n".join([
            "ZEN AI SHOW BUILD PREVIEW", "", f"Song: {plan['song']}", f"Target Sequence: {sequence}", f"New label: {label}",
            f"Resources referenced: Groups {', '.join(map(str, sorted(referenced_groups)))}; Presets {', '.join(sorted(referenced_presets))}",
            "Effects: none (no verified production Effect-call grammar)", f"Will create: Sequence {sequence}; Cues {len(plan['cues'])}",
            "Will modify existing TEMPLATE: NONE", "Will modify production Cue: NONE", "", "Safety: MODIFY", "Approval required.", "", "Generated MA2 commands:", *[f"- {command}" for _, _, command in steps],
        ])
        intent = Intent("build_first_song", {"song": plan["song"], "sequence": sequence, "sequence_label": label, "cue_count": len(plan["cues"]), "cue_labels": [cue["label"] for cue in plan["cues"]], "cues": plan["cues"], "referenced_groups": sorted(referenced_groups), "referenced_presets": sorted(referenced_presets), "warnings": plan.get("warnings", [])}, "ZEN_SHOW_PLAN")
        return WorkflowPlan(Task("first-song-build", "Build First Song", intent, "show.builder", ("groups", "presets", "sequences")), (Subtask("resolve", "Resolve scanned resources and unused Sequence", "Planning"), Subtask("preview", "Preview Agent-owned Sequence build", "Planning"), Subtask("execute", "Execute approved cue build", "Execution"), Subtask("verify", "Verify Sequence/Cue metadata", "Verification")), (SkillGraphNode("root", "show.builder", "First Song Builder"),), action_steps, "MODIFY", preview, ("PREVIEW",), "Read Sequence and Cue metadata after build; Preset value call is PARTIAL because Cue-content readback has no provider.", f"Narrow rollback: Delete Sequence {sequence} only after exact Agent-owned label verification.", True)

    @staticmethod
    def _allocate_sequence(plan: dict[str, Any], profile: dict[str, Any]) -> int:
        limits = plan.get("active_sequence_range")
        if not isinstance(limits, list) or len(limits) != 2:
            raise FirstSongBuildError("Plan has no explicit active Sequence range.")
        used = {item.get("number") for item in profile.get("sequences", [])}
        for number in range(int(limits[0]), int(limits[1]) + 1):
            if number not in used:
                return number
        raise FirstSongBuildError("BLOCKED: no unused Sequence is available in the active range.")

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
