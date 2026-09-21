# Multi-Agent Design Plan

Status: the bounded four-role MVP (`RESEARCHER -> LIGHTING_DESIGNER -> CRITIC
-> FINALIZER`) is implemented in `zen_ma2_agent.llm.multi_agent_runtime`.
It is portable, sequential, checkpointed, and ends at a validated
`zen.autonomous_design.v0.1` artifact. A separate conditional live-Show route
is implemented below. The other roles in the longer-term target pipeline
remain plan-only; this document does not implement a Resolver/Builder or any
MA2 write path.

## Current inference/deployment boundary

The four-role MVP is no longer constrained to one CPU-only 7B model.

Current design target:

```text
RESEARCHER
-> role-routed provider

LIGHTING_DESIGNER
-> bounded parallel provider candidates when configured

CRITIC
-> bounded parallel provider candidates when configured

FINALIZER
-> one canonical validated zen.autonomous_design.v0.1 artifact

LOCAL MODEL
-> lightweight 3B-4B class offline/degraded fallback
```

The two physical Worker hosts remain unavailable for current verification and
their actual OS must not be assumed. Worker A is known to have 16 GB RAM and a
GTX 1650 4 GB; Worker B has 16 GB RAM and an older/weaker GPU whose exact model
is still TO_VERIFY. Cloud/free providers may carry primary creative/reasoning
work while local inference preserves degraded/offline capability.

The Provider Router is provider-agnostic and supports OpenAI-compatible slots,
role routing, priorities, `FREE_FIRST`, bounded parallel fan-out, and
replaceable provider/model configuration. Free-tier status is not a permanent
product fact and must be verified at configuration time.

Do not load multiple large local models merely to imitate multi-provider
diversity. Local compute is better spent on lightweight fallback, retrieval,
cache, preprocessing, and orchestration unless later measurements prove a
different allocation useful.

See `ZEN_MULTI_PROVIDER_PARALLEL_POOL_001.md` for the current implementation.

## Conditional live-Show spatial route (read-only)

When a caller explicitly supplies a validated current-Show snapshot, the
runtime executes:

```text
RESEARCHER
-> RIG_DESIGNER
-> POSITION_DESIGNER
-> LIGHTING_DESIGNER
-> CRITIC
-> FINALIZER
```

Without that input, the existing four-role route remains unchanged. The
snapshot is caller-supplied; the LLM module does not scan MA2 or read a
machine-specific path. Its normalized content and Show fingerprint are part
of the context hash and run metadata, and checkpoint resume rejects a
different fingerprint or role order. Cached Show evidence whose fingerprint
does not match is excluded from current truth. Unverified current-fingerprint
capabilities and coordinate-axis semantics remain `UNKNOWN`. Fixture 9999
may be visible in inventory evidence but is marked unavailable for artistic
assignment and placement.

`RIG_DESIGNER` and `POSITION_DESIGNER` are semantic roles routed through the
existing `LIGHTING_DESIGNER` provider-eligibility bucket. Their artifacts are
independently validated against the live inventory and fingerprint; these
roles run sequentially and do not require private provider-role configuration
changes. `LIGHTING_DESIGNER`, `CRITIC`, and `FINALIZER` receive the validated
upstream spatial artifacts according to their role contracts. Finalization
must reference the canonical Position Designer artifact and may not silently
contradict its exact fixture/subfixture coordinates.

The two spatial roles use the same explicit exact-first-schema contract as the
established roles. A deterministic envelope normalizer may add only the known
Rig or Position `schema` identity when that key is wholly absent, every other
required top-level field is already present, and
`codex_artistic_intervention=NONE`. It cannot replace a wrong/blank schema or
add spatial/artistic content. The unchanged role validator still owns all
fingerprint, fixture-reference, protected-fixture, finite-coordinate,
mutation/command and consistency checks. Raw provider output remains separate
from any normalized accepted artifact in secret-safe diagnostics.

