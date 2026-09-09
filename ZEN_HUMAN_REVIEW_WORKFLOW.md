# ZEN Human Review Workflow

## Lifecycle

`IndustryReferenceSource` → `DerivedObservation` → `HumanReviewRecord`

Sources and observations are immutable. A review is a separate record with `zen.industry_evidence_review.v0.1`, reviewer type, decision, confidence, reason, scope confirmation, notes and timestamp.

## Decisions

- `ACCEPT`: interpretation and documented scope are accurate; not a global rule.
- `ACCEPT_WITH_LIMITATION`: accepted only with recorded boundary.
- `NEEDS_CONTEXT`: retain, but do not activate.
- `REJECT`: interpretation is not reliable enough; retain for audit, do not activate.
- `DUPLICATE`: retain the source record, exclude duplicate candidate.
- `UNSURE`: defer without forcing a decision.

## Eligibility

Only `ACCEPT` and `ACCEPT_WITH_LIMITATION` can become future Designer knowledge candidates, and they retain their original domain/scope. Cross-source and cross-domain promotion is separate and remains disabled here.

## AI assistance

`AIReviewRecommendation` uses `zen.industry_evidence_ai_recommendation.v0.1` and is never copied into a human decision. Visual and model interpretations are always HIGH review priority; direct statements from the current pack are MEDIUM priority.

## Bias

All six Pack 001 sources are manufacturer/technical case-study style and carry `MANUFACTURER_CASE_STUDY_BIAS`. This is a review limitation, not an automatic rejection.

## Runtime boundary

No UI, Designer context adapter, MA2 connection or MA2 write is part of this workflow.
