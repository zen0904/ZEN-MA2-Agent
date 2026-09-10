# ZEN Shadow Advisory Evaluation 001

Status: `SHADOW_ONLY / LOCAL_ONLY`. No MA2, Telnet, plugin, Builder, Resolver,
or production Designer path was invoked.

## Methodology

The existing deterministic `FirstSongDesigner` was run once as baseline and
once through `run_shadow_designer` for every evaluation input. The baseline
and shadow `actual_show_plan` values were compared structurally. Guidance only
produced a separate advisory envelope.

Existing `examples/REALISTIC_SONG_ANALYSIS.json` was reused as a baseline
control. The repository did not contain five sufficiently diverse structures,
so five new inputs in
`tests/fixtures/shadow_advisory_evaluation_001.json` are explicitly labelled
`SYNTHETIC_EVALUATION_ONLY`. They describe abstract musical form and do not
imitate a copyrighted artist or arrangement.

All cases use bounded `TRAINING_CASE_001`. Its unverified geometry state is
retained as a case constraint, not repaired or inferred.

## Rubric

Each case is assessed independently: musical-structure understanding,
energy-arc coherence, complete-look reasoning, hierarchy, palette, restraint
and impact judgment, repeated-section development, context/resource awareness,
evidence traceability, conflict handling, non-formulaic reasoning, and
actionable design value. There is intentionally no weighted total.

`STRONG` means traceable evidence and case-specific advisory support;
`ACCEPTABLE` means the model correctly exposes a limitation but cannot yet
resolve it; `WEAK` and `FAIL` remain visible rather than being averaged away.

## Shared evidence boundary

Active human-reviewed signals are clean hierarchy, palette coherence, musical
structure/rhythm/dynamics alignment, multi-level energy, intentional restraint,
progressive energy arc, complete energy states (`HIGH` priority), and bounded
controlled impact/maximalism. Context-dependent candidates remain excluded:
dominant theme color, unusually strong transient impact, high section delta,
between-peak restraint, controlled buildup, and geometric composition.

The rejected/non-global interpretations stayed explicit in every case:
`HIGH_IMPACT_ALWAYS`, `MAXIMALISM_EQUALS_CLUTTER`,
`MULTICOLOR_EQUALS_BAD`, `MINIMALISM_EQUALS_LOW_PREFERENCE`, and
`KPOP_YG_EQUALS_GLOBAL_STYLE_RULE`.

Industry Pack 001/002 evidence remained separate and review-state-bound. It
was never promoted into a universal rule or used to override the song/case.

## Case A — High-energy contemporary pop

Energy map: `INTRO LOW -> VERSE_1 MEDIUM -> PRE_1 MEDIUM -> CHORUS_1 HIGH ->
VERSE_2 MEDIUM -> CHORUS_2 HIGH -> BREAK LOW -> FINAL_CHORUS HIGH -> OUTRO LOW`.

The advisory identifies multiple peaks, repeated chorus development, a reset,
and specific accent/hit opportunities. It recommends complete low/high looks,
section identity with hierarchy/palette coherence, bounded rhythmic
punctuation, and an intentional relationship between repeated choruses. It
does **not** ask for constant maximum output, a mandatory dominant color, or
automatic maximum density.

Relevant sources: `SONG`, `CASE`, `USER_STYLE`, `INDUSTRY` as a separately
reviewable evidence trace. Relevant user signals include complete energy
states, progressive arc, hierarchy, palette, rhythmic sync, and controlled
impact. Bounded/not-applied signals include dominant color, strong transient
impact, section delta, between-peak restraint, controlled buildup, and
geometry.

Conflict: `CONTEXT_OVERRIDES_STYLE` records that geometry-specific choices are
not available in the current case. Result: all reasoning dimensions `STRONG`
except resource awareness/actionable value `ACCEPTABLE`.

## Case B — Medium-energy Verse / Chorus

Energy map: `INTRO LOW -> VERSE_1 MEDIUM -> CHORUS_1 MEDIUM -> VERSE_2 MEDIUM
-> CHORUS_2 HIGH -> BRIDGE MEDIUM -> OUTRO LOW`.

The advisory treats the verse/chorus map as intentional structure without
requiring a giant first-chorus delta. It retains repeated-section development
as a relationship rather than an automatic escalation, and asks for complete
energy states rather than a simple intensity ramp. No rhythmic punctuation
advisory is generated because this input has no accent/hit events.

