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
Show-bound verified Dimmer capability, and the Cue Effect application
capability is `REAL_MACHINE_CONTENT_VERIFIED` for the exact
`AT_EFFECT_POOL_CALL` grammar. A SELECTIVE Effect with the same label is not
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


Template Effect exposure also needs target Dimmer evidence. FixtureType DIMMER
profiles remain the preferred technical proof, but this Test Show has a second
bounded path: Build 001 successfully used SET_DIMMER on all seven Groups. ZEN
may recover that Group-level application evidence only when Sequence 901 still
matches the owned Test Show identity and the current Group member set exactly
matches the historical eight fixtures for that Group. Selection order may
change without invalidating capability evidence; the current order is preserved
as runtime context because it affects chase appearance, not Dimmer existence.
This evidence unlocks reusable native TEMPLATE Dimmer Chase resources without
pretending it is a universal FixtureType capability.

### Verified Cue Effect storage grammar

The historical direct `Effect <id>` call is not an accepted production
grammar. Its command-success evidence was downgraded after Sequence 5 content
readback contained no expected Effect references.

A bounded real-machine POC later created a new Agent-owned Effect 2 and proved:

```text
Group 1
At Effect 2
Store Cue 1 Sequence 6 ...
```

Fresh Sequence Export readback contained the expected Effect identity for every
current Group 1 member. The resulting `CueEffectApplicationCapability` is
`REAL_MACHINE_CONTENT_VERIFIED`, grammar `AT_EFFECT_POOL_CALL`, bound to
Sequence Export SHA-256
`2801690a2c512bd0fc5ba1930aef4cc2538090357e6b086519619beecaab4cbd`.

The production Builder now emits the same `At Effect <id>` grammar and remains
fail-closed if that capability is absent or downgraded.

### Repeated-song Sequence ownership labels

A repeated smoke/A-B build of the same song may encounter an earlier
Agent-owned Sequence label such as `ZEN_AI_TEST_SHEESH`. That collision is
operational metadata, not an artistic-plan failure and does not justify another
Lighting Designer call.

The Builder now preserves the base label for the first build and, when that
base label already belongs to another scanned Sequence, deterministically uses
a Sequence-scoped label such as `ZEN_AI_TEST_SHEESH_SEQ3` for the newly
allocated Sequence. If that label is also occupied, ZEN appends the next unique
suffix instead of stopping the operator. Existing Sequences are never renamed
or overwritten.

## Operational self-heal and front-first allocation

Safety constrains consequences, not problem-solving.

For a new ZEN-owned object, a high numeric ID is not considered safer. ZEN
first reads the current pool, starts at the front, skips every occupied or
protected slot, and uses the first safe free slot. This policy is shared by
Sequence/Executor/Effect allocation and the disposable-test helpers for Color
Presets, Groups and Timecodes.

Examples:

```text
Sequence 1 occupied
Sequence 2 occupied
Sequence 3 free
=> create Sequence 3

Executor 2.001 occupied
Executor 2.002 occupied
Executor 2.003 free
=> use Executor 2.003
```

Ordinary operational problems are self-healed rather than escalated:

- occupied IDs advance to the next free ID;
- repeated Agent-owned labels receive a deterministic unique suffix;
- duplicate exact verified semantic Effects reuse the lowest verified ID;
- stale runtime state is refreshed;
- a canonical ShowPlan that already passed compilation is resumed after a
  backend failure instead of replaying provider output or artistic compilation.

A canonical retry may change only ZEN-owned operational metadata such as a new
Sequence/Executor allocation. It refreshes the exact current Preset/Effect
objects referenced by the frozen plan. If an object is actually missing, the
runtime reports that concrete resource loss; it does not silently substitute
art or recall a provider for a metadata problem.

Hard stops remain for destructive boundaries: Patch/Address, Fixture identity
or type, Fixture 9999, foreign/production object overwrite, arbitrary raw
MA2/Telnet/Lua, unauthorized deletion and paid-provider use.

A genuine artistic-resource mismatch may use the one bounded Designer delta
already allowed by Design Mode. Backend collisions do not consume that budget.

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

## Current real-machine retry status

`ZEN_FULL_ARTISTIC_PATH_RUNTIME_RESUME_001.md` closes the saved post-write
retry failure on the disposable Test Show. Latest main recovered the existing
Sequence 5 / Executor 2.004 / six-Cue build before any new allocation, verified
the current identities of Effects 2500-2502 and the exact referenced Color
Presets, and completed with zero new provider calls, zero artistic compile
replay, zero Builder replay and zero MA2 writes.

This verifies backend self-heal and exact referenced-resource refresh. It does
not upgrade Cue attribute content to VERIFIED. Cue labels/fades and object
identity are metadata/readback evidence; stored Cue Dimmer/Preset/Effect content
remains a separate next gate.

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

### Production Builder preview-only gate

The current production Builder can be exercised against fresh real-machine
read-only state without crossing the approval boundary. The smoke runner now
supports --preview-only, which:

- resumes a previously compiled canonical ShowPlan without a provider call,
- refreshes referenced current-Show resources,
- allocates the next safe disposable Sequence and Executor,
- generates the exact show.builder command plan,
- queues the ActionPlan,
- returns before approve_action,
- performs zero MA2 writes and does not run cleanup writes.

