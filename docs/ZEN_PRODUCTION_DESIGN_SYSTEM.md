# ZEN Production Design System

Status: OWNER_APPROVED_ARCHITECTURE_CAPTURE_ONLY  
Owner decision date: 2026-10-02  
Current implementation authority: NONE

## Purpose

ZEN Production Design System is the future shared production-design layer that coordinates
stage/scenic design, lighting design, physical rigging/structural feasibility, and spatial
truth before department-specific execution.

This is not a replacement for the current Lighting Designer, Spatial System, grandMA2
Builder, venue engineer, qualified rigger, or licensed/authorized structural engineering
sign-off. It records how those responsibilities should cooperate when ZEN later supports
real production design rather than only console programming.

The core principle is:

```text
A visually desirable design
!=
a physically buildable design
!=
an engineered/approved structure
```

ZEN must preserve all three distinctions.

## Roles

### STAGE_SCENIC_DESIGNER

Owns the visual and functional stage world.

Typical responsibilities:

- overall stage proportion and visual composition;
- MAIN_STAGE / RUNWAY / B_STAGE / RISER / PLATFORM relationships;
- scenic forms, scenic masking and visible architecture;
- LED/video-surface placement as part of the stage composition;
- stairs, performer routes, entrances, exits and usable performance areas;
- whether truss, Layher/scaffold or towers are intentionally visible scenic language;
- conceptual modularity and build intent;
- sightline and audience-view concerns;
- coordination with Lighting Designer on where useful lighting positions should exist.

This role may request structure but does not declare that a structure is safe or approved.

### LIGHTING_DESIGNER

Owns lighting visual intent and the lighting requirements imposed on the physical design.

Typical responsibilities:

- visual hierarchy, direction, density and negative space;
- useful fixture families and visual capabilities;
- desired lighting-position regions and mounting heights;
- target coverage and useful incidence angles;
- front / side / back / cross / floor / overhead relationships;
- beam-path and aerial requirements;
- serviceable fixture spacing and useful Pan/Tilt operating range;
- requests for lighting positions that support the song/show design.

A Lighting Designer may say that a side position, tower, low boom or truss is artistically
valuable. It may not invent a load rating, rigging point or structural capacity to make that
request possible.

### STRUCTURAL_RIGGING_ENGINEER

Owns physical constructability and structural/rigging feasibility for the proposed production
model.

Typical responsibilities:

- verified truss family/model, segment and connection compatibility;
- verified Layher/scaffold/module inventory and permitted assembly configurations;
- supports, towers, bases, bracing and support geometry;
- hoists, motors, pick points and support reactions where verified data exists;
- fixture, LED, scenic, audio and other attached-load inventory;
- span, point-load, distributed-load and deflection constraints;
- collision, clearance, rotation envelope and access/maintenance constraints;
- assembly/disassembly feasibility and relevant site constraints;
- inventory reconciliation: requested resources versus physically available resources;
- producing explicit unresolved engineering questions instead of filling missing facts.

This role is an engineering planning/review role inside ZEN. It must not represent an
AI-generated proposal as a legally sufficient engineering calculation, stamped drawing,
venue approval, competent-person approval, or structural sign-off.

### SPATIAL_SYSTEM

Spatial System is the shared physical data plane, not an artistic authority.

It carries the common world model used by all three roles, including where available:

- venue geometry and coordinate frames;
- stage surfaces and performer zones;
- scenic objects and video surfaces;
- truss, pipes, towers, scaffold/Layher and support objects;
- rigging/support points and known constraints;
- fixtures and their physical/kinematic geometry;
- PA/video/scenic objects that can obstruct placement or beam paths;
- target volumes, focus regions and audience direction;
- object transforms, dimensions, parent/child mounting relationships and provenance.

No role may silently overwrite verified physical facts in order to make its design easier.

## Collaboration model: negotiation loop, not one-way pipeline

Stage/scenic, lighting and structural design are tightly coupled. The product must support
iterative negotiation rather than a single handoff.