Position Designer receives a deterministic, compact `position_context` rather
than the entire live snapshot. In `IMPORTED_EXISTING_SHOW`, this includes
geometry-bearing fixture/subfixture identities with scanned XYZ/rotation and
availability. In `NEW_UNDESIGNED_SHOW`, it instead includes verified resource
identities/capabilities and the canonical ZEN stage frame, with initial XYZ
deliberately excluded. Both modes carry the fingerprint, exact backend-
generated `allowed_placement_refs`, protected references, and limitations.
Patch, Address, unrelated pools, and Fixture 9999 as a placement candidate are
excluded. The prompt requires coordinate metadata to be copied exactly as an
object and every placement identity to come from the allow-list; the validator
checks both. This is structural context reduction only and does not choose or
repair spatial content.

#### Independent stage frame and new-show bootstrap

The runtime also supports the explicit `NEW_UNDESIGNED_SHOW` bootstrap mode.
In this mode, fixture inventory and exact Show-bound capability evidence are
authoritative, while initial fixture XYZ/rotation is `UNDESIGNED` and is not
sent to Rig or Position Designer as a target or calibration input. A Show may
have all fixtures stacked at the same origin. Position resources are derived
from verified inventory/subfixture identities, not fixture extrema; if no
subfixture identity was scanned, the root fixture identity is used rather than
inventing a subfixture number. Fixture 9999 remains unavailable.

The independent `ZEN_STAGE_FRAME_V1` design-space convention uses origin
`STAGE_CENTER`, X positive `STAGE_LEFT` / negative `STAGE_RIGHT`, Y positive
`UPSTAGE` / negative `DOWNSTAGE_AUDIENCE`, and Z positive `UP`. It is bound to
fingerprinted Stage/audience/performer context and is never inferred from raw
fixture positions or Pan/Tilt. Conceptual XYZ is expressed in
`ZEN_CONCEPTUAL_STAGE_UNITS`; metric scale and a direct transform to MA2 Pos
remain unknown. Consequently bootstrap geometry is a virtual design proposal,
not an executable MA2 position map or physical installation approval, and its
comparison to scanned fixture XYZ is recorded as not comparable across frames.

`IMPORTED_EXISTING_SHOW` remains the optional legacy mode: scanned fixture
geometry can inform comparison/calibration, but is not a general prerequisite
for a new ZEN-designed Show. The live-snapshot launcher accepts the mode,
operator Stage context, and Show-bound capability artifact as explicit inputs;
it does not discover them from a machine-local path. Neither mode adds MA2,
Resolver, Builder, or write authority.

This route is design-artifact generation only. It does not call MA2, Resolver,
or Builder, and it does not write geometry. A provider artifact that fails
schema, inventory, evidence, or safety validation stops the route at that
role; downstream roles do not run.

The portable launcher also exposes `--spatial-readiness` for a non-inference
preflight. It normalizes caller-supplied snapshot, operator Stage context, and
Show-bound capability files, verifies the referenced Stage View image hash,
then evaluates conceptual bootstrap readiness without constructing a
`ProviderRouter`. In `NEW_UNDESIGNED_SHOW`, readiness depends on the
fingerprint-bound `ZEN_STAGE_FRAME_V1`, operator-confirmed Stage/orientation/
performer context, complete non-protected fixture identity coverage, and exact
Show-bound capabilities. It does not depend on initial fixture XYZ/rotation,
fixture extrema, Pan/Tilt-derived XYZ signs, or a native MA2 coordinate
transform. A verified transform remains a separate prerequisite for any later
writeback; this preflight never makes Resolver/Builder/Preview or writeback
eligible.

### Live spatial review and bounded revision

