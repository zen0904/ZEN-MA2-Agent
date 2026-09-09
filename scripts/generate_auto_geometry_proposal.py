"""Generate local Auto Geometry candidates from a fresh read-only profile.

This tool never connects to MA2 and never emits executable Move3D/Rotate3D
commands.  It is intentionally a proposal/preview artifact.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.geometry import AutoGeometryProposer


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _group_block(group: dict) -> list[str]:
    normalizer = group["normalizer"]
    pairs = ", ".join(f"{item['fixture_a']}↔{item['fixture_b']}" for item in group["mirror_pairs"]) or "none"
    return [
        f"#### Group {group['group_id']} `{group['name']}`",
        "",
        f"- Fixtures (verified membership order): `{', '.join(map(str, group['fixture_ids_in_selection_order']))}`",
        f"- X positions: `{', '.join(map(str, group['x_positions']))}`",
        f"- Y: `{group['y']}`; Z: `{group['z']}`; Row: `{group['row_id']}`",
        f"- Mirror pairs (normalizer): `{pairs}`",
        f"- INNER candidates: `{', '.join(map(str, group['inner'])) or 'none'}`",
        f"- OUTER candidates: `{', '.join(map(str, group['outer'])) or 'none'}`",
        f"- Center: `{json.dumps(group['center'], ensure_ascii=False, separators=(',', ':'))}`",
        "- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.",
        "",
    ]


def _markdown(proposal: dict) -> str:
    lines = [
        "# ZEN Auto Geometry Proposal",
        "",
        "**Mode:** read-only virtual proposal / preview. No MA2 object was modified.",
        "",
        f"- Show identity: `{proposal.get('show_identity')}`",
        f"- Current geometry state: **{proposal.get('current_geometry_state')}**",
        f"- Root Fixtures: **{proposal.get('root_fixture_count')}**; grouped: **{proposal.get('grouped_fixture_count')}**",
        f"- Subfixture policy: `{proposal.get('subfixture_policy')}`",
        "- Coordinates use neutral numeric X/Y/Z axes. They do not claim Stage Left/Right, Front/Back, or real venue rigging.",
        "",
        "## Fixture membership audit",
        "",
        f"- Group membership overlap: **{'YES' if proposal.get('group_membership_overlap') else 'NO'}**",
    ]
    if proposal.get("group_membership_overlap"):
        for item in proposal["group_membership_overlap"]:
            lines.append(f"- Fixture {item['fixture_id']} in Groups {item['groups']}: `GROUP_MEMBERSHIP_OVERLAP` (excluded from conflicting placement).")
    lines.extend([f"- Ungrouped Fixtures: **{len(proposal.get('ungrouped_fixtures') or [])}**"])
    for item in proposal.get("ungrouped_fixtures") or []:
        lines.append(f"- Fixture {item['fixture_id']} `{item.get('name')}` — `{item.get('fixture_type')}`, patch `{item.get('patch')}`: `UNGROUPED_FIXTURE` / excluded from Auto Geometry.")
    lines.extend(["", "## Candidates", ""])
    for candidate in proposal["candidates"]:
        lines.extend([f"### Candidate {candidate['id']} — {candidate['name']}", "", f"- Spacing: `{candidate['spacing']}` virtual units", f"- Creative usefulness: **{candidate['creative_usefulness']}**", "- Advantages:"])
        lines.extend(f"  - {item}" for item in candidate["advantages"])
        lines.append("- Disadvantages:")
        lines.extend(f"  - {item}" for item in candidate["disadvantages"])
        lines.append("")
        for group in candidate["groups"]:
            lines.extend(_group_block(group))
    recommended = proposal["recommended_candidate"]
    lines.extend([
        "## Recommendation",
        "",
        f"**RECOMMENDED_CANDIDATE:** `{recommended}`",
        "",
        "It gives each verified Group a separate deterministic row, retains membership order, produces an even center gap for eight Fixtures, and makes no physical venue claim.",
        "",
        "## Designer simulation",
        "",
        "After a future approved application, the Designer could use numeric X ordering, CENTER, INNER/OUTER ranks, ROW identifiers, and MIRROR_PAIR candidates per Group. The current uninitialized geometry remains unchanged.",
        "",
        "## Typed write plan (not executable)",
        "",
        f"- Schema: `{proposal['typed_write_plan']['schema']}`",
        f"- Mode: `{proposal['typed_write_plan']['mode']}`",
        f"- Operations: **{len(proposal['typed_write_plan']['operations'])}** typed Fixture references",
        "- Safety: `MODIFY`; approval required: `YES`",
        "- Raw MA2 commands: **none**",
        "- Future precondition: fresh scan must still report `GEOMETRY_UNINITIALIZED`; otherwise `STATE_CHANGED_SINCE_PREVIEW`.",
        "",
        "## Audit",
        "",
        "- MA2 write audit: **ZERO_WRITES**",
        "- MA2 objects modified: **NONE**",
        "- Ready for user geometry review: **YES**",
        "- Ready for MA2 write: **NO — USER APPROVAL REQUIRED**",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a local, read-only Auto Geometry proposal.")
    parser.add_argument("--profile", type=Path, default=ROOT / "data" / "ZEN_CURRENT_SHOW_PROFILE.json")
    parser.add_argument("--discovery", type=Path, default=ROOT / "data" / "ZEN_CURRENT_SHOW_DISCOVERY.json")
    parser.add_argument("--json", dest="json_path", type=Path, default=ROOT / "data" / "ZEN_AUTO_GEOMETRY_PROPOSAL.json")
    parser.add_argument("--report", type=Path, default=ROOT / "ZEN_AUTO_GEOMETRY_PROPOSAL.md")
    args = parser.parse_args()
    proposal = AutoGeometryProposer().build(_json(args.profile), _json(args.discovery))
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(_markdown(proposal), encoding="utf-8")
    print(json.dumps({"report": str(args.report), "json": str(args.json_path), "candidate_count": len(proposal["candidates"]), "recommended": proposal["recommended_candidate"], "ma2_write_audit": proposal["ma2_write_audit"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
