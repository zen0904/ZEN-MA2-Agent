# ZEN Production Role Contracts

Status: ARCHITECTURE_V0_1
Implementation authority: NOT_GRANTED
Parent: docs/ZEN_PRODUCTION_DESIGN_SYSTEM.md

## 1. Why role contracts exist

Production design fails when responsibilities blur.

These contracts define what each role may decide, what evidence it receives, what it must
return, and which facts it may never invent. They also define how disagreement is exchanged
without silently letting one role overwrite another.

## 2. Shared rules

All roles:

- operate on the same Production Physical Context revision;
- cite evidence/provenance IDs for physical claims;
- distinguish FACT, ASSUMPTION, REQUEST, PROPOSAL, and UNKNOWN;
- may request another role to revise;
- may not mutate another role's accepted intent without an explicit negotiation result;
- must preserve unresolved questions;
- must not turn vision inference into structural truth;
- must not create raw MA2 commands or bypass department execution boundaries.

## 3. STAGE_SCENIC_DESIGNER_ENGINEER

### Receives

- production brief and visual references;
- venue geometry/dimensions;
- audience and performer context;
- available stage/scenic inventory;
- Lighting position requirements;
- Structural/Rigging constraints;
- LED/video requirements that affect stage form;
- operator/client requirements.

### Decides

- stage/scenic visual language;
- plan/elevation composition;
- platforms, risers, stairs and performance-space relationships;
- scenic forms and envelopes;
- LED/video placement as stage architecture;
- scenic module boundaries;
- assembly-aware scenic interfaces;
- visible vs hidden structure as a design choice;
- visual adaptation when engineering constraints change geometry.

### Must output

Architecture-level fields:

~~~text
design_intent
stage_surfaces
scenic_objects
video_surface_intent
performer_routes
module_intent
interface_requirements
lighting_interface_requests
structural_interface_requests
fabrication_unknowns
assumptions
evidence_refs
revision_reason
~~~

### Must not decide

- allowable structural capacity without verified engineering evidence;
- truss WLL by intuition;
- scaffold structural adequacy;
- venue roof/pick capacity;
- legal approval;
- motor WLL if exact equipment is not verified;
- final Lighting artistic behavior.

## 4. LIGHTING_DESIGNER

### Receives

- Stage/Scenic proposal;
- Production Physical Context;
- performer/audience targets;
- current/available fixture capabilities;
- structural mounting regions/constraints;
- song/show artistic context where relevant.

### Decides

- visual lighting strategy;
- required directions/angles;
- position-region requirements;
- fixture capability/family requirements;
- target coverage;
- acceptable compromises and artistic alternatives;
- whether asymmetry, lower height or changed placement still preserves intent.

### Physical request shape

A Lighting position request should be semantic before it is exact hardware:

~~~text
request_id
purpose
preferred_region
acceptable_region
preferred_height
height_tolerance
target_regions
direction_intent
fixture_capability_need
quantity_range
beam_clearance_need
serviceability_need
priority
artistic_cost_if_changed
~~~

Exact fixture/product assignment comes later from verified resources.

### Must not decide

- unsupported load capacity;
- structural support design;
- fabricated venue pick points;
- missing fixture weight/geometry;
- final Scenic composition outside negotiated changes.

## 5. STRUCTURAL_RIGGING_ENGINEER

### Receives

- exact physical-context revision;
- Scenic geometry/interfaces;
- Lighting position requests;
- exact known structural inventory;
- exact device/load inventory;
- venue support/floor/roof constraints where available;
- manufacturer/engineering data refs.

### Decides within evidence

- whether requested support geometry is compatible with exact available systems;
- whether required product identity/data is missing;
- whether a request fits bounded verified load-table/configuration rules;
- where collision/clearance/support conflicts exist;
- whether external analysis/sign-off is required;
- feasible alternatives that minimize artistic damage.

### Must output

~~~text
review_id
context_revision
scope
status
checked_objects
verified_constraints
load_cases_considered
inventory_conflicts
clearance_conflicts
required_adjustments
acceptable_alternatives
required_external_analysis
required_human_review
unknowns
evidence_refs
~~~

### Must not decide

- an artistic winner among multiple equally feasible visual alternatives;
- missing numerical engineering values by estimate;
- that software analysis equals legal approval;
- that one manufacturer's table applies to a different product;
- that a photograph proves product identity.

## 6. SPATIAL_SYSTEM

### Receives

Evidence-backed geometry updates only.

### Owns

- IDs;
- coordinate frames;
- transforms;
- dimensions;
- parent/mount relationships;
- geometry provenance;
- revision history;
- confidence/state of each physical field.

### Does not own

- lighting style;
- scenic aesthetics;
- structural certification.

## 7. Negotiation artifact

Architecture-level proposed shape:

~~~json
{
  "schema": "zen.production.negotiation.v0.1-draft",
  "negotiation_id": "NEG-001",
  "context_revision": "PPC-0007",
  "raised_by": "LIGHTING_DESIGNER",
  "affected_roles": [
    "STAGE_SCENIC_DESIGNER_ENGINEER",
    "STRUCTURAL_RIGGING_ENGINEER"
  ],
  "intent": "preserve steep side cross-light from both sides",
  "requested_change": {
    "object_ref": "SIDE_TOWER_SR",
    "change": "move outward"
  },
  "constraint": {
    "classification": "VERIFIED_PHYSICAL_CONSTRAINT",
    "evidence_refs": ["VENUE-014"]
  },
  "responses": [],
  "resolution": "UNRESOLVED"
}
~~~

This is a design contract, not an implemented schema.

## 8. Resolution vocabulary

~~~text
ACCEPTED_AS_PROPOSED
ACCEPTED_WITH_ADAPTATION
REJECTED_ARTISTICALLY
RESOURCE_CONFLICT
STRUCTURAL_ANALYSIS_REQUIRED
ENGINEERING_SIGNOFF_REQUIRED
IMPOSSIBLE
UNKNOWN
~~~

A Structural/Rigging constraint can force rejection of one physical proposal. It does not get
to select the final artistic alternative if more than one feasible option remains.

## 9. Priority conflicts

Use:

~~~text
SAFETY / VERIFIED PHYSICAL CONSTRAINT
    >
VENUE / LEGAL / ENGINEERING REQUIREMENT
    >
OWNER-APPROVED PRODUCTION REQUIREMENT
    >
ARTISTIC INTENT
    >
CONVENIENCE / AUTOMATION PREFERENCE
~~~

Within the artistic layer, no deterministic score chooses between Stage/Scenic and Lighting.
The owner/creative lead decides unresolved aesthetic tradeoffs.

## 10. Revision discipline

A revision should be delta-first.

If one tower position is blocked, do not regenerate the entire stage. Preserve unchanged
accepted geometry and revise only affected objects/requirements.

Every revision carries:

- parent revision ID;
- reason;
- changed objects;
- roles affected;
- evidence that caused the change;
- feasibility result.

## 11. Role/provider mapping

Roles are semantic product responsibilities, not model names.

Possible runtime assignment:

~~~text
STAGE_SCENIC_DESIGNER_ENGINEER
  -> strong multimodal / design-capable provider

LIGHTING_DESIGNER
  -> ZEN Primary Lighting Designer / interactive ChatGPT / configured provider

STRUCTURAL_RIGGING_ENGINEER
  -> reasoning provider + deterministic engineering tools

SPATIAL_SYSTEM
  -> deterministic data/services
~~~

No role gains extra authority because a particular provider is perceived as smarter.
