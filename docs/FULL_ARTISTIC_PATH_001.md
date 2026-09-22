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


## Artistic Resource Map

The current implementation uses `zen.artistic_resource_map.v0.1` as the
authoritative model-facing resource boundary.

It exists because these statements are not equivalent:

```text
Group is named BEAM
!= Group has verified Beam capability

Preset is COLOR
!= Preset is verified applicable to this Group

Effect ID exists in MA2
!= Effect is a verified artistic resource for this Group
```

The resource map is built from the current Show profile and may combine:

- exact Group membership from the current Show;
- exact Show-bound FixtureType capability profiles;
- explicit current-Show Preset applicability bindings;
- exact Agent-owned Effect catalog entries whose Show identity and current
  Effect label both still match;
- the separately verified Cue Effect application grammar.

Arbitrary rows returned by `List Effect` are never offered to the Lighting
Designer merely because they exist.

Preset resources are Group-eligible only when explicit binding evidence matches
the exact current Show identity. Preset type alone is insufficient.

The lean compact context carries this map so the primary model sees the actual
Group-specific toolbox instead of a flat dump of unrelated Presets and Effects.

The bounded SHEESH smoke runner now refreshes Group membership and FixtureType
capability evidence before building the resource map, then feeds only
Group-bound executable resources to the provider contract.


### Current Test Show evidence recovery

The fingerprinted SHEESH Test Show has one additional bounded evidence path.

`zen_ma2_agent/test_show_evidence.py` may recover Color Preset applicability
only for Group/Preset pairs that were actually present in the committed real
MA2 Build 001 plan, and only while the current Show still exposes the exact
Test Show Sequence identity and exact current Color Preset references/types/
labels from that build.

This does **not** generalize one observed Color call to every Group or every
Color. It reuses only observed pairs and binds them to the current scanned Show
identity.

Effect recovery has a similarly narrow fallback already recognized by the
Effect Resource Resolver: exact current Effect labels
`FX_DIM_CHASE_SLOW`, `FX_DIM_CHASE_MED`, and `FX_DIM_CHASE_FAST` may be
offered without a portable Agent catalog only when fresh MA2 inventory also
classifies that pool object as a native `TEMPLATE` Effect, the target Group has
Show-bound verified Dimmer capability, and the Cue Effect application grammar
is `REAL_MACHINE_VERIFIED`. A SELECTIVE Effect with the same label is not
reusable across Groups. Near-matching or arbitrary Effect names remain
unavailable.

The bounded Test Show resource-restoration mode may recreate the missing
4.101-4.113 Color palette and three Dimmer Chase template Effects without
touching geometry, existing Cues, Sequence 901, or its Executor. Every created
Effect is read back immediately; creation stops before additional Effects if
exact label + TEMPLATE-kind verification fails.

The first real resource-restore attempt created Effect 2500 but the generic
List Effect pool row did not expose enough information to prove TEMPLATE kind.
That is a readback limitation, not permission to trust the label. grandMA2's
authoritative distinction is the Effect-line QTY field: QTY=None means template,
while a numeric QTY means selective. ZEN therefore performs a bounded read-only
List Effect 1.<id>.* query only for the three reserved FX_DIM_CHASE_* labels and
promotes kind only from explicit QTY evidence. If QTY is absent, zero, mixed, or
otherwise ambiguous, the resource remains unavailable.

The current Test Show has another native quirk: its generic `List Preset All`
view can omit the Agent-created 4.101-4.113 Color rows. The smoke runner
therefore performs thirteen bounded read-only `List Preset 4.xxx` lookups
against the committed Build 001 palette manifest, accepts only exact label
matches, merges those verified rows into the scanned profile, and recomputes
the Show identity before deriving Group/Preset applicability. This is not a
general Preset-number sweep.

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
