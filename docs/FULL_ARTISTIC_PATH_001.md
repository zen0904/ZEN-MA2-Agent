# FULL_ARTISTIC_PATH_001

Status: ACTIVE MAINLINE

## Purpose

Restore full artistic expression without undoing the lean single-designer
architecture.

The regression to six-cue dimmer/preset-only output happened because execution
limitations leaked upward into the artistic contract. This gate separates those
layers again.

## Fixed architecture

```text
Current Show / Knowledge / Cache
        ↓
Capability + Resource Map
        ↓
ONE Lighting Designer
        ↓
full artistic intent
        ↓
Resource Resolver / Compiler
        ↓
strict typed ShowPlan
        ↓
deterministic MA2 Builder
        ↓
MA2
        ↓
readback
```

The LLM owns artistic choices. ZEN owns operational representation and resource
eligibility. The Builder owns native MA2 execution.

## Artistic vocabulary

The artistic layer must be able to reason about all normal lighting dimensions,
even when a particular Show cannot execute every dimension yet:

```text
DIMMER
COLOR
POSITION
FOCUS
BEAM
GOBO
PRISM
ZOOM
FROST
EFFECT
MOVEMENT
STROBE
```

Unsupported dimensions are reported as unsupported for the current Show. They
must never be silently deleted, substituted, clamped into another artistic
meaning, or converted into raw MA2 command text.

## Current executable resource forms

ARTISTIC_CUES_V0_2 currently compiles these verified forms:

- direct typed Dimmer level;
- generic verified Preset reference;
- verified COLOR Preset;
- verified POSITION Preset;
- verified FOCUS Preset;
- verified BEAM Preset;
- verified GOBO Preset;
- verified Effect ID.

A dimension-specific Preset requires verified Preset type metadata. Effect calls
require a verified current-Show Effect identity; the Builder still requires its
existing real-machine Effect-call capability before execution.

Preset and Effect are implementation resources, not the artistic ontology.

## Smoke test versus product design

`scripts/run_sheesh_programming_test.py` is a six-cue bounded smoke test only.
Its cue count and SHEESH labels are not product defaults.

The normal Design Mode remains song-agnostic and must not inherit the smoke
test's cue-count policy.

The smoke test may use ARTISTIC_CUES_V0_2 to prove verified Preset/Effect
resource flow, but it is not evidence that a six-cue design is artistically
complete.

## Lean context

Compact Design Mode context must include verified Groups, Presets, Effects,
capability summaries and accepted spatial/design context without copying the raw
Show dump.

Delta revision must never guess Cue 1 when a request cannot be localized.
If cue/label matching fails, use the bounded accepted plan so the single model
revision call can identify the affected region.

## Historical paths

The old deterministic FirstSongDesigner and the historical multi-agent design
pipeline remain regression/research paths. They are not the ordinary product
designer.

Old resource reports remain evidence for their captured fingerprint/time only.
A stale report such as "no Color Preset exists" must not override fresher
current-Show state or later Test Show provisioning.

## Safety retained

Do not weaken:

- Fixture 9999 protection;
- Patch / Address / Fixture identity/type boundaries;
- protected object rules;
- no raw LLM -> MA2/Telnet/Lua;
- verified Group/Preset/Effect identity;
- typed Builder only;
- preview/approval where required;
- deterministic readback;
- fail closed on unsupported artistic resources.

## Acceptance direction

The next real full-design proof should demonstrate that the designer can use
the current verified artistic resources rather than only switch Groups on/off.
The report must distinguish:

```text
OBJECT/METADATA_READBACK
CUE_CONTENT_READBACK
PARTIAL / VERIFIED / UNSUPPORTED
```

A generic `READBACK_VERIFICATION=PASS` is insufficient when Cue attribute
content is not actually readable.
