# ZEN Human Design Review 001

Status: `READY_FOR_HUMAN_INPUT`. This is a presentation/extraction package for
the existing deterministic A/B-003 evaluation. It does not grade the artistic
quality of B3 and does not change B3, the production Designer, or MA2.

## Method and Scope

The package re-runs `evaluate_ab003_case` and extracts the actual `baseline_plan`,
`b2_plan`, `b3_plan`, and `b3_trace` through
`zen_ma2_agent.human_design_review.extract_human_review_case`. No idealized
look was substituted. Cases A–H are the existing deterministic synthetic
mutations used by A/B-003; they remain `SYNTHETIC_EVALUATION_ONLY`.

Some sections produce two actual cues under the existing Designer contract.
The extractor retains both occurrences; where their data is identical this
document describes the section once and calls out the duplicate occurrence.

All action listings below are typed operations only. Group references and
preset references are the actual synthetic profile references in the evaluator;
they are not MA2 command strings.

## Audience-Perception Safety Classification

- `SUPPORTED_BY_INPUT`: the section role, repeat relationship, measured density,
  explicit events and the measured later peak used by Case H.
- `BOUNDED_INFERENCE`: every B3 `audience_perception_goal` (for example,
  “establish a coherent visual identity” or “reinforce recognizable DROP
  identity”). These are design inferences from the supplied structure, not
  claimed audience emotion.
- `TOO_SPECULATIVE`: none of the extracted goals makes an unsupported claim
  about loneliness, excitement, lyrics, vocal emotion or audience psychology.

## Human Review Cards

Every card ends with `HUMAN REVIEW: UNSET`; the questions are prompts, not
pre-filled answers.

### Case A — Repeated Drop with New Rhythmic Evidence

**SECTION / OCCURRENCE:** `drop_2` (both actual cue occurrences retained)

**ENERGY:** `0.98`; density `0.95`; accent `1.00`; two explicit events (`HIT`
and added `ACCENT`); notes: none.

**KNOWN SONG CONTEXT:** role `DROP`, measured high energy/density, two explicit
rhythmic events, repeated role after `drop_1`.

**NOT AVAILABLE:** instrumentation, arrangement texture beyond supplied notes,
harmony, vocal emotion, lyrics/semantic meaning, performer staging,
choreography, camera framing, venue visual response.

**PREVIOUS VISUAL STATE:** `PRIMARY_FOCUS`, `COLOR_FIELD`, `DENSITY_LAYER`,
`MOVER_TEXTURE_LAYER`, `TIMING_LAYER` from `drop_1`.

**UPCOMING CONTEXT:** next section `outro`; no later major peak is measured.

**DESIGN INTENT (actual):** audience goal is “Reinforce the recognizable DROP
identity unless available song context justifies a meaningful delta.”
Continuity/change: `DEVELOP`; relationship to previous occurrence:
`MUSICALLY_JUSTIFIED_REPEAT_DELTA`. Focus:
`PRESERVE_OR_REBALANCE`; palette: `COHERENT_CONTINUITY_OR_CONTEXTUAL_CHANGE`;
density: `ACTIVE_BY_MEASURED_DENSITY`; texture:
`CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT`; timing:
`RHYTHMIC_PUNCTUATION_CONTEXT`; negative space `CONTEXTUAL`; impact
`CONTEXTUAL_NOT_AUTOMATIC`; headroom `NO_KNOWN_LATER_PEAK_REQUIREMENT`.
Development: `MUSICALLY_JUSTIFIED_DELTA`, basis
`MORE_EXPLICIT_RHYTHMIC_EVENTS`. Intentional omissions: none.

**VISUAL STRATEGY:**

- KEEP: `PRIMARY_FOCUS`, `COLOR_FIELD`, `DENSITY_LAYER`,
  `MOVER_TEXTURE_LAYER`, `TIMING_LAYER`
