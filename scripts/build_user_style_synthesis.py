"""Build human-readable user-style evidence and synthesis reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zen_ma2_agent.user_style import compare_with_industry, synthesize_candidates, validate_evidence
from zen_ma2_agent.industry_pack_002 import build_pack_002

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_FILE = ROOT / "tests" / "fixtures" / "user_style_evidence_001.json"
PACK_FILE = ROOT / "tests" / "fixtures" / "industry_reference_pack_002.json"
CANDIDATE_NAMES = [
    "CONTROLLED_HIGH_IMPACT", "CLEAN_VISUAL_HIERARCHY", "PALETTE_COHERENCE", "DOMINANT_THEME_COLOR",
    "MUSIC_STRUCTURE_ALIGNMENT", "RHYTHMIC_ACCENT_SYNC", "DYNAMIC_CONTOUR_TRACKING", "STRONG_TRANSIENT_IMPACT",
    "HIGH_SECTION_DELTA", "CONTROLLED_BUILDUP", "RESTRAINT_BETWEEN_PEAKS", "MULTI_LEVEL_ENERGY_DESIGN",
    "EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK", "PROGRESSIVE_ENERGY_ARC", "NEGATIVE_SPACE_ACCEPTANCE",
    "GEOMETRIC_COMPOSITION", "CONTROLLED_MAXIMALISM", "IMPACT_WHEN_MUSICALLY_JUSTIFIED", "INTENTIONAL_RESTRAINT",
    "HIGH_IMPACT_ALWAYS",
]


def load() -> tuple[list[dict], dict]:
    raw = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
    evidence = [validate_evidence(item) for item in raw["evidence"]]
    pack = build_pack_002(json.loads(PACK_FILE.read_text(encoding="utf-8")))
    return evidence, pack


def write_reports() -> None:
    evidence, pack = load()
    candidates = synthesize_candidates(evidence, CANDIDATE_NAMES)
    alignment = compare_with_industry(candidates, pack)
    positives = [e for e in evidence if e["strength"] in {"STRONG_POSITIVE", "POSITIVE"}]
    mixed = [e for e in evidence if e["strength"] == "NEUTRAL"]
    negatives = [e for e in evidence if e["strength"] == "STRONG_NEGATIVE"]
    report = ["# ZEN User Style Evidence 001", "", "Human-reviewed visual preference evidence. This is reversible candidate evidence, not a permanent style profile and not Designer runtime input.", "", "## Primary positive references", "", "- **BABYMONSTER contemporary / HELLO MONSTERS-type stage language** — all reviewed states liked; strongest direction for personal design.", "", "## Strong positive cross-domain reference", "", "- **Subtronics — TESSERACT Tour 2024** — controlled density, geometric framework, negative space and single-theme color were liked at the same tier as the primary reference.", "", "## Positive second-tier references", "", "- **Drake** — intentional minimalist arena composition was liked and did not feel empty.", "- **Billie Eilish** — palette and visual rest were liked, with lower overall preference.", "", "## Mixed and negative references", "", "- **Karol G — Mañana Será Bonito** — mixed visual elements reduced perceived hierarchy/cleanliness; maximalism itself was not rejected.", "- **Billy Strings examples** — case-local negative evidence for messy hierarchy and busy/mixed palette; this is not a dislike of band lighting as a category.", "", "## Evidence records", ""]
    for item in evidence:
        report.append(f"- `{item['evidence_id']}` `{item['strength']}` `{item['reference_type']}` — {item['raw_user_reaction']} Traits: {', '.join(item['normalized_traits'])}. Provenance: `{item['provenance']}`.")
    report += ["", "## Interpretation boundary", "", "The raw reaction is human evidence. Normalized traits are reversible interpretation. Industry professional validity and user preference are separate dimensions; a professionally valid design may still be disliked.", "", "## Explicitly not supported", "", "- HIGH_IMPACT_ALWAYS", "- MAXIMALISM_ALWAYS_BETTER", "- K-POP_ONLY", "- YG brand identity as a rule", "- MULTICOLOR_BAD", "- MINIMALISM_DISLIKED", "- Every chorus must use Beam/Strobe", ""]
    (ROOT / "ZEN_USER_STYLE_EVIDENCE_001.md").write_text("\n".join(report), encoding="utf-8")

    synthesis = ["# ZEN Style Synthesis 001", "", "Status: `STYLE_CANDIDATE / HUMAN_REVIEWED_EVIDENCE`. No `ZEN_STYLE_PROFILE` is created or promoted.", "", "## Current working style description", "", "Zen currently prefers highly controlled contemporary stage design: clear visual hierarchy, coherent dominant palette, strong musical alignment, complete low/medium/high energy states, intentional restraint between peaks, and powerful transient impact when musically justified. High-density looks are welcome when geometry, color, timing and focus remain organized.", "", "## Strong candidates", "", "| Candidate | Status | Evidence | Contradictions | Promotion |", "|---|---|---:|---|---|"]
    for item in candidates:
        if item["status"] in {"SUPPORTED", "PARTIAL"} and item["confidence"] in {"HIGH", "MEDIUM"}:
            synthesis.append(f"| `{item['name']}` | **{item['status']}** | {len(item['supporting_references'])} | {', '.join(item['contradicting_references']) or 'none'} | HUMAN_REVIEWED_CANDIDATE |")
    moderate = "".join(f"- `{item['name']}` — {item['status']} / confidence {item['confidence']}.\n" for item in candidates if item["status"] not in {"SUPPORTED"} or item["confidence"] == "LOW")
    synthesis += ["", "## Candidate correction", "", "`IMPACT_WHEN_MUSICALLY_JUSTIFIED` replaces any simplistic HIGH_IMPACT_ALWAYS rule. A/B/C review supports multi-level energy design: each state is complete, and A → B → C is preferred over constant C.", "", "## Moderate / uncertain candidates", "", moderate, "", "## Industry alignment (bounded Pack 002 window 2022–2025)", "", *[f"- `{item['candidate']}` — **{item['status']}**; no automatic promotion." for item in alignment], "", "## Contradictions preserved", "", "- High impact is valued in high-energy, musically justified contexts, but Drake/Billie show that intentional restraint and negative space can also be strongly positive.", "- Maximalism is acceptable when organized; Karol G/Billy Strings feedback identifies clutter and busy palette as the disliked boundary.", "- KPOP_YG_LEANING remains a direction label only; Subtronics and Drake demonstrate cross-domain preference.", "", "## Future Designer boundary", "", "GENERAL_DESIGN_KNOWLEDGE + CONTEMPORARY_MAINSTREAM_PRIOR + CURRENT_CASE_CONTEXT + USER_STYLE_EVIDENCE → Designer. User style may influence variant ranking, but never overrides safety, resource reality, professional validity or song context.", "", "## Promotion gate", "", "Permanent promotion requires repeated evidence across multiple artists, musical styles and rig scales, no major contradictory feedback, and explicit human confirmation. Until then: `ZEN_STYLE_PROFILE = DEFERRED`."]
    (ROOT / "ZEN_STYLE_SYNTHESIS_001.md").write_text("\n".join(synthesis), encoding="utf-8")


if __name__ == "__main__":
    write_reports()
    print("User style synthesis reports written.")
