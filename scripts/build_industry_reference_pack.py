"""Build the copyright-safe Industry Reference Pack 001 reports locally."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from zen_ma2_agent.industry_references import build_pack, cross_analyze
from zen_ma2_agent.industry_review import ai_recommendation, antipattern_review_matrix, observation_priority_summary, principle_review_matrix, review_priority


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "industry_reference_pack_001.json"


def _load() -> dict:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return build_pack(raw["sources"], raw["observations"])


def _principles() -> list[str]:
    return [
        "RESERVE_HEADROOM", "SECTION_CONTRAST", "REPEATED_SECTION_DEVELOPMENT",
        "EFFECT_FATIGUE_AVOIDANCE", "LAYER_ESCALATION", "FOCUS_HIERARCHY",
        "RESOURCE_AWARENESS", "ASYMMETRY_TOLERANCE",
    ]


def _anti_patterns() -> list[str]:
    return [
        "INTENSITY_ONLY_PROGRESSION", "SAME_GROUP_EVERY_CUE", "SAME_PRESET_EVERY_CUE",
        "EFFECT_FATIGUE", "EFFECT_TOO_EARLY", "FINAL_EQUALS_ONE_HUNDRED", "GEOMETRY_IGNORED",
    ]


def _source_lines(pack: dict) -> list[str]:
    lines = []
    for source in pack["sources"]:
        date = source["publication_date"] or "date not stated"
        lines.append(f"- **{source['source_id']}** — [{source['title']}]({source['url']}) — {source['publisher']}; {source['designer'] or 'designer not named'}; {source['production']}; {source['domain']}; {date}; reliability **{source['reliability']}**.")
    return lines


def _obs_lines(pack: dict) -> list[str]:
    source_map = {s["source_id"]: s for s in pack["sources"]}
    lines = []
    for obs in pack["observations"]:
        source = source_map[obs["source_id"]]
        refs = ", ".join(obs.get("principle_refs", [])) or "none"
        lines.append(f"- `{obs['observation_id']}` **{obs['category']}** ({obs['domain']}, {obs['evidence_type']}, confidence {obs['confidence']}, review {obs['review_status']}) — {obs['observation']} ([source]({source['url']})). Teaching note: {obs['teaching_note'] or 'none'}. Principle refs: {refs}.")
    return lines


def write_reports() -> None:
    pack = _load()
    analysis = cross_analyze(pack, _principles(), _anti_patterns())
    source_counts = {}
    for source in pack["sources"]:
        source_counts[source["reliability"]] = source_counts.get(source["reliability"], 0) + 1
    domain_counts = {}
    for source in pack["sources"]:
        domain_counts[source["domain"]] = domain_counts.get(source["domain"], 0) + 1

    main = [
        "# ZEN Industry Reference Pack 001", "", "Local, read-only, copyright-safe derived observations for human review.", "",
        "## Scope and guardrails", "", "This pack stores short paraphrased observations, not scripts, cue sheets, plots, transcripts, or command strings. Every observation retains a source URL, domain, context, evidence type, confidence, limitations and review status. All records default to `HUMAN_REVIEW_REQUIRED`; nothing is promoted into Designer runtime in this round.", "",
        "## Pack metadata", "", f"- Schema: `{pack['schema']}`", f"- Sources: **{len(pack['sources'])}**", f"- Observations: **{len(pack['observations'])}**", f"- Reliability: {source_counts}", f"- Domains: {domain_counts}", "- Runtime wiring: **NOT_RUN**", "- MA2 writes: **ZERO**", "- Zen style training: **NOT_RUN**", "",
        "## Sources", "", *_source_lines(pack), "",
        "## Derived observations", "", *_obs_lines(pack), "",
        "## Evidence discipline", "", "`DIRECT_SOURCE_STATEMENT` records paraphrase what a named designer or source explicitly reports. `VISUAL_INFERENCE` records a bounded interpretation of documented imagery or arrangement. `MODEL_INTERPRETATION` is a testable hypothesis and never a fact. Contradictions and context limits are retained in the cross-analysis report.",
    ]
    (ROOT / "ZEN_INDUSTRY_REFERENCE_PACK_001.md").write_text("\n".join(main) + "\n", encoding="utf-8")

    cross = [
        "# Industry Reference Pack 001 — Cross Analysis", "", "## Repeated across domains", "",
        *([f"- `{item['category']}` — {item['observation_count']} observations across {', '.join(item['domains'])} ({item['source_count']} sources)." for item in analysis["repeated_cross_domain"]] or ["- None yet; no category meets the two-domain threshold."]),
        "", "## Domain-specific evidence", "", *([f"- `{item['category']}` — currently limited to {', '.join(item['domains'])}; do not globalize." for item in analysis["domain_specific"]] or ["- None."]),
        "", "## Conflicts and context dependence", "", *([f"- `{item['category']}` retains stances: {', '.join(item['stances'])} (sources: {', '.join(item['source_ids'])})." for item in analysis["conflicts"]] or ["- No explicit contradiction record; context-dependent observations remain marked in the source data."]),
        "", "## Interpretation policy", "", "Repeated observations are candidates for review, not automatic global rules. A repeated category may still have different applicability or evidence types. No global promotion occurred in this pack.",
    ]
    (ROOT / "ZEN_INDUSTRY_REFERENCE_PACK_001_CROSS_ANALYSIS.md").write_text("\n".join(cross) + "\n", encoding="utf-8")

    principles = ["# Internal Principle External Validation 001", "", "External validation is evidence-led and does not rewrite internal principles.", "", "| Principle | Status | Evidence sources/domains |", "|---|---|---|"]
    for item in analysis["principles"]:
        evidence = f"{', '.join(item['source_ids']) or 'none'} / {', '.join(item['domains']) or 'none'}"
        principles.append(f"| `{item['name']}` | **{item['status']}** | {evidence} |")
    principles += ["", "Statuses are deterministic: cross-domain repeated support is `EXTERNALLY_SUPPORTED`; single-domain support is `PARTIALLY_SUPPORTED`; support plus contradiction is `MIXED`; no linked evidence is `NO_EVIDENCE_YET`. This round makes no global promotions.", ""]
    (ROOT / "ZEN_INTERNAL_PRINCIPLE_EXTERNAL_VALIDATION_001.md").write_text("\n".join(principles), encoding="utf-8")

    anti = ["# Training Case 001 — Industry Review", "", "`TRAINING_CASE_001_RESOURCE_RICH_KPOP_ORIENTED` remains unchanged. This review compares its lessons with external evidence; it does not alter the Case or Designer runtime.", "", "## Convergent lessons", "", "- Preserve headroom and section contrast; evidence appears in large concert, band/live and theatre contexts.", "- Use focus and spatial layers deliberately; a large rig and a compact theatre both solve readability with selective layers.", "- Resource awareness is contextual: consistency can be a strength in one tour, while reusable environments provide variation in another.", "", "## Case-specific or not yet validated", "", "- The Case's exact seven-group role assignment and K-pop-oriented staging remain `CASE_SPECIFIC`.", "- No external source validates the Case's exact effect IDs, MA2 groups, or geometry layout.", "- Effect fatigue and early-effect cautions are useful review prompts, but one source documents an intentional early signature effect; keep `CONTEXT_DEPENDENT`.", "", "## Anti-pattern review", "", "| Anti-pattern | Status |", "|---|---|"]
    for item in analysis["anti_patterns"]:
        anti.append(f"| `{item['name']}` | **{item['status']}** |")
    anti += ["", "All external extractions require human review before teaching use. No Zen style profile is created."]
    (ROOT / "ZEN_TRAINING_CASE_001_INDUSTRY_REVIEW.md").write_text("\n".join(anti) + "\n", encoding="utf-8")

    _write_review_reports(pack)


def _write_review_reports(pack: dict) -> None:
    source_map = {item["source_id"]: item for item in pack["sources"]}
    priority = observation_priority_summary(pack["observations"])
    cards = ["# Industry Reference Pack 001 — Human Review", "", "This is a human-readable review packet. It contains no parser contract and no checkbox automation. Each card is a short derived observation; the original source and observation records remain immutable.", "", "## Review guidance", "", "- ACCEPT confirms source interpretation and documented scope; it does not create a global design truth.", "- ACCEPT WITH LIMITATION records a valid observation with an explicit boundary.", "- NEEDS CONTEXT, REJECT and UNSURE keep the observation out of active knowledge candidates.", "- AI recommendations, where shown, are separate suggestions and never human decisions.", ""]
    for index, obs in enumerate(pack["observations"], start=1):
        source = source_map[obs["source_id"]]
        recommendation = ai_recommendation(obs)
        cards.extend([
            f"## OBSERVATION {index:02d}", "", f"**Source:** [{source['production']} — {source['title']}]({source['url']})", f"**Domain:** {obs['domain']}", f"**Evidence type:** {obs['evidence_type']}", f"**Observed:** {obs['observation']}", f"**Why this may matter:** {obs['teaching_note'] or 'Review whether this changes how a designer allocates attention, contrast or resources.'}", f"**Possible lesson:** {obs['teaching_note'] or 'None recorded.'}", f"**Current confidence:** {obs['confidence']}", f"**Possible scope:** DOMAIN / GENERAL_CANDIDATE / UNKNOWN", f"**Review priority:** {review_priority(obs)}", f"**AI review recommendation (not a human decision):** {recommendation['recommended_decision']} — {recommendation['recommended_reason']}", "", "**Review:**", "[ ] ACCEPT  [ ] ACCEPT WITH LIMITATION  [ ] NEEDS CONTEXT  [ ] REJECT  [ ] UNSURE", "", f"**Limitations:** {obs['limitations']}", "", "---", ""])
    (ROOT / "ZEN_INDUSTRY_REFERENCE_PACK_001_HUMAN_REVIEW.md").write_text("\n".join(cards), encoding="utf-8")

    principles = ["RESERVE_HEADROOM", "SECTION_CONTRAST", "REPEATED_SECTION_DEVELOPMENT", "EFFECT_FATIGUE_AVOIDANCE", "LAYER_ESCALATION", "FOCUS_HIERARCHY", "RESOURCE_AWARENESS", "ASYMMETRY_TOLERANCE"]
    matrix = ["# Industry Principle Review Matrix 001", "", "No principle status is changed by this packet. Human decisions are separate records and remain empty until a reviewer submits them.", "", "| Principle | Supporting observations | Conflicting / context observations | Human accepted | Needs context | Rejected | Current status |", "|---|---|---|---|---|---|---|"]
    for item in principle_review_matrix(pack, principles):
        matrix.append(f"| `{item['name']}` | {', '.join(item['supporting_observations']) or 'none'} | {', '.join(item['conflicting_observations']) or 'none'} | none | none | none | **{item['current_status']}** |")
    matrix.append("\nHuman ACCEPT confirms interpretation and scope only; cross-source and cross-domain promotion remains a separate policy.")
    (ROOT / "ZEN_INDUSTRY_PRINCIPLE_REVIEW_MATRIX_001.md").write_text("\n".join(matrix), encoding="utf-8")

    anti_names = ["INTENSITY_ONLY_PROGRESSION", "SAME_GROUP_EVERY_CUE", "SAME_PRESET_EVERY_CUE", "EFFECT_FATIGUE", "EFFECT_TOO_EARLY", "FINAL_EQUALS_ONE_HUNDRED", "GEOMETRY_IGNORED"]
    anti = ["# Industry Anti-pattern Review Matrix 001", "", "External anti-pattern support is pending human review. Training Case evidence is not silently converted into external truth.", "", "| Anti-pattern | Supporting observations | Conflicting / context observations | Human accepted | Needs context | Rejected | Current status |", "|---|---|---|---|---|---|---|"]
    for item in antipattern_review_matrix(pack, anti_names):
        anti.append(f"| `{item['name']}` | {', '.join(item['supporting_observations']) or 'none'} | {', '.join(item['conflicting_observations']) or 'none'} | none | none | none | **{item['current_status']}** |")
    anti.append("\nNo anti-pattern is marked externally accepted in this round.")
    (ROOT / "ZEN_INDUSTRY_ANTIPATTERN_REVIEW_MATRIX_001.md").write_text("\n".join(anti), encoding="utf-8")

    workflow = ["# ZEN Human Review Workflow", "", "## Lifecycle", "", "`IndustryReferenceSource` → `DerivedObservation` → `HumanReviewRecord`", "", "Sources and observations are immutable. A review is a separate record with `zen.industry_evidence_review.v0.1`, reviewer type, decision, confidence, reason, scope confirmation, notes and timestamp.", "", "## Decisions", "", "- `ACCEPT`: interpretation and documented scope are accurate; not a global rule.", "- `ACCEPT_WITH_LIMITATION`: accepted only with recorded boundary.", "- `NEEDS_CONTEXT`: retain, but do not activate.", "- `REJECT`: interpretation is not reliable enough; retain for audit, do not activate.", "- `DUPLICATE`: retain the source record, exclude duplicate candidate.", "- `UNSURE`: defer without forcing a decision.", "", "## Eligibility", "", "Only `ACCEPT` and `ACCEPT_WITH_LIMITATION` can become future Designer knowledge candidates, and they retain their original domain/scope. Cross-source and cross-domain promotion is separate and remains disabled here.", "", "## AI assistance", "", "`AIReviewRecommendation` uses `zen.industry_evidence_ai_recommendation.v0.1` and is never copied into a human decision. Visual and model interpretations are always HIGH review priority; direct statements from the current pack are MEDIUM priority.", "", "## Bias", "", "All six Pack 001 sources are manufacturer/technical case-study style and carry `MANUFACTURER_CASE_STUDY_BIAS`. This is a review limitation, not an automatic rejection.", "", "## Runtime boundary", "", "No UI, Designer context adapter, MA2 connection or MA2 write is part of this workflow."]
    (ROOT / "ZEN_HUMAN_REVIEW_WORKFLOW.md").write_text("\n".join(workflow) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_reports()
    print("Industry Reference Pack 001 reports written.")
