# ZEN Product Roadmap

## Use

This is a milestone tree, not a percentage estimate or a promise that every
listed capability must be implemented independently. A milestone advances only
through its stated acceptance gate. Shared abstractions are preferred to
one-off capability projects.

## Milestone tree

### M1 — Designer Foundation

**Goal:** reason from Song/Performance context to Design Intent and Visual
Strategy using traceable professional knowledge rather than fixture-name rules.

Includes evidence/provenance boundaries, human-like Design Intent, repetition,
progression, restraint, hierarchy, and external knowledge ingestion.

**Done means:** the reasoning layer is sufficiently traceable and bounded to
support real expressive case experiments without fabricated knowledge.

### M2 — Expressive Capability

**Goal:** allow typed plans to express a useful professional lighting language
without bypassing Design Intent or evidence boundaries.

Potential capability families include density, color, movement, texture,
timing/punctuation, focus/position, beam/aerial, and other justified families.
This is not a fixture-name checklist.

**Done means:** multiple expressive mechanisms can be proven useful,
traceable, realizable, context-aware, and reviewable in bounded cases; the
result does not depend on artificial rules or unsupported Show facts.

### M3 — Show / Rig Adaptation

**Goal:** adapt reasoning to actual resources and imperfect information rather
than fixed fixture roles.

Includes Current Show inventory, Show-bound technical capability, visual
affordance where known, unknown-safe behavior, Existing Show/confirmed-layout
routes, and optional assisted planning.

**Done means:** case-specific resource selection remains provenance-bearing,
does not invent visual/spatial facts, and handles incomplete rig information
with bounded fallbacks.

### M4 — Professional MA2 Implementation

**Goal:** turn valid intent and strategy into clean, native, maintainable MA2
programming.

Acceptance covers Groups, Presets, Sequences/Cues, tracking/Cue Only,
Block/Unblock when justified, Effects/MAtricks/Speed Masters where justified,
Executors, edit/update workflows, cleanup/recovery, naming and handover.
“Works but messy” fails this milestone.

### M5 — Focus Execute

**Goal:** reach a rehearsal/refinement-ready Show quickly.

Acceptance is the Operator Handover Test: Zen can understand, run, modify,
recover, and continue the Show manually through normal MA workflows, with low
`TIME_TO_REFINEMENT`.

### M6 — Production Validation

**Goal:** demonstrate reliability with multiple songs, rigs, venues,
incomplete information, and real operator changes. One successful A/B case is
not production readiness.

## Current mainline

```text
CURRENT_MILESTONE: M4 — PROFESSIONAL MA2 IMPLEMENTATION
DEFAULT_DESIGN_MODE:
  VERIFIED KNOWLEDGE / CACHE
  -> ONE PRIMARY LIGHTING DESIGNER CALL
  -> OPTIONAL ONE DELTA REVISION
  -> ZEN ARTISTIC PLAN COMPILER
  -> STRICT INTERNAL SHOW PLAN
  -> DETERMINISTIC MA2 BUILDER
  -> READBACK
DEFAULT_PROVIDER_CONTRACT: ARTISTIC_CUES_V0_1
STRICT_INTERNAL_SCHEMA_AUTHORITY: ZEN
LEGACY_MULTI_AGENT_DEFAULT: NO
PAID_PROVIDER_ALLOWED: NO
```

The first real programming path is now proven on the fingerprinted Test Show.
ZEN has successfully compiled AI-authored artistic cue intent into native MA2
programming, created six Cues, assigned a new Sequence to Page 2 / Executor
2.002, and passed Sequence/Cue/Executor readback while preserving Group order,
XYZ, protected Fixture 9999, the prior Sequence 301 baseline, and Executor
2.001.

The current product objective is therefore no longer "make a provider emit a
perfect internal JSON document" and no longer "run every historical role on
every song." The default path is the lean Design Mode defined in
`docs/ZEN_DESIGN_MODE.md`.

