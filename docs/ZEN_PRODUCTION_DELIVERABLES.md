# ZEN Production Deliverables

Status: ARCHITECTURE_V0_1
Implementation authority: NOT_GRANTED
Parent: docs/ZEN_PRODUCTION_DESIGN_SYSTEM.md

## 1. Purpose

A production design is useful only if people can build, review, program and revise it.

ZEN's future output should therefore be a coordinated package, not a pretty render plus an
untraceable equipment list.

## 2. Deliverable maturity

Use:

~~~text
CONCEPT
COORDINATION
TECHNICAL_PROPOSAL
ENGINEERING_REVIEW_REQUIRED
APPROVED_FOR_BUILD_BY_HUMAN
AS_BUILT
~~~

ZEN may generate the first four when supported. The last two require explicit human/project
authority and evidence.

## 3. Stage / Scenic Plan

Should show, as applicable:

- venue/stage reference;
- overall dimensions;
- stage/deck/riser/runway geometry;
- scenic objects;
- LED/video surfaces;
- stairs/ramps;
- performer routes/access zones;
- object IDs;
- revision;
- scale/unit;
- unresolved notes.

## 4. Stage elevations and sections

Needed when vertical relationships matter.

Include:

- floor/deck levels;
- truss/tower heights;
- scenic/LED heights;
- fixture mounting regions;
- sightline-critical geometry;
- clearance dimensions;
- section/elevation reference IDs.

## 5. Lighting Plot

Lighting Plot is a physical placement drawing, not the cue program.

Potential fields:

- fixture symbol;
- fixture ID/unit number;
- exact fixture type when selected;
- position/truss/tower;
- X/Y/Z or dimensioned placement;
- orientation;
- purpose/system;
- clamp/accessory where relevant;
- notes for floor/side/special mounting;
- unresolved placement constraints.

Patch, address, universe and network data can be separate layers/schedules and should not be
invented merely to make the plot appear complete.

## 6. Lighting Position Schedule

For each position:

~~~text
position_id
physical_support_ref
height
fixture_count
fixture_types
target/use intent
mounting constraints
service constraints
feasibility status
~~~

This connects artistic Lighting requirements to the physical structure.

## 7. Rigging Plot

Where applicable:

- truss/support IDs;
- exact truss/system identity;
- motors/hoists;
- pick/support points;
- relevant spans;
- attached equipment/load groups;
- load direction/location;
- support/venue references;
- unresolved engineering items;
- analysis/sign-off state.

Do not present preliminary loads as approved loads.

## 8. Truss / support schedule

Track:

- position ID;
- product family/model;
- section lengths;
- corners/junctions;
- connection system;
- orientation;
- support condition;
- self weight;
- source/evidence;
- status.

## 9. Motor / pick schedule

Track, where verified:

- motor ID;
- exact model;
- WLL source;
- location;
- supported structure;
- design/reaction load from analysis;
- venue point ref;
- venue capacity ref;
- status;
- notes.

Missing venue capacity remains explicit.

## 10. Preliminary load schedule

May include:

- load object;
- weight;
- location;
- attachment;
- load case;
- source;
- whether weight is measured/manufacturer/assumed;
- engineering inclusion status.

It is not an engineering report unless generated/reviewed through the appropriate engineering
process.

## 11. BOM / material requirement

Separate:

~~~text
REQUIRED
AVAILABLE
RESERVED
SHORTAGE
SUBSTITUTE_CANDIDATE
~~~

Classes may cover:

- stage modules;
- scenic modules;
- truss;
- scaffold/Layher;
- motors/hardware;
- lighting fixtures;
- clamps/accessories;
- LED/scenic support;
- department-specific hardware.

A substitute candidate is not accepted until compatibility/engineering consequences are
reviewed.

## 12. Inventory gap report

High-value output:

~~~text
item needed
quantity needed
quantity available
gap
why needed
acceptable alternatives
design consequence
~~~

This lets ZEN redesign before load-in instead of discovering shortages during assembly.

## 13. Collision / clearance report

Separate findings by severity:

~~~text
HARD_COLLISION
MOVEMENT_COLLISION
BEAM_OBSTRUCTION
SERVICE_CLEARANCE
ACCESS_CONFLICT
SIGHTLINE_CONFLICT
SOFT_DESIGN_WARNING
~~~

Each finding names exact objects and context revision.

## 14. Structural/Rigging review report

Must include:

- scope actually checked;
- method/tool;
- evidence;
- unresolved inputs;
- feasibility status;
- required changes;
- external analysis/sign-off requirement.

Never summarize unperformed checks as "all safe."

## 15. Negotiation / revision log

Record only meaningful decisions:

- issue;
- affected roles;
- prior intent;
- physical constraint;
- accepted adaptation;
- owner decision when aesthetic tradeoff exists;
- context revision.

This becomes durable production memory.

## 16. Drawing metadata

Every generated drawing/report should carry:

- project;
- venue;
- title;
- drawing ID;
- revision;
- date;
- authoring system;
- scale or NTS;
- units;
- context revision;
- maturity state;
- approval/sign-off state;
- explicit limitations.

## 17. Export candidates

Future exports may include:

- PDF drawing package;
- SVG/DXF/DWG through appropriate tooling;
- MVR;
- CSV/XLSX schedules;
- JSON canonical artifacts;
- glTF/GLB visualization;
- Vectorworks-compatible interchange where technically/licensing-wise appropriate.

Format does not determine authority. A polished PDF can still be only CONCEPT.

## 18. Quality gate before issue

Before a package leaves ZEN, verify:

- all drawings use one known revision;
- dimensions/units are explicit;
- IDs are consistent across plots/schedules;
- inventory counts reconcile;
- unresolved engineering items are visible;
- no VISION_INFERRED capacity became verified;
- no preliminary structural status is mislabeled approved;
- Lighting Plot matches the accepted physical support geometry;
- Stage/Scenic and Rigging drawings do not contradict each other;
- revision metadata is complete.

## 19. As-built feedback

Future field workflow should support:

~~~text
DESIGNED
-> BUILT
-> MEASURED / CORRECTED
-> AS_BUILT CONTEXT
-> Lighting/Spatial recalibration
~~~

Onsite changes should update the shared Production Physical Context rather than living only in
someone's marked-up paper plan.