This demonstrates that a Chorus need not always be “larger”; progression may
be moderate and delayed. Result: `STRONG` structure, arc, complete-look,
hierarchy/palette, repeat, traceability, conflict, and non-formulaic reasoning;
resource/actionability remain `ACCEPTABLE`.

## Case C — Restrained / minimal

Energy map: `INTRO LOW -> VERSE_1 LOW -> REFRAIN_1 MEDIUM -> VERSE_2 LOW ->
REFRAIN_2 MEDIUM -> INSTRUMENTAL LOW -> OUTRO LOW`.

The advisory accepts extended low-energy passages as complete visual states and
does not create an effect or high-impact recommendation. It explicitly frames
low sections as a different composition, not a high look with a lower Dimmer.
Repeated refrains remain related without forced escalation.

This passes the critical minimalism tests: low energy is not incomplete, no
maximal density is required, and minimalism is not treated as a low preference.
Weakness: the current wording does not yet give a rich, role-specific negative
space or layer-removal alternative; it remains an abstract complete-look
recommendation. Result: same `STRONG` core traceability/reasoning dimensions,
with actionable value `ACCEPTABLE` rather than `STRONG`.

## Case D — Buildup / Drop

Energy map: `INTRO LOW -> BUILD_1 MEDIUM -> DROP_1 HIGH -> RESET LOW ->
BUILD_2 MEDIUM -> DROP_2 HIGH -> OUTRO LOW`.

The advisory keeps `BUILDUP_RELEASE` distinct from `RHYTHMIC_ACCENT`: builds
and resets derive from sections/dynamic contour, while the two drop hits become
bounded punctuation candidates. It expressly says that every event is not a
mandatory maximum-impact moment. It does not convert `CONTROLLED_BUILDUP` or
`STRONG_TRANSIENT_IMPACT` into fixed Zen rules, and does not require adding
fixture groups during each buildup.

This is the strongest current result because the evidence chain is inspectable
across section form, dynamic contour, hit events, complete looks, repeated
development, and a reset. Resource/geometry remains only `ACCEPTABLE`.

## Case E — Irregular / non-linear

Energy map: `OPENING MEDIUM -> PEAK_A HIGH -> FALL MEDIUM -> PLATEAU MEDIUM ->
DELAYED_BUILD MEDIUM -> PEAK_B HIGH -> AFTERGLOW MEDIUM -> OUTRO LOW`.

The energy sequence is deliberately non-monotonic. The advisory preserves a
coherent whole-song arc while allowing peak, fall, plateau, delayed build,
second peak, and release. It includes the explicit limitation: this is not a
prescribed energy curve. Accent events are bounded punctuation candidates, not
instructions to make both peaks identical or maximal.

This passes the negative test against a fixed `A -> B -> C` model. Result:
`STRONG` non-formulaic reasoning and core evidence dimensions; resource and
actionability remain `ACCEPTABLE`.

## Complete-look comparison

Case A’s `INTRO/BREAK/OUTRO` versus `CHORUS_1/CHORUS_2/FINAL_CHORUS`, and Case
C’s extended low passages versus its restrained refrains, are both represented
as distinct visual compositions. The advisory permits differences in active
layers, focus, hierarchy, density, palette behaviour, negative space, movement
and effect use where the song/case supports them. It emits none of those as MA2
programming decisions.

## Negative-test result

No generic-prose failure was detected: every case includes actual section
signal references, and the complete-look recommendation names its low/high
sections. No rejected interpretation was reintroduced. No context-dependent
candidate was promoted. No requirement appeared for a dominant color, geometry,
large chorus delta, universal buildup, universal drop, or universal maximalism.

## Baseline preservation and limitations

All five synthetic cases and the reused realistic control produced baseline vs
shadow `ZEN_SHOW_PLAN: IDENTICAL`. The only new material is advisory trace data.

Current limitations:

- advisories are still deterministic high-level intentions, not alternative
  look compositions;
- only Training Case 001 was exercised, so limited, LED-only, asymmetric, and
  real-geometry resource contexts remain untested;
- industry evidence remains independently review-gated;
- no human lighting-designer review has yet judged these advisory outputs;
- no Guidance-Assisted Designer A/B experiment has occurred.

## Readiness

`NEEDS_MORE_SHADOW_WORK`.

The reasoning is song-specific, traceable, non-formulaic, context-aware, and
free of prohibited global assumptions. It is not yet sufficiently concrete or
cross-rig reviewed to justify a Guidance-Assisted Designer A/B activation.
