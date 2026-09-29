# ZEN Spatial System vNext

Status: DESIGN CAPTURED / NOT YET IMPLEMENTING

## Purpose

Spatial System vNext upgrades Position from raw console values or a small fixed
Preset list into a semantic, calibratable, show-bound spatial layer.

The central rule is:

> Incomplete data must reduce spatial confidence, not make ZEN unusable.

Small and medium shows must remain workable with limited venue information.
Large productions may provide a much richer model, but the richer model is an
optional precision source rather than a mandatory operating requirement.

This document defines product direction only. It does not authorize MA writes,
Patch/Address changes, Fixture identity/type changes, or a broad Position
rewrite.

## Architecture boundary

The intended path is:

```text
OC / Lighting Designer artistic intent
        ↓
Semantic Spatial Target
        ↓
ZEN Spatial Resolver
        ↓
show-bound target / calibration / resource binding
        ↓
Position Preset reference or deterministic derived solution
        ↓
typed ShowPlan
        ↓
existing Preview / Approval / Builder / native readback boundary
```

OC remains free to reason in human spatial language such as "open the outside",
"bring the floor fixtures inward", "keep negative space", "converge on the
singer", or "build a tunnel". ZEN owns the conversion from that intent into a
verified current-Show spatial implementation. The MA boundary remains
deterministic and fail-closed.

## Data completeness levels

### BASIC

Minimum useful information:

- stage direction;
- approximate main-stage dimensions;
- fixture inventory;
- limited calibration;
- current MA state.

ZEN may work at BASIC level, but spatial confidence must remain lower and
unsupported physical claims stay UNKNOWN.

### STANDARD

Typical formal-event information:

- stage dimensions;
- fixture XYZ;
- basic rotation/orientation;
- five to nine calibration targets where useful;
- floor/aerial direction information;
- named Stage Surfaces.

### FULL / PREVIS

Large-production information may include:

- complete 3D scene;
- Main Stage, Runway, B Stage, Risers, Platforms;
- Set, Truss, LED/scenic surfaces;
- fixture XYZ and rotation;
- Performer Zones;
- Target Maps;
- Blender / glTF / MVR-derived geometry.

FULL data increases precision. It is not a prerequisite for ordinary operation.

## Spatial source modes

ZEN should support four source modes without changing the operator-facing
artistic contract.

### AUTO_ZEN

When no usable 3D scene exists, ZEN creates a stage frame, basic fixture layout,
audience direction and bounded target map from operator-supplied dimensions and
known Show evidence.

### IMPORT_MA

When grandMA Stage View / MA 3D geometry is available through a verified reader,
ZEN imports that geometry as evidence. Visual pixels alone do not become exact
machine geometry.

### HYBRID

Imported geometry may be corrected or extended by operator input. Later scene
changes produce a Spatial Diff so only affected fixtures, targets or
calibration regions are invalidated.

### BLENDER

For complex productions, Blender may provide a richer world model. This is a
future adapter, not a dependency of Spatial vNext's first implementation slice.


## Geometry authority and provenance

Spatial geometry must be accepted or rejected by provenance and verification, not merely by whether a workflow originally began as `NEW_UNDESIGNED_SHOW`.

ZEN must always be able to read fresh native fixture geometry when grandMA2 exposes it, including:

- fixture/subfixture Pos X / Pos Y / Pos Z;
- Rot X / Rot Y / Rot Z;
- Pan/Tilt offsets and invert metadata when exposed by the verified reader.

The intended authority classes are:

### AGENT_AUTHORED_VERIFIED

Geometry proposed by ZEN, explicitly approved, written through the deterministic MA boundary, and then native-read back with exact XYZ/rotation agreement becomes valid current spatial geometry. It must not continue to be treated as `UNDESIGNED` merely because the original bootstrap mode was `NEW_UNDESIGNED_SHOW`.

### OPERATOR_AUTHORED_VERIFIED

Geometry intentionally arranged by the operator in grandMA2 and then freshly read back may become current spatial geometry once the operator confirms that the arrangement is intentional. ZEN must not require the operator to recreate that layout in a separate ZEN editor.

### IMPORTED_VERIFIED

Geometry imported from a verified supported source may be used according to its bound source/frame confidence.

### UNDESIGNED_OR_UNKNOWN

Default, all-zero, stale, accidental, or provenance-unknown geometry remains non-authoritative. This is the state that the historical `NEW_UNDESIGNED_SHOW` exclusion was protecting against.

### Calculation rule

