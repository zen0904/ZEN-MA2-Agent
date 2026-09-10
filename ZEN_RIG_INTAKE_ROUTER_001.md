# ZEN Rig Intake Router 001

Status: `LOCAL_ONLY / SHADOW_ONLY`. This document and its typed models do not
invoke MA2, Telnet, plugins, the Builder, or the Resolver.

## One user-facing ZEN MA2 Agent

The product exposes one primary entry point. Internal intake and rig-planning
components are routing details, not separate agents the user has to select.

```text
User input
  -> ZEN MA2 Agent intake/router
     -> confirmed layout | optional assisted proposal | existing show reuse
     -> normalized Rig Context
     -> shadow Design Guidance
     -> unchanged production Designer
     -> typed ZEN_SHOW_PLAN
     -> existing Resolver / Builder / Preview / Approval / Verification
```

The right-hand production path is intentionally unchanged. Rig Context enters
only the existing advisory envelope in this release, so the actual deterministic
`ZEN_SHOW_PLAN` remains byte/structurally identical in baseline/shadow tests.

## Typed contracts

- `zen.show_intake.v0.1`: one request, requested task, inventory, facts,
  visual observations, constraints, optional user-confirmed placement, and the
  selected route.
- `zen.rig_context.v0.1`: normalized downstream representation independent of
  whether it originated from the user, a bounded proposal, or a show scan.
- `zen.rig_proposal.v0.1`: a reviewable, semantic placement proposal. It has
  no physical coordinates, MA2 object references, or command fields.

All planning-relevant facts preserve `certainty` (`CONFIRMED`, `INFERRED`, or
`UNKNOWN`) and `source`. Fixture-family roles are explicitly capability
hypotheses, not verified physical placement facts. The context keeps placement
semantics, available/inferred roles, constraints, unknowns, asymmetry, and
shadow-only `KEEP` / `REDUCE` / `OMIT` / `SUBSTITUTE` affordances separate.

## Routing modes

### USER_CONFIRMED_LAYOUT

When the user says where fixtures go, that placement is authoritative:
`layout_source=USER_CONFIRMED`, `planning_status=BYPASSED`. No rig planner
runs and the placement is copied into Rig Context unchanged.

The only exception is transparent safety clarification, not redesign. A user
can confirm a flown location, but if the intake lacks confirmed hanging/load
approval, the layout is retained while the route returns exactly the targeted
`CONFIRM_HANGING_CAPABILITY` requirement. It never silently turns a user
placement into a certified rigging fact.

### ASSISTED_RIG_PLANNING

The planner is optional and currently bounded to a safe floor-only proposal
when the intake confirms `FLOOR_ONLY` and supplies at least an inferred or
confirmed usable floor zone. It emits semantic zones such as
`FLOOR_REAR_LINE` and `FLOOR_REAR_CLUSTER`, a compact rear-line fallback, its
assumptions, and unknowns. It does not invent dimensions, physical coordinates,
structural capacity, or a flying configuration.

When no viable floor zone is known, the router does not issue a broad
questionnaire. It returns one material question: `CONFIRM_SAFE_FLOOR_ZONE`.

### EXISTING_SHOW

An existing scanned show/profile is reused as `layout_source=EXISTING_SHOW_SCAN`
and `planning_status=BYPASSED_EXISTING_SHOW`. The router retains its placement
semantics and profile reference; it does not redraw the physical rig merely
because it can produce a normalized context.

## Partial information and photos

Partial input is normal. A sparse venue request with confirmed inventory,
confirmed `FLOOR_ONLY`, an inferred rear-floor observation, and unknown stage
width/power still produces a bounded floor proposal plus fallback.

Visual observations are intentionally limited to observations. A photo can
enter facts such as `VISIBLE_TRUSS` or `REAR_FLOOR_ZONE_USABLE` only as
`INFERRED`. It cannot confirm structural load, electrical capacity, certified
rigging points, or `SAFE_TO_HANG_FIXTURES`. A visible truss is never permission
to fly fixtures.

## Examples

### User-confirmed layout

Input: 8 LED PAR in a rear floor line; 10 moving heads split between confirmed
front-corner and rear-floor positions; `FLOOR_ONLY`.

Result: planner bypassed. The three exact placement records remain
`USER_CONFIRMED / CONFIRMED` in Rig Context. The downstream shadow advisory
can adapt to the supplied asymmetry or capability limits, but cannot move
fixtures.

### Sparse floor-only venue

Input: 8 LED PAR, 10 moving heads, no CAD, unknown dimensions/power,
`FLOOR_ONLY`, and a photo-derived inferred usable rear floor zone.

Result: a `BOUNDED_PROPOSAL` uses a rear floor line/cluster and states a compact
rear-line fallback if side zones prove unavailable. No hanging, power, or exact
dimension claim is made.

### LED-only

The normalized context supplies only inferred `COLOR_FIELD`, `DENSITY_LAYER`,
and `TIMING_LAYER` roles. Its shadow affordances preserve a complete low state
with color/negative space, develop medium through density, and use timing only
where appropriate. It does not depend on movers, beams, gobos, or position
language.

### Asymmetric confirmed layout

If the user confirms unequal left/right moving-head counts, the record carries
`ASYMMETRIC_LAYOUT=CONFIRMED`. The planner remains bypassed; downstream
reasoning can see that it should adapt rather than pretend the layout is
mirrored.

## Cross-rig reasoning carried forward

Evaluation 002's successful reasoning is represented as bounded context rather
than a universal fixture-priority list:

- preserve only the roles relevant to the section;
- deliberately reduce or omit nonessential roles to create negative space;
- combine roles where a medium rig has one flexible source;
- substitute LED color/density/timing language when mover language is absent;
- use explicitly declared asymmetry intentionally rather than forcing symmetry.

Those choices remain `SHADOW_ONLY` review material. They do not select MA2
Groups, Presets, Effects, cue timing, dimmer values, fades, or fixture positions.

## Safety and not-run boundaries

- No full computer vision, image segmentation, photogrammetry, SLAM, 3D
  reconstruction, dimensions, electrical calculation, or rigging analysis.
- No actual venue safety certification.
- No Guidance-Assisted Designer A/B.
- No `ZEN_STYLE_PROFILE`.
- No MA2/Telnet/plugin action and no MA2 object write.

## Long-term workflow

The eventual one-agent workflow accepts whatever is available: venue photos,
fixture counts/types, known restrictions, song/script, or a scanned show. It
creates a bounded venue/rig understanding, optionally proposes placement,
normalizes Rig Context, gives context-aware design guidance, then retains the
established typed-plan, deterministic-build, preview, approval, and verification
path. If the user already knows the placement, the venue/planning path is
skipped rather than repeated.

## Current limitation

The assisted proposal is intentionally floor-only and semantic; it is not a
physical plot. Its capability-role inference needs human lighting/venue review
and later real-case validation before any runtime guidance-assisted Designer
experiment.
