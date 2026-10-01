# ZEN Production Design System

Status: OWNER_APPROVED_ARCHITECTURE_V0_1_COMPLETE
Owner decision date: 2026-10-02
Implementation authority: NOT_GRANTED
Current M4 / Spatial acceptance gate: UNCHANGED

## 1. Purpose

ZEN Production Design System is the future production-planning layer that coordinates:

- STAGE_SCENIC_DESIGNER_ENGINEER
- LIGHTING_DESIGNER
- STRUCTURAL_RIGGING_ENGINEER
- the shared SPATIAL_SYSTEM

Its job is to make one coherent production proposal from real venue geometry, real stage
dimensions, real inventory, artistic requirements and physical constraints before any
department-specific execution is treated as buildable.

The governing distinction is:

~~~text
ARTISTICALLY DESIRABLE
!=
PHYSICALLY CONSTRUCTABLE
!=
ENGINEERED / APPROVED
~~~

A production plan is mature only when those states are explicit instead of being collapsed
into one vague "looks possible" answer.

## 2. Product boundary

This system extends ZEN's long-term Show Agent Controller. It does not replace:

- the existing grandMA2 Lighting execution path;
- the existing Spatial System vNext;
- professional stage/scenic fabrication practice;
- qualified riggers;
- venue engineering;
- structural-analysis software;
- legally required engineering/competent-person review;
- human production management.

The AI layer may propose, compare, negotiate and prepare reviewable drawings/data. It may not
invent structural truth or convert an unverified visual proposal into a safety approval.

## 3. Core roles

### 3.1 STAGE_SCENIC_DESIGNER_ENGINEER

This is deliberately a combined creative + scenic-technical role.

It owns:

- stage visual concept and proportion;
- MAIN_STAGE / RUNWAY / B_STAGE / RISER / PLATFORM topology;
- scenic forms, skins, masks, frames and visible architecture;
- LED/video surfaces as stage-form elements;
- performer circulation, entrances, exits, stairs and usable performance areas;
- sightlines and audience-facing composition;
- modularization of scenic pieces for fabrication, transport, assembly and strike;
- scenic interface dimensions and attachment requirements;
- non-structural fabrication intent, material concept and finish intent;
- coordination of locations where lighting, video, PA or automation need physical interfaces;
- revision of the scenic design when lighting or structural constraints make the first proposal impractical.

It may design a scenic tower, frame, portal, fascia or platform concept and describe how it is
intended to be fabricated. It does not self-certify the primary load path, support capacity,
suspension safety, temporary-structure stability or legal structural adequacy.

Detailed role I/O is defined in docs/ZEN_PRODUCTION_ROLE_CONTRACTS.md.

### 3.2 LIGHTING_DESIGNER

Lighting Designer owns the lighting picture and the physical requirements needed to realize it.

It owns:

- visual hierarchy, direction, contrast, density and restraint;
- useful lighting-position regions and preferred mounting heights;
- front / side / back / cross / overhead / floor relationships;
- target and focus requirements;
- aerial/beam-path requirements;
- fixture-family/capability requirements without inventing unavailable inventory;
- useful Pan/Tilt working range and desired target coverage;
- placement requests that preserve serviceability and realistic spacing;
- revision of lighting intent when a requested position is physically poor or impossible.

Lighting Designer does not create a fake truss, rigging point or WLL merely because an angle is
artistically valuable.

### 3.3 STRUCTURAL_RIGGING_ENGINEER

Structural/Rigging Engineer owns physical constructability and engineering constraint review.

It owns, only where supported by verified data:

- exact truss family/model, segment, corner and connection compatibility;
- Layher/scaffold/system component compatibility and assembly constraints;
- towers, bases, outriggers, bracing and support geometry;
- motors/hoists, pick points and support reactions;
- attached loads from lighting, scenic, LED, audio, video and other departments;
- span/load/deflection checks within verified manufacturer/engineering data;
- clearance, collision, movement envelope and maintenance access;
- support/floor/venue interface questions;
- assembly/strike feasibility;
- actual inventory reconciliation;
- identification of cases requiring external structural analysis or sign-off.

