# Real Song + Existing Show A/B 001

Status: `READY_FOR_HUMAN_REVIEW` — an honest no-action-change result.

This is a read-only, deterministic A/B-003 evaluation. It uses a real existing
Show snapshot and the existing real-song analysis fixture; it does not contact
MA2, Telnet, a Plugin, or Builder.

## Exact inputs

- Song input: `examples/REALISTIC_SONG_ANALYSIS.json`
  (`ZEN_REAL_SONG_ANALYSIS_TEST`, `source: MANUAL`, confidence `1.0`). This is
  structured analysis, not a claim of audio-derived instrumentation, lyrics,
  harmony, vocal emotion, staging, choreography, camera, or venue response.
- Existing Show snapshot: `tests/fixtures/real_song_existing_show_ab_001.json`,
  sanitized from the read-only `data/ZEN_CURRENT_SHOW_PROFILE.json` capture on
  2026-09-09.
- Show identity: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`
  (`PARTIAL` scanned-profile fingerprint).
- Intake route: `EXISTING_SHOW`; planner status: `BYPASSED_EXISTING_SHOW`.

## Existing Show resources actually available in the fixture

| Group | Name | Ordered fixtures |
| --- | --- | --- |
| 1 | HYBRID | 101–108 |
| 2 | SPOT | 301–308 |
| 3 | BEAM | 201–208 |
| 4 | WASH | 501–508 |
| 5 | B-EYE | 401–408 |
| 6 | LED PAR | 601–608 |
| 7 | STROBE | 701–708 |

The verified usable preset inventory is Focus `6.1 narrow`, `6.2 normal`,
`6.3 wide`, `6.4 min Focus`, and `6.5 max Focus`. No semantic position preset
is available. Geometry is `GEOMETRY_UNINITIALIZED`; no geometry claim is made.
The full Effect inventory is intentionally not treated as a safe effect source
because internal parameters are not verified.

Training Case role suggestions for these Groups remain
`INFERRED_FROM_GROUP_IDENTITY`. They are not promoted to confirmed role-to-Group
bindings here. Therefore B3 may reason but may not target additional Groups or
invent Color/Texture/Timing programming.

## A/B result

### A — Production baseline

The unchanged production `FirstSongDesigner` generates 11 typed cues from the
real-song fixture. Every cue calls Focus `6.2` on Group `1 HYBRID` and sets the
following dimmer level:

| Cue | Exact occurrence | Section | Level |
| --- | --- | --- | --- |
| cue-1 | intro_1 / base | INTRO | 31 |
| cue-2 | verse_1 / base | VERSE_1 | 47 |
| cue-3 | pre_chorus_1 / base | PRE_CHORUS | 67 |
| cue-4 | chorus_1 / base | CHORUS_1 | 85 |
| cue-5 | chorus_1 / accent_1 | CHORUS_1_ACCENT_1 | 96 |
| cue-6 | verse_2 / base | VERSE_2 | 57 |
| cue-7 | solo_1 / base | SAX_SOLO | 73 |
| cue-8 | chorus_2 / base | CHORUS_2 | 94 |
| cue-9 | chorus_3 / base | FINAL_CHORUS | 100 |
| cue-10 | chorus_3 / accent_1 | FINAL_CHORUS_ACCENT_1 | 100 |
| cue-11 | outro_1 / base | OUTRO | 39 |

### B — Guidance-Assisted B3 experimental candidate

`GUIDANCE_ASSISTED_AB_ONLY` is preserved. B3 produces its actual Design Intent
and occurrence-level trace, but its typed actions are exactly the same as A.
This is deliberate: there are no confirmed role-to-scanned-Group bindings in
the Existing Show context. Treating the Training Case's inferred Group roles as
confirmed would fabricate a resource capability decision.

All eleven B3 cues therefore have:

- canonical `role_states: []`;
- `intent_realizability.status = NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES`;
- `actual_action_delta = UNCHANGED`;
- `HUMAN_REVIEW = UNSET`.

This is not an artistic failure claim. It is a capability/provenance limit:
the current B3 action compiler cannot turn abstract Design Intent into extra
existing-Show actions until a human or a separately verified resource-mapping
workflow confirms which real Groups safely implement which roles.

## Human-review cards

| Occurrence | B3 desired development | B3 known context | Actual realization | Human review |
| --- | --- | --- | --- | --- |
| intro_1 | FIRST_OCCURRENCE | INTRO, energy .20, density .20, no rhythmic event | NOT_EXPRESSIBLE; A actions retained | UNSET |
| verse_1 | FIRST_OCCURRENCE | VERSE, energy .40, density .35 | NOT_EXPRESSIBLE; A actions retained | UNSET |
| pre_chorus_1 | FIRST_OCCURRENCE | PRE_CHORUS, energy .65, density .60 | NOT_EXPRESSIBLE; A actions retained | UNSET |
| chorus_1 | FIRST_OCCURRENCE | CHORUS, energy .88, Accent event .95 | NOT_EXPRESSIBLE; A actions retained | UNSET |
| chorus_1 / accent_1 | FIRST_OCCURRENCE | Same section event occurrence | NOT_EXPRESSIBLE; A actions retained | UNSET |
| verse_2 | MUSICALLY_JUSTIFIED_DELTA | Second VERSE; available transition/repeat context | NOT_EXPRESSIBLE; A actions retained | UNSET |
| solo_1 | FIRST_OCCURRENCE | SOLO, energy .72; supplied note `Sax at stage left` | NOT_EXPRESSIBLE; A actions retained | UNSET |
| chorus_2 | MUSICALLY_JUSTIFIED_DELTA | Second CHORUS; available repeat/contour context | NOT_EXPRESSIBLE; A actions retained | UNSET |
| chorus_3 | MUSICALLY_JUSTIFIED_DELTA | Final CHORUS, energy 1.0, Accent event 1.0 | NOT_EXPRESSIBLE; A actions retained | UNSET |
| chorus_3 / accent_1 | MUSICALLY_JUSTIFIED_DELTA | Same final-section event occurrence | NOT_EXPRESSIBLE; A actions retained | UNSET |
| outro_1 | FIRST_OCCURRENCE | OUTRO, energy .30, density .20 | NOT_EXPRESSIBLE; A actions retained | UNSET |

The review trace resolves every entry by `CUE_ID`, `SECTION_INSTANCE_ID`, and
`CUE_OCCURRENCE_INDEX`, not label matching. Human review should judge B3's WHY
and desired strategy separately from its currently unrealized action delta.

## Safety and decision boundary

- Production Designer: `UNCHANGED`.
- Experimental Designer: `GUIDANCE_ASSISTED_AB_ONLY`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- MA2 objects modified: `NONE`.
- MA2 write audit: `ZERO_WRITES`.
- Human decision: `UNSET`.

## Next blocker and recommended step

The next bounded need is a human-reviewed, provenance-bearing mapping from the
real Existing Show's Groups/resources to the limited B3 role vocabulary — or a
separately verified capability resolver that can establish such mapping without
guessing. It must remain experimental and must not activate B3 in production.
