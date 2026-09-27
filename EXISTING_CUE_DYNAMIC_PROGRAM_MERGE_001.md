# EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001

Status: **OFFLINE IMPLEMENTATION COMPLETE — LIVE-EVIDENCE PREVIEW BLOCKED — MA2_WRITES=0**

Action `8a5d699c36fa` is rejected as noncompliant. It was not approved or
executed. Action `97d3a82f1220` was not replayed. Sequence 302, its Executor
assignment, and Fixture 9999 were not modified.

## Capability gap closed

The new bounded implementation is
`zen_ma2_agent/existing_cue_dynamic_program_merge.py` with builtin Skill
`existing_cue.dynamic_program_merge`.

It composes two already proven boundaries without exposing a generic MA command
interface:

1. verified existing-Cue Position merge using explicit PAN/TILT values; and
2. verified Cue Effect grammar: `Group <verified group>` followed by
   `At Effect <verified effect>`.

Every write target is an existing Cue in an already verified ZEN-owned Sequence.
The compiler has no Sequence allocator and cannot create a replacement Sequence,
Effect, Group, Executor, Preset, fixture, Patch, or Address.

## Deterministic workflow

```text
fresh native Sequence export
+ fresh Group membership
+ fresh List Effect and Agent-owned catalog evidence
+ content-verified At Effect capability
+ fresh geometry/capability limits
+ verified Position baseline and direction semantics
+ explicit artistic per-Cue plan
+ Stage View/operator amplitude assessment
    -> deterministic compile
    -> preservation-diff Preview
    -> explicit human approval (future live Action only)
    -> existing-Cue /merge /cueonly
    -> fresh native Sequence Export verification
```

No live Action is registered from stale, retained, fixture, or unbound visual
evidence.

## Supported artistic vocabulary

Effect intent:

- `STATIC_LOOK`
- `DIMMER_CHASE_SLOW`
- `DIMMER_CHASE_MED`
- `DIMMER_CHASE_FAST`
- `ALTERNATE`
- `PULSE`
- `HIT`
- `BUILD`
- `RELEASE`
- `BLACKOUT`
- `RESET`

Dynamic intents must bind to an existing, freshly verified Effect. Static,
release, blackout, and reset entries do not invent an Effect reference. The
compiler does not claim that omitting a new Effect call clears a tracked Effect;
that would require a separately verified release grammar.

Position pattern:

- `CENTER`
- `LEFT` / `RIGHT`
- `FRONT` / `UPSTAGE`
- `NARROW_FAN` / `WIDE_FAN`
- `CROSS`
- `ALTERNATE`
- `EXPLODE`
- `COLLAPSE`

Current Test Show direction semantics are preserved:

- PAN negative -> stage right
- PAN positive -> stage left
- TILT negative -> audience/front
- TILT positive -> upstage/inward

The known Group 1 baseline remains PAN `20`, TILT `30`. The compiler does not
copy that baseline to another Group. A larger Position amplitude requires all
three of:

1. readable Stage View evidence;
2. operator assessment `PRIOR_VARIATION_TOO_SMALL`; and
3. fixture-specific verified natural limits.

The offline contract Preview uses scale `1.5`; a nominal +/-12 WIDE_FAN becomes
+/-18 raw value, while every final value is still checked against fixture
limits. This is a relative-shape proposal and does not claim physical targeting,
world coordinates, audience safety, or high/low geometry.

## Per-Cue Preview contract

Every Cue row contains:

- Cue number and fresh native label;
- selected Effect intent and exact Effect ID, or no new Effect;
- verified target Group;
- Position pattern;
- expected PAN and TILT ranges;
- intended attribute families (`EFFECT`, `POSITION`);
- exact fixture values and deltas; and
- an individual protected-content fingerprint.

A 29-Cue Preview must cover exactly Cues 1-29. Empty Cue applications, an
Effect-only pool creation action, or a Position request with no fixture values
is noncompliant.

## Preservation contract

Allowed intended changes:

- PAN/TILT and known Position-family companion rows;
- explicitly selected Effect references on the verified target Group.

