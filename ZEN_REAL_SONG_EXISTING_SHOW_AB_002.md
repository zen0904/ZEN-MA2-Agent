# Real Song + Existing Show A/B 002

**Recommendation:** `NEEDS_REVISION` — this is a genuine, traceable B3 typed
action-delta experiment, but it is not production readiness or artistic
approval. Zen's review remains `UNSET`.

## Scope and exact inputs

- **Song analysis:** [`examples/REALISTIC_SONG_ANALYSIS.json`](examples/REALISTIC_SONG_ANALYSIS.json),
  `ZEN_REAL_SONG_ANALYSIS_TEST`, `source: MANUAL`, confidence `1.0`.
  This does not claim instrumentation, harmony, lyrics, vocal emotion,
  performer staging, choreography, camera, venue response, or audio analysis.
- **Existing Show snapshot:**
  [`tests/fixtures/real_song_existing_show_ab_001.json`](tests/fixtures/real_song_existing_show_ab_001.json),
  Show fingerprint
  `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.
  Route: `EXISTING_SHOW`; planner: `BYPASSED_EXISTING_SHOW`.
- **Case approval fixture:**
  [`tests/fixtures/real_song_existing_show_ab_002.json`](tests/fixtures/real_song_existing_show_ab_002.json).
- **Current Show technical evidence:** all six FixtureTypes are
  `SHOW_BOUND_VERIFIED` by the real-console compound export proof in
  [`ZEN_FIXTURE_TYPE_EXPORT_SCHEMA_RESEARCH_001.md`](ZEN_FIXTURE_TYPE_EXPORT_SCHEMA_RESEARCH_001.md).

## Exact human approval boundary

Zen approved Groups `1–7` as `DENSITY_LAYER` candidate resources **only** for
`REAL_SONG_EXISTING_SHOW_AB_002`:

| Group | Exact Show label | FixtureType | Approval |
| ---: | --- | --- | --- |
| 1 | HYBRID | 2 — ZEN BAW 20R Mode 2 | `DENSITY_LAYER` candidate only |
| 2 | SPOT | 3 — ZEN DMH-160 St_Preset | `DENSITY_LAYER` candidate only |
| 3 | BEAM | 2 — ZEN BAW 20R Mode 2 | `DENSITY_LAYER` candidate only |
| 4 | WASH | 5 — ZEN MAC AU XB Standard | `DENSITY_LAYER` candidate only |
| 5 | B-EYE | 4 — ZEN K10 Shapes | `DENSITY_LAYER` candidate only |
| 6 | LED PAR | 6 — ZEN LEDPar 9c 9Ch Mode A | `DENSITY_LAYER` candidate only |
| 7 | STROBE | 7 — Atomic 3000 LED Extended | `DENSITY_LAYER` candidate only |

Approval provenance is
`ZEN_HUMAN_CASE_SPECIFIC_DENSITY_ELIGIBILITY_AB002` and scope is
`CASE_SPECIFIC_ELIGIBILITY_ONLY`. It is not a permanent Group mapping,
priority, use requirement, artistic identity, production activation, or
approval for any other B3 role.

## A — unchanged production baseline

The production `FirstSongDesigner` remains unchanged. A has eleven typed cues;
each calls Focus `6.2` on Group 1 and sets Group 1 dimmer as follows:

| Cue | Exact occurrence | A Group 1 level |
| ---: | --- | ---: |
| 1 | `intro_1` / base | 31 |
| 2 | `verse_1` / base | 47 |
| 3 | `pre_chorus_1` / base | 67 |
| 4 | `chorus_1` / base | 85 |
| 5 | `chorus_1` / `accent_1` | 96 |
| 6 | `verse_2` / base | 57 |
| 7 | `solo_1` / base | 73 |
| 8 | `chorus_2` / base | 94 |
| 9 | `chorus_3` / base | 100 |
| 10 | `chorus_3` / `accent_1` | 100 |
| 11 | `outro_1` / base | 39 |

## B — case-scoped Guidance-Assisted B3 candidate

B3 remains `GUIDANCE_ASSISTED_AB_ONLY`. It consumes the existing occurrence
identity, B3 Design Intent, density field, repeat relationship, previous look,
and measured later-peak information before selecting a subset of the approved
cohort. It then emits only typed `SET_DIMMER` actions. It does not emit
`CALL_PRESET`, `CALL_EFFECT`, position, color, movement, beam, strobe,
pixel/shape, or raw-console actions.

When two same-role occurrences have B3-recorded `MUSICALLY_JUSTIFIED_DELTA`,
the neutral density cohort is redistributed. When B3 has no such basis, the
previous cohort is continued where possible. Group numeric IDs are only a
deterministic tie-breaker inside an otherwise equal approved pool; neither
labels nor FixtureTypes choose a Group. This is a technical allocation policy,
not an asserted visual hierarchy.

| Cue / occurrence | B3 density intent; previous / headroom relationship | Selected Groups | Intentionally unused | B typed `SET_DIMMER` actions | Desired vs realized |
| --- | --- | --- | --- | --- | --- |
| `cue-1` `intro_1` / base | `NOT_REQUIRED_BY_CURRENT_CONTEXT`; first occurrence; no measured later peak | 1, 2 | 3, 4, 5, 6, 7 | G1 19; G2 19 | `FIRST_OCCURRENCE` / `REALIZED` |
| `cue-2` `verse_1` / base | `NOT_REQUIRED_BY_CURRENT_CONTEXT`; continue prior look | 1, 2 | 3, 4, 5, 6, 7 | G1 32; G2 32 | `FIRST_OCCURRENCE` / `REALIZED` |
| `cue-3` `pre_chorus_1` / base | `ACTIVE_BY_MEASURED_DENSITY`; continue prior cohort and expand | 1, 2, 3, 4 | 5, 6, 7 | G1 54; G2 54; G3 54; G4 54 | `FIRST_OCCURRENCE` / `REALIZED` |
| `cue-4` `chorus_1` / base | `REDUCED_FOR_HEADROOM`; known later `final_chorus` | 1, 2, 3 | 4, 5, 6, 7 | G1 38; G2 38; G3 38 | `FIRST_OCCURRENCE` / `REALIZED` |
| `cue-5` `chorus_1` / `accent_1` | same section; reuse cohort (no inferred Effect/strobe) | 1, 2, 3 | 4, 5, 6, 7 | G1 43; G2 43; G3 43 | same section / `REALIZED` |
| `cue-6` `verse_2` / base | `NOT_REQUIRED_BY_CURRENT_CONTEXT`; repeat delta: transition context changed | 2, 3, 4 | 1, 5, 6, 7 | G2 40; G3 40; G4 40 | `MUSICALLY_JUSTIFIED_DELTA` / `REALIZED`, action delta `CHANGED` |
| `cue-7` `solo_1` / base | `REDUCED_FOR_HEADROOM`; known later `final_chorus` | 2, 3, 4 | 1, 5, 6, 7 | G2 33; G3 33; G4 33 | `FIRST_OCCURRENCE` / `REALIZED` |
| `cue-8` `chorus_2` / base | `ACTIVE_BY_MEASURED_DENSITY`; repeat delta: transition and future-headroom context changed | 2, 3, 4, 5, 6, 7 | 1 | G2 89; G3 89; G4 89; G5 89; G6 89; G7 89 | `MUSICALLY_JUSTIFIED_DELTA` / `REALIZED`, action delta `CHANGED` |
| `cue-9` `chorus_3` / base | `ACTIVE_BY_MEASURED_DENSITY`; repeat delta: more rhythmic events, stronger transient evidence, transition changed | 1, 2, 3, 4, 5, 6, 7 | none | G1–G7 100 each | `MUSICALLY_JUSTIFIED_DELTA` / `REALIZED`, action delta `CHANGED` |
| `cue-10` `chorus_3` / `accent_1` | same final section; reuse cohort | 1, 2, 3, 4, 5, 6, 7 | none | G1–G7 100 each | same section / `REALIZED` |
| `cue-11` `outro_1` / base | `NOT_REQUIRED_BY_CURRENT_CONTEXT`; continue then contract from prior state | 1, 2 | 3, 4, 5, 6, 7 | G1 23; G2 23 | `FIRST_OCCURRENCE` / `REALIZED` |

All 11 records preserve `CUE_ID`, `SECTION_INSTANCE_ID`, and
`CUE_OCCURRENCE_INDEX`. Every selected/unused set accounts for exactly the
approved Groups 1–7. `case_role_assignment` remains absent: these are B3
experimental per-cue resource selections, not a stored Show mapping.

### Exact B3 Design Intent dimension trace

This compact trace exposes the actual B3 fields relevant to this density-only
case. `focus` and `palette` are `UNAVAILABLE` in every row because this case
did not approve their roles; no missing information is filled in. Each cue
also retains B3's typed audience goal, rationale, evidence provenance, and
`unknown_context` (`INSTRUMENTATION_CHANGE`, `VOCAL_EMOTION`,
`HARMONY_CHANGE`, `PERFORMER_STAGING` are `NOT_AVAILABLE`) in the experimental
plan and human-review cards.

| Cue | Density | Texture intent (not action-enabled) | Timing intent (not action-enabled) | Negative space / impact |
| --- | --- | --- | --- | --- |
| cue-1 | NOT_REQUIRED | NOT_REQUIRED | NOT_REQUIRED | INTENTIONAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-2 | NOT_REQUIRED | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | INTENTIONAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-3 | ACTIVE_BY_MEASURED_DENSITY | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | CONTEXTUAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-4 / cue-5 | REDUCED_FOR_HEADROOM | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | INTENTIONAL / BOUNDED_BY_HEADROOM |
| cue-6 | NOT_REQUIRED | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | INTENTIONAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-7 | REDUCED_FOR_HEADROOM | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | INTENTIONAL / BOUNDED_BY_HEADROOM |
| cue-8 | ACTIVE_BY_MEASURED_DENSITY | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | NOT_REQUIRED | CONTEXTUAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-9 / cue-10 | ACTIVE_BY_MEASURED_DENSITY | CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT | RHYTHMIC_PUNCTUATION_CONTEXT | CONTEXTUAL / CONTEXTUAL_NOT_AUTOMATIC |
| cue-11 | NOT_REQUIRED | NOT_REQUIRED | NOT_REQUIRED | INTENTIONAL / CONTEXTUAL_NOT_AUTOMATIC |

Texture/timing intent does not bypass this case's approval boundary: neither
role has a binding or a typed action in B.

## A/B delta and repeat trace

| Check | A | B | Traceable conclusion |
| --- | --- | --- | --- |
| Typed actions | Group 1 Focus `6.2` + dimmer only | Approved target Groups with `SET_DIMMER` only | B changes typed target composition without new console grammar. |
| Section contrast | one Group and level curve | 2/2/4/3/3/3/6/7/2 base-cohort participation | Not monotonic; `chorus_1` and `solo_1` contract for measured later headroom. |
| Repeated verse | no occurrence-specific resource delta | `verse_2`: G1/G2 becomes G2/G3/G4 | Delta is linked to B3's recorded transition-context change. |
| Repeated chorus | same production Group 1 route | `chorus_1`: G1–3; `chorus_2`: G2–7; final: G1–7 | Each B3 change has recorded repeat/future/rhythmic basis; no label-based role selection. |
| Intentional omission | none outside Group 1 baseline limitation | every cue except final leaves one or more approved Groups unused | Omission is explicit and reviewable. |
| Realizability | not applicable | repeat composition deltas are `REALIZED` because Group target/action shapes change | No Design Intent delta is claimed realized when actions are identical. |

## Technical and design-quality review

The experiment proves that the approved `DENSITY_LAYER` cohort can produce a
deterministic, occurrence-addressable, action-level B candidate using only
Show-bound verified DIMMER resources. It also proves that an earlier high
section need not use the largest cohort: `chorus_1` and `solo_1` have explicit
headroom reduction while `chorus_2` is allowed to expand.

Two limits are intentionally surfaced rather than concealed:

1. `FINAL_COHORT_SATURATION_RISK` — the supplied final section has density
   `1.0`, base level `100`, no later measured peak, and all seven equal cohort
   members. Current B3 therefore produces G1–G7 at 100. This is a result of
   the present bounded density path, not a global “final must be biggest”
   rule, but it needs human review before any future implementation.
2. `GROUP_LEVEL_HOMOGENEITY_UNRESOLVED` — selected Groups use equal dimmer
   levels because the approved evidence distinguishes DIMMER availability but
   gives no verified spatial, coverage, or artistic hierarchy among Groups.
   Inventing differentiated per-Group levels would be less honest than
   reporting this limitation.

The system does **not** infer that STROBE must impact, WASH must color, BEAM
must beam, or HYBRID must focus. It does **not** use Group labels to select the
cohort. It also does not infer Color, texture, movement, effects, timing,
semantic positions, or pixel behavior.

## Remaining blockers for richer expression

- Case-approved, provenance-bearing eligibility or action resources for any
  non-density B3 role.
- Verified Color preset/action applicability, if a case needs color intent.
- Semantic target/position and geometry evidence before performer/area focus
  or spatial composition can be expressed.
- A safe, separately verified texture/timing/effect action grammar.
- Human judgment on whether neutral numeric cohort distribution is acceptable
  for this real Show, or whether a future case must provide real visual
  relationships before multi-Group density composition is meaningful.

## Safety and decision boundary

- Production Designer: `UNCHANGED`.
- Experimental Designer: `GUIDANCE_ASSISTED_AB_ONLY`.
- Guidance-Assisted production activation: `NOT_RUN`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- MA2 objects modified: `NONE`.
- MA2 write audit: `ZERO_WRITES`.
- Fixture 9999 touched: `NO`.
- Human review: closed; see **Human Density Cohort Review 001** below.

## Human Density Cohort Review 001

Zen has reviewed the actual A/B 002 result. This review preserves the
technical experiment and prevents an unsupported artistic conclusion.

| Review dimension | Human conclusion | Boundary |
| --- | --- | --- |
| Technical capability | `PASS` / `TECHNICAL_EXPRESSIVE_PATH_PROVEN` | B3 safely and traceably changed current Existing Show Group participation and typed `SET_DIMMER` actions. |
| Artistic generalization | `ARTISTIC_GENERALIZATION_NOT_APPLICABLE` | The observed cohort is neither a universally good nor bad lighting design. Group selection, participation count, and levels depend on Design Intent, song/performance, composition, hierarchy, contrast, spatial relationships, rig, other visual dimensions, previous/future looks, and production context. |
| Density concept | `DENSITY_IS_CONTEXT_DEPENDENT_DIMENSION` | Density is descriptive and controllable, not a prescriptive rule. It does not imply higher energy needs more Groups, a chorus needs density, a final chorus needs all resources, negative space needs fewer fixtures, or more fixtures make a stronger design. |
| Neutral cohort allocator | `NEUTRAL_ALLOCATOR_EXPERIMENTAL_ONLY` | Numeric-ID tie-breaking, equal Group levels, and full-cohort saturation remain proof-of-path mechanics only. They are not Lighting Design knowledge, an artistic strategy, a permanent Group mapping, or production behavior. |

The prior `FINAL_COHORT_SATURATION_RISK` and
`GROUP_LEVEL_HOMOGENEITY_UNRESOLVED` findings remain useful technical review
signals. They do not make Density fail, and they do not authorize a silent
allocator correction. A future case may use Density only through its own
Design Intent, verified resources, visual/context evidence, and human review.
