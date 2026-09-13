# Multi-Agent Design Plan

Status: **plan only, not implemented**. See
`ZEN_AUDIT_AND_FIXES_STATUS_002.md` Section 2 -- zero role orchestration
exists in the codebase as of this writing. This document is the agreed shape
for it, so any coding agent picking up the work builds toward the same
target instead of inventing a different one.

## Hardware this must run on

Project owner's current development machine (photographed 2026-09-13):
2014 MacBook Pro under Bootcamp, Intel i7-4770HQ (4 cores / 8 threads),
16GB DDR3 RAM, **no discrete GPU** (Intel Iris Pro 5200 integrated only).
CPU-only inference. This is the binding constraint on every design choice
below -- do not propose anything that assumes CUDA/GPU acceleration or more
than ~16GB total system memory is available. A future secondary machine
(~NT$20,000 used desktop) is discussed but is not an implementation
dependency; design for the machine that exists today.

Consequence: a single large prompt asking one CPU-bound 7B-class model to
produce the entire Show Plan in one shot (which is what
`autonomous_designer.py` currently does) is both an architectural gap
(Section 2 of the status report) and a poor fit for this hardware even once
wired up. Smaller, role-scoped prompts are not just "more like a real
department" -- they are the more reliable way to get a valid
`zen.autonomous_design.v0.1` document out of a small local model at all.

## Model and runtime

- Runtime: **llama.cpp server**, CPU-only build, `-t 8` (matches the 4770HQ's
  8 logical threads). No GPU offload flags.
- Model: a single 7B-8B instruct model, Q4_K_M GGUF quantization
  (~4.5-5GB), e.g. Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct. Do not start
  larger (13B+) on 16GB total RAM -- the risk is swapping, which is worse
  than a slower response from a smaller model.
- Wiring: llama.cpp server is OpenAI-compatible out of the box, so it plugs
  directly into the existing `ProviderRouter` as `OPENAI_COMPATIBLE_LOCAL`
  (see `config/providers.private.env.example`). No changes to `llm/router.py`
  are needed to add the model itself.
- One model, many roles: do **not** load multiple models concurrently. Every
  role below is the same loaded model given a different, narrower system
  prompt and a different, narrower slice of context. This is what keeps
  memory pressure constant regardless of how many roles the pipeline has.

## Role pipeline (sequential, single model)

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

## What is explicitly out of scope for this document

- The Resolver/Builder that turns a finalized `zen.autonomous_design.v0.1`
  document into real MA2 actions. That is a separate, higher-risk piece of
  work tracked in `ZEN_AUDIT_AND_FIXES_STATUS_002.md` Section 2, and needs
  the project owner in the loop for the field-to-resource mapping decisions.
- Per-role system prompt wording. That is itself a design decision (what
  each role is told it is allowed to decide), not a mechanical implementation
  detail -- draft it with the project owner present, don't have a coding
  agent invent it unsupervised.