Song-specific constraints belong at the calling task boundary. The generic
Artistic Plan Compiler must remain song-agnostic: it may normalize
representation and attach ZEN-owned operational metadata, but it must not
encode universal assumptions such as "every song has six cues" or fixed
SHEESH section labels.

The historical Researcher / Rig Designer / Position Designer / Lighting
Designer / Critic / Finalizer runtime remains available for explicit research,
spatial bootstrap experiments, independent deep review, and regression
comparison. It is not the ordinary song-programming default.

Near-term mainline:

1. keep the lean one-call design path stable;
2. use Knowledge/State and cached compact context instead of repeatedly sending
   full Show dumps to the model;
3. implement delta-first artistic revision so a local Cue/region change does
   not restart the full design pipeline;
4. expand typed artistic capability only when the corresponding deterministic
   MA2 Builder/readback path is actually verified;
5. keep live operation event-driven and local-first so routine state monitoring
   costs zero model calls.

M2 expressive-learning work remains useful as a supporting knowledge track,
but it no longer justifies automatically inserting extra model roles into the
default product path.

## Ongoing tracks — non-interrupting by default

| Track | Purpose | Boundary |
| --- | --- | --- |
| Industry Design Learning | Acquire broad, scoped, provenance-bearing conditional reasoning. | Research does not become a rule or interrupt a milestone automatically. |
| Fixture Market Learning | Approximately every 120 days, discover materially new fixture technology and its affordances. | Discovery does not expire existing knowledge or select equipment. |
| MA / Console Knowledge | Improve native-console judgment and implementation options. | Must follow learning evidence and Stable Operator Contract. |
| Future MA3 Architecture | Preserve separable capability/resolution boundaries. | No MA3 Builder implementation is currently authorized. |
| OpenCode ZEN Quota HUD | Side-track: expose one normalized remaining-capacity indicator inside OpenCode, e.g. `ZEN 73%`, without requiring the operator to inspect individual providers. | PARKED / non-blocking. Display-only first; no paid-provider enablement and no routing-policy changes until explicitly resumed. |
| MA3D Scene Read / Full Stage Context | Future read-only scene ingestion from grandMA2 Stage View / MA 3D for stage, truss, LED/scenic objects, object transforms, dimensions, hierarchy, and visual context. | PARKED / non-blocking. Do not interrupt the current MA2 programming mainline; fixtures remain the only fully proven structured scan path today. |

## Fixture knowledge boundary

```text
Fixture learning != fixture selection
Fixture capability != visual role
Fixture type != artistic identity
```

For an Existing Show, use only its current verified inventory. For a
user-confirmed rig, use only confirmed resources. Only an appropriate flexible
or large-production planning case may run a human-reviewable
`FIXTURE_REQUIREMENT_ASSESSMENT`.

That assessment may conclude `NOT_NEEDED`, `OPTIONAL_BENEFIT`,
`RECOMMENDED_FOR_DESIGN_GAP`, or
`REQUIRED_FOR_EXPLICIT_PRODUCTION_REQUIREMENT`; it considers design fit,
availability, budget, reliability, serviceability, console/profile support,
rental/inventory reality, and production constraints. Newness is never a
selection priority by itself.

Fixture labels never establish a permanent artistic function. A strobe-capable
resource can be background material, texture, pulse, punctuation, or unused
only where verified action capability and case context justify it. A hybrid or
spot can expose several visual materials without acquiring a fixed role.

## Design knowledge boundary

Technical fixture data teaches what a tool can do; lighting-design knowledge
teaches how and why to use it. Keep them separate.

Industry design knowledge must be broad and multi-source. YouTube is a
first-class source alongside official/manufacturer education, interviews,
walkthroughs, conference panels, trade press, podcasts, books, case studies,
and lower-classified professional community material. Video evidence should
retain title, publisher/channel, speaker, date, timestamp where available, a
short contextual extract, and scope. Do not store complete videos or
transcripts.