- CHANGE: timing emphasis (`TIMING_LAYER` multiplier `1.00`)
- REDUCE: none
- OMIT: none
- SUBSTITUTE: none
- INTENTIONALLY UNCHANGED: focus, palette and existing high-role identity

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 1 -> 6.2`,
`SET_DIMMER Group 1 -> 97`; `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 97`; `SET_DIMMER Group 4 -> 95`,
`SET_DIMMER Group 3 -> 97`; `SET_DIMMER Group 5 -> 97`.

**A / B2 / B3:** A uses only Group 1 / preset 6.2 at level 97. B2 adds the
same five bound roles. B3 keeps the same semantic role set and levels; its
trace adds the explicit second-event rationale and changes typed action order
only (`TEXTURE` before `TIMING`).

**EVIDENCE TRACE:** SONG = section/event data; RIG = confirmed synthetic role
bindings; USER_STYLE = human-reviewed hierarchy, palette, musical alignment,
rhythmic sync, dynamic contour, restraint, arc, complete-look and bounded
impact/density signals; INDUSTRY = no action-level mapping claimed; OTHER =
experimental scope.

**HUMAN REVIEW QUESTIONS:** Does the extra event justify this timing emphasis?
Would a real designer change timing rather than brightness/effect count? Does
the repeated Drop still feel intentionally related? Are all five roles needed?
Does this read as HUMAN_LIKE, ACCEPTABLE_BUT_MECHANICAL, TOO_FORMULAIC, WRONG,
or NEED_REAL_SONG_CONTEXT?

HUMAN REVIEW: UNSET

### Case B — Repeated Drop with Matching Evidence

**SECTION / OCCURRENCE:** `drop_2` (two actual cue occurrences retained)

**ENERGY:** `0.94`; density `0.90`; accent `1.00`; one explicit `HIT`; notes:
none.

**KNOWN SONG CONTEXT:** same measured repeat evidence as `drop_1` after the
case normalization.

**NOT AVAILABLE:** instrumentation, arrangement texture, harmony, vocal
emotion, lyrics/semantic meaning, performer staging, choreography, camera
framing and venue visual response.

**PREVIOUS VISUAL STATE:** all five resource-rich roles from `drop_1`.

**UPCOMING CONTEXT:** `outro`; no later major peak is material.

**DESIGN INTENT (actual):** `INTENTIONAL_SIMILARITY`; relationship to previous
occurrence is `INTENTIONAL_SIMILARITY`; rationale:
“Available repeat context supports continuity over novelty.” Focus and palette
remain preserved, density is active by measured density, texture is justified
by the section accent, timing is rhythmically contextual, and impact is not
automatic. Intentional omissions: none.

**VISUAL STRATEGY:** KEEP all five roles; CHANGE none; REDUCE none; OMIT none;
SUBSTITUTE none; INTENTIONALLY UNCHANGED = recognizable Drop identity.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 1 -> 6.2`,
`SET_DIMMER Group 1 -> 94`; `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 94`; `SET_DIMMER Group 4 -> 89`,
`SET_DIMMER Group 3 -> 94`; `SET_DIMMER Group 5 -> 85`.

**A / B2 / B3:** A keeps only Group 1. B2 and B3 have the same role/action
composition for this case. B3 adds the conscious similarity rationale; no
variation was invented merely to make the repeat different.

**HUMAN REVIEW QUESTIONS:** Should this repeat remain this similar? Is the
continuity valuable, or does the real song require another kind of delta?

HUMAN REVIEW: UNSET

### Case C — Same-Energy Repeat with Contextual Change

**SECTION / OCCURRENCE:** `drop_2` (two actual cue occurrences retained)

**ENERGY:** `0.94`; density `0.90`; accent `1.00`; one `HIT`; supplied note:
`Sustained textural opening`.

**KNOWN SONG CONTEXT:** same energy as Case B, but the section note differs
from `drop_1`.

**PREVIOUS VISUAL STATE:** all five roles from `drop_1`.

**UPCOMING CONTEXT:** `outro`; no later major peak.

**DESIGN INTENT (actual):** `MUSICALLY_JUSTIFIED_REPEAT_DELTA`, basis
`SECTION_NOTES_CONTEXT_CHANGED`; texture dimension is
`CONTEXTUALLY_JUSTIFIED_BY_SECTION_NOTES_OR_ACCENT`; other focus/palette and
measured density dimensions remain coherent.

**VISUAL STRATEGY:** KEEP all five roles; CHANGE = contextual textural intent;
REDUCE none; OMIT none; SUBSTITUTE none; INTENTIONALLY UNCHANGED = focus,
palette and recognizable Drop relationship.

