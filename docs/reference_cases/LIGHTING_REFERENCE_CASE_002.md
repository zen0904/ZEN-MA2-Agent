# Lighting Reference Case 002

Status: SHADOW_ONLY / PROFESSIONAL_PRACTICE

## Provenance

This case is derived from a public YouTube walkthrough explicitly supplied by
the ZEN MA2 Agent project owner for analysis on 2026-09-30.

- Source: `YOUTUBE_SNOWMAN003_GRANDMA3_SHOWFILE_2026`
- Video ID: `sE5H_PPUS4c`
- Title: `Walkthrough my personal showfile | grandMA3`
- Publisher/channel: `Snowman 003`
- Published: 2026-09-14
- Duration: 32m19s
- Speaker description: Tom, a lighting programmer/operator based in Germany
- Source URL: https://youtu.be/sE5H_PPUS4c
- Analysis input: public video metadata plus accessible English captions
- Original media/transcript storage: NOT IN REPOSITORY

The repository retains only concise derived observations. This is one
programmer's self-documented busking showfile, not a universal grandMA3
workflow and not direct evidence for grandMA2 execution behavior.

## Source structure

The published chapter structure is:

| Time | Subject |
| --- | --- |
| 00:00 | Introduction |
| 01:24 | Dimmer FX |
| 06:36 | Color |
| 09:30 | Color FX |
| 13:18 | Position |
| 16:51 | Position FX |
| 19:56 | Gobo / Prism / Zoom |
| 22:32 | Bump |
| 24:21 | Chaser / extra bumps |
| 28:37 | Playbacks |
| 31:43 | Outro |

## Primary architectural finding

The highest-value observation is not the author's Layout. Across multiple pages,
the showfile repeatedly separates:

```text
TARGET
  Group / Groups
        ↓
ATTRIBUTE OR BEHAVIOR
  Dimmer / Color / Position / Zoom / movement-like behavior
        ↓
DISTRIBUTION
  Phase / direction / wings / blocks / shuffle / X-Y relationships
        ↓
TIMING
  Speed / fade / delay
        ↓
LAYER
  Base / Effect / Override / Bump
        ↓
TRIGGER
  prepare / fire / hold / release
```

This suggests a reusable design abstraction:

```text
WHAT CHANGES
!=
HOW FIXTURES ARE DISTRIBUTED
!=
WHEN THE STATE IS COMMITTED
```

For ZEN, the useful lesson is the separation itself. The author's exact buttons,
pages, priorities, preset numbers, group count and custom macros are not
portable rules.

## 1. Prepare versus commit

The author's firing system allows a look to be prepared before Fire applies it
to live output. A visible blind/live state communicates whether edits are
staged or immediately live.

ZEN already has a stronger safety boundary:

```text
artistic intent
→ compile
→ Preview
→ explicit human Approval
→ deterministic Builder
→ native readback
```

Therefore this case reinforces prepared-intent versus committed-output
separation, but does not justify a new ZEN Fire control or any bypass around
Preview/Approval.

## 2. Distribution as a reusable layer

Dimmer, Color, Position and other pages reuse a similar family of controls:
Phase, direction/reverse, wings, blocks, shuffle, speed, and X/Y-related
distribution.

The useful generalized interpretation is:

```text
BEHAVIOR
+ ATTRIBUTE SCOPE
+ SPATIAL / SELECTION DISTRIBUTION
+ TIMING CHARACTER
```

rather than a large ontology of separately named fixed effects such as
`DIM_CHASE_LEFT`, `COLOR_CHASE_LEFT`, and `POSITION_CHASE_LEFT`.

Pool objects remain implementation resources. They should not become the
artistic ontology merely because they exist.

## 3. Spatial order can serve more than Position

The author describes frequent use of X/Y grid organization, including diagonal
behavior. The case therefore provides professional-practice evidence that a
trusted spatial ordering model can be useful for:

- Dimmer modulation;
- Color progression or gradient;
- Strobe distribution;
- Zoom or beam modulation;
- Movement / Position phase;
- transient event or bump behavior.

For ZEN, this is conditional on authoritative geometry and stage-frame
semantics. Fixture IDs, labels, or unverified coordinates are not substitutes
for a real spatial model.

