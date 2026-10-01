# Visual Director Artistic Brief 001

Status: **OWNER-APPROVED ARCHITECTURE DIRECTION / DESIGN CAPTURE ONLY**

Date: 2026-10-01

## Purpose

ZEN may use a visually strong provider, with Gemini as the current preferred
candidate, as an optional **Visual Director** whose job is to propose the
whole-song visual language and meaningful lighting moments before the Primary
Lighting Designer performs resource-aware realization.

This deliberately uses the provider where visual taste is valuable while
isolating it from MA2 identities, resource authority and execution details.

The role is provider-independent. Gemini is the current candidate, not a
permanent architectural dependency.

## Fixed authority split

```text
Song / audio / performance / reference evidence
        ↓
optional Visual Director
        ↓
artistic brief
        ↓
Primary Lighting Designer
        + verified Show / Spatial / Resource Map
        ↓
mechanism-level artistic realization
        ↓
ARTISTIC_CUES_V0_2 or its accepted successor
        ↓
ZEN Compiler / Resolver
        ↓
strict typed ShowPlan
        ↓
deterministic Builder
        ↓
Preview
        ↓
explicit Human Approval
        ↓
MA2
        ↓
native readback
```

The Visual Director is upstream artistic input. It is not a second Primary
Brain and not a permanent multi-agent committee.

## Visual Director owns

The Visual Director may reason about and propose:

- the whole-song visual thesis;
- scene/world progression across the arrangement;
- visual identity, continuity, contrast, development, callbacks and resets;
- meaningful lighting moments around musical or performance events;
- energy, restraint, hierarchy, density and negative space;
- color behavior and visual temperature;
- spatial character such as narrow, wide, centered, outward, deep or low;
- focus character such as vocal, silhouette, floor or full-stage;
- artistic mechanism ideas such as Beam, Position, Movement, Strobe, Blackout,
  Reveal or related lighting language when those ideas are part of the visual
  concept;
- deliberate non-use or withholding of a mechanism.

The Visual Director is allowed to think like a lighting designer. It is not
restricted to vague emotion words. Execution limitations must not become
artistic limitations.

## Visual Director does not own

The Visual Director must not choose or invent implementation-specific truth:

- Group IDs or exact Group identities;
- Fixture IDs or subfixture identities;
- Preset IDs or applicability;
- Effect IDs;
- exact Pan/Tilt values;
- Sequence or Cue numbers;
- Executor addresses;
- Patch, Address, Fixture identity or Fixture type;
- MA2 command syntax;
- Builder operations;
- approval;
- post-write truth.

The Visual Director should not receive the current Show Resource Map merely to
make its output executable. Resource-aware realization belongs to the Primary
Lighting Designer.

## Brief shape

The first validation phase should use an **artistic brief**, not a new permanent
production schema.

The brief should normally be created whole-song-first:

```text
1. VISUAL THESIS
2. SCENE / WORLD ARC
3. MEANINGFUL VISUAL EVENTS
4. RELATIONSHIPS BETWEEN EVENTS
5. WITHHELD / DELIBERATELY UNUSED MECHANISMS
```

A Visual Event is not automatically a Cue.

A high-density K-pop design may contain dozens of Visual Events, but the Visual
Director should not be told to manufacture an exact Cue count merely to hit a
number. The owner may provide a target density or approximate range, while the
model remains free to return fewer or more meaningful events when musically
justified.

One or more Visual Events may later become one Cue, multiple Cues, a Free Cue,
a transition behavior, or no separate Cue at all after Primary realization.

Example:

```text
EVENT: SECOND_CHORUS_ENTRY
intent: major spatial release
energy: HIGH
space: WIDE / OUT
focus: CENTER_STRONG
color_behavior: preserve existing world
accent: rare WHITE punctuation
relationship: substantially larger than first chorus without simple palette swap
```

The machine-relevant portion may use a small controlled vocabulary for a few
stable fields, while free-form rationale remains allowed. Do not force every
field to be populated and do not turn the vocabulary into a checklist.

## Vocabulary boundary

A useful test is:

> If the rig changes, does the concept still mean the same thing?

If yes, it is likely Visual-Director-level intent.

Examples:

```text
IMPACT
RESTRAINT
NEGATIVE_SPACE
EXPAND
CONTRACT
WIDE
NARROW
CENTERED
OUTWARD
COLD
WARM
RAW
CLEAN
AGGRESSIVE
FLOWING
STAGGERED
HOLD
RELEASE
```

Mechanism-level decisions begin when the design chooses how to produce that
effect on a real rig. The Primary Lighting Designer owns that realization.

No universal mapping such as:

```text
EXPAND -> Position Preset X
IMPACT -> Effect Y
```

may be encoded.

The same artistic intent may be realized differently on different rigs, songs,
sections or neighboring Cue contexts.

## Semantic preservation

The Primary may freely choose a different implementation mechanism when the
requested artistic effect is preserved.

For example, an `EXPAND` intent could be realized through Position, fixture
participation, Beam/Zoom, side-layer reveal, depth or an intentional
combination. That is not semantic substitution.