It may return UNKNOWN or ENGINEERING_SIGNOFF_REQUIRED. Those are successful safe outcomes
when the evidence is insufficient for a stronger claim.

### 3.4 SPATIAL_SYSTEM

Spatial System is the shared physical-world data plane.

It owns no artistic decision and no structural certification. It stores the current,
provenance-bearing geometry and relationships needed by the other roles:

- venue envelope and coordinate frames;
- stage surfaces, performer zones and audience direction;
- scenic objects;
- truss, pipe, tower, scaffold/Layher and supports;
- fixtures and device geometry;
- LED/video and PA objects;
- target/focus regions;
- parent-child mounting relationships;
- dimensions, transforms and confidence/provenance;
- collision/clearance geometry when available.

Verified physical facts may be revised only through an explicit evidence update, not because
a Designer would prefer different numbers.

## 4. Collaboration model

These roles are peers around one production problem, not a one-way generation chain.

~~~text
                 PRODUCTION BRIEF
                       |
        +--------------+--------------+
        |                             |
        v                             v
STAGE_SCENIC_DESIGNER_ENGINEER <--> LIGHTING_DESIGNER
        |                             |
        +--------------+--------------+
                       |
                       v
            STRUCTURAL_RIGGING_ENGINEER
                       |
         +-------------+--------------+
         |             |              |
       PASS       ADJUSTMENT       BLOCK / UNKNOWN
         |             |              |
         |       +-----+-----+        |
         |       v           v        |
         |    Scenic      Lighting    |
         |    revision    revision    |
         |       +-----+-----+        |
         |             |              |
         +-------------+--------------+
                       |
                       v
                 SPATIAL UPDATE
                       |
                       v
                 PHYSICAL RE-CHECK
~~~

A role may request a revision; it does not silently perform another role's creative work.

Examples:

- Lighting asks for side towers farther out to improve cross-light geometry.
- Scenic checks sightline/composition impact and revises the tower form.
- Structural/Rigging checks actual bay/module/truss/support feasibility.
- If only one side can move, Lighting may redesign asymmetrically rather than forcing symmetry.
- The accepted geometry is written back to the shared Spatial proposal with provenance.

## 5. Negotiation rules

Every cross-role conflict must preserve four things:

1. the original intent;
2. the verified physical constraint;
3. the proposed adaptation;
4. the unresolved remainder, if any.

The system must not flatten every conflict into a generic conservative layout.

A negotiation cycle ends when one of these is true:

- ACCEPTED_AS_PROPOSED
- ACCEPTED_WITH_ADAPTATION
- RESOURCE_CONFLICT
- STRUCTURAL_ANALYSIS_REQUIRED
- ENGINEERING_SIGNOFF_REQUIRED
- IMPOSSIBLE
- UNKNOWN

Repeated model disagreement is not a reason to keep generating forever. When new evidence is
required, the cycle stops and asks for that evidence.

## 6. Physical-feasibility states

Canonical architecture-level status vocabulary:

~~~text
PASS
PASS_WITH_ADJUSTMENT
RESOURCE_CONFLICT
STRUCTURAL_ANALYSIS_REQUIRED
ENGINEERING_SIGNOFF_REQUIRED
IMPOSSIBLE
UNKNOWN
~~~

PASS means all checks within the current bounded verified tooling/data passed. It never means
a legal certificate.

## 7. Physical truth authority

Use this precedence:

1. current venue/engineering documents and measured/operator-confirmed facts;
2. exact manufacturer model data, manuals, load tables and approved system documentation;
3. current real inventory with exact product identity;
4. validated CAD/MVR/GDTF/imported scene data with provenance;
5. explicitly labelled project assumptions;
6. visual/model inference as advisory evidence only.

A model looking at a photograph can infer "this appears to be a truss" or "a beam may obstruct
this light path." It cannot infer the exact truss series, allowable load, floor capacity,
approved scaffold configuration or WLL unless those are separately verified.

## 8. Deterministic engineering boundary