Protected unless explicitly planned:

- Cue labels;
- Fade and Delay;
- Color;
- unrelated static Dimmer values;
- unrelated Presets;
- unrelated Effects;
- Sequence identity; and
- Executor assignment.

If a target Cue already contains an Effect, the planner must explicitly list
all replaced Effect IDs. Otherwise compilation fails with
`DYNAMIC_MERGE_UNRELATED_EFFECT_CONFLICT`. Post-write verification requires the
planned Effect set exactly and rejects protected-content fingerprint drift.

## Command boundary

Only these exact command families are allowed:

```text
ClearAll
Group <positive integer>
At Effect <positive integer>
Fixture <verified exact refs>
Attribute "Pan" At <bounded numeric value>
Attribute "Tilt" At <bounded numeric value>
Store Cue <existing cue> Sequence <existing sequence> /merge /cueonly /nc
```

There is no raw command string input and no `Sequence 303`, allocation, label,
Assign, Delete, Patch, Address, Fixture identity/type, playback, or Executor
command.

Effect and Position are isolated into two deterministic Programmer/store phases
for the same existing Cue, each using `/merge /cueonly`, so Effect application
does not leak into Position selection and vice versa.

## Verification

Fresh post-write Sequence Export must prove:

- all approved PAN/TILT values per exact fixture;
- the exact planned Effect identity per target fixture;
- unrelated pre-existing Effect IDs remain, unless explicitly replaced;
- Cue labels remain identical; and
- the protected-content fingerprint is unchanged.

The verifier reports intended Position/Effect matches separately from protected
content.

## Regression coverage

`tests/test_existing_cue_dynamic_program_merge.py` covers:

1. existing Sequence 302 never allocates a new Sequence;
2. Effect is attached to the requested existing Cue;
3. different Cues use different Effects;
4. Effect and Position coexist in one Cue workflow;
5. unknown attribute drift fails closed;
6. Fixture 9999 is rejected;
7. stale Sequence, Effect, or Group evidence blocks;
8. Effect creation without Cue application is noncompliant;
9. Position requested without Position values is noncompliant;
10. native verification separates intended changes from protected content;
11. unrelated existing Effect replacement requires an explicit plan; and
12. Stage View/operator scaling remains bounded by fixture limits.

Focused result: `41 tests / OK` across the new capability, existing Position
merge, Cue Effect application, and builtin Skill discovery coverage.

Authoritative Windows result: `917 tests / OK` using
`python -m unittest discover -s tests -q`.

## Preview-only artifact

Files:

- `projects/runs/EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001/preview_only.json`
- `projects/runs/EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001/preview_only.md`

The generated artifact demonstrates:

- 29 Cue applications;
- three different verified-resource placeholders for slow/medium/fast dynamics;
- per-Cue Effect/no-Effect choices;
- per-Cue Position patterns and exact fixture values;
- 484 allow-listed deterministic commands; and
- `MA2_WRITES=0`.

Its status is deliberately
`OFFLINE_CONTRACT_FIXTURE_NOT_APPROVABLE`. Fixture Cue labels and evidence hashes
are not current native Sequence 302 evidence and cannot be promoted to an
Action.

## Fresh live Preview blocker

A separate read-only MA2 connection reached the console as guest rather than the
already authenticated Field Core user, so fresh binding lookup failed with
`POSITION_MERGE_VERIFIED_BASELINE_BINDING_UNAVAILABLE`. The implementation did
not weaken that gate or reuse stale evidence.

The next safe operation is read-only: run this compiler inside the already
authenticated Field Core so it can collect the fresh native Sequence 302,
Group, Effect, geometry, capability, and calibration evidence. Only then may it
return a real Preview with current Cue labels. No live write follows without a
new explicit human approval.

## Safety outcome

- `MA2_WRITES=0`
- Sequence 302 modified: **NO**
- Sequence 303 created: **NO**
- Executor assignment changed: **NO**
- Fixture 9999 touched: **NO**
- Action `97d3a82f1220` replayed: **NO**
- Action `8a5d699c36fa` approved/executed: **NO**