- Height comes from the fixture/world Z coordinate after the relevant frame mapping is established; Rotation is orientation, not height.
- XYZ + Rot XYZ describe the fixture pose.
- A beam direction/target calculation additionally requires the fixture's verified Pan/Tilt state or requested Pan/Tilt, Pan/Tilt offsets/inversion where relevant, and the fixture's verified axis/model semantics.
- Raw MA2 coordinates alone do not prove which sign is Stage Left, Stage Right, Upstage or Downstage. A stage-frame/orientation mapping is still required for those semantic labels.
- When ZEN itself authored the geometry from `ZEN_STAGE_FRAME_V1`, the authored transform plus native readback can preserve that known frame relation instead of discarding it.

The long-term spatial pipeline therefore becomes:

```text
Agent- or operator-authored fixture layout
        ↓
fresh native XYZ + Rotation readback
        ↓
geometry provenance / authority classification
        ↓
ZEN Stage Frame mapping
        ↓
fixture world pose
        ↓
semantic target / vector resolution
        ↓
Position Preset / derived solution
```

This rule also means future Auto Geometry proposals must treat fixture Rotation as real design data. A blanket `Rot X/Y/Z = 0` is only a bounded placeholder, not the final Spatial vNext behavior.

## Stage coordinate system

The semantic world is stage-centric.

Recommended canonical orientation:

```text
+X = Stage Left
-X = Stage Right
+Y = Upstage
-Y = Downstage / Audience direction
+Z = Up
Origin = Stage Center
```

Audience direction must have a reliable anchor. AUTO_ZEN knows the anchor from
setup. Imported external geometry that lacks orientation metadata should ask
the operator once rather than guess.

Exact mapping from any external scene or MA coordinate representation into this
world remains evidence-bound. A naming convention does not prove coordinate
semantics.

## Stage Surfaces

Spatial reasoning is not limited to one 3x3 main-stage grid.

The shared world may contain:

- MAIN_STAGE
- RUNWAY
- B_STAGE
- RISER
- PLATFORM
- future named surfaces justified by the production.

Each Surface may own its own target map and local bounds while remaining in one
shared stage coordinate system.

## Point targets

A basic Main Stage should normally support at least:

- CENTER
- STAGE_LEFT
- STAGE_RIGHT
- UPSTAGE
- DOWNSTAGE

A more detailed target map may expose:

```text
USL / USC / USR
CSL / CENTER / CSR
DSL / DSC / DSR
```

The grid is an anchor set, not a closed vocabulary. The artistic layer may ask
for intermediate or relational targets.

## World-vector targets

Floor and aerial fixtures often need a direction rather than a point on the
deck. ZEN therefore needs explicit world-vector targets in addition to point
targets.

Examples:

- VERTICAL_UP
- INWARD_15
- INWARD_30
- OUTWARD_15
- OUTWARD_30
- CROSS
- FAN
- PARALLEL
- UPSTAGE_VECTOR
- DOWNSTAGE_VECTOR

A Point Target means "aim at this world position". A Vector Target means "send
the beam in this world direction". They must not be conflated.

## Fixture mount context

Possible mount classifications include:

- OVERHEAD
- SIDE_TRUSS
- FLOOR
- UPSTAGE_FLOOR
- STAGE_EDGE
- TOWER
- OUTER_TRUSS
- SET_PIECE

Mount type supplies reachability and natural-orientation context. It is not an
artistic role assignment and must never become a rule such as "floor fixture
always does aerial".

## Calibration model

Calibration is not the artistic Position design itself. It is the correction
layer between a virtual target and the real rig.

Useful operating modes:

- 3-point quick calibration;
- 5-point general calibration;
- 9-point higher-precision calibration.

The intended long-term model is adaptive calibration. ZEN should evaluate
residual error and request additional evidence only in the region where the
model is weak. The operator should not be forced to redo nine points every time
one part of a rig changes.

## Semantic Position resources

Position Presets become Spatial Anchors / Calibration Resources, not the
provider's complete artistic vocabulary.

Examples of stable semantic anchors:

- MAIN.C
- MAIN.SL
- MAIN.SR
- MAIN.US
- MAIN.DS
- MAIN.USL
- MAIN.USR
- MAIN.DSL
- MAIN.DSR
- AIR.UP
- AIR.IN
- AIR.OUT
- AIR.CROSS

The artistic layer may still request relational intent such as "CENTER slightly
downstage", "outer fixtures wider", or "rear row higher". ZEN resolves that
intent against the current Show.

