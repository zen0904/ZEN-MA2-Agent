# Guidance-Assisted Designer A/B 003 — Design-Intent-First Refinement

Status: `GUIDANCE_ASSISTED_AB_ONLY`. This is a command-free local experiment;
it does not replace the production `FirstSongDesigner` or invoke the MA2
Builder path.

## Why B3 Exists

B2 correctly removed the LED energy/layer ladder, but its resource selector
still made choices too close to isolated signal thresholds. B3 puts a bounded
`zen.design_intent.v0.1` between Song/Performance Context and resource choice:

```text
Known song and rig context
  -> reviewable Design Intent
  -> visual strategy (keep / reduce / omit)
  -> existing typed action composition
```

The order is now: section function, audience perception, prior visual state,
known upcoming context/headroom, available signals, confirmed rig roles,
intentional omissions, then typed actions. No raw MA2/Telnet/Lua field is valid
in a Design Intent.

Concretely, B2 treated repeated development mainly as stronger rhythm or a
material density increase, and made mover texture depend on dynamic/accent
signals. B3 retains those as valid evidence but adds supplied section context,
predecessor transition, known later headroom and conscious continuity. It does
not treat any one of those signals as a mandatory trigger.

## B3 Design Intent Trace

Each experimental cue carries a reviewable trace:

- `KNOWN_SONG_CONTEXT`: section role, density, accent level, explicit events,
  and supplied notes.
- `PREVIOUS_VISUAL_STATE`: roles selected immediately before the section.
- `UPCOMING_CONTEXT`: next section and a later major peak only when measured
  energy actually establishes one.
- `DESIGN_INTENT`: audience goal, continuity/change relation, visual-dimension
  intents, headroom, evidence provenance and intentional omissions.
- `KEEP`, `CHANGE`, `OMIT`, `SUBSTITUTE`, typed action delta and
  `HUMAN_REVIEW: UNSET`.

Current Song Analysis does not provide instrumentation changes, vocal emotion,
harmony changes, or performer staging. B3 records each as `NOT_AVAILABLE`; it
does not fabricate them.

## Repeated Sections

`MUSICALLY_JUSTIFIED_DELTA` now considers the available comparison between a
repeat and its prior occurrence: event count/strength, density, accent level,
section notes, predecessor transition and whether a later measured peak changes
headroom. A repeated section can instead state `INTENTIONAL_SIMILARITY` with
the conscious rationale that continuity is more useful than novelty.

Development is not an escalation instruction. It can reflect a section-note
texture difference, altered transition context, timing character, role balance
or a deliberate omission. Neither `REPEAT_ALWAYS_BIGGER` nor
`EVERY_REPEAT_SHOULD_LOOK_DIFFERENT` is allowed.

## Bounded Evaluation Cases

All cases are deterministic `SYNTHETIC_EVALUATION_ONLY` variations on the
existing buildup/drop analysis. They are evidence of reasoning boundaries, not
claims about a real song or venue.

| Case | Available evidence | B3 result |
| --- | --- | --- |
| A — repeated Drop, new rhythm | Drop 2 contains an extra explicit accent. | `MUSICALLY_JUSTIFIED_DELTA`; the reason is extra rhythmic evidence, not its repeat index. |
| B — repeated Drop, matching signals | Same repeat energy, density, accent and event evidence. | `INTENTIONAL_SIMILARITY`; recognizable identity is deliberately preserved. |
| C — same-energy repeat, contextual change | Drop 2 adds a sustained textural section note. | Development occurs without higher energy; texture can be a meaningful delta. |
| D — quiet texture | Low-energy intro has an atmospheric/sustained note and no rhythmic event. | `MOVER_TEXTURE_LAYER` can be retained for atmosphere without a hit or rise. |
| E — high texture omission | High Drop has no texture-supporting note/accent/event. | Texture is intentionally omitted; high energy does not require it. |
| F — low rhythmic section | Low intro has an explicit strong accent. | Timing can be retained even at low energy. |
| G — sustained high section | High Drop has little rhythmic punctuation. | Timing can be omitted; high energy does not force timing. |
| H — earlier high before later peak | A high Drop is followed by a materially stronger measured peak. | Density is reduced to preserve known future headroom; this is not a save-for-final rule. |

## A vs B2 vs B3

| Path | Scope | Reasoning visibility |
| --- | --- | --- |
| A — production baseline | Current deterministic `FirstSongDesigner`; unchanged. | Existing typed plan only. |
| B2 — A/B-002 reference | Explicit experimental version retained for comparison. | Resource-choice trace with narrower density/rhythm repeat basis. |
| B3 — A/B-003 candidate | Explicit experimental version only. | Typed Design Intent, prior-look/upcoming context, known/unknown signals, conscious similarity/development, and human review trace. |

B3 need not differ from B2 in every case. Preserving an existing candidate is
valid when the richer trace finds no new contextual reason to change it.

## Guardrails

B3 explicitly rejects these formulaic interpretations:

- `MORE_RHYTHM_MEANS_MORE_LIGHTING`
- `MORE_DENSITY_MEANS_MORE_LAYERS`
- `TEXTURE_REQUIRES_ACCENT`
- `TEXTURE_REQUIRES_DYNAMIC_CHANGE`
- `REPEATED_SECTION_REQUIRES_DELTA`
- `EVERY_REPEAT_SHOULD_LOOK_DIFFERENT`
- `FINAL_SECTION_ALWAYS_BIGGEST`
- `HIGH_ENERGY_ALWAYS_COMPLEX`
- `LOW_ENERGY_ALWAYS_SIMPLE`
- `AVAILABLE_FIXTURE_ROLE_MUST_BE_USED`

The existing B2 formula guards remain as well. Human-confirmed style evidence
guides hierarchy, palette coherence, musical alignment, intentional restraint,
whole-song development and complete looks. It is still preference evidence, not
law. Context-dependent candidates remain inactive as fixed rules.

## Quality Assessment

The B3 test harness reports independent statuses for Design Intent coherence,
whole-song, prior-look and future-headroom awareness, repeat reasoning,
similarity, texture judgment, visual-dimension selection, complete looks,
resource/context awareness, non-formulaic reasoning, evidence traceability and
human readability. It deliberately has no weighted total.

The bounded cases support `READY_FOR_HUMAN_REVIEW`: the reasoning is now
inspectable enough for a lighting designer to challenge the intent rather than
only the resulting role list. This is not production readiness. The remaining
weakness is that current Song Analysis has only structural/dynamic/event/note
signals, so a real human review and a real venue/rig case are still needed.

The strongest B3 improvement is the review trace that makes an intentionally
similar repeat, a context-driven texture choice and a headroom reservation
distinguishable from missing variation. Its weakest area is the quality of the
upstream musical analysis: supplied notes are bounded evidence, not automatic
understanding of arrangement, harmony, performer staging or emotion.

## Safety

- Production Designer: `UNCHANGED`
- Experimental mode: `GUIDANCE_ASSISTED_AB_ONLY`
- Guidance-Assisted production activation: `NOT_RUN`
- `ZEN_STYLE_PROFILE`: `DEFERRED`
- Real venue validation: `WAIT_FOR_REAL_CASE`
- MA2 objects modified: `NONE`
- MA2 write audit: `ZERO_WRITES`