**TYPED ACTIONS (B3 actual):** same role/action levels as Case B.

**A / B2 / B3:** A remains the one-Group production look. B2 and B3 produce
the same typed action composition here; B3 makes the contextual delta visible
in Design Intent even though the available typed action set has no second
texture preset. This is an important limitation for review, not a hidden fix.

**HUMAN REVIEW QUESTIONS:** Is a textural change without an action-level
texture variant a credible design delta, or should this remain similar until a
real resource can express it?

HUMAN REVIEW: UNSET

### Case D — Quiet Atmosphere Without a Transient

**SECTION / OCCURRENCE:** `intro`

**ENERGY:** `0.22`; density `0.15`; accent `0.00`; zero events; note:
`Sustained atmospheric texture`.

**KNOWN SONG CONTEXT:** low-energy INTRO with supplied atmosphere/sustain note.

**PREVIOUS VISUAL STATE:** NONE / START OF SONG.

**UPCOMING CONTEXT:** next `build_1`; no later major peak rule is asserted.

**DESIGN INTENT (actual):** establish a coherent INTRO identity; palette remains
coherent, negative space is intentional, texture is justified by section notes,
density and timing are not required by current context, and headroom is not
claimed from a high-energy future peak.

**VISUAL STRATEGY:** KEEP `PRIMARY_FOCUS`, `COLOR_FIELD`,
`MOVER_TEXTURE_LAYER`; CHANGE = atmospheric texture layer; REDUCE none; OMIT
`DENSITY_LAYER`, `TIMING_LAYER`; SUBSTITUTE none; INTENTIONALLY UNCHANGED =
quiet focus and palette.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 1 -> 6.2`,
`SET_DIMMER Group 1 -> 33`; `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 33`; `SET_DIMMER Group 3 -> 33`.

**A / B2 / B3:** A uses Group 1 only. B2 omits texture for this input; B3
adds Group 3 from the supplied atmosphere note, despite no hit/accent.

**HUMAN REVIEW QUESTIONS:** Is atmosphere a sufficient reason for the texture
role here? Does the three-role low look preserve useful negative space?

HUMAN REVIEW: UNSET

### Case E — High Energy with Texture Omitted

**SECTION / OCCURRENCE:** `drop_1`

**ENERGY:** `0.94`; density `0.90`; accent `0.05`; zero events; no notes.

**KNOWN SONG CONTEXT:** high-energy Drop, but no supplied texture, rhythmic or
transient evidence.

**PREVIOUS VISUAL STATE:** `PRIMARY_FOCUS`, `COLOR_FIELD` from the intro/build
path.

**UPCOMING CONTEXT:** reset follows; no later major peak is material.

**DESIGN INTENT (actual):** establish a coherent Drop identity; density is
active by measured density, texture and timing are not required by current
context, and impact remains contextual rather than automatic.

**VISUAL STRATEGY:** KEEP `PRIMARY_FOCUS`, `COLOR_FIELD`, `DENSITY_LAYER`;
CHANGE = density/focus hierarchy; REDUCE none; OMIT `MOVER_TEXTURE_LAYER`,
`TIMING_LAYER`; SUBSTITUTE none; INTENTIONALLY UNCHANGED = coherent palette.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 1 -> 6.2`,
`SET_DIMMER Group 1 -> 90`; `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 90`; `SET_DIMMER Group 4 -> 86`.

**A / B2 / B3:** A is Group 1 only. B2 and B3 agree on omitting texture and
timing for this evidence set; B3 adds the explicit reason and review trace.

**HUMAN REVIEW QUESTIONS:** Is omitting texture a useful high-energy choice,
or does the real song provide unrepresented material that should change it?

HUMAN REVIEW: UNSET

### Case F — Low-Energy Rhythmic Timing

**SECTION / OCCURRENCE:** `intro`

**ENERGY:** `0.25`; density `0.20`; accent `0.10`; one explicit `ACCENT` at
strength `0.80`.

**KNOWN SONG CONTEXT:** low-energy intro with a strong explicit rhythmic event;
LED-only bindings are `COLOR_FIELD`, `DENSITY_LAYER`, `TIMING_LAYER`.

**PREVIOUS VISUAL STATE:** NONE / START OF SONG.

