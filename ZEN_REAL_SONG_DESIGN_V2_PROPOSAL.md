# ZEN Real Song Design V2 Proposal

**Status:** proposal only — do not execute  
**V1 baseline preserved:** Sequence 205 `ZEN_AI_TEST_REAL_LIGHTING_DESIGN_TEST`  
**MA2 objects changed by this proposal:** none  
**Creative decision required:** `USER_CREATIVE_REVIEW_REQUIRED`

## Evidence boundary

This read-only creative evaluation uses the verified Sequence 205 cue labels, stored fades, resolved Group/Preset/Effect references, and builder execution record in `ZEN_REAL_SONG_DESIGN_REPORT.md`.

It does **not** claim a visual Cue-content read-back: that provider is still partial for Effect content. No MA2 command was sent while preparing this proposal.

## V1 design diagnosis

V1 is a clean, dependable programming skeleton rather than a finished performance design. It establishes an energy curve through dimmer levels, uses the verified Dimmer Chase for build sections, and returns to a slow outro fade.

Its limitation is resource concentration: every cue addresses Group 1 `HYBRID`, calls Focus Preset 6.2 `normal`, and has access to only Effect 3520 `ZEN_FX_DIM_CHASE_SLOW_GROUP1`. Verified numeric fixture geometry is not expressed as a cue-level strategy. Most musical progression is therefore intensity-only.

| Resource dimension | V1 actual use | Creative implication |
|---|---:|---|
| Groups | 1 | No fixture-family or layer contrast |
| Presets | 1 | No look or focus vocabulary change |
| Effects | 1 | A single chase carries every build section |
| Geometry strategies | 0 applied | Neutral geometry is not visible in programming |
| Fade classes | 3: 2.0 s, 1.2 s, 0.5 s | Basic hierarchy, but PRE/CHORUS/FINAL share one attack |

## Cue-by-cue creative evaluation

| Cue | Section | Energy | Purpose | Groups | Preset / look | Effect | Geometry strategy | Fade | Difference from previous Cue | Design rationale / assessment |
|---:|---|---:|---|---|---|---|---|---:|---|---|
| 1 | INTRO | 0.18 | Restrained opening | HYBRID | Focus 6.2 `normal`, low dimmer | None | None applied | 2.00 | Baseline | Credible gentle entry; the long fade is the strongest part. |
| 2 | VERSE_1 | 0.38 | Support first verse | HYBRID | Same Focus, higher dimmer | None | None applied | 1.20 | Intensity rises only | Functional but visually close to Cue 1; no separate verse identity. |
| 3 | PRE_CHORUS_1 | 0.62 | Begin anticipation | HYBRID | Same Focus, higher dimmer | 3520 slow chase | None applied | 0.50 | First effect entry | The effect spends much of the chorus signature too early. |
| 4 | CHORUS_1 | 0.86 | First major opening | HYBRID | Same Focus, higher dimmer | 3520 slow chase | None applied | 0.50 | Brighter Cue 3 | Intensity uplift rather than a new chorus look. |
| 5 | VERSE_2 | 0.46 | Release into verse | HYBRID | Same Focus, reduced dimmer | None | None applied | 1.20 | Effect off; intensity drops | Readable release, but nearly V1 verse vocabulary again. |
| 6 | PRE_CHORUS_2 | 0.72 | Stronger second build | HYBRID | Same Focus, higher dimmer | 3520 slow chase | None applied | 0.50 | Same as Cue 3, brighter | Escalates numerically, not enough visually. |
| 7 | CHORUS_2 | 0.94 | Increase second chorus | HYBRID | Same Focus, higher dimmer | 3520 slow chase | None applied | 0.50 | Brighter Chorus 1 | Same resource combination as Chorus 1. |
| 8 | SOLO | 0.68 | Make space for solo | HYBRID | Same Focus, mid-high dimmer | None | None applied | 0.50 | Effect removed | Stops the chase but lacks focused or spatial solo identity. |
| 9 | FINAL_CHORUS | 1.00 | Strongest point | HYBRID | Same Focus, full dimmer | 3520 slow chase | None applied | 0.50 | Higher intensity only | The small final energy increment is not a convincing final distinction on its own. |
| 10 | OUTRO | 0.28 | Release and leave song | HYBRID | Same Focus, low dimmer | None | None applied | 2.00 | Effect off; long fade | Clear functional resolution; needs a distinct release look later. |

