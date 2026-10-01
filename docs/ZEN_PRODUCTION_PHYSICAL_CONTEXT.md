# ZEN Production Physical Context

Status: ARCHITECTURE_V0_1_DRAFT_CONTRACT
Implementation authority: NOT_GRANTED
Parent: docs/ZEN_PRODUCTION_DESIGN_SYSTEM.md

## 1. Purpose

Production Physical Context is the future read-only shared-world artifact consumed by
Stage/Scenic, Lighting and Structural/Rigging roles.

It answers:

- what is physically present;
- where it is;
- how objects relate;
- what equipment is actually available;
- which values are verified;
- which values are assumptions;
- what remains unknown.

It is not an artistic plan and not a structural certificate.

## 2. Identity and revision

Every context requires:

~~~text
schema
context_id
revision
created_at
project_id
venue_id
source_hashes
coordinate_frame
units
evidence_ledger
limitations
~~~

Any calculation/review must name the exact context revision it used.

## 3. Coordinate system

Use one explicit project frame. Do not silently equate it with MA2 Stage View, GDTF or MVR
coordinates.

Recommended production frame remains compatible with ZEN's stage-centric convention:

~~~text
origin = STAGE_CENTER
+X = STAGE_LEFT
-X = STAGE_RIGHT
+Y = UPSTAGE
-Y = DOWNSTAGE / AUDIENCE
+Z = UP
length_unit = mm preferred at engineering interchange boundary
~~~

Imports must preserve source coordinate metadata and record the transform into the project
frame.

## 4. Evidence state per field

Physical fields should carry or inherit one of:

~~~text
VERIFIED_DOCUMENT
VERIFIED_MEASUREMENT
VERIFIED_MANUFACTURER
VERIFIED_IMPORT
OPERATOR_CONFIRMED
ASSUMED
VISION_INFERRED
UNKNOWN
~~~

A lower-confidence state never silently upgrades itself.

## 5. Venue

Minimum useful venue model:

~~~text
venue envelope
stage origin/reference
roof/ceiling height
walls/columns/obstructions
audience boundary
loading/access doors where relevant
known rigging/support points
known point capacities if officially provided
floor zones and known limits if officially provided
restricted/no-build zones
egress/fire/access constraints when supplied
~~~

Missing structural venue data remains unknown.

## 6. Stage and scenic objects

Object classes may include:

~~~text
STAGE_DECK
RISER
RUNWAY
B_STAGE
STAIR
RAMP
SCENIC_FRAME
SCENIC_PANEL
PORTAL
TOWER_SCENIC
LED_WALL
VIDEO_SURFACE
MASK
FASCIA
PLATFORM
ACCESS_ZONE
PERFORMER_ZONE
~~~

Each object may carry:

- exact dimensions;
- transform;
- geometry/bounding volume;
- parent;
- intended material;
- known mass;
- structural interface refs;
- service/access zones;
- revision/provenance.

## 7. Structural/rigging objects

Classes may include:

~~~text
TRUSS_SEGMENT
TRUSS_CORNER
TRUSS_JUNCTION
PIPE
TOWER
SCAFFOLD_STANDARD
SCAFFOLD_LEDGER
SCAFFOLD_DIAGONAL
SCAFFOLD_DECK
BASE_PLATE
BASE_JACK
OUTRIGGER
HOIST
MOTOR
PICK_POINT
SLING
SHACKLE
CLAMP
SUPPORT
BALLAST
~~~

Required identity is exact where engineering claims depend on it:

~~~text
manufacturer
family
model
part_number
revision/version if applicable
quantity
unit_mass
verified_capacity_data_ref
connection_system
condition/status if inventory tracking supports it
~~~

Generic "400 mm truss" is not sufficient for a manufacturer load-table claim.

## 8. Devices and loads

Load-bearing planning must include relevant objects from every department.

Examples:

- lighting fixture;
- LED cabinet/frame;
- PA cabinet/array;
- projector;
- scenic piece;
- cable bundle where material;
- video equipment;
- automation element;
- rigging hardware self-weight.

A load record should distinguish:

~~~text
self_weight
payload_weight
dynamic_factor_source
position
attachment_ref
load_case
evidence_ref
~~~

Do not invent dynamic factors.

## 9. Fixture physical model

For Lighting constructability, useful fields include:

~~~text
manufacturer/model
mass
base envelope
yoke envelope
head envelope
mounting interface
safety attachment interface
pan axis/range
tilt axis/range
beam origin
beam direction
zoom/beam range
service clearance
cable connector side/clearance where known
GDTF ref
geometry source
~~~

GDTF can supply useful hierarchy/geometry when the fixture file is trustworthy, but missing
or vendor-authored geometry quality must be respected.

## 10. Mount relationships

Physical graph example:

~~~text
VENUE_PICK_01
  -> MOTOR_01
    -> TRUSS_A
      -> CLAMP_101
        -> FIXTURE_101
      -> LED_SUPPORT_A
        -> LED_WALL_A
~~~

Every child load must be traceable to a support path when structural analysis is attempted.

## 11. Lighting position requirements

Lighting requirements belong beside, not inside, structural facts.

Example:

~~~json
{
  "request_id": "LPR-004",
  "purpose": "steep SR cross-light",
  "preferred_region": "SR_OUTER_HIGH",
  "acceptable_regions": ["SR_OUTER_HIGH", "SR_SIDE_MID"],
  "height_mm": {"preferred": 6500, "min": 5200, "max": 7500},
  "target_regions": ["CENTER", "DSL", "USL"],
  "movement_margin_required": true,
  "priority": "HIGH",
  "artistic_cost_if_changed": "loss of lateral separation"
}
~~~

The numbers are requests until realized against actual geometry.

## 12. Inventory

Inventory is separate from geometry because available stock may not yet be placed.

Track:

- item identity;
- quantity owned/available/rented/planned;
- location/storage if useful;
- reserved quantity;
- condition/out-of-service state;
- compatible accessories;
- evidence timestamp.

Planning compares required_quantity against available_quantity.

## 13. Obstruction and clearance volumes

When geometry exists, preserve separate volumes for:

- hard collision;
- service clearance;
- performer exclusion;
- audience/sightline sensitivity;
- beam-path obstruction;
- movement envelope.

A soft design warning must not be confused with a hard collision.

## 14. Provenance ledger

Example:

~~~json
{
  "evidence_ref": "TRUSS-S36-LOADTABLE-001",
  "classification": "VERIFIED_MANUFACTURER",
  "source": "manufacturer manual",
  "product_identity": "exact series/model",
  "retrieved_at": "2026-10-02",
  "scope": "allowable load table only",
  "limitations": "does not establish venue support capacity"
}
~~~

## 15. Import adapters

Candidate adapters:

- MVR scene import;
- GDTF device import;
- Vectorworks export/interchange;
- venue CAD/DWG/DXF through an approved parser/converter;
- PDF plan extraction;
- Blender/glTF scenic geometry;
- manual measured survey;
- laser-scan/point-cloud derived geometry.

Every adapter must retain source hash and transform provenance.

## 16. Read-only first

PDS-001 should support:

~~~text
IMPORT / ENTER
-> NORMALIZE
-> VALIDATE
-> INSPECT
-> REPORT UNKNOWN
~~~

It should not place real motors, change MA geometry, write a console, or certify a structure.

## 17. Future deterministic queries

Once implemented and verified, the context may support queries such as:

- nearest viable support region;
- collision between fixture movement envelope and truss/scenic;
- target reach from candidate fixture pose;
- beam-path obstruction;
- count of required Layher/truss/stage components;
- inventory deficit;
- exact product data available/missing;
- load case ready/not ready for engineering analysis.

Those queries should return evidence and limitations, not only a boolean.