**UPCOMING CONTEXT:** next `build_1`; no later major peak is claimed.

**DESIGN INTENT (actual):** coherent INTRO identity; palette is coherent,
timing is `RHYTHMIC_PUNCTUATION_CONTEXT`, density is not required, negative
space remains intentional, and energy is not treated as layer count.

**VISUAL STRATEGY:** KEEP `COLOR_FIELD`, `TIMING_LAYER`; CHANGE = bounded
rhythmic punctuation; REDUCE none; OMIT `DENSITY_LAYER`; SUBSTITUTE none;
INTENTIONALLY UNCHANGED = palette/negative-space relationship.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 35`; `SET_DIMMER Group 5 -> 31`.

**A / B2 / B3:** A uses the production focus Group. B2 and B3 select the same
LED roles; B3 makes the reason and unknowns reviewable.

**HUMAN REVIEW QUESTIONS:** Does the explicit accent justify low-level timing?
Would the timing feel intentional rather than like an energy formula?

HUMAN REVIEW: UNSET

### Case G — High Sustained Section with Little Punctuation

**SECTION / OCCURRENCE:** `drop_1`

**ENERGY:** `0.94`; density `0.90`; accent `1.00`; zero events after the case
removes rhythmic punctuation.

**KNOWN SONG CONTEXT:** high-energy LED-only Drop with density evidence but no
explicit timing event.

**PREVIOUS VISUAL STATE:** `COLOR_FIELD` from the intro/build path.

**UPCOMING CONTEXT:** reset follows; no later major peak is material.

**DESIGN INTENT (actual):** density can carry the sustained high state while
timing is `NOT_REQUIRED_BY_CURRENT_CONTEXT`; palette remains coherent and no
mover/beam/geometry language is introduced.

**VISUAL STRATEGY:** KEEP `COLOR_FIELD`, `DENSITY_LAYER`; CHANGE = sustained
density relationship; REDUCE none; OMIT `TIMING_LAYER`; SUBSTITUTE none;
INTENTIONALLY UNCHANGED = LED palette.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 90`; `SET_DIMMER Group 4 -> 86`.

**A / B2 / B3:** A is the production Group 1 look. B2 and B3 agree that high
energy does not require timing here; B3 exposes the sustained-context reason.

**HUMAN REVIEW QUESTIONS:** Is this high state complete without timing? Does
color plus density provide enough composition for this actual song context?

HUMAN REVIEW: UNSET

### Case H — Earlier High State with Measured Future Headroom

**SECTION / OCCURRENCE:** `drop_1`

**ENERGY:** `0.80`; density `0.85`; the later `drop_2` is measured at energy
`0.98`, density `0.98`.

**KNOWN SONG CONTEXT:** high Drop followed by a materially stronger measured
Drop; this is the only case with `PRESERVE_FOR_KNOWN_LATER_PEAK`.

**PREVIOUS VISUAL STATE:** `PRIMARY_FOCUS`, `COLOR_FIELD`,
`MOVER_TEXTURE_LAYER` from the build.

**UPCOMING CONTEXT:** later major peak = `drop_2`; next section after this Drop
is `reset`.

**DESIGN INTENT (actual):** give the Drop a coherent identity while retaining
contrast for `drop_2`; density = `REDUCED_FOR_HEADROOM`, timing is not required,
negative space is intentional, impact is bounded by headroom.

**VISUAL STRATEGY:** KEEP `PRIMARY_FOCUS`, `COLOR_FIELD`,
`MOVER_TEXTURE_LAYER`; CHANGE = reserve density/impact contrast; REDUCE
`DENSITY_LAYER` to multiplier `0.45`; OMIT `TIMING_LAYER`; SUBSTITUTE none;
INTENTIONALLY UNCHANGED = focus, palette and texture identity.

**TYPED ACTIONS (B3 actual):** `CALL_PRESET Group 1 -> 6.2`,
`SET_DIMMER Group 1 -> 79`; `CALL_PRESET Group 2 -> 4.1`,
`SET_DIMMER Group 2 -> 79`; `SET_DIMMER Group 3 -> 79`;
`SET_DIMMER Group 4 -> 36`.

**RAW OUTPUT NOTE:** The current experimental plan appends reduced roles to its
`selected_roles` action list as well as to `reduced_roles`; the authoritative
interpretation here is `REDUCE DENSITY_LAYER`. This is surfaced, not repaired,
for human review.