```text
Production Brief / Venue / Real Inventory
                  |
                  v
        STAGE_SCENIC_DESIGNER
             <-------->
         LIGHTING_DESIGNER
                  |
                  v
      STRUCTURAL_RIGGING_ENGINEER
                  |
       feasible / adjustment /
       conflict / unknown
                  |
                  +-------------------+
                  |                   |
                  v                   v
        STAGE_SCENIC revision   LIGHTING revision
                  \                   /
                   \                 /
                    +---- Spatial ----+
                           |
                           v
                  physical re-check
```

Examples of valid negotiation:

- Scenic asks for two tall side towers. Lighting asks to move them outward to gain useful
  cross-light geometry. Structural/Rigging may accept one side, reject the other because of
  verified support/venue constraints, and return a buildable alternative.
- Lighting asks for a steep side/back fixture position. Structural/Rigging checks whether a
  real support location exists, whether the luminaire/clamp/rotation envelope clears the
  structure, and whether the resulting load belongs on that structure.
- Structural/Rigging may require an extra support or changed span. Scenic then decides how
  that change should be visually integrated instead of allowing the engineering layer to
  redesign the artistic composition by itself.

A constraint response should preserve the original design intent where possible. It should
not reduce every conflict to a generic safe layout.

## Physical-feasibility contract

Future production-design artifacts should be able to report at least:

```text
PASS
PASS_WITH_ADJUSTMENT
RESOURCE_CONFLICT
STRUCTURAL_ANALYSIS_REQUIRED
ENGINEERING_SIGNOFF_REQUIRED
IMPOSSIBLE
UNKNOWN
```

`PASS` means the bounded checks ZEN is actually authorized and equipped to perform have
passed. It never means universal legal or structural certification.

`UNKNOWN` is a first-class result. Missing manufacturer data, venue support data, outdoor
wind assumptions, floor loading, connection details or inventory identity must not be
replaced with plausible model guesses.

## Data authority

For physical truth, use this authority order:

1. current venue/engineering documents and operator-confirmed measured facts;
2. exact manufacturer model data, manuals, load tables and verified structural data;
3. current real inventory and exact equipment identity;
4. validated CAD/MVR/GDTF/imported production data with provenance;
5. explicit human-entered assumptions labelled as assumptions;
6. visual/model inference, advisory only.

A photo, render, vision-model observation or LLM inference can identify a question or propose
a hypothesis. It does not establish truss capacity, WLL, support capacity, Layher assembly
approval, floor loading, wind design, or a legally meaningful structural fact.

## Deterministic engineering boundary

Language models may reason about requirements, conflicts and alternatives. Numerical
engineering checks must use verified data and deterministic calculation/engineering tooling
where the task requires them.

Candidate future integrations include dedicated structural analysis, manufacturer load
tables, CAD/rigging calculation systems and scaffold planning systems. A solver result still
does not automatically grant engineering sign-off.

Required separation:

```text
AI DESIGN / CONSTRAINT REASONING
        |
        v
VERIFIED PRODUCT + VENUE DATA
        |
        v
DETERMINISTIC CALCULATION / ANALYSIS
        |
        v
HUMAN / VENUE / ENGINEERING REVIEW where required
```

The same Preview/Approval philosophy used by ZEN's MA execution path applies conceptually:
high-consequence physical output must remain reviewable and attributable.

## Lighting-position constructability

The collaboration must evaluate more than whether a structure can carry static weight.
Lighting positions also need to be useful.

Future checks may include, when reliable geometry/data exists:

- clamp/hanging-point compatibility;
- luminaire body, yoke and head rotation clearance;
- required safety attachment and cable/service access;
- usable Pan/Tilt target reach;
- whether desired targets are too close to a physical movement limit;
- beam-path obstruction by structure, scenic, LED, PA or other fixtures;
- throw-distance and beam/zoom implications;
- fixture-to-fixture collision and practical spacing;
- whether a nominally reachable position is awkward enough that Lighting should revise it.

This is where Lighting Designer, Spatial System and Structural/Rigging Engineer must exchange
constraints repeatedly rather than treating fixture XYZ as sufficient proof.

## Real-inventory model

Production design must reconcile proposals against actual available material.

Examples include:

- truss make/family/model and segment lengths;
- corners, junctions, base plates and connection hardware;
- Layher/scaffold standards, ledgers, diagonals, decks, bases, stairs and guardrails;
- motors/hoists and verified WLL;
- clamps, rigging hardware and approved accessories;
- stage decks, risers and stairs;
- lighting fixtures and their verified weights/geometry;
- LED/scenic/audio/video loads when they participate in the structure.

```text
DESIGN REQUIREMENT
        !=
AVAILABLE STOCK
```

A shortage is a `RESOURCE_CONFLICT` or a reason to redesign/source equipment. It is not
permission to invent inventory.

## Scene interchange and physical model

MVR/GDTF are preferred candidates for interoperable entertainment-scene/device data when the
source data is available and trustworthy. MVR is explicitly intended to exchange scene
geometry and objects such as fixtures, trusses and video screens while maintaining hierarchy
and device relationships. This makes it relevant to the future shared Production Spatial
Model, but importing MVR/GDTF does not by itself prove structural safety.

Blender/glTF may remain useful for visualization and richer scenic geometry. It is not the
structural authority merely because it contains a mesh.

## Model/provider responsibilities

Provider choice is replaceable and must not become architecture.

Current candidate division:

- a strong multimodal model such as Gemini may act as a Visual Production Interpreter for
  venue plans, reference images, renders, PDFs and scenic context;
- the ZEN reasoning layer may coordinate Stage/Scenic, Lighting and Structural/Rigging
  requirements and negotiate constraint-preserving revisions;
- deterministic engineering/calculation tools remain authority for numerical engineering
  checks that they are actually configured to perform.

A vision model observation remains visual evidence, not verified structural fact.

## Expected future outputs

A mature Production Design run may eventually produce:

- Stage/Scenic design artifact;
- Lighting requirements / light-plot intent;
- Production Spatial Model;
- Rigging/structural proposal;
- fixture and structural placement map;
- rigging/load list with provenance;
- material/BOM requirement list;
- actual-inventory reconciliation;
- collision/clearance report;
- unresolved-constraint report;
- drawing/export package for human review.

Output formats are not yet authorized or fixed by this architecture capture.

## Relationship to current ZEN mainline

This direction extends the existing long-term Show Agent Controller and cross-department
production model. It does not change the current M4 acceptance gate.

It also does not replace the existing historical `RIG_DESIGNER` role by name automatically.
That role currently concerns lighting/spatial bootstrap. A future implementation must decide
whether to rename/split/migrate it without breaking established artifacts or operator
workflow.

No current authorization is granted for:

- production code for these new roles;
- new permanent provider stages;
- automatic structural calculations;
- automatic Truss/Layher selection;
- venue/engineering approval;
- MA2 writes, Stage geometry writes, Patch/Address/Fixture identity changes;
- changing the active Spatial vNext acceptance gate.

## Research anchors

These sources establish useful industry boundaries and interoperability concepts. They are
research anchors, not a substitute for current project-specific engineering data.

- Vectorworks Braceworks: integrated entertainment rigging modeling and structural/FEM
  analysis, with calculation reports intended to be reviewed/validated in engineering
  workflows:
  https://www.vectorworks.net/en-US/braceworks
- Vectorworks Braceworks structural-analysis concept:
  https://app-help.vectorworks.net/2027/eng/VW2027_Guide/Braceworks/Concept_Braceworks_structural_analysis.htm
- GDTF/MVR developer documentation and MVR 1.6 specification:
  https://gdtf-share.com/help/developers/
  https://gdtf-share.com/help/developers/mvr_1_6/index.html
- Prolyte current manuals and load-table guidance:
  https://www.prolyte.com/support/manuals
- Layher technical documentation / verified structural calculations / assembly instructions
  and Layher SIM digital planning:
  https://www.layher.com/en/services/downloads
  https://www.layher.com/en/knowledge/layher-sim

## First future bounded slice

Do not start by building a full structural solver.

The first implementation slice, when separately authorized, should only define a read-only
`Production Physical Context` and a negotiation artifact that can express:

1. verified stage/scenic geometry;
2. verified real inventory identities;
3. Lighting position requirements;
4. structural/rigging constraints and unknowns;
5. conflict-preserving revision requests;
6. explicit feasibility status and provenance.

No physical mutation or safety claim is needed to prove that collaboration model.