If the requested meaning cannot be preserved with verified current-Show
resources, the Primary must report the result as partial or unsupported rather
than silently replacing it with an unrelated available mechanism.

```text
artistic meaning preserved -> implementation may vary
artistic meaning not preserved -> report partial / unsupported
```

## Timing boundary

The Visual Director identifies semantic moments, not authoritative seconds.

Examples:

```text
SECOND_CHORUS_FIRST_HIT
DANCE_BREAK_ENTRY
FINAL_RELEASE
VOCAL_FOCUS_CHANGE
```

Exact `start_seconds` must come from evidence such as audio analysis,
waveform/beat analysis, cue sheets, operator input or the actual playback
timeline.

A Visual Director interpretation such as "this is the drop" is a hypothesis
until bound to timing evidence.

Unbound events remain `UNBOUND`; ZEN must not invent seconds.

This architecture does not modify the separately bounded Cue Timeline task.
The already-defined separation between `start_seconds`, `trigger_mode` and
`fade` remains intact. Any future optional `event_id` linkage is a later
explicit task after that timeline slice is accepted; it is not authorized by
this document.

## Whole-song coherence

Do not call the Visual Director independently per Cue by default.

The model should see enough of the whole song to establish a coherent visual
language before proposing individual events. Otherwise a sequence of individually
attractive moments can become a visually incoherent collage.

The brief should preserve reasoning about:

- motifs;
- callbacks;
- continuity;
- contrast;
- development;
- resets;
- negative space;
- withheld mechanisms;
- intentional repetition;
- the relationship between early and late peaks.

The goal is not maximum difference between events. The goal is a coherent song
identity with meaningful change at the right moments.

## Research evidence boundary

Reference research is separate from the artistic brief.

When a provider analyzes YouTube, video, images or external references, keep:

```text
OBSERVATION
what was actually observed

INTERPRETATION
what the provider believes it means

ARTISTIC ADAPTATION
how ZEN may reuse the principle
```

separate.

Unsupported interpretation must never become verified Show fact merely because
the provider states it confidently.

These research fields are not required inside the artistic brief itself.

## Interactive mode

When ChatGPT is the interactive Lead / Primary Lighting Designer:

```text
Human Owner
    ↓
ChatGPT Primary Lighting Designer
    ↕
optional Visual Director, currently Gemini-preferred
    ↓
one unified artistic plan
```

The Primary may adopt, modify, combine or reject Visual Director suggestions.
The Primary is not an approval rubber stamp.

## Unattended mode

The Visual Director remains optional.

A visually enhanced unattended run may use:

```text
Visual Director pre-analysis call
        ↓
one strong resource-aware Primary design call
```

This is not permission to restore a permanent Researcher -> Designer -> Critic
-> Finalizer chain.

The default one-primary-call design path remains valid when the Visual Director
is unavailable, unnecessary, out of quota or disabled.

Do not use the same model's "abstract pass" as evidence that its later
resource-aware output is correct. The deterministic Show/resource boundaries
remain unchanged regardless of provider identity.

## Validation before schema promotion

Do not create a permanent `zen.artistic_intent.v0.1` schema merely because
this architecture exists.

First run one or two representative songs through a bounded Visual Director
brief and compare:

- whether the final design materially improves;
- whether song-level coherence improves;
- whether event choices align with real musical/performance landmarks;
- whether the Primary actually makes useful independent realization decisions;
- whether the brief becomes repetitive or template-like;
- whether unsupported intent remains visible instead of being silently degraded.

Only then decide whether a compact machine schema is worth maintaining.

## Failure modes to watch

1. **Template collapse** — the same few abstract words appear on every song.
2. **Primary rubber-stamping** — the Primary stops exercising independent
   artistic judgment.
3. **Structural hallucination** — musical sections/events are invented from
   prior knowledge rather than evidence.
4. **Hidden semantic substitution** — unsupported intent is quietly replaced by
   whatever resource happens to exist.
5. **Premature implementation leakage** — the Visual Director begins inventing
   Group/Preset/Effect/MA details.
6. **Section collage** — individually attractive events fail to form one song
   identity.
7. **Cue-count gaming** — the model pads or deletes events to satisfy an
   arbitrary requested count.

## Unchanged safety and workflow boundaries

This decision does not authorize:

- production code changes;
- a new provider schema;
- a new permanent model stage;
- Task 002 changes;
- Timecode writes;
- Spatial writes;
- MA2 writes;
- Builder changes;
- raw provider-to-MA execution.

Preview, explicit Approval, deterministic Builder execution, protected-object
policy and native MA2 readback remain unchanged.

```text
VISUAL_DIRECTOR_CAN_BE_CREATIVE = YES
VISUAL_DIRECTOR_CAN_BE_WRONG = YES
VISUAL_DIRECTOR_CAN_TOUCH_MA_AUTHORITY = NO
PRIMARY_OWNS_RESOURCE_AWARE_ARTISTIC_REALIZATION = YES
ZEN_OWNS_DETERMINISTIC_EXECUTION = YES
```