Technical execution completion and design review are recorded separately.
For live-Show runs, a validated Critic `severity.classification=BLOCKER`
sets `design_review_status=BLOCKED_BY_CRITIC` even if Finalizer succeeds and
`execution_status=COMPLETE`. Finalizer receives the exact accepted spatial,
lighting, and Critic artifacts plus this runtime-owned state; its output
cannot clear the blocker. `WRITEBACK_ELIGIBLE`, `RESOLVER_ELIGIBLE`, and
`PREVIEW_FOR_WRITEBACK_ELIGIBLE` remain `NO`; a non-blocking Critic result is
not human write approval. Qualitative Critic classifications are
`BLOCKER`, `DESIGN_WEAKNESS`, `OPTIONAL_IMPROVEMENT`, and legacy `NONE`.

The explicit `run_spatial_revision_loop()` path requires owner decision
`REJECT_FOR_REVISION`, verified source-run checkpoints, identical request,
context, snapshot-source hash and Show fingerprint, and a validated
`SHEESH_SPATIAL_FACT_CALIBRATION_001` artifact. The runtime passes prior
Researcher/Rig/Position/Lighting/Critic artifacts unchanged to ZEN's
revision roles; code does not derive geometry from Critic prose. At most two
`RIG_DESIGNER_REVISION -> POSITION_DESIGNER_REVISION -> LIGHTING_DESIGNER
-> CRITIC` cycles run. A second `BLOCKER` yields
`BLOCKED_AFTER_REVISION_LIMIT`. Zero coordinate change is reported as evidence
but is not a deterministic failure rule. Finalizer receives the latest role
artifacts and blocked/passed review state; all write eligibility remains
`NO`. Calibration distinguishes official MA2 software coordinate concepts
from current-Show venue/sign mapping and from operator-supplied facts. A live
revision remains blocked when Show identity, sufficient venue-coordinate
orientation, stage/performance-area context, or exact current-fingerprint
capability evidence is missing. Exact fixture Pos units, an image artifact,
obstruction/truss detail, and orientation writeability are not universally
required when other verified evidence supports a meaningful read-only
proposal. An operator-supplied Stage View image has a fingerprinted,
provenance-separated input schema; visual observations are not automatically
verified physical facts. Pan/Tilt direction notes are Show-scoped and never
fill XYZ sign mappings.

### Researcher provenance boundary

Researcher model context includes a deterministic `research_context.allowed_source_refs`
projection containing exact `{source_id, record_id}` pairs from that role's
selected canonical knowledge records. `sources` may contain only exact copies
of those objects. `evidence_refs` is a separate namespace containing exact
`evidence_ledger[].evidence_ref` values; verified current-Show facts belong in
`evidence_refs`, never in `sources`. An empty `sources` array is valid when no
canonical external source is being cited.

Before canonical source resolution, runtime rejects non-object/string source
claims, extra metadata, unknown or mismatched pairs, and duplicates. It never
maps prose/evidence refs back to source identity or silently discards invalid
claims. The existing full canonical source resolver remains the final
authority. A bounded Researcher retry may ask for exact allowed pairs or an
empty array without asking the model to change valid observations; raw response
and secret-safe validation diagnostics remain distinct from the accepted role
artifact.

## Role pipeline and dependency order

```
RESEARCHER
  -> SONG_ANALYST
    -> RIG_DESIGNER
      -> POSITION_DESIGNER
        -> LIGHTING_DESIGNER
          -> CUE_PROGRAMMER
            -> FX_MOVEMENT_DESIGNER
              -> FREE_CUE_DESIGNER
                -> MA2_REVIEW (checked against the real scanned Show profile)
                  -> CRITIC
                    -> FINALIZER -> assembles the final zen.autonomous_design.v0.1
```

Rules that apply to every role:

- Role dependencies remain ordered even when independent provider candidates
  are generated in parallel inside Designer/Critic stages.
- Each role receives **only the slice of Designer Context it needs**, not the
  full bundle `build_designer_context()` currently assembles. For example
  `RIG_DESIGNER` needs fixture capability + rig spatial affordance; it does
  not need the external lighting knowledge pack. Narrower context is both
  more reliable for a small model and cheaper per call.
