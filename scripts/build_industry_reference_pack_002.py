"""Build Pack 002 and its human-review reports from traceable sources."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zen_ma2_agent.industry_pack_002 import build_pack_002, compare_packs, style_alignment
from zen_ma2_agent.industry_references import build_pack

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "industry_reference_pack_002.json"
PACK001 = ROOT / "tests" / "fixtures" / "industry_reference_pack_001.json"


def load_pack() -> dict:
    return build_pack_002(json.loads(FIXTURE.read_text(encoding="utf-8")))


def write_reports() -> None:
    pack = load_pack()
    sources = {s["source_id"]: s for s in pack["sources"]}
    categories = Counter(o["category"] for o in pack["observations"])
    reliability = Counter(s["reliability"] for s in pack["sources"])
    windows = sorted({s["time_window"] for s in pack["sources"]})

    source_lines = [f"- **{s['source_id']}** — [{s['title']}]({s['url']}) — {s['publisher']}; {s['designer']}; {s['production']}; {s['time_window']}; reliability **{s['reliability']}**; visual language: {', '.join(s['visual_language'])}. Visual reference: {s['visual_reference']}. Bias: {s['selection_bias']}." for s in pack["sources"]]
    obs_lines = [f"- `{o['observation_id']}` **{o['category']}** — {o['observation']} ([source]({sources[o['source_id']]['url']})); evidence `{o['evidence_type']}`, confidence `{o['confidence']}`, scope `{o['scope']}`. Limitation: {o['limitations']}" for o in pack["observations"]]
    main = ["# ZEN Industry Reference Pack 002", "", "Contemporary Mainstream Pop / K-pop reference pack. Local, read-only, derived observations for human visual review; it is not Designer training or a ZEN style profile.", "", "## Pack metadata", "", f"- Schema: `{pack['schema']}`", f"- Sources: **{len(pack['sources'])}**", f"- Observations: **{len(pack['observations'])}**", f"- Reliability: `{dict(reliability)}`", f"- Time windows: `{', '.join(windows)}`", "- Runtime wiring: **NOT_RUN**", "- MA2 writes: **ZERO**", "- Global promotions: **NONE**", "", "## Contemporary Mainstream Prior", "", "The prior is a bounded, reviewable model of contemporary large-stage evidence, not a global rule. It is limited to the source window and source mix below.", "", f"- Domain: `{pack['contemporary_prior']['domain']}`", f"- Time window: `{pack['contemporary_prior']['time_window']}`", f"- Evidence count: `{pack['contemporary_prior']['evidence_count']}`", f"- Visual language: `{', '.join(pack['contemporary_prior']['visual_language'])}`", f"- Confidence: `{pack['contemporary_prior']['confidence']}`", f"- Source diversity: `{pack['contemporary_prior']['source_diversity']}`", "", "## Sources", "", *source_lines, "", "## Derived observations", "", *obs_lines, "", "## Evidence discipline", "", "`DIRECT_SOURCE_STATEMENT` records bounded source statements. `VISUAL_INFERENCE` records a limited reading of published imagery. `MODEL_INTERPRETATION` is explicitly hypothetical. No exact cue timing, DMX value, or universal K-pop rule is inferred."]
    (ROOT / "ZEN_INDUSTRY_REFERENCE_PACK_002.md").write_text("\n".join(main) + "\n", encoding="utf-8")

    cards = ["# Industry Reference Pack 002 — Visual-First Human Review", "", "Review the visual evidence before accepting a lesson. These cards are prompts, not automated training labels. Source records and observations remain immutable.", "", "## How to review", "", "For each card, inspect the linked production/source page and record whether the observation is visible, what remains uncertain, and whether it is useful only in this production context.", ""]
    for i, o in enumerate(pack["observations"], 1):
        s = sources[o["source_id"]]
        cards += [f"## CARD {i:02d} — {o['category']}", "", f"**SOURCE / PRODUCTION:** [{s['title']} — {s['production']}]({s['url']})", f"**WHAT TO LOOK AT:** Visual language `{', '.join(o['visual_language'])}`; reference `{s['visual_reference']}`.", f"**ACTUAL VISUAL PHENOMENON:** {o['observation']}", f"**POSSIBLE DESIGN LESSON:** {o['teaching_note']}", f"**EVIDENCE:** `{o['evidence_type']}` / confidence `{o['confidence']}` / source window `{s['time_window']}`", f"**LIMITATION:** {o['limitations']}", "", "Human review: [ ] ACCEPT  [ ] ACCEPT WITH LIMITATION  [ ] NEEDS CONTEXT  [ ] REJECT  [ ] UNSURE", "", "---", ""]
    (ROOT / "ZEN_INDUSTRY_REFERENCE_PACK_002_VISUAL_REVIEW.md").write_text("\n".join(cards), encoding="utf-8")

    prior = pack["contemporary_prior"]
    analysis = ["# Contemporary Mainstream Analysis 001", "", "This is a bounded prior from Pack 002, not a global design rule.", "", "## Evidence summary", "", f"- Domain: {prior['domain']}", f"- Window: {prior['time_window']}", f"- Sources: {len(pack['sources'])} across {prior['source_diversity']} publishers", f"- Visual languages: {', '.join(prior['visual_language'])}", f"- Observation categories: {dict(categories)}", "", "## Cautious synthesis", "", "Across the selected cases, contemporary large-stage work repeatedly treats hierarchy, camera readability, purposeful impact and section contrast as design problems. The set also contains both controlled maximal and clean minimal approaches; fixture density alone is not the lesson.", "", "## Boundaries", "", "The source set is not a random sample, is weighted toward large productions, and mixes vendor/portfolio and trade reporting. It cannot establish a universal K-pop grammar or replace a human visual review."]
    (ROOT / "ZEN_CONTEMPORARY_MAINSTREAM_ANALYSIS_001.md").write_text("\n".join(analysis) + "\n", encoding="utf-8")

    yg = ["# YG Style Hypothesis Review 001", "", "The sources include two BLACKPINK/YG-adjacent cases, but they do not prove a proprietary YG visual rule. This document keeps hypotheses separate from evidence.", "", "| Hypothesis | Status | Evidence | Limitation |", "|---|---|---|---|", "| Coordinated high-impact pop spectacle can be effective | PARTIAL | IR201, IR202 | Not unique to YG; source selection is narrow. |", "| Camera readability and choreography matter in pop concert design | PARTIAL | IR201, IR202, IR203, IR205 | Evidence describes selected productions, not all YG work. |", "| A fixed YG palette or cue grammar can be inferred | NO_EVIDENCE | none | No source supplies a proprietary rule or complete cue data. |", "| Controlled maximalism is always preferable | MIXED | IR201, IR204, IR209 | Drake and Subtronics provide contrasting context. |", "", "Status is review-only. No YG rule is promoted and no ZEN_STYLE_PROFILE is created."]
    (ROOT / "ZEN_YG_STYLE_HYPOTHESIS_REVIEW_001.md").write_text("\n".join(yg) + "\n", encoding="utf-8")

    p1raw = json.loads(PACK001.read_text(encoding="utf-8"))
    p1 = build_pack(p1raw["sources"], p1raw["observations"])
    diff = compare_packs(p1, pack)
    comparison = ["# Industry Pack 001 vs 002", "", "Both packs coexist. Pack 001 remains the earlier cross-domain evidence set; Pack 002 is a contemporary mainstream large-stage subset.", "", "| Dimension | Pack 001 | Pack 002 |", "|---|---:|---:|", f"| Sources | {diff['pack001_sources']} | {diff['pack002_sources']} |", f"| Observations | {len(p1['observations'])} | {len(pack['observations'])} |", f"| New visual categories | — | {', '.join(diff['new_categories'])} |", "", "## Difference", "", "Pack 002 has a tighter 2022–2025 time window, more camera/broadcast and contemporary arena evidence, and explicit visual-language tags. Pack 001 has broader theatre and band/live comparison. Neither is automatically more authoritative.", "", "## Style candidate", "", f"`{style_alignment(pack, pack['style_candidate'])}`", "", "No style profile or runtime promotion occurs."]
    (ROOT / "ZEN_INDUSTRY_PACK_001_VS_002.md").write_text("\n".join(comparison) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_reports()
    print("Industry Reference Pack 002 reports written.")
