"""Non-executable Builder PoC.

This preserves the existing ActionPlan model while refusing to invent MA2
syntax for a plan whose Fixture/Preset/Effect semantics are not yet readable.
"""
from __future__ import annotations

from typing import Any

from ..designer.schema import validate_show_plan
from ..models import Intent
from ..workflow import SkillGraphNode, Subtask, Task, WorkflowPlan


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