The current Test Show preview allocated Sequence 7 / Executor 2.005 with label
ZEN_AI_TEST_SHEESH_SEQ7, six Cues, seven Groups, seven Color Presets, and
seven Effect calls. All Effect commands use the content-verified
At Effect <id> grammar. The preview contains 149 commands total and remains
behind the normal owner approval gate.

### Strict full-build post-write acceptance

The bounded full-artistic acceptance harness now treats Cue-content readback as
mandatory. A real build is `SUCCESS` only when AgentCore returns all three:

- exact Sequence/Cue metadata verification,
- exact Executor assignment verification when an Executor is requested,
- `Cue-content verification: VERIFIED` backed by a fresh Sequence Export SHA-256.

`PARTIAL` readback is not promoted to success by the harness. It is recorded as
`FAILED_POSTWRITE_VERIFICATION`. The saved result preserves the exact approved
Preview metadata, so a later retry enters post-write recovery and re-runs
metadata/resource/Cue-content readback against the already-written Sequence
without replaying Builder writes or calling a provider.

The read-only production Preview remains Sequence 7 / Executor 2.005, six Cues,
149 commands, seven `At Effect` calls, zero provider calls, and zero MA2 writes.

### Sequence 7 full-build mismatch and Programmer ordering correction

Owner-approved production Builder execution created Sequence 7 / Executor 2.005
and exact metadata readback verified all six Cue labels and fades. Fresh Sequence
Export then found exactly one content mismatch: Cue 5 `SHEESH_IMPACT`, Group 7,
`CALL_PRESET 4.112`. All eight Group 7 fixtures (701-708, Atomic 3000 LED Extended)
stored `DIM=100` but no Preset identity for 4.112. Every other approved action in
Sequence 7 verified.

This is not a Preset applicability failure. Read-only replay of the committed
Sequence 901 Test Show plan against fresh Sequence 901 export verified every action,
including Group 7 / Preset 4.112 in Cues 6 and 14. Those successful rows contain
`COLORRGB1/2/3=100` linked to Preset No components `1.4.112` for all fixtures 701-708.

The production Builder has therefore been narrowed to a Programmer-order correction:
verified COLOR Preset calls are emitted before remaining Cue actions while the
canonical typed ShowPlan and original action indexes remain unchanged. This mirrors
the content-verified Sequence 901 ordering and does not change artistic intent.

A new read-only production Preview allocated Sequence 8 / Executor 2.006, six Cues,
149 commands, and the same seven `At Effect` calls. Cue 5 now emits all 4.112 Color
Preset calls before its Dimmer commands. Provider calls and MA2 writes were both zero.

Post-write recovery was also hardened: a saved Cue-content mismatch with an exact
owned Preview now re-verifies the existing Sequence before any allocation. A real
read-only retry of the Sequence 7 failure reproduced the same mismatch with
`write_execution_attempted=false` and zero new writes, proving no duplicate Sequence
is created by recovery.

### Sequence 8 failure and exact Group subfixture root cause

The owner-approved repaired Full Build was revalidated byte-for-byte against the
approved Preview before execution. Sequence 8 / Executor 2.006 used the same
149 commands and the command-list SHA-256
`334e8f13932e08da781cfeb1fc81eb56fb81c966758b2e0a9954ddde0a1ac47f`.
The build again failed strict Cue-content verification at exactly Cue 5,
Group 7, `CALL_PRESET 4.112`.

This real-machine result disproves the prior Color-before-Dimmer hypothesis:
Sequence 8 emitted all Cue 5 Color Preset calls before direct Dimmer values, yet
Group 7 still exported only eight DIM rows and no COLORRGB rows.

Read-only Sequence Export comparison identified the actual identity difference:

- successful historical Sequence 901 Cue 6 / Cue 14 stores Group 7 DIM and
  COLORRGB1/2/3 on `subfixture_id=2` for Fixtures 701-708;
- failed Sequence 8 Cue 5 stores Group 7 DIM on the parent
  (`subfixture_id=null`) and contains no Group 7 COLORRGB rows;
- a fresh read-only raw Export Group 7 shows the current Group members are
  `701.1, 702.1, 703.1, 704.1, 705.1, 708.1, 706.1, 707.1`.

The prior normal-Group reorder evidence records Group 7 as the only Group
rewritten in the first Phase A pass. The old Group export parser retained only
`fix_id`, discarding `sub_index`, and the reorder path synthesized the
minimum discovered instance for multi-instance fixtures. That made a change
from one subfixture instance to another invisible to membership verification.

The Group state model now preserves both backward-compatible root Fixture IDs
and exact serialized member references such as `701.2`. Group-order writes
must preserve those exact references and may no longer infer a subfixture from
geometry inventory. The production Builder also returned to canonical typed
action order because the global Color-before-Dimmer rewrite is not supported by
real-machine evidence.

No Group repair has been executed. Changing Group 7 from the current exact
`.1` membership to a different subfixture identity is a separate consequential
write and requires a new explicit owner approval.
