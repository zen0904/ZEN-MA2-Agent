# Multi-Agent Design Plan

Status: the bounded four-role MVP (`RESEARCHER -> LIGHTING_DESIGNER -> CRITIC
-> FINALIZER`) is implemented in `zen_ma2_agent.llm.multi_agent_runtime`.
It is portable, sequential, checkpointed, and ends at a validated
`zen.autonomous_design.v0.1` artifact. The remaining roles below are still
plan-only; neither the MVP nor this document implements a Resolver/Builder or
any MA2 write path. This remains the agreed target shape so later work extends
the same pipeline rather than inventing a different one.

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
