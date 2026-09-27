# EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001

Date: 2026-09-27 (Taiwan)

Status: `OFFLINE_CONVERGED_V0_2_HARDENED_AWAITING_FRESH_LIVE_PREVIEW`

## Goal

Close the implementation gap between the documented full artistic workflow and the actual deterministic existing-Cue compiler. The target workflow is:

Current Show / FixtureType / Geometry / Preset / Effect evidence
-> one Lighting Designer
-> per-Cue artistic capability selection
-> strict typed ShowPlan
-> existing Sequence/Cue deterministic Preset + Effect + Position merge
-> explicit owner approval
-> native Sequence Export verification.

This work does **not** make Prism/Gobo/Zoom/Frost/etc mandatory. It makes those capability families visible to the Designer with a strict boundary between technical availability and executable MA2 authority.

## Capability vocabulary

The shared artistic vocabulary now includes:

- DIMMER
- COLOR
- POSITION / MOVEMENT
- FOCUS
- BEAM
- GOBO / GOBO_ROTATION
- PRISM / PRISM_ROTATION
- ZOOM
- FROST
- IRIS
- SHUTTER / STROBE
- EFFECT

FixtureType capability discovery now includes BEAM, GOBO_ROTATION, PRISM_ROTATION and IRIS in addition to the previously available families.

A capability may be `SHOW_BOUND_VERIFIED` technically while still having `NO_VERIFIED_RESOURCE` for execution. In that state the Designer may reason about it through `capability_intent`, but the compiler generates **no raw Attribute command** and performs no silent substitution.

### v0.2 full-fixture execution boundary

The Dynamic Program path now also executes existing Group-bound Presets for the already typed ShowPlan families `COLOR`, `FOCUS`, `BEAM`, and `GOBO` when all of the following are fresh and verified:

- exact current-Show Preset identity/type/label;
- exact Group application binding;
- every selected fixture's current FixtureType/function profile; and
- a non-empty common affected-attribute set for that Preset family.

The planner still treats Prism, Gobo, Strobe, and every other family as optional artistic tools. A technical capability without a verified executable resource remains Preview intent only. It never becomes a guessed `Attribute` command. Existing Presets and Effects are reused; this workflow cannot create either.

## Cue-level artistic contract

Provider-facing Cue intent may now include:

- `capability_intent[]`: Group + dimension + `USE|AVOID|OPTIONAL` + reason
- `position_pattern`: `CENTER|LEFT|RIGHT|FRONT|UPSTAGE|NARROW_FAN|WIDE_FAN|CROSS|ALTERNATE|EXPLODE|COLLAPSE`
- `position_scale`: bounded `0.5..2.5`

The Position language remains relative raw/natural MA values. It does not claim physical degrees, exact stage targets, XYZ sign mapping, or high/low semantics.

Every per-Cue Preview row now reports used capability families, selected existing Presets, selected Effect, Position pattern/range, Beam/Gobo/Focus changes, intentionally unused available capabilities with reasons, optional capabilities, and requested-but-unexecutable capability intent. This makes full-fixture consideration auditable without making any feature mandatory.

## Current-show spatial evidence

The dynamic path feeds the Lighting Designer only fresh bounded current-show spatial evidence:

- exact target Group fixture refs
- fresh structured stage geometry for those fixtures
- current operator-verified PAN/TILT direction semantics
- Position baseline and FixtureType limits
- relative Position pattern semantics

Stale committed Stage View calibration artifacts are not promoted into current truth. Stage View pixels remain supplemental visual observation, not structured geometry authority.

## Existing-Cue composite merge

New skill: `existing_cue.dynamic_program_merge`

New intent: `merge_existing_cue_dynamic_program`

Recognized explicit request form includes:

`Dynamic existing Sequence 302 Position Effect Group 1 Preset 2.13 Cues 1-29 Executor 2.8`

This route is evaluated before the generic Show Builder, so it cannot silently allocate a replacement Sequence.

Bounded executable grammar is deliberately split into already verified stores instead of inventing a new combined Programmer-store grammar. A selected existing Preset uses its own isolated phase:

1. `ClearAll`
2. verified `Group <id>`
3. verified `At Preset <type.id>`
4. `Store Cue <n> Sequence <existing> /merge /cueonly /nc`

For a Cue with a new Effect call:

1. `ClearAll`
2. verified `Group <id>`
3. verified `At Effect <id>`
4. `Store Cue <n> Sequence <existing> /merge /cueonly /nc`
5. `ClearAll`
6. verified Fixture selection(s)
7. `Attribute "Pan" At <verified bounded value>`
8. `Attribute "Tilt" At <verified bounded value>`
9. `Store Cue <n> Sequence <existing> /merge /cueonly /nc`
10. final `ClearAll`

For a Cue with no new Effect call, the existing Effect state is preserved. Only artistically selected verified Preset phases and the explicit Position phase are generated. No unverified Effect-release/clear grammar is synthesized.