## Resolution modes

### REUSE

Use an existing verified semantic target / Position Preset binding.

### DERIVE

Interpolate or otherwise derive a deterministic spatial solution from known
anchors when the requested target falls between them. Example: a target one
third of the way from CENTER toward DOWNSTAGE.

DERIVE must remain bounded by known geometry/calibration and expose confidence;
it may not invent physical semantics.

### SPECIAL

Create or use a song-specific Position resource only when the requested look is
genuinely special and should remain a named reusable object, for example:

`SHEESH.CHORUS_AERIAL_CONVERGE`

The system must not create a new Position Preset for every Cue.



## Geometry-to-Group-order-to-Position workflow

Once a fixture layout becomes trusted spatial geometry, normal Group selection
order should be rebuilt from that geometry before song programming begins.

The intended production sequence is:

```text
Agent designs fixture XYZ + Rotation
        ↓
Preview / explicit approval
        ↓
MA2 geometry write
        ↓
fresh native XYZ + Rotation readback
        ↓
trusted Spatial geometry
        ↓
rebuild existing normal Group selection order from live spatial order
        ↓
Store Group <id> /overwrite /nc
        ↓
fresh exact Group membership/order readback
        ↓
hydrate / update reusable Position anchor Presets
        ↓
Lighting design / Cues / Movement / Effects reference those resources
        ↓
onsite operator corrects foundation Position Presets as needed
```

Normal Group reorder is membership-preserving:

- preserve the exact verified fixture/subfixture member set;
- preserve exact subfixture references such as `.1` or `.2`;
- change selection order only;
- do not create duplicate normal Groups solely to represent the new geometry;
- Fixture 9999 remains protected;
- fresh native Group readback must exactly match the desired order and original
  member set.

The default spatial ordering policy remains deterministic:

- one spatial row: order by live stage-space X;
- multiple rows/layers: order by stage depth/layer first, then X inside the row;
- the exact stage-frame axis convention and row grouping must come from the
  trusted Spatial model rather than Fixture numeric IDs.

Special artistic orders are separate resources. A song may require a dedicated
Group for a special chase, cross-order, center-out, or other non-normal sequence,
but that must not corrupt the ordinary spatial Group order.

This reorder step belongs after trusted geometry and before effect/movement
programming because MAtricks, phase, fan and chase behavior may depend on native
selection order.

The historical Group 7 incident remains a hard safety lesson: never reconstruct
a normal Group from parent Fixture IDs when the verified Group contains exact
subfixture identities. The committed `GroupOrderSpec` builder already enforces
same-member-set and exact-reference preservation; future Spatial orchestration
should call that bounded path rather than synthesizing ad-hoc Group overwrite
commands.

## Pre-named empty Position Presets as Spatial Anchor Slots

A normal operator template may intentionally contain Position Preset pool objects
whose identity and label already exist while their fixture content is still
empty. These are not unused noise. When explicitly designated by the operator,
ZEN should treat them as reserved Spatial Anchor Slots.

Example operator template:

```text
Position Preset 2.x  MAIN_CENTER
Position Preset 2.y  MAIN_LEFT
Position Preset 2.z  MAIN_RIGHT
Position Preset 2.a  MAIN_DSC
Position Preset 2.b  MAIN_USC
Position Preset 2.c  AIR_IN
Position Preset 2.d  AIR_OUT
```

The intended workflow is:

```text
operator pre-names empty Position Preset slots
        ↓
ZEN reads exact Preset reference / type / label
        ↓
operator-approved semantic mapping
        ↓
Space resolves per-fixture values for the target
        ↓
Preview
        ↓
approved deterministic hydration of the same Preset slot
        ↓
native content readback
        ↓
Cues reference the Position Preset
        ↓
onsite focus correction updates the Preset, not every Cue
```

This is preferred over allocating a new Position Preset for every song or Cue.
A semantic target should normally remain a reusable native Position resource.

Important boundaries:

- Existing label identity is not content proof.
- A pre-named slot must be verified as a POSITION Preset and explicitly empty
  before first hydration.
- ZEN must not silently repurpose a non-empty or differently typed Preset.
- Exact update/merge grammar for hydrating an already existing empty Position
  Preset requires separate real-machine verification before it becomes an
  executable capability. Do not assume `/merge` behavior from Cue-store grammar.
- Post-write native evidence must prove the expected per-fixture PAN/TILT rows
  and exact Preset identity.
