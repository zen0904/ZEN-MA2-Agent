"""Build human-readable user-style evidence and synthesis reports."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zen_ma2_agent.user_style import build_review_records, compare_with_industry, synthesize_candidates, validate_evidence
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

    synthesis = ["# ZEN Style Synthesis 001", "", "Status: `STYLE_CANDIDATE / HUMAN_REVIEWED_EVIDENCE`. No `ZEN_STYLE_PROFILE` is created or promoted.", "", "## Current working style description", "", "Zen currently prefers highly controlled contemporary stage design with clear visual hierarchy, coherent palette structure, strong musical alignment, meaningful low/medium/high energy progression, and intentional restraint. High-density looks are welcome when geometry, color, timing, and focus remain organized. Controlled high-impact and dominant-theme color are strong but not yet universal preference candidates.", "", "## Strong candidates", "", "| Candidate | Status | Evidence | Contradictions | Promotion |", "|---|---|---:|---|---|"]
    for item in candidates:
        if item["status"] in {"SUPPORTED", "PARTIAL"} and item["confidence"] in {"HIGH", "MEDIUM"}:
            synthesis.append(f"| `{item['name']}` | **{item['status']}** | {len(item['supporting_references'])} | {', '.join(item['contradicting_references']) or 'none'} | HUMAN_REVIEWED_CANDIDATE |")
    moderate = "".join(f"- `{item['name']}` — {item['status']} / confidence {item['confidence']}.\n" for item in candidates if item["status"] not in {"SUPPORTED"} or item["confidence"] == "LOW")
    synthesis += ["", "## Candidate correction", "", "`IMPACT_WHEN_MUSICALLY_JUSTIFIED` replaces any simplistic HIGH_IMPACT_ALWAYS rule. A/B/C review supports multi-level energy design: each state is complete, and A → B → C is preferred over constant C.", "", "## Moderate / uncertain candidates", "", moderate, "", "## Industry alignment (bounded Pack 002 window 2022–2025)", "", *[f"- `{item['candidate']}` — **{item['status']}**; no automatic promotion." for item in alignment], "", "## Contradictions preserved", "", "- High impact is valued in high-energy, musically justified contexts, but Drake/Billie show that intentional restraint and negative space can also be strongly positive.", "- Maximalism is acceptable when organized; Karol G/Billy Strings feedback identifies clutter and busy palette as the disliked boundary.", "- KPOP_YG_LEANING remains a direction label only; Subtronics and Drake demonstrate cross-domain preference.", "", "## Future Designer boundary", "", "GENERAL_DESIGN_KNOWLEDGE + CONTEMPORARY_MAINSTREAM_PRIOR + CURRENT_CASE_CONTEXT + USER_STYLE_EVIDENCE → Designer. User style may influence variant ranking, but never overrides safety, resource reality, professional validity or song context.", "", "## Promotion gate", "", "Permanent promotion requires repeated evidence across multiple artists, musical styles and rig scales, no major contradictory feedback, and explicit human confirmation. Until then: `ZEN_STYLE_PROFILE = DEFERRED`."]
    (ROOT / "ZEN_STYLE_SYNTHESIS_001.md").write_text("\n".join(synthesis), encoding="utf-8")

    reviews = build_review_records(candidates)
    groups = {
        "A. Strong candidate preferences": [c for c in candidates if c["status"] == "SUPPORTED" and c["name"] != "HIGH_IMPACT_ALWAYS"],
        "B. Moderate / bounded candidates": [c for c in candidates if c["status"] == "PARTIAL"],
        "C. Weak / uncertain candidates": [c for c in candidates if c["status"] == "UNKNOWN"],
        "D. Explicitly rejected interpretations": [c for c in candidates if c["status"] == "REJECTED_BY_EVIDENCE"],
    }
    review_lines = ["# ZEN User Style Review 001", "", "Review-ready human decisions for User Style Evidence and Style Candidates.", "", "Human decisions are intentionally `UNSET`. AI recommendations are separate seed suggestions and do not accept, reject or promote anything.", "", "## Decision vocabulary", "", "`ACCEPT`, `ACCEPT_WITH_LIMITATION`, `NEEDS_MORE_EVIDENCE`, `REJECT`, `UNSURE`; every record also supports `UNSET` until a reviewer acts.", ""]
    review_map = {item["candidate_id"]: item for item in reviews}
    for title, items in groups.items():
        review_lines += [f"## {title}", ""]
        for candidate in items:
            review = review_map[candidate["candidate_id"]]
            review_lines += [f"### `{candidate['name']}`", "", f"- Current evidence status: **{candidate['status']}**", f"- Strongest supporting references: {', '.join(candidate['supporting_references']) or 'none'}", f"- Contradicting evidence: {', '.join(candidate['contradicting_references']) or 'none'}", f"- Current scope: USER_STYLE_CANDIDATE", f"- AI recommendation: `{review['ai_recommendation']}` (not a decision)", "- Human decision: **UNSET**", f"- Meaning: {candidate['meaning']}", ""]
    review_lines += ["## Explicitly rejected interpretations", "", "- `HIGH_IMPACT_ALWAYS`", "- `MAXIMALISM_EQUALS_CLUTTER`", "- `MULTICOLOR_EQUALS_BAD`", "- `MINIMALISM_EQUALS_LOW_PREFERENCE`", "- `KPOP_YG_EQUALS_GLOBAL_STYLE_RULE`", "", "## Reversibility", "", "A human ACCEPT only makes a candidate eligible for future knowledge/style consideration. It does not create a global Designer rule, hard constraint or permanent `ZEN_STYLE_PROFILE` trait.", "", "## Runtime boundary", "", "Designer runtime wiring: `NOT_RUN`; MA2 writes: `ZERO`; Industry Pack 001/002: unchanged and independent."]
    (ROOT / "ZEN_USER_STYLE_REVIEW_001.md").write_text("\n".join(review_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_reports()
    print("User style synthesis reports written.")