## Repeated-section assessment

| Comparison | Result | Evidence |
|---|---|---|
| VERSE_1 → VERSE_2 | **PARTIAL** | Cue 5 is brighter but keeps Group, Focus, no Effect, and 1.2 s fade. |
| PRE_CHORUS_1 → PRE_CHORUS_2 | **PARTIAL** | Cue 6 raises energy but repeats Cue 3's Group, Preset, chase, and fade. |
| CHORUS_1 → CHORUS_2 | **WEAK** | Cue 7 is brighter, but all named resources and transition class are unchanged. |
| CHORUS_1 → FINAL_CHORUS | **WEAK** | Cue 9 reaches full intensity while retaining the same Group, Preset, Effect, geometry treatment, and fade. |

## Effect and fade assessment

### Effect usage: REPETITIVE

Effect 3520 appears in five of ten cues: both pre-choruses and all three chorus-level moments. With one slow Dimmer Chase, that risks effect fatigue and makes the first chorus less distinctive.

V2 should retain the verified effect, not invent another family, but reserve it for fewer payoff moments: at minimum CHORUS_1 and FINAL_CHORUS. CHORUS_2 can reuse it only when a separately resolved group or layer makes the look materially different.

### Fade quality: NEEDS_ADJUSTMENT

The 2.0 s INTRO and OUTRO fades work well; 1.2 s verses read as measured. PRE_CHORUS, CHORUS, SOLO, and FINAL_CHORUS all use 0.5 s, flattening the musical shape.

V2 should use a controlled pre-chorus build, more decisive chorus entries, and a deliberate solo focus transition.

## V2 design direction — not an execution plan

The next build must allocate a **new** Agent-owned Sequence such as `ZEN_AI_REAL_SONG_V2_*`; it must never overwrite Sequence 205. Each choice below remains typed design intent to be resolved, previewed, and approved through the existing Builder. It is not an MA2 command list.

| Section | V2 intent | Effect policy | Distinctiveness requirement |
|---|---|---|---|
| INTRO | Keep restrained opening and slow transition. | None | Preserve V1's useful space. |
| VERSE_1 | Establish base look with modest intensity. | None | Keep it intentionally simple. |
| PRE_CHORUS_1 | Build without spending chase immediately. | None by default | Different fade class from chorus. |
| CHORUS_1 | First clear release. | Reuse 3520 after fresh resolution. | Decisive entry and a confirmed typed layer choice. |
| VERSE_2 | Return, but not as a copy. | None | Resolve a different safe group layer or approved preset; otherwise flag limitation. |
| PRE_CHORUS_2 | Stronger preparation. | None by default | Higher level and shorter fade, still save payoff. |
| CHORUS_2 | Escalate over CHORUS_1. | 3520 only with a second verified target/layer. | Change at least two dimensions: target/layer, preset, geometry, or transition. |
| SOLO | Create reduction and focal point. | None | Requires semantic position or group-layer fallback; do not fake spatial solo. |
| FINAL_CHORUS | Unique final release. | Reuse 3520, broader layer only if verified. | Must differ from CHORUS_2 in more than dimmer level. |
| OUTRO | Remove effect and resolve slowly. | None | Preserve 2.0 s release; use distinct look only when supported. |

## Acceptance rules for a future V2 build

1. At least two material design dimensions must change between repeated CHORUS sections. Dimmer level alone does not count.
2. The Dimmer Chase must be reserved for a defined payoff, not every build.
3. A geometry strategy may be used only through verified typed resources. Numeric geometry alone is not a visible cue treatment.
4. Any additional Group or Preset must be freshly resolved and remain inside the existing preview/approval boundary.
5. The SOLO must remain a stated fallback when no exact semantic position resource is available.
6. V2 requires Zen's artistic approval, not merely technical validation.

## Recommended creative review

**USER_CREATIVE_REVIEW_REQUIRED.** Sequence 205 remains the technical baseline. Review this proposal against the intended genre, lyrics, staging, and available show resources, then authorize a separate V2 Preview. Only that approved V2 may create a new sequence.