- Cues should preserve native Preset references wherever possible so onsite
  Preset correction propagates to all dependent Cues.
- Song-specific exceptional looks may still use SPECIAL resources, but they
  should not replace the reusable anchor library.

This creates a practical onsite focus model: the operator adjusts a small set of
foundation Position Presets to match the real venue, while the already-built Cue
structure continues to reference those native resources.

## Selective Position Presets

One semantic Position Preset may contain different PAN/TILT values for different
fixtures while representing one common world target.

For example, `MAIN_STAGE.CENTER` may contain unique values for Fixture 101,
102, 201 and 501, all aimed at the same semantic location.

This is the desired native-console bridge because it preserves normal MA
editability and lets onsite focus correction propagate through Preset links.

## Onsite correction model

The desired operational flow is:

```text
OC intent
→ semantic target
→ ZEN binding
→ Position Preset reference
→ Cue
```

If `MAIN_STAGE.CENTER` is physically too far upstage onsite, the operator fixes
the calibration / linked Position Preset. Cues that preserve the native
reference follow the correction, and future ZEN designs use the corrected
binding.

This is preferred over embedding raw PAN/TILT into every Cue.

## Spatial Diff

When geometry changes, ZEN should compare old and new world state and mark only
affected resources.

Examples:

- Runway length changed;
- B Stage moved;
- Outer Truss moved.

Expected result:

```text
Spatial Diff
→ affected fixtures / targets / calibration regions
→ RECALIBRATION_REQUIRED only where necessary
```

A geometry change is not permission to rebuild the entire Show.

## Shared-production boundary

Stage Geometry, Stage Surfaces, Performer Zones, Timeline anchors and Video
Surfaces are not inherently lighting-only concepts. The data architecture
should avoid baking "lighting" into these shared world entities.

This is an architectural allowance, not authorization to implement an AV
Production OS now.

## First implementation slice

The first Spatial vNext implementation slice, after the current Core Pipeline
Closure review, is:

```text
SEMANTIC POSITION BINDING

OC Artistic Intent
→ Semantic Spatial Target
→ ZEN Target Binding
→ Position Preset Reference
→ Cue
```

The first slice should prefer existing verified Position Preset links and
calibration evidence. It must keep the current Preview / explicit Approval /
native readback boundary and must not broaden MA write authority.

## Explicitly deferred

Do not start these merely because this document records them:

- full Blender pipeline;
- full Production Model;
- Audio integration;
- Video integration;
- complete graphical Spatial UI;
- whole-Show Position rewrite;
- arbitrary automatic Position Preset creation.

They remain captured future work until normal triage promotes a bounded task.

## Implementation status — Semantic Position Binding foundation (2026-09-28)

The first bounded Spatial vNext implementation foundation is now offline-verified.

Implemented:

- `zen.semantic_position_binding.v0.1` maps one semantic POINT target to one
  already content-verified Position Preset application binding.
- The semantic layer cannot create Position applicability. It delegates that
  truth to the existing `zen.position_preset_application_binding.v0.1`
  real-machine evidence and fails closed when that proof drifts.
- Current first-slice resolution mode is `REUSE` only.
- Current first-slice target kind is `POINT` only.
- Semantic bindings are persisted in
  `data/ZEN_SEMANTIC_POSITION_BINDINGS.json` through a local evidence store.
- The Artistic Resource Map exposes semantic targets only when both the native
  Position application proof and semantic binding remain current.
- The provider contract may use
  `{"group": 1, "position_target": "MAIN_STAGE.CENTER"}`.
- The deterministic compiler resolves that semantic target back into the
  existing typed `CALL_PRESET` action with the verified Position Preset.
- No new Builder grammar or MA transport grammar was introduced.
- AgentCore loads verified semantic bindings into the normal lean root resource
  map. With no semantic binding catalog, current behavior is unchanged.

Verification:

- Windows full suite: 973 tests / OK.
- `git diff --check`: PASS.
- MA2 writes: 0.
- No Preview or Approval was created by this implementation task.

Not implemented by this foundation:

- automatic semantic guessing from Preset labels;
- DERIVE or SPECIAL resolution;
- world-vector targets;
- creation of new Position Presets;
- live MA writes;
- full Spatial Setup UI.

The next bounded gate is an operator-facing, no-MA-write capture surface that
can inspect a verified Position application binding and explicitly assign a
semantic target such as `MAIN_STAGE.CENTER`. The resulting local binding must
remain show-bound, provenance-bearing and stale-safe before it may appear in a
future Preview.
