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

## Product direction update — Show Agent Controller

Owner direction, 2026-09-28:

The long-term product should no longer be understood as only a grandMA2
programming assistant. The broader product direction is a **Show Agent
Controller**: a virtualized production control plane inspired by the way a
large K-pop / touring production coordinates the whole Show across departments.

Instead of replacing the real department systems, ZEN virtualizes the
coordination/intelligence layer: it understands the Show, shared world,
timeline, performer/blocking context and production intent, then delegates
bounded technical execution to department-specific verified adapters.

This is an intelligence and control layer that can understand the whole Show
and coordinate shared production context while preserving strict,
department-specific execution authority.

A useful conceptual split is:

```text
Show Agent Controller
        ↓
Shared Production World / Timeline / Intent
        ↓
Department Intelligence / Mapping
        ↓
Verified Department Adapters
        ↓
Physical systems
```

For the current implementation:

```text
Show Agent Controller
        ↓
Lighting Intelligence
        ↓
ZEN MA2 Adapter
        ↓
grandMA2 deterministic execution
```

The existing ZEN MA2 Agent work therefore becomes the first mature
department-specific execution adapter, not discarded prototype work.

The intended analogy is a large K-pop / touring production system moved into a
virtual Agent-control layer. Today, creative direction, show calling,
programming, system departments, rehearsal feedback and technical control are
distributed across people and specialist systems. ZEN should model that
coordination layer virtually while leaving physical execution in the systems
that already do it well.

This does **not** mean one unconstrained Agent directly drives every device.
The Show Agent Controller acts more like a virtual production brain / team:

global Show understanding and coordination
        ↓
bounded department intent
        ↓
department-specific authority / mapping
        ↓
deterministic adapters
        ↓
console / media server / audio / show-control systems

Long-term candidate domains may include:

- Lighting;
- Audio;
- Video / media server;
- Stage / scenic state;
- performer zones / blocking;
- timeline / trigger / timecode;
- production geometry;
- rehearsal/update state;
- show-wide observations and operator intent.

This direction does **not** authorize implementing all departments now.
The current development rule remains:

1. preserve the proven MA2 execution core;
2. build Shared Production / Spatial abstractions above it;
3. add new department adapters only as bounded, independently verifiable
   capabilities;
4. never let a global Agent bypass a department's deterministic write and
   verification boundary.

The architecture should therefore avoid naming shared entities as
lighting-exclusive when they are truly production-wide, while keeping MA2
objects and write grammar inside the Lighting/MA adapter.

### Progress interpretation

Two progress measures should be kept separate:

- MA2 execution-core maturity: approximately 90–95% of the originally intended
  core architecture is now in place.
- Broader Show Agent Controller vision: approximately 30–40% at the current
  design/implementation stage.

These are planning estimates, not release metrics. The apparent drop is caused
by an expanded product boundary, not regression of the completed MA2 work.