Use language models for:

- requirements reasoning;
- alternatives;
- constraint negotiation;
- drawing/document interpretation;
- missing-information detection;
- intent-preserving redesign.

Use deterministic/engineering tools and verified data for:

- load-table lookup;
- span/load comparison;
- reaction/force analysis;
- deflection analysis;
- FEA or equivalent structural analysis;
- scaffold/system configuration checking;
- collision and geometric intersection checks;
- material counting;
- dimension and clearance calculations.

Then use human/venue/engineering review where required.

~~~text
AI DESIGN / NEGOTIATION
        |
        v
VERIFIED PRODUCT + VENUE DATA
        |
        v
DETERMINISTIC CHECK / ANALYSIS
        |
        v
HUMAN / VENUE / ENGINEERING REVIEW
~~~

## 9. Lighting-position constructability

A light position is not proven useful merely because fixture XYZ exists.

When data permits, check:

- mounting/clamp interface;
- structure/chord/accessory compatibility;
- fixture body/yoke/head envelope;
- Pan/Tilt physical reach;
- useful operating margin from movement limits;
- obstruction of the beam path;
- fixture-to-fixture collision;
- scenic/LED/PA obstruction;
- cable/service access;
- safety attachment path;
- throw distance and zoom/beam consequence;
- maintenance/replacement access;
- whether installation orientation creates programming or servicing problems.

The result may cause either a structural revision or a lighting revision.

## 10. Stage/scenic constructability

The scenic role should progressively move from concept to fabrication-aware design:

~~~text
VISUAL CONCEPT
-> DIMENSIONED STAGE/SCENIC LAYOUT
-> MODULE / INTERFACE DEFINITION
-> STRUCTURAL/RIGGING REVIEW
-> FABRICATION-AWARE REVISION
-> REVIEW DRAWING PACKAGE
~~~

Examples of scenic technical data:

- overall envelope;
- module boundaries;
- deck/riser elevations;
- stair dimensions;
- LED opening/enclosure dimensions;
- removable panels;
- assembly direction;
- access hatches;
- cable/service paths;
- interfaces requiring a structural support;
- scenic-piece mass when known;
- center of mass when required and verified;
- finish/material intent.

The scenic role must label unverified material strength, fastening or primary structural
assumptions instead of treating fabrication intuition as engineering proof.

## 11. Real inventory

Production planning must compare requirement against stock.

Relevant inventory classes include:

- truss sections, corners, junctions and accessories;
- Layher/scaffold standards, ledgers, braces, decks, bases, stairs and guardrails;
- towers, base plates, outriggers and ballast systems;
- motors/hoists and rigging hardware;
- clamps and adapters;
- stage decks/risers/stairs;
- lighting fixtures;
- LED cabinets/processors/support frames where structurally relevant;
- scenic modules;
- PA/video equipment where it creates load or spatial obstruction.

DESIGN REQUIREMENT != AVAILABLE STOCK.

A shortage creates an explicit sourcing/redesign decision.

## 12. Scene interchange

MVR/GDTF are preferred entertainment-industry candidates where available.

MVR 1.6 is defined for exchanging complete entertainment scenes and parametric objects
including fixtures, trusses, supports and video screens. GDTF describes device geometry and
physical/logical dependencies such as base/yoke/head/beam geometry.

Those formats can provide strong scene/device evidence, but import does not prove structural
safety.

Blender/glTF can support scenic visualization and geometry exchange. A mesh remains geometry,
not load capacity.

## 13. Provider/model division

Provider identity is replaceable.

Recommended architecture:

- multimodal model: visual production interpretation of plans, venue photos, PDFs, renders,
  reference stages and marked-up drawings;
- ZEN primary reasoning: coordinate the three professional roles and preserve intent across
  constraint revisions;
- deterministic geometry/engineering layer: calculations and machine-verifiable checks;
- human review: approve artistic tradeoffs and engineering/legal outputs where required.

Gemini is currently a plausible multimodal candidate, not a permanent architectural
dependency. GPT/ChatGPT can perform the coordinating reasoning role when operating
interactively. Neither provider becomes structural authority.

