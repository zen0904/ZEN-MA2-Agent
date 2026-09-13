# Foundation Hardening 001

## Scope

This hardening pass addressed four review findings only. No Local LLM was
called, no training ran, no live web research or MA2/Telnet/Builder/Resolver
execution occurred, and no artistic output or B3 logic was changed.

## Changes

1. `HUMAN_REVIEW_REQUIRED` is now included in the experimental retrieval
   allow-list. Its original `promotion_state` survives projection and remains
   a review boundary; it is not production truth.
2. `build_designer_context()` now supplies a canonical Evidence Ledger and
   canonical knowledge records. Researcher, Lighting Designer, Critic and
   Finalizer receive `evidence_ledger`; checkpoint validation rejects unknown
   evidence references before persistence.
3. `resolve_research_sources()` binds Researcher references to the exact Source
   Registry and record identity. Unknown source/record IDs, source/record
   mismatches, and conflicting title/URL/publisher metadata fail closed.
   Canonical metadata is runtime-resolved, never model-authored.
4. Retry prompts explicitly preserve UNKNOWN/uncertainty and valid evidence,
   forbid invented color/position/intensity/role/geometry/source metadata, and
   require shortening prose before removing semantics. Repair is structural,
   not artistic invention.

## Verification examples

- A `HUMAN_REVIEW_REQUIRED` Visual Hierarchy record is selected deterministically
  and projects with that state unchanged.
- A valid `source_id` + `record_id` resolves registry-owned title/URL/publisher;
  a different-source record or fabricated title is rejected.
- An unknown runtime `evidence_ref` fails closed; valid refs are accepted and
  resolved source references are recorded in the Researcher artifact.
- A malformed first attempt causes a retry prompt containing the anti-invention,
  uncertainty-preservation, and prose-shortening clauses.

## Acceptance

- `HUMAN_REVIEW_REQUIRED_RETRIEVABLE = YES`
- `EVIDENCE_LEDGER_RUNTIME_BOUND = YES`
- `UNKNOWN_EVIDENCE_REF_FAILS_CLOSED = YES`
- `RESEARCH_SOURCE_IDENTITY_CANONICAL = YES`
- `LLM_CAN_OVERRIDE_SOURCE_METADATA = NO`
- `RETRY_PRESERVES_UNKNOWN = YES`
- `RETRY_CAN_INVENT_TO_PASS_SCHEMA = NO`
- `LOCAL_LLM_CALLED = NO`
- `TRAINING_EXECUTED = NO`
- `MA2_WRITES = 0`
- `CODEX_ARTISTIC_INTERVENTION = NONE`

Full suite: `402 passed, 2 warnings, 18 subtests passed`.

Production Designer remains unchanged, B3 remains
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains `DEFERRED`, and
`REAL_VENUE_VALIDATION` remains `WAIT_FOR_REAL_CASE`.
