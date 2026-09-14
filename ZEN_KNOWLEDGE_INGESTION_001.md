# ZEN Knowledge Ingestion 001

## Outcome

Pack 001 now contains **140** concise, descriptive records backed by **15** registered sources across global design education, professional case practice, MA2/fixture documentation, and human-confirmed ZEN preference evidence. The pack remains shadow/review material; no record is promoted to production truth.

## Batches

| Batch | Scope | Added | Evidence boundary |
|---|---|---:|---|
| A | Global design principles (ETC focus/composition and education) | 40 | GENERAL_DESIGN_KNOWLEDGE, descriptive, shadow/review |
| B | Professional touring/case practice (PLASA) | 30 | CASE_CONTEXT / PROFESSIONAL_PRACTICE, scoped to case disciplines |
| C | MA2 programming and fixture provenance (MA2/GDTF) | 25 | OFFICIAL_DOCUMENTED / technical, shadow-only |
| D | Human-confirmed ZEN visual/workflow preference | 20 | USER_PREFERENCE, CONTEXT_DEPENDENT, never global law |

The pre-existing 25 records remain unchanged, giving 25 + 40 + 30 + 25 + 20 = 140 total records. Every record is `DESCRIPTIVE`; no copied articles, transcripts, videos, binaries, commands, or raw web archive were added.

## Source registry

The 15 metadata-only sources are in `data/external_lighting_knowledge_source_registry_001.json`: ETC educational resources and focus/composition material; official grandMA2 tracking and sequence-editing documentation; GDTF channel and fixture-information documentation; PLASA case references for Paradise Under the Stars, Alice in Chains, Enter Shikari, Muni Long, and Black Keys; and the human-confirmed ZEN visual-language reference. Each source retains URL, retrieval date, authority, scope/bias, and a derived-extract copyright policy.

## Distribution

Records cover all 14 existing topics, including hierarchy, negative space, density, contrast, color relationships, layering/depth, movement, focus, rhythm, energy progression, repeated sections, headroom, MA2 maintainability, and fixture capability provenance. Source classifications remain distinct: official documentation, general design knowledge, professional practice, case context, and user preference. User-preference records normalize to the `ZEN_STYLE_AND_WORKFLOW_KNOWLEDGE` store category.

## Deterministic retrieval inspections

The same store and retrieval function were run for five requests (limit 6, one record per topic). Selected IDs are deterministic and source-linked:

1. `high energy K-pop repeated chorus` → `elk001_contrast_plasa`, `elk001_negative_space_chauvet`, `elk002_b27`, `elk002_a20`, `elk002_b06`, `elk002_b19`.
2. `quiet ballad with sparse visual language` → `elk001_restraint_plasa`, `elk002_b17`, `elk001_density_etc`, `elk001_resource_selection_muse`, `elk001_color_muse`, `elk001_contrast_plasa`.
3. `rap section with rhythmic accents` → `elk002_d16`, `elk001_complete_look_etc`, `elk001_density_etc`, `elk001_repetition_muse`, `elk001_resource_selection_muse`, `elk002_a34`.
4. `limited rig with no spatial evidence` → `elk001_complete_look_etc`, `elk001_palette_restraint_chauvet`, `elk002_b07`, `elk002_b10`, `elk002_b21`, `elk001_contrast_plasa`.
5. `YG-style restrained high-impact concert lighting` → `elk001_negative_space_chauvet`, `elk002_d11`, `elk001_energy_arc_plasa`, `elk001_focus_etc`, `elk002_a01`, `elk002_b06`.

Role-specific Researcher/Designer/Critic/Finalizer retrieval is deterministic. For the first request, all four roles select the same first four IDs; Critic's fifth is `elk002_d07` while the other three select `elk002_b06`, reflecting topic scope rather than a recipe.

## Duplicate and rejected-candidate review

`find_duplicate_candidates()` performs deterministic token-Jaccard comparison within topic and returns review candidates without deleting or merging. Pack 001 currently yields **0** candidates at threshold 0.82. This is a review signal, not proof that semantic duplication is impossible. Rejected records: **0** in this ingestion; unsupported or conflicting ideas remain explicit in record exclusions/conflicts and promotion state rather than being silently removed.

## Visual-reference foundation

`zen_ma2_agent/visual_reference.py` and `data/visual_reference_foundation_001.json` provide metadata-only visual reference records (`NEEDS_REVIEW`, `POSITIVE`/`NEGATIVE`/`MIXED`) with transferable concepts and non-transferable specifics. No binary media is stored. This foundation is not wired into Production Designer or B3.

## What the pack can and cannot do

The pack can supply contextual questions about hierarchy, contrast, restraint, repetition, resource headroom, and professional MA2 maintainability. It cannot establish current-Show positions, coverage, performer targets, beam intersections, visual dominance, or safe action applicability. Those remain Show-bound evidence questions. Knowledge therefore flows only through the existing evidence ledger and shadow/review context; it does not bypass Design Intent → Visual Strategy → typed plan → Resolver → Builder.

## Safety and status

- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`; no production activation.
- Local model / training execution: **NO**.
- MA2/Telnet/Builder execution: **NO**; MA2 writes: **ZERO_WRITES**.
- Fixture 9999 untouched; no permanent fixture-role mapping; no MA3 Builder.
- Git LFS, bulk media, and expensive CI: **NOT INTRODUCED**.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.

## Remaining gaps and next leverage

The pack is broad enough for shared retrieval across Researcher, Designer, Critic, and Finalizer, but artistic usefulness still requires human case review. Highest leverage is a bounded visual/spatial evidence case (or real operator review) that lets the shadow critique distinguish cohort homogeneity, headroom, and hierarchy without inventing Group relationships. Further packs should add diverse sources and preserve scope, not accumulate fixed recipes.

## Visual reference correction addendum (2026-09-14)

`VR_ZEN_YG_LANGUAGE_001` is now recorded as `POSITIVE` and
`HUMAN_CONFIRMED`, reflecting the user's explicit approval of that reference
as a preference-layer example. Its observations and transferable concepts are
bounded around hierarchy, negative space, restraint, headroom, depth, focus,
contrast, and movement restraint; no color, fixture, placement, timing, or
genre-wide recipe is promoted. The source is a user-provided media metadata
reference (`media_ref` only); no binary media is stored and `source_url` is
nullable for this origin.