A key architecture distinction follows:

```text
SPATIAL MODEL
→ derive an artistic order
→ resolver chooses implementation

DERIVED ARTISTIC ORDER
!=
mandatory persistent Group rewrite
```

The ordinary geometry-derived Group order should remain stable and readable.
Additional center-out, diagonal, radial or other orders may be virtual or
materialized only when the native implementation and lifecycle justify it.

## 4. Axis-preserving Position

The author's Position system separates Pan-oriented and Tilt-oriented controls
because he may want to change one axis without disturbing the other.

This is a useful artistic distinction:

```text
FULL_POSITION_REPLACEMENT
vs
PAN_ONLY
vs
TILT_ONLY
vs
PRESERVE_OTHER_AXIS
```

For current ZEN, this is artistic vocabulary only. Existing grandMA2 Position
execution remains bounded by verified Preset/application and raw Pan/Tilt
evidence. This reference does not authorize a generic axis-scoped write path.

## 5. Static gradient and modulation share structure

The Color FX workflow can reduce temporal speed while retaining phase/spatial
distribution, producing a static gradient-like result from the same underlying
relationship.

The useful idea is not to force gradients through an Effect engine. It is that
temporal modulation and static spatial variation can share a higher-level
description:

```text
VALUE RELATIONSHIP
+ FIXTURE DISTRIBUTION
+ temporal rate
```

A zero/static temporal rate may resolve differently from an animated rate on
grandMA2 versus grandMA3. Console-specific realization belongs below the
artistic layer.

## 6. Event / Bump as a separate layer

The Bump workflow combines:

- target Group;
- transient behavior;
- optional attribute scope;
- attack / immediate behavior;
- release or fade-off behavior.

This is relevant to ZEN's existing distinction between sustained Scene World
and Event Layer, and to future Free Cue modeling.

A useful future intent shape may include:

```text
event behavior
target
attribute scope
spatial distribution
attack
release
priority
output ceiling
```

This does not require manual bumps, and it does not imply every song needs
Free Cues. Timecode, trigger and manual operation may realize the same artistic
event differently.

## 7. Family-level masters

The author exposes effect-output and speed-oriented masters so the operator can
scale an existing family of behavior without rebuilding it.

This is retained only as a workflow option. Creating or changing Masters,
Executor layout, or playback placement would materially affect the operator
surface and therefore remains subject to the Stable Operator Contract and
explicit owner approval.

## 8. Layer priority

The walkthrough demonstrates practical separation between sustained base
choices, effect layers, higher-priority color/override behavior, and transient
bumps.

The generalizable design concept is:

```text
SCENE LAYER
  sustained visual world

EFFECT / MODULATION LAYER
  ongoing change

EVENT LAYER
  short structural or musical punctuation

OPERATOR INTERVENTION
  live temporary control when the production wants it
```

These are conceptual layers, not mandatory MA priority numbers.

## 9. What ZEN must not copy

Do not promote any of the following from this single case:

- the exact Layout or page count;
- the author's group count;
- the author's custom preset slots;
- specific effect recipes;
- permanent use of random, strobe, movement, rainbow or chaos;
- a rule that every attribute needs a separate busking page;
- a rule that every live show needs bump masters or a firing UI;
- grandMA3 Phaser/Grid implementation details as grandMA2 execution facts.

The source demonstrates one effective personal workflow. It does not prove
universality.

## ZEN integration boundary

Retain as shadow knowledge:

1. separate behavior/content from spatial distribution;
2. allow trusted Spatial state to derive reusable artistic orders;
3. preserve the possibility of axis-scoped Position intent;
4. keep Scene / Effect / Event concepts distinct;
5. model transient event behavior independently of a fixed pool ID;
6. keep family-level live scaling as an optional operator-approved workflow;
7. keep console implementation below the artistic ontology.

Current execution authority is unchanged:

```text
LLM / Primary Designer
→ artistic intent only
→ ZEN Compiler / Resolver
→ strict typed plan
→ Preview
→ explicit Approval
→ deterministic Builder
→ native readback
```

MA2 writes from this learning task: 0.
MA3 writes from this learning task: 0.
Operator Workflow change: NONE.
