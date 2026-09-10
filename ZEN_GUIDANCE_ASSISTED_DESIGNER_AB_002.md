# Guidance-Assisted Designer A/B 002 — Human Review Refinement

Status: `GUIDANCE_ASSISTED_AB_ONLY` / local deterministic evaluation only.

This document records Human A/B Review 001 separately from the original A/B
fixtures and describes the bounded experimental refinement. It does not modify
the production `FirstSongDesigner`, default routing, Builder, Resolver, or any
grandMA2 object.

## Human A/B Review 001

Records use `zen.guidance_ab_human_review.v0.1` and are stored in
`tests/fixtures/guidance_ab_human_review_001.json`. They reference the original
baseline and experimental report rather than changing either source.

| Case | Human decision | Bounded result |
| --- | --- | --- |
| High-energy buildup/drop | `DIRECTION_ACCEPTED_WITH_REQUIRED_IMPROVEMENT` | Low states, buildup, headroom and bounded peaks were accepted. A second Drop needs a real delta only when music supports it. |
| Restrained/minimal | `CONTEXT_DEPENDENT` | Complete looks remain required; `Verse sparse -> Refrain add layers` is not a universal recipe. |
| LED-only | `NEEDS_GUIDANCE_REWORK` | The former `COLOR -> COLOR+DENSITY -> COLOR+DENSITY+TIMING` energy ladder was rejected as formulaic. |
| Asymmetric rig | `ACCEPT_WITH_CONTEXT_LIMITATION` | Physical asymmetry must stay factual; whether it is highlighted, softened or visually centered is contextual. |

New A/B-002 outputs are review-ready with `HUMAN REVIEW: UNSET`. No human
approval is inferred for them.

## Experimental Refinement

The experiment now derives role composition from separately retained song
signals and confirmed role-to-scanned-Group bindings:

- `COLOR_FIELD` and `PRIMARY_FOCUS` provide bounded palette/hierarchy choices.
- `DENSITY_LAYER` is selected from measured section density, not energy state.
- `TIMING_LAYER` is selected only when the section carries explicit rhythmic
  events (`ACCENT`, `HIT`, `KICK`, `DRUM`, or `TRANSIENT`), so a low section can
  have timing and a high section can intentionally omit it.
- `MOVER_TEXTURE_LAYER` needs contextual dynamic/accent evidence, not merely a
  section label.
- Repeated-section delta requires stronger/more rhythmic evidence or a material
  density change relative to the prior occurrence of the same section role.
  Otherwise the result is explicitly `INTENTIONAL_SIMILARITY`.

`energy_is_not_a_layer_count: true` is carried per experimental cue. A complete
look is an intentional composition of available roles, hierarchy, palette,
omission and timing; it is independent of energy and of raw layer count.

## A/B 002 Bounded Results

| Evaluation | Baseline A | Experimental B | Result / human review |
| --- | --- | --- | --- |
| Repeated buildup/drop | Reuses its existing deterministic look logic. | Drop 2 receives a timing-emphasis delta only after a second explicit rhythmic event is supplied. | `SUPPORTED`; `UNSET` |
| Same repeated drop signals | Existing deterministic actions may retain their own baseline variation. | Same selected roles and multipliers; `INTENTIONAL_SIMILARITY`, not repeat-index escalation. | `SUPPORTED`; `UNSET` |
| LED low-energy accent | Baseline has no role interpretation. | A low intro with an explicit accent keeps `COLOR_FIELD` plus `TIMING_LAYER`. | `SUPPORTED`; `UNSET` |
| LED high-energy, no accent | Baseline remains canonical. | A high Drop may keep color/density while omitting timing when there is no rhythmic event. | `SUPPORTED`; `UNSET` |
| LED medium, rhythmic but low density | Baseline remains canonical. | A medium build can select timing and omit density. | `SUPPORTED`; `UNSET` |
| Restrained/minimal | Existing plan is untouched. | Selection responds to section density/accent evidence; no fixed Verse/Refrain layer instruction exists. | `CONTEXT_DEPENDENT`; `UNSET` |
| Asymmetric context | Existing physical layout remains user-confirmed. | No mirror/symmetry role is invented; no aesthetic assertion that imbalance must be emphasized is emitted. | `CONTEXT_DEPENDENT`; `UNSET` |

### KEEP / REDUCE / OMIT / SUBSTITUTE

These remain typed experimental design intent, never commands. `KEEP` now
means the role has a song/context justification; `REDUCE` and `OMIT` make
negative space inspectable; `SUBSTITUTE` remains available for bounded resource
adaptation. The new LED cases show that these choices are not an energy-to-role
ladder.

## Explicit Rejection Guard

Every experimental candidate records these rejected formulaic interpretations:

- `REPEAT_ALWAYS_BIGGER`
- `SECOND_DROP_ALWAYS_BIGGER`
- `LED_LOW_COLOR_ONLY`
- `LED_MEDIUM_ADDS_DENSITY`
- `LED_HIGH_ADDS_TIMING`
- `ENERGY_EQUALS_LAYER_COUNT`
- `ASYMMETRY_MUST_BE_EMPHASIZED`
- `MINIMAL_VERSE_ALWAYS_SPARSE`
- `REFRAIN_ALWAYS_ADDS_LAYERS`

This is a trace/safety declaration, not a new production style profile.
Context-dependent User Style candidates remain non-fixed, and all prior
rejected interpretations remain preserved.

## Safety and Scope

- Production Designer: `UNCHANGED`
- Experimental mode: `GUIDANCE_ASSISTED_AB_ONLY`
- Guidance-Assisted production activation: `NOT_RUN`
- `ZEN_STYLE_PROFILE`: `DEFERRED`
- Real venue validation: `WAIT_FOR_REAL_CASE`
- MA2 objects modified: `NONE`
- MA2 write audit: `ZERO_WRITES`

## Remaining Limitations

This remains synthetic, role-bound evaluation. It does not prove that the
chosen Group/preset compositions are artistically right for a real venue, does
not create palette variants, and cannot inspect live cue contents. A human
lighting-designer review of the new cue-by-cue deltas is required before any
future production A/B promotion is considered.

Recommended next step: conduct human review of A/B 002 cue-level outputs, then
use a real venue/rig case to determine whether the same bounded experiment is
artistically useful under actual resources.
