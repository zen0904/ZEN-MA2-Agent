"""Adapt the existing portable ProviderRouter to the one-call lean Designer seam."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..designer.lean_provider import LeanDesignIntelligence
from .router import ProviderRouter, ProviderUnavailable


LEAN_DESIGN_ROLE = "LIGHTING_DESIGNER"
ALLOWED_RUNTIME_COST_CLASSES = frozenset({"FREE", "LOCAL"})

_SYSTEM_PROMPT = """You are ZEN's Lighting Designer.
Return exactly one JSON object following ARTISTIC_CUES_V0_2.
You choose artistic intent only. Never emit MA2 commands, Telnet, Lua, shell,
patch/address operations, Fixture identity changes, allocation decisions, or
executor/sequence addresses.

Output shape:
{"cues":[{"label":"...", "fade":0, "actions":[...]}]}

Each compact action MUST use the exact field `group` with a JSON integer Group ID.
Never use `group_id`, a Group name/string, `target`, or `operation` in compact actions.
Examples:
{"group":1,"dimmer":50}
{"group":1,"color_preset":"4.101"}
{"group":1,"effect":2500}
Each action must contain exactly one artistic value such as dimmer, preset,
color_preset, position_preset, focus_preset, beam_preset, gobo_preset, or effect.
Use only resources explicitly exposed in verified_resource_contract.
Do not invent unavailable resources. Return JSON only, with no markdown.
"""


class ProviderRouterLeanDesignIntelligence(LeanDesignIntelligence):
    """One logical Designer call routed only through explicit FREE/LOCAL slots."""

    def __init__(self, router: ProviderRouter):
        safe_slots = tuple(
            slot
            for slot in router.slots
            if slot.configured
            and slot.supports(LEAN_DESIGN_ROLE)
            and slot.cost_class in ALLOWED_RUNTIME_COST_CLASSES
        )
        if not safe_slots:
            raise ValueError("No explicit FREE/LOCAL provider is eligible for LIGHTING_DESIGNER.")
        # Normal design is a single logical role call. Ordered transport fallback
        # may occur inside that call, but only across explicit FREE/LOCAL slots.
        # Parallel candidate generation remains deep/research mode only.
        self.router = ProviderRouter(
            router.mode,
            safe_slots,
            adapter=router.adapter,
            parallelism=1,
            parallel_roles=(),
        )
        self.last_diagnostics: dict[str, Any] | None = None

    def design(self, request: str, context: Mapping[str, Any]) -> str:
        if not isinstance(request, str) or not request.strip() or len(request) > 2048:
            raise ValueError("Lean design request must be a non-empty bounded string.")
        if not isinstance(context, Mapping):
            raise ValueError("Lean design context must be a mapping.")
        user = json.dumps(
            {"request": request, "context": dict(context)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        content, slot, attempts = self.router.complete_with_diagnostics(
            role=LEAN_DESIGN_ROLE,
            system=_SYSTEM_PROMPT,
            user=user,
        )
        self.last_diagnostics = {
            "role": LEAN_DESIGN_ROLE,
            "provider_identity": slot.safe_identity(),
            "attempts": list(attempts),
            "paid_provider_allowed": False,
            "parallel_candidates": False,
        }
        return content

    def safe_summary(self) -> dict[str, Any]:
        return {
            "role": LEAN_DESIGN_ROLE,
            "eligible_slots": [
                slot.safe_identity() for slot in self.router.candidates(LEAN_DESIGN_ROLE)
            ],
            "paid_provider_allowed": False,
            "parallel_candidates": False,
        }


def lean_design_intelligence_from_router(
    router: ProviderRouter,
) -> ProviderRouterLeanDesignIntelligence | None:
    eligible = [
        slot
        for slot in router.slots
        if slot.configured
        and slot.supports(LEAN_DESIGN_ROLE)
        and slot.cost_class in ALLOWED_RUNTIME_COST_CLASSES
    ]
    if not eligible:
        return None
    return ProviderRouterLeanDesignIntelligence(router)


def load_portable_lean_design_intelligence(
    path: Path | None = None,
) -> ProviderRouterLeanDesignIntelligence | None:
    """Load portable config only. This function performs no provider/network call."""
    router = ProviderRouter.from_portable_config(path)
    return lean_design_intelligence_from_router(router)


__all__ = [
    "LEAN_DESIGN_ROLE",
    "ALLOWED_RUNTIME_COST_CLASSES",
    "ProviderRouterLeanDesignIntelligence",
    "lean_design_intelligence_from_router",
    "load_portable_lean_design_intelligence",
]