**A / B2 / B3:** A uses Group 1 at level 79. B2 retains timing and full density
roles. B3 omits timing and reduces density because the later peak is actually
measured; this is not a global “save for final” rule.

**HUMAN REVIEW QUESTIONS:** Is this measured headroom distinction useful? Is
reducing density while keeping focus/palette/texture the right tradeoff, or
should another dimension carry the contrast?

HUMAN REVIEW: UNSET

## Compact Review Matrix

| Case / section | B3 design intent | Main visual change | Intentional omission | Previous-look relation | Future-headroom relation | Human review |
| --- | --- | --- | --- | --- | --- | --- |
| A / drop_2 | Develop repeat from extra rhythmic event | Timing emphasis | None | Delta from drop_1 | None material | UNSET |
| B / drop_2 | Preserve recognizable repeat | None beyond continuity | None | Intentional similarity | None material | UNSET |
| C / drop_2 | Develop same-energy repeat from textural note | Textural intent, no new typed variant | None | Contextual delta | None material | UNSET |
| D / intro | Quiet atmosphere is complete | Keep texture without hit | Density, timing | Start of song | Next build only | UNSET |
| E / drop_1 | High state without unsupported texture | Focus/color/density composition | Texture, timing | From intro/build | None material | UNSET |
| F / intro | Low state with rhythmic punctuation | Timing at low energy | Density | Start of song | Next build only | UNSET |
| G / drop_1 | Sustained high LED state | Color/density only | Timing | From prior LED state | None material | UNSET |
| H / drop_1 | Preserve contrast for measured later peak | Density reduction/headroom | Timing | Develop from build | Preserve for drop_2 | UNSET |

## Evidence and Capability Boundary

User Style evidence actually active in the B3 context is limited to the human
confirmed preferences (hierarchy, palette coherence, musical alignment,
rhythmic sync, dynamic contour, restraint, progressive arc, complete looks) and
the accepted-with-limitation high-impact/maximalism signals. Context-dependent
items (`DOMINANT_THEME_COLOR`, `STRONG_TRANSIENT_IMPACT`, `HIGH_SECTION_DELTA`,
`RESTRAINT_BETWEEN_PEAKS`, `CONTROLLED_BUILDUP`, `GEOMETRIC_COMPOSITION`) are not
used as fixed preferences. Rejected interpretations remain rejected.

Industry evidence is preserved as provenance in the surrounding guidance
context, but no verified action-level Industry mapping is claimed in these
cards. Rig evidence is the confirmed synthetic role binding; no real MA2
geometry or venue claim is made.

| Current Song/Performance input | Status |
| --- | --- |
| Section identity / boundaries | AVAILABLE |
| Energy, density, accent level | AVAILABLE |
| Explicit rhythmic events | AVAILABLE when supplied; otherwise NONE |
| Supplied section notes | PARTIAL (manual/context notes only) |
| Instrumentation change | NOT_AVAILABLE |
| Arrangement texture | PARTIAL only through supplied notes; not audio-understood |
| Harmony | NOT_AVAILABLE |
| Vocal emotion | NOT_AVAILABLE |
| Lyrics / semantic meaning | NOT_AVAILABLE |
| Performer staging | NOT_AVAILABLE |
| Choreography | NOT_AVAILABLE |
| Camera framing | NOT_AVAILABLE |
| Venue visual response | NOT_AVAILABLE |

## Technical Review Outcome

The extraction is deterministic, schema-backed and provenance-preserving. A/B
003 production behavior remains untouched, every new review field is unset, and
the package does not declare B3 artistically better or more human-like. The
correct next decision belongs to a human lighting designer reviewing the cards,
especially Case C's intent-without-new-action limitation and Case H's raw
`selected_roles`/`reduced_roles` presentation quirk.

Production Designer: `UNCHANGED`  
Experimental B3: `UNCHANGED`  
Guidance-Assisted production activation: `NOT_RUN`  
`ZEN_STYLE_PROFILE`: `DEFERRED`  
Real venue validation: `WAIT_FOR_REAL_CASE`  
MA2 objects modified: `NONE`  
MA2 write audit: `ZERO_WRITES`