Normalize recurring conditional reasoning, for example “in contexts where X,
designers may use Y because Z,” rather than recipes such as “chorus = Y.”
Zen preference remains personalization among valid alternatives; it does not
replace general professional knowledge or technical facts.

## Current discussion corrections

- Current Show visual-relationship fields are optional case evidence, not
  universal intake requirements.
- Fixture visual use depends on placement, orientation, geometry, Show context
  and Design Intent.
- `HYBRID`, `SPOT`, `BEAM`, `WASH`, and `STROBE` labels do not define fixed
  artistic functions.
- Possible visual affordances are not role assignments and require verified
  action capability plus case context.
- Broad industry evidence, not Zen’s habits alone, supplies the general design
  prior; Zen preference remains a distinct layer.


## Parked side-track — OpenCode ZEN Quota HUD

**Status:** RECORDED / PARKED / NON-BLOCKING

**Purpose:** Use OpenCode's own plugin/UI surface to show one operator-facing
remaining-capacity value for the ZEN free-provider pool. The normal view should
answer only: “roughly how much ZEN capacity is still usable?” The operator does
not need to care which provider contributes it.

Example normal status:

```text
ZEN 73%
```

An optional expanded view may later show estimated remaining full Designs,
Revisions, pool health, free-only state, and next known refill/reset time.

This is **not** a raw average of provider quota percentages. Providers use
different units and reset rules, so a future Quota Engine should normalize
available capacity from whatever evidence is actually obtainable, potentially
including provider-reported remaining quota, ZEN-observed call/token/neuron
usage, provider health, role eligibility, recent success rate, and known reset
windows.

Initial implementation boundary when this side-track is resumed:

1. OpenCode integration is UI/plugin-only; do not fork OpenCode merely for this.
2. ZEN remains the authority for quota/capacity calculation.
3. The first version is display-only and must not change provider routing.
4. `PAID_PROVIDER_ALLOWED=NO` remains unchanged.
5. Missing provider quota telemetry must remain UNKNOWN/estimated rather than
   fabricated.
6. This side-track must not interrupt the current MA2 design/programming
   mainline.

**Future acceptance:** OpenCode can render a stable `ZEN <percent>%` status
from a local ZEN quota-state artifact, with clear provenance for measured,
derived, and unknown inputs. Routing-aware conservation modes are a separate
future decision, not part of this parked task.


## Parked side-track — MA3D Scene Read / Full Stage Context

**Status:** RECORDED / PARKED / NON-BLOCKING

**Purpose:** When the core MA2 programming path is stable, allow ZEN to consume
a richer stage scene than fixture-only geometry. The intended source may be
grandMA2 Stage View and/or the MA 3D application joined to the same session.

Future scene evidence may include, where reliably obtainable:

- stage/deck geometry;
- truss and support objects;
- LED walls and scenic objects;
- generic 3D objects;
- object XYZ, rotation and dimensions;
- object grouping/hierarchy;
- fixture objects in scene context;
- a visual Stage View / MA 3D screenshot as optional visual evidence.

Important boundary:

```text
Stage View can display an object
!=
ZEN currently has a structured authoritative reader for that object
```

Today the proven structured scan path is fixture-oriented. A future read-only
Scene Adapter should separate machine-readable scene facts from visual
evidence. Numeric/object properties should come from structured data where
possible; screenshots should help interpret composition and space rather than
replace exact object metadata.

Potential future flow:

```text
grandMA2 / MA 3D scene
        ↓
read-only Scene Adapter
        ↓
ZEN Scene Model
        ↓
Spatial Designer
        ↓
existing deterministic validation / write paths
```

Do not make MA 3D, full-stage object scanning, truss ingestion, scenic-object
recognition, or visual scene parsing a prerequisite for the current ZEN MA2
programming milestone. This side-track resumes only after the basic path from
AI lighting intent to native MA2 Preset/Cue/Sequence execution is proven.
