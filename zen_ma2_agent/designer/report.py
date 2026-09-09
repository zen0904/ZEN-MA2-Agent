"""Human-readable report for a typed, deterministic real-song design."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def write_real_song_design_report(plan: dict[str, Any], profile: dict[str, Any], path: Path) -> Path:
    """Write only a local explanation of already typed design choices."""
    cues = list(plan.get("cues") or [])
    effect_ids = sorted({action.get("effect_ref", {}).get("id") for cue in cues for action in cue.get("actions", []) if action.get("operation") == "CALL_EFFECT" and isinstance(action.get("effect_ref"), dict) and isinstance(action["effect_ref"].get("id"), int)})
    preset_refs = sorted({str(action.get("preset_ref")) for cue in cues for action in cue.get("actions", []) if action.get("operation") == "CALL_PRESET" and action.get("preset_ref")})
    geometry = plan.get("designer", {}).get("uses_neutral_geometry")
    lines = [
        "# ZEN Real Song Design Report", "", f"Song: {plan.get('song')}", f"Sections / generated cues: {len(cues)}", "",
        "## Deterministic progression", "",
        "| Cue | Section | Role | Energy | Fade | Preset | Effect |",
        "|---:|---|---|---:|---:|---|---|",
    ]
    for cue in cues:
        actions = cue.get("actions") or []
        preset = next((str(item.get("preset_ref")) for item in actions if item.get("operation") == "CALL_PRESET"), "NONE")
        effect = next((str(item.get("effect_ref", {}).get("id")) for item in actions if item.get("operation") == "CALL_EFFECT" and isinstance(item.get("effect_ref"), dict)), "NONE")
        lines.append(f"| {cue.get('cue_number')} | {cue.get('label')} | {cue.get('role')} | {float(cue.get('design_energy', 0)):.2f} | {float(cue.get('fade', 0)):.2f} | {preset} | {effect} |")
    lines += [
        "", "## Resources", "", f"- Groups: dynamic scanned references ({len(profile.get('groups') or [])} available)",
        f"- Presets used: {', '.join(preset_refs) or 'NONE'}",
        f"- Effects used: {', '.join(map(str, effect_ids)) or 'NONE'}",
        f"- Geometry usage: {'neutral numeric geometry available to Designer' if geometry else 'FALLBACK — no fresh geometry profile was required for this safe Group-based build'}",
        f"- Semantic Position: {'AVAILABLE' if profile.get('semantic_presets') else 'FALLBACK — no exact POS_STAGE_* resource was referenced'}",
        "", "## Repeated-section variation", "", "Repeated roles receive a bounded occurrence uplift to intensity; PRE/CHORUS Effect requirements are intentionally reused when the input selects the reuse-only policy.",
        "", "## Warnings / fallbacks", "",
    ]
    lines.extend(f"- {warning}" for warning in (plan.get("warnings") or ["None."]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
