# ZEN Spatial Setup UX

Status: DESIGN CAPTURED / NOT YET IMPLEMENTING

## Purpose

Spatial setup must be usable in real production conditions without requiring
the operator to hand-edit backend JSON. JSON remains a machine artifact.

The product should expose two complementary surfaces:

1. a very small grandMA2-side capture/update surface for work that belongs at
   the console; and
2. a ZEN graphical setup surface for geometry, targets, calibration and binding.

This document preserves the Stable Operator Contract. Any later change that
materially changes ZEN's normal operating workflow still requires explicit
human approval under `docs/ZEN_WORKFLOW_CONTRACT.md`.

## Principle

The setup workflow should scale with available information.

```text
no drawing / small show
→ dimensions + orientation + a few calibration points

existing MA geometry
→ import + verify + correct only what is missing

plan / PDF / image
→ scale + corners + audience direction + fixture/target placement

large production model
→ import rich scene + verify semantic mapping
```

The operator should not be forced into a large-production workflow for a small
event.

## MA2 Lua Plugin role

The MA2-side tool should stay intentionally narrow.

Suitable responsibilities:

- Capture Calibration;
- Assign Preset;
- Update Target;
- Verify current mapping;
- Sync mapping state;
- show current semantic binding;
- capture a bounded operator-confirmed point or vector.

It should not become a CAD editor or duplicate ZEN's full world-model UI.
Complex state, scene import and cross-system logic belong outside the console
unless a native MA mechanism is clearly the cleaner operator-facing solution.

All MA-bound names/text remain subject to the existing ASCII boundary.

## ZEN Spatial Setup UI role

The graphical setup surface should eventually support:

- Top View;
- Side View;
- fixture selection;
- stage-surface editing;
- target placement;
- point-target and vector-target editing;
- Preset Binding;
- Calibration Wizard;
- Stage Plan Import;
- geometry import;
- confidence / unknown-state display;
- Spatial Diff review;
- selective recalibration.

The UI is an editor for a typed world model. It is not a direct raw MA command
surface.

## Setup from no plan

When no drawing or scene exists, ask only for information that changes the
model:

- Stage Width;
- Stage Depth;
- Stage Height when relevant;
- Audience direction;
- fixture locations/orientation where known.

ZEN creates a simple stage frame and records unknowns explicitly.

The minimum path must remain practical for small and medium productions.

## Setup from plan / PDF / JPG

A plan-image workflow may be:

```text
Upload plan
→ set scale
→ identify stage corners / reference dimension
→ define audience direction
→ create Stage Frame
→ place or confirm fixtures
→ create Stage Surfaces / target anchors
→ calibration
```

Image pixels are not automatically authoritative geometry. The scale and
reference points provide the mapping.

## Setup from grandMA Stage View / MA 3D

Where a verified structured scene reader exists:

```text
Import structured geometry
→ bind to current Show identity
→ show confidence / missing semantics
→ request only missing orientation or venue facts
→ calibration / correction
```

Screenshots remain visual evidence and may help interpretation, but they do not
replace exact structured metadata when exact geometry is required.

## Calibration Wizard

The wizard should support quick and detailed paths without forcing one fixed
point count.

Possible UX:

- Quick: 3 points;
- Standard: 5 points;
- Detailed: 9 points;
- Adaptive: add a point only where residual error is high.

Each captured point should retain:

- Show/fingerprint provenance;
- fixture or Group scope;
- semantic target;
- expected world position/vector;
- captured native resource/value;
- residual / confidence where calculable;
- timestamp/version evidence.

Calibration capture does not itself create an artistic Cue.

## Preset binding UX

The operator should be able to bind one semantic target to a selective Position
Preset without thinking in raw PAN/TILT.

Example:

```text
MAIN_STAGE.CENTER
→ Position Preset 2.xxx
→ contains per-fixture PAN/TILT for the selected scope
```

The UI should distinguish:

- verified existing binding;
- derived candidate;
- needs calibration;
- stale because geometry changed;
- unsupported / unknown.

The provider should see only verified or explicitly bounded executable
resources, not raw backend noise.

## Point targets and vector targets

The UI must make the difference visible.

Point target interaction:
- click a position on a Stage Surface or enter coordinates.

Vector target interaction:
- choose or manipulate a direction in world space;
- optionally define named patterns such as INWARD / OUTWARD / VERTICAL.

A floor fixture's useful target may be a vector with no meaningful deck point.

## Stage Surfaces

The UI should allow named production surfaces such as:

- MAIN_STAGE;
- RUNWAY;
- B_STAGE;
- RISER;
- PLATFORM.

Targets should belong to a surface when that relationship is meaningful.
Shared world coordinates still allow cross-surface relationships.

## Spatial confidence

The operator needs to know when ZEN is certain and when it is improvising from
limited evidence.

The UX should expose confidence/unknown state without turning the workflow into
a warning dashboard.

Useful states include:

- VERIFIED;
- CALIBRATED;
- DERIVED;
- PARTIAL;
- UNKNOWN;
- RECALIBRATION_REQUIRED.

Unknown is a valid state. It must not be converted into fabricated precision.

## Spatial Diff UX

When imported or entered geometry changes, show a bounded diff such as:

- affected Surface;
- moved fixtures;
- invalidated target bindings;
- calibration regions requiring review.

The default action is not "rebuild Show". The operator decides whether and when
to recalibrate affected regions.

## Backend artifact

A typed backend artifact may eventually include:

- stage frame and coordinate version;
- source mode;
- Stage Surfaces;
- fixtures and transforms;
- mount context;
- point targets;
- vector targets;
- calibration observations;
- semantic bindings;
- confidence/provenance;
- diff/invalidation state.

The exact schema is an implementation decision for a later bounded slice. The
operator should not need to author it manually.

## First UX implementation boundary

Do not build the entire graphical editor first.

The first implementation that should accompany Semantic Position Binding is the
smallest UI/command surface needed to:

1. inspect a semantic target;
2. bind it to an existing verified Position Preset;
3. show scope and provenance;
4. mark the binding stale when its evidence changes;
5. feed that binding into Preview without writing MA automatically.

Full plan import, Blender editing and rich calibration visualization remain
later slices.