## 14. Production artifacts

The intended review package is defined in docs/ZEN_PRODUCTION_DELIVERABLES.md.

At maturity it may include:

- Production Physical Context;
- Stage/Scenic Plan;
- Stage elevations/sections;
- Lighting Plot;
- Lighting Position Schedule;
- Rigging Plot;
- Truss/support schedule;
- motor/pick schedule;
- preliminary load schedule;
- inventory/BOM requirement;
- actual-stock reconciliation;
- collision/clearance report;
- unresolved engineering questions;
- revision/negotiation log;
- export/interchange package.

## 15. Companion architecture documents

Read together:

- docs/ZEN_PRODUCTION_ROLE_CONTRACTS.md
- docs/ZEN_PRODUCTION_PHYSICAL_CONTEXT.md
- docs/ZEN_PRODUCTION_ENGINEERING_EVIDENCE_POLICY.md
- docs/ZEN_PRODUCTION_DELIVERABLES.md

These are architecture contracts, not implemented schemas.

## 16. Relationship to existing RIG_DESIGNER

The historical RIG_DESIGNER in docs/MULTI_AGENT_DESIGN_PLAN.md is a lighting/spatial
bootstrap role. It is not the new Structural/Rigging Engineer and must never be described as
structural authority.

Future migration may rename the historical role to a less ambiguous name, but no runtime
rename is authorized by this documentation task.

## 17. Research basis

Official/currently available anchors reviewed for this architecture include:

- Vectorworks Braceworks:
  https://www.vectorworks.net/en-US/braceworks
- GDTF/MVR developer documentation and MVR 1.6:
  https://gdtf-share.com/help/developers/
  https://gdtf-share.com/help/developers/mvr_1_6/index.html
- GDTF geometry documentation:
  https://gdtf-share.com/help/users/gdtf_builder/geometry/index.html
- Prolyte manuals/load-table guidance:
  https://www.prolyte.com/support/manuals
- Layher technical downloads:
  https://www.layher.com/en/services/downloads
- Layher SIM:
  https://www.layher.com/en/knowledge/layher-sim
- Taiwan OSHA scaffold guidance:
  https://www.osha.gov.tw/media/rojjkges/%E6%96%BD%E5%B7%A5%E6%9E%B6%E4%BD%9C%E6%A5%AD%E5%AE%89%E5%85%A8%E6%AA%A2%E6%9F%A5%E9%87%8D%E9%BB%9E%E5%8F%8A%E6%B3%A8%E6%84%8F%E4%BA%8B%E9%A0%85.pdf

The Taiwan item is a safety/regulatory research anchor, not a complete legal-compliance
checklist. Applicable law/venue rules must be re-verified for the actual project.

## 18. Implementation sequence

No full solver first.

### PDS-001 — read-only Production Physical Context
- schema/validator;
- provenance;
- venue/stage/scenic/structure/device identities;
- actual inventory;
- zero physical writes.

### PDS-002 — negotiation artifact
- Scenic request;
- Lighting request;
- structural constraint;
- adaptation;
- unresolved evidence;
- feasibility state.

### PDS-003 — deterministic geometry checks
- collision;
- clearances;
- device movement envelope;
- beam obstruction;
- material counting.

### PDS-004 — bounded manufacturer-data checks
- exact-product load-table lookup only where semantics are unambiguous;
- no generalized FEA inference;
- explicit escalation.

### PDS-005 — deliverable generation
- drawing/data package;
- schedules;
- BOM;
- unresolved report;
- human review.

A structural solver/FEA integration is a later explicit decision, not implied by these slices.

## 19. Current authorization

This architecture specification is complete enough to guide future implementation.

It does not authorize:

- production code;
- a new default multi-agent pipeline;
- automatic Truss/Layher selection;
- structural sign-off;
- venue approval;
- physical-world mutation;
- MA2 writes or Stage geometry writes;
- changing the active M4 / Spatial acceptance gate.

The active mainline resumes from data/zen_project_control.json.