- Each role emits a **small, independently schema-validated JSON artifact**.
  A role's output is only handed to the next role after it passes validation.
  An invalid artifact stops the pipeline at that role, not silently downstream.
- Every artifact is written to
  `projects/runs/<run_id>/steps/<role_name>.json` as it completes. This is a
  resumability requirement, not just an audit trail: on this hardware a full
  run may take a long time, and if it is interrupted (crash, the machine
  being needed for something else, a bad response from one role), the next
  run must be able to resume from the last completed role instead of
  restarting the whole pipeline.
- `CODEX_ARTISTIC_INTERVENTION = NONE` applies to every role's output, same
  as the existing single-call path. No coding agent writes or edits the
  artistic content any role produces.
- `MA2_REVIEW` is the one role that is allowed (and required) to consult the
  actual scanned Show profile (Groups/Presets/Effects/Sequences that really
  exist), not just the Designer Context -- its job is to flag anything
  upstream roles proposed that does not resolve to a real resource, before
  `CRITIC`/`FINALIZER` finalize the plan.
- `FINALIZER`'s output is the only thing that gets validated against
  `zen.autonomous_design.v0.1` and handed to the (not yet built) Resolver.

## Intake authority and feasibility

Real production inputs may be incomplete, approximate or technically impossible.

Use `docs/DESIGN_INTAKE_AND_FEASIBILITY.md` when the design request includes
audio, song metadata, arrangement notes, cue sheets, choreography notes,
student/client requests or sparse/open-ended briefs.

The important distinction is:

```text
what the requester wants
!=
what the current production can literally realize
```

External cue sheets are not executable truth by default. A later intake /
Designer implementation should preserve provenance and distinguish request
authority from technical feasibility so the system can preserve intent while
adapting an impossible or weak mechanism.

Examples of expected reasoning outcomes include:

```text
PRESERVE
ADAPT
NOT_USED
UNRESOLVED
```

No future implementation may invent missing rig capability merely to satisfy a
written cue request. Conversely, sparse or absent input must not force the
Designer to refuse creative work; it may produce an explicitly bounded
artistic proposal when constraints allow.

## Show-level identity and anti-template review

Multi-song design must not reduce to one song template with changed parameter
values, and must not optimize for maximum novelty between songs.

Use `docs/SHOW_LEVEL_VISUAL_IDENTITY.md` as the current reasoning reference.

The intended review distinction is:

```text
SHOW LANGUAGE
= recurring production grammar and recognizable identity

SONG IDENTITY
= why this song feels like itself inside that language
```

A later Designer/Critic prompt revision may operationalize concepts such as
continuity, development, contrast, callback and reset. Until the owner approves
that wording and any schema change, these remain review concepts rather than
mandatory output fields.

The Critic should eventually be able to identify two opposite failure modes:

1. **rubber-stamp design** -- repeated verse/chorus/bridge logic with only
   colors, values, or targets substituted; and
2. **forced novelty** -- arbitrary differences introduced only to make songs
   appear different, damaging chapter coherence or show identity.

No deterministic diversity score should be treated as artistic truth. Similar
visual fingerprints can be correct when they represent a chapter, motif,
callback or deliberate continuity.

## What is explicitly out of scope for this document

- The Resolver/Builder that turns a finalized `zen.autonomous_design.v0.1`
  document into real MA2 actions. That is a separate, higher-risk piece of
  work tracked in `ZEN_AUDIT_AND_FIXES_STATUS_002.md` Section 2, and needs
  the project owner in the loop for the field-to-resource mapping decisions.
- Per-role system prompt wording. That is itself a design decision (what
  each role is told it is allowed to decide), not a mechanical implementation
  detail -- draft it with the project owner present, don't have a coding
  agent invent it unsupervised.
