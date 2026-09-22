"""Bounded artistic resources for the disposable SHEESH Test Show.

This module contains only deterministic, fixed Test Show resources. It does
not inspect MA2, call a provider, or perform transport. The script-level
Builder owns execution and must still verify the resulting native objects.

Template Effects are intentionally different from the existing selective
Effect Builder v1: they contain no stored fixture selection and therefore may
be applied to a current selection only after MA2 read-back proves that the pool
object is a TEMPLATE effect.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


_TEMPLATE_EFFECTS = (
    ("FX_DIM_CHASE_SLOW", 30),
    ("FX_DIM_CHASE_MED", 60),
    ("FX_DIM_CHASE_FAST", 120),
)


@dataclass(frozen=True)
class TemplateEffectSpec:
    effect_id: int
    label: str
    speed_bpm: int
    attribute: str = "Dim"
    form: str = "PWM"
    low: int = 0
    high: int = 100
    phase: str = "0..360"
    groups: int = 1

    def summary(self) -> dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "label": self.label,
            "speed_bpm": self.speed_bpm,
            "attribute": self.attribute,
            "form": self.form,
            "low": self.low,
            "high": self.high,
            "phase": self.phase,
            "groups": self.groups,
        }


def allocate_template_effect_specs(
    existing_effects: Iterable[Mapping[str, Any]],
    *,
    start: int = 2500,
) -> tuple[TemplateEffectSpec, ...]:
    """Allocate three unused Test Show Effect IDs without overwriting anything."""
    used = {
        int(item["number"])
        for item in existing_effects
        if isinstance(item, Mapping)
        and isinstance(item.get("number"), int)
        and not isinstance(item.get("number"), bool)
        and int(item["number"]) > 0
    }
    specs: list[TemplateEffectSpec] = []
    candidate = max(1, int(start))
    for label, bpm in _TEMPLATE_EFFECTS:
        while candidate in used:
            candidate += 1
        specs.append(TemplateEffectSpec(candidate, label, bpm))
        used.add(candidate)
        candidate += 1
    return tuple(specs)


def template_effect_commands(spec: TemplateEffectSpec) -> tuple[str, ...]:
    """Return deterministic native commands for one template Effect.

    The critical property is the absence of Group/Fixture selection and the
    absence of a post-selection Take Selection store. The caller must begin
    from ClearAll and verify the created Effect is reported as TEMPLATE.
    """
    if spec.label not in {label for label, _ in _TEMPLATE_EFFECTS}:
        raise ValueError("Unapproved Test Show template Effect label.")
    expected_speed = dict(_TEMPLATE_EFFECTS)[spec.label]
    if spec.speed_bpm != expected_speed:
        raise ValueError("Template Effect speed does not match its fixed label.")
    line = f"1.{spec.effect_id}.1"
    return (
        "ClearAll",
        f"Store Effect {spec.effect_id} /nc",
        f"Store Effect {line} /nc",
        f'Assign Attribute "{spec.attribute}" At Effect {line}',
        f'Assign Form "{spec.form}" At Effect {line}',
        f"Assign Effect {spec.effect_id} /lowvalue={spec.low} /highvalue={spec.high} /speed={spec.speed_bpm} /phase={spec.phase} /groups={spec.groups}",
        f'Label Effect {spec.effect_id} "{spec.label}" /nc',
        "ClearAll",
    )


def verify_template_effect_rows(
    rows: Iterable[Mapping[str, Any]],
    specs: Iterable[TemplateEffectSpec],
) -> dict[int, dict[str, Any]]:
    """Verify exact ID/label and native TEMPLATE classification from List Effect."""
    by_id = {
        int(item["number"]): item
        for item in rows
        if isinstance(item, Mapping)
        and isinstance(item.get("number"), int)
        and not isinstance(item.get("number"), bool)
    }
    result: dict[int, dict[str, Any]] = {}
    for spec in specs:
        row = by_id.get(spec.effect_id)
        label_ok = bool(row and str(row.get("name") or "") == spec.label)
        template_ok = bool(row and str(row.get("kind") or "").upper() == "TEMPLATE")
        result[spec.effect_id] = {
            "label": spec.label,
            "label_verified": label_ok,
            "template_kind_verified": template_ok,
            "verified": label_ok and template_ok,
        }
    return result