The path cannot create or assign Sequence, Executor, Effect, Preset, Group, Patch, Address, Fixture identity/type, or Fixture 9999.

## Effect authority

The already closed real-machine proof `ZEN_CUE_EFFECT_APPLICATION_AT_EFFECT_001.md` established `AT_EFFECT_POOL_CALL` through native Cue-content readback with Sequence Export SHA-256:

`2801690a2c512bd0fc5ba1930aef4cc2538090357e6b086519619beecaab4cbd`

The durable grammar capability is now retained in `data/ZEN_CUE_EFFECT_APPLICATION_CAPABILITY.json`.

This recovery **does not assert current Effect object identity**. Every Effect used by the dynamic path still requires fresh current-show object/label/template evidence through the resource map before it can become executable.

## Preservation verifier

The composite verifier distinguishes intended changes from protected content.

Intended:

- PAN/TILT and grandMA2 Position-family representation
- explicitly approved Effect identity / Effect* metadata on target fixtures and Cues
- exact attribute families proven for explicitly selected existing Presets

Protected:

- static Dimmer Value/Fade/Delay
- unplanned Color/Focus/Beam/Gobo families
- unrelated Preset references
- unrelated Effect content
- Cue labels
- Cue Fade/Delay metadata
- Sequence identity
- Executor assignment
- Show identity

Effect allowance does not hide static Dimmer drift. Regression proves that a `DIM Value 55 -> 56` change still fails closed even when an Effect was intentionally attached.

Existing Effect state is captured from the native pre-export before the Lighting Designer call. Existing-Effect replacement/clear is **not** real-machine verified and therefore fails closed. If a target Cue already contains Effect data, this route may preserve it with `NO_NEW_EFFECT_CALL`, but it may not apply a different Effect until a separate replacement grammar is proven. `replace_effect_ids` is not executable authority. Post-write native verification still requires the exact expected Effect-ID set on every exact target fixture.

## Approval semantics

Preview may use one Lighting Designer call. Approval-time revalidation performs **no second artistic/model call**. It rescans current Show/resource/Sequence evidence, reconstructs the approved per-Cue Position/Effect intent deterministically, and rejects stale semantic drift before any MA2 write.

## Regression status

Windows authoritative suite:

`954 tests / OK`

Coverage includes:

- full fixture capability vocabulary
- capability intent vs execution authority separation
- no raw Prism/Zoom/Frost invention
- existing verified COLOR/FOCUS/BEAM/GOBO Preset reuse in existing Cues
- missing Preset identity or exact FixtureType attribute evidence fails closed
- native Preset identity verification per target fixture
- per-Cue used, optional, intentionally unused, and requested-unexecutable capability reporting
- existing Sequence path never allocates a replacement Sequence
- different Cues may use different verified Effects
- Position and Effect coexist as one Cue-level composite intent while using separate verified Store grammars
- existing Effect replacement/clear fails closed until a separate real-machine grammar is verified
- post-write Effect-ID sets must match exactly on every target fixture
- no-new-Effect Cues preserve their pre-existing Effect set
- explicit Position intent required
- Effect variation required for dynamic mode
- static Dimmer/Color/unplanned Effect drift fails closed
- Fixture 9999 protection
- root routing bypasses generic Builder
- fresh spatial context is target-Group bounded
- durable real-machine Effect grammar capability cannot silently disappear


### Mainline convergence hardening

The v0.2 full-capability path and the earlier safety hardening are now one code path. The merged implementation additionally enforces:

- exact Cue ordering and duplicate-Cue rejection;
- exact fixture/subfixture channel identity for Effect/Position preservation checks;
- Effect kind -> attribute-family verification (`DIMMER_CHASE` may mutate Effect metadata only on `DIM`);
- route-scoped provider resources and executable operations;
- exact Preview schema;
- unrelated-fixture Position-family drift remains protected; and
- one verified Effect state plus `NO_NEW_EFFECT_CALL` may satisfy dynamic state variation without inventing another Effect.

No MA2 writes occurred during convergence/hardening.

## Current acceptance state

`MA2_WRITES_DURING_IMPLEMENTATION=0`

Action `8a5d699c36fa` remains noncompliant and must not be approved or executed. It represented Effect creation without existing-Cue application or Position.

The concurrent OC implementation's retained `projects/runs/EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001/preview_only.*` artifacts remain offline contract fixtures and are not approvable. A separate read-only guest MA2 session could not recover the fresh Position binding and therefore registered no live Action.

The next safe acceptance step is **Preview only** through the new route inside the already authenticated current Field Core against Sequence 302. A valid Preview must show per-Cue artistically selected existing Presets and Effects, Position variation, used/optional/intentionally-unused/requested-unexecutable capability families, preserve the full capability-intent audit, and report `MA2_WRITES=0`. No live write occurs until the owner separately approves that exact Preview.
