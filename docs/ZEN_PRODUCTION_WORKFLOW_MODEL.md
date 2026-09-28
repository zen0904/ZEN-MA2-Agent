# ZEN Production Workflow Model

Status: RESEARCH / DESIGN CAPTURED

## Purpose

ZEN MA2 Agent currently builds lighting programming. Its future data model
should nevertheless avoid treating shared production facts as if they belong
only to lighting.

This document captures production-workflow research and architectural
implications. It does not authorize implementation of Audio, Video, Rigging,
Camera, RF, Power, Network or a general Production OS.

## General production flow

A large show commonly moves through a flow shaped roughly like:

```text
Creative / Show Concept
        ↓
Production Design
        ↓
Shared Show Model / Documentation
        ↓
Lighting / Audio / Video / Rigging / Stage / Camera / RF / Power / Network
        ↓
Previs / Preprogram
        ↓
System Integration
        ↓
Production Rehearsal
        ↓
Load-in
        ↓
Real-world Calibration
        ↓
Artist Rehearsal / Soundcheck
        ↓
Show
        ↓
Update / next venue
```

Departments are specialized, but they are not independent islands. They share
stage geometry, timeline, performer position, set/scenic state and show
structure.

## Lighting workflow implication

A professional lighting workflow can be modeled as:

```text
Creative Concept
→ Fixture / Rig Design
→ Plot / Patch / Geometry
→ Focus / Position
→ Preset / Palette
→ Previs
→ Cue Programming
→ Timecode / Trigger / Busking
→ Onsite Focus
→ Update Preset
→ Rehearsal
→ Show
```

The important architectural observation is the edit loop:

```text
Previs intent
→ real rig differs slightly
→ onsite calibration / Preset update
→ linked Cue structure remains editable
```

That strongly supports Spatial vNext's Preset-linked Position architecture over
embedding raw PAN/TILT throughout the Show.

## Audio analogy

Audio system work frequently follows:

```text
Prediction / model
→ measurement
→ correction
```

The analogy is useful at the architecture level: a preproduction model is not
the final physical truth; onsite evidence updates the model.

This document does not infer that lighting should copy any particular audio
algorithm.

## Video / media-server analogy

Modern media-server workflows often separate:

- creative timeline/content;
- stage/world geometry;
- routing/output and technical feed.

ZEN has a similar separation:

- OC / Lighting Designer: Creative;
- ZEN: World / Mapping / Capability / binding;
- MA: Physical execution.

The analogy supports clean boundaries; it is not a reason to merge all
departments into one runtime.

## Shared production data

Potentially shared, non-lighting-exclusive entities include:

- Stage Geometry;
- Stage Surfaces;
- Performer Zones;
- Timeline / show sections;
- Set/scenic objects;
- Video Surfaces;
- production-space transforms;
- named production areas.

Lighting-specific objects such as MA2 Presets, Effects, Sequences and Executor
bindings should remain in the lighting/console implementation layer.

## Layering direction

A future architecture should prefer:

```text
Shared Production World
        ↓
department-specific interpretation
        ↓
department-specific technical implementation
```

For ZEN MA2 Agent, that means the lighting system may consume shared geometry
without forcing the shared geometry schema to contain MA2 concepts.

## Large-production 3D sources

For complex productions, Blender may be a practical authoring source.

Preferred future interchange should prioritize formats capable of preserving
hierarchy and transforms. glTF / GLB is a strong candidate because it can
retain:

- hierarchy;
- rotation;
- scale;
- object metadata/custom properties.

MVR remains relevant to entertainment-production interchange and should be
investigated separately rather than assumed equivalent to glTF.

OBJ may still be useful as geometry-only fallback, but it is weaker when
hierarchy/metadata matter.

No format is promoted to production authority until an adapter is verified.

## Example object taxonomy

Possible large-show objects:

```text
STAGE_MAIN
STAGE_RUNWAY
STAGE_B

TRUSS_UPSTAGE
TRUSS_OUTER_L
TRUSS_OUTER_R

FIX_101
FIX_102
FIX_501

TARGET_MAIN_CENTER
TARGET_RUNWAY_01
TARGET_B_CENTER
```

Possible metadata:

```text
zen_type = fixture
fixture_id = 101
mount_type = OVERHEAD
```

or:

```text
zen_type = stage_surface
surface_id = MAIN_STAGE
```

This is design notation, not a frozen schema.

## Venue change and touring implication

A touring or evolving scene should support Spatial Diff rather than whole-Show
regeneration.

Examples:

- Runway length changes;
- B Stage moves;
- Outer Truss moves.

A shared world model can identify the dependent lighting bindings and mark only
those for recalibration. The same principle may later help other departments,
but lighting remains the only authorized implementation scope today.

## Product boundary

Do not build these now:

- full AV Production OS;
- Audio runtime integration;
- Video/media-server runtime integration;
- cross-department automation;
- full Blender authoring pipeline;
- production-wide asset database.

Capture the shared-world boundary now so future implementation does not have to
undo a lighting-exclusive data model later.

## Relationship to current roadmap

Spatial System vNext is the next major design track after the current Core
Pipeline Stabilization / Closure work is reviewed.

The first implementation slice remains Semantic Position Binding. A richer
shared Production Model is research/backlog work and must not preempt that
slice.
