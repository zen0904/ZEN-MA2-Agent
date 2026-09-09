"""Build local Training Case 001 documentation from the fresh Show profile."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.training_case import build_training_case_001


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _role_block(group: dict) -> list[str]:
    role = group["role_assignment"]
    return [
        f"### Group {group['group_id']} `{group['name']}`",
        "",
        f"- Fixture IDs (verified selection order): `{', '.join(map(str, group['fixture_ids_in_selection_order']))}`",
        f"- Fixture Type(s): `{'; '.join(group['fixture_types'])}`",
        f"- Primary role: **{role['primary_role']}**",
        f"- Secondary roles: `{', '.join(role['secondary_roles']) or 'none'}`",
        f"- Contextual roles: `{', '.join(role['contextual_roles']) or 'none'}`",
        f"- Possible rig zones: `{', '.join(role['possible_rig_zones'])}` (**PROPOSED_RIG_ZONE**)",
        f"- Rationale: {role['rationale']}",
        f"- Confidence: `{role['confidence']}`; scope: `{role['scope']}`",
        "",
    ]


def render_framework(case: dict) -> str:
    lines = [
        "# ZEN Lighting Design Training Case Framework",
        "",
        "## Training philosophy",
        "",
        "A Training Case is a bounded design-learning context, not a fixed rig profile and not a global Designer rulebook. It records what a particular resource set makes possible, what was inferred, and which lessons generalize to other shows.",
        "",
        "The pipeline boundary remains:",
        "",
        "`ZEN_SHOW_PROFILE + Training Case knowledge + ZEN_SONG_ANALYSIS → Designer → typed ZEN_SHOW_PLAN → Builder`",
        "",
        "Training Cases never contain MA2 commands. Designer remains command-free; Builder remains the only MA2 command-generation boundary.",
        "",
        "## Global design principles",
        "",
    ]
    for principle in case["design_principles"]:
        lines.extend([f"### {principle['principle']}", "", f"- Why: {principle['why']}", f"- Useful when: {principle['when_useful']}", f"- Not automatically applicable when: {principle['when_not_applicable']}", f"- Scope: `{principle['scope']}`", ""])
    lines.extend(["## Rig Role vocabulary", "", "A Role describes the design job a Fixture can perform in context. `ROLE != FIXTURE TYPE`; one Fixture family may take different roles in another Case.", "", "`" + "`, `".join(case["rig_roles"]) + "`", "", "## Proposed Rig Zone vocabulary", "", "These are design-language candidates only, not verified MA2 geometry: `" + "`, `".join(case["constraints"]["spatial_zones_status"] for _ in [0]) + "`.", "", "Allowed names: `UPSTAGE`, `MIDSTAGE`, `DOWNSTAGE`, `HIGH`, `MID`, `LOW`, `FLOOR`, `CENTER`, `INNER`, `OUTER`, `SIDE`, `EDGE`.", "", "## Visual Layer model", ""])
    for layer in case["visual_layers"]:
        lines.append(f"- **{layer['name']}** — {layer['purpose']}")
    lines.extend(["", "A Cue may use only a subset of layers. Increased energy can come from adding coverage, contrast, movement, focus, geometry, or an impact layer—not just Dimmer.", "", "## Anti-pattern evidence", ""])
    for item in case["anti_patterns"]:
        lines.append(f"- **{item['id']}** — {item['description']} ({item['evidence']}; `{item['scope']}`)")
    lines.extend(["", "## Training Case 001", "", f"- Case: `{case['case_id']}` — {case['case_name']}", f"- Type: `{case['case_type']}`", f"- Resource scale: `{case['resource_scale']}`", f"- Style orientation: `{case['style_orientation']}` (case context only)", f"- Show profile: `{case['show_profile_ref']}`", f"- Confidence: `{case['confidence']}`", "", "### Current resource evidence", "", f"- Groups: {case['verified_resources']['group_count']} with fresh ordered membership", f"- Root Fixtures: {case['verified_resources']['fixture_count']}", f"- Preset references: {case['verified_resources']['preset_count']}", f"- Effects: {case['verified_resources']['effect_count']} inventory entries; line parameters `{case['verified_resources']['effect_parameters']}`", f"- Geometry: `{case['verified_resources']['geometry']}`", f"- Semantic position labels: `{case['verified_resources']['semantic_positions']}`", ""])
    lines.extend(["### Current Group role analysis", ""])
    for group in case["fixture_groups"]:
        lines.extend(_role_block(group))
    lines.extend(["### K-pop-oriented virtual rig architecture", "", "This is a case-specific design study. It is not a global rule such as CHORUS = BEAM + STROBE.", ""])
    for item in case["rig_architecture"]:
        lines.extend([f"#### {item['role']}", "", f"- Purpose: {item['purpose']}", f"- Why this fixture: {item['why_this_fixture']}", f"- Expected looks: {', '.join(item['expected_looks'])}", f"- Scope: `{item['scope']}`", ""])
    lines.extend(["### Case-specific assumptions", ""])
    for item in case["assumptions"]:
        lines.append(f"- {item['text']} (`{item['scope']}`, confidence `{item['confidence']}`)")
    lines.extend(["", "### Generalizable lessons", ""])
    for item in case["designer_lessons"]:
        lines.append(f"- {item['lesson']} (`{item['scope']}`; evidence: {item['evidence']})")
    lines.extend(["", "## Future Case stubs", "", "Only schema examples exist; no additional Cases are implemented.", ""])
    for item in case["future_cases"]:
        lines.append(f"- `{item['case_id']}` — scale `{item['resource_scale']}`, orientation `{item['style_orientation']}`, status `{item['status']}`")
    lines.extend(["", "## Designer integration boundary", "", f"- Input: `{', '.join(case['designer_integration']['input'])}`", f"- Output: `{case['designer_integration']['output']}`", f"- Status: `{case['designer_integration']['status']}`", f"- Boundary: {case['designer_integration']['boundary']}", "", "## User-style separation", "", "No `ZEN_STYLE_PROFILE` was created. General professional design competence stays separate from future user preferences and review feedback.", "", "## Safety", "", "- Read-only/local-only case artifact.", "- No Move3D, Rotate3D, Store, Assign, Clone, Delete, Preset, Effect, Sequence, Cue, or Patch operation.", "- Prior A/B/C Auto Geometry proposals remain proposal-only and were not applied.", ""])
    return "\n".join(lines)


def render_case(case: dict) -> str:
    lines = [f"# {case['case_id']} — Resource-rich K-pop-oriented Training Case", "", f"Case type: `{case['case_type']}`", f"Show profile: `{case['show_profile_ref']}`", "", "This document describes a virtual design study; it is not a physical XYZ layout and contains no MA2 commands.", "", "## Resource snapshot", "", f"Groups: {len(case['fixture_groups'])}; Fixtures: {case['verified_resources']['fixture_count']}; Preset references: {case['verified_resources']['preset_count']}; Effects: {case['verified_resources']['effect_count']}; Geometry: `{case['verified_resources']['geometry']}`", "", "## Role assignments"]
    for group in case["fixture_groups"]:
        lines.extend(_role_block(group))
    lines.extend(["## KPOP_ORIENTED_RIG_ARCHITECTURE_V1", "", "The following is case-specific and intentionally does not become a global Designer rule.", ""])
    for item in case["rig_architecture"]:
        lines.extend([f"### {item['role']}", "", f"Purpose: {item['purpose']}", f"Why: {item['why_this_fixture']}", f"Expected looks: {', '.join(item['expected_looks'])}", ""])
    lines.extend(["## Layer combinations", "", "- Intro/Verse: BASE + selective SUBJECT; reserve headroom.", "- Pre: add COLOR or TEXTURE gradually; protect IMPACT resources.", "- Chorus: open additional coverage and AERIAL/TEXTURE where verified.", "- Final Chorus: combine the broadest available layers with a reserved impact accent.", "- Outro: remove layers deliberately and resolve the look.", "", "## Evidence and limits", ""])
    for item in case["assumptions"]:
        lines.append(f"- {item['text']} — `{item['scope']}` / `{item['confidence']}`")
    lines.extend(["", "## Generalizable lessons extracted", ""])
    for item in case["designer_lessons"]:
        lines.append(f"- {item['lesson']}")
    lines.extend(["", "## Review status", "", "`CASE_SPECIFIC` decisions require user creative review. No geometry write, MA2 Preview write, or Sequence build was performed.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Training Case 001 documentation locally.")
    parser.add_argument("--profile", type=Path, default=ROOT / "data" / "ZEN_CURRENT_SHOW_PROFILE.json")
    parser.add_argument("--json", dest="json_path", type=Path, default=ROOT / "data" / "ZEN_TRAINING_CASE_001.json")
    parser.add_argument("--case-report", type=Path, default=ROOT / "ZEN_TRAINING_CASE_001_RESOURCE_RICH.md")
    parser.add_argument("--framework", type=Path, default=ROOT / "ZEN_LIGHTING_DESIGN_TRAINING_FRAMEWORK.md")
    args = parser.parse_args()
    case = build_training_case_001(_load(args.profile))
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.case_report.write_text(render_case(case), encoding="utf-8")
    args.framework.write_text(render_framework(case), encoding="utf-8")
    print(json.dumps({"case": case["case_id"], "groups": len(case["fixture_groups"]), "framework": str(args.framework), "case_report": str(args.case_report), "ma2_write": "NONE"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
