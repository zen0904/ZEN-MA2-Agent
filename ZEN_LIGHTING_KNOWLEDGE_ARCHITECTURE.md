# ZEN Lighting Design Knowledge / Evidence Architecture

## Scope

This is a local, read-only knowledge model. It does not connect to grandMA2,
generate MA2 commands, or change the Designer/Builder runtime path.

The intended future boundary is:

`ZEN_SHOW_PROFILE + knowledge evidence + CASE_CONTEXT + ZEN_SONG_ANALYSIS → Designer → typed ZEN_SHOW_PLAN → Builder`

Knowledge is evidence, not an absolute rule. Every claim keeps its domain,
context, provenance, confidence and review status.

## Four knowledge layers

| Layer | Meaning | Allowed scope |
|---|---|---|
| `INDUSTRY_REFERENCE` | Derived observations from documented professional practice | `DOMAIN` |
| `GENERAL_DESIGN_KNOWLEDGE` | Principles supported by multiple references, domains or validated cases | `GLOBAL` candidate only after promotion |
| `CASE_CONTEXT` | Current Show/Rig/Song/Training Case facts and constraints | `CASE` |
| `USER_PREFERENCE` | Zen feedback and A/B choices | `CASE` first; `USER` candidate after repetition |

`TRAINING_CASE_001` is a `CASE_CONTEXT` source. It is not an Industry
Reference and cannot overwrite a global principle.

## Evidence schema

Schema: `zen.lighting_design_evidence.v0.1`

Each `DesignEvidence` record contains:

| Field | Purpose |
|---|---|
| `evidence_id` | Stable local identifier |
| `source_type` | Industry, principle, case, user feedback, real-show review, or model inference |
| `domain` | Concert, K-pop, band, theatre, small venue, limited rig, general, or other |
| `claim` | Short normalized claim; no raw MA2 command text |
| `context` | Rig, song, case, source and comparison context |
| `support_count` / `contradiction_count` | Evidence balance, kept independently |
| `confidence` | Evidence confidence, including `UNKNOWN` and `CASE_LOCAL` |
| `scope` | `GLOBAL`, `DOMAIN`, `CASE`, or `USER` |
| `provenance` | Where and how the claim was obtained |
| `review_status` | Unreviewed, candidate, accepted, or rejected |

## Industry Reference model

Industry observations must retain domain, rig scale, style, song context,
frequency and confidence. A K-pop example such as floor beam plus impact
strobe supports a `KPOP` / large / high-energy hypothesis; it does not imply
`CHORUS always uses BEAM + STROBE`.

Copyrighted show files, scripts and videos are not copied into the knowledge
base. Future ingestion stores only source-linked, copyright-safe derived
observations and an audit-friendly provenance reference.

## General Design Knowledge

Current principles remain available with provenance
`CURRENT_INTERNAL_GENERAL_PRINCIPLE`:

`RESERVE_HEADROOM`, `SECTION_CONTRAST`, `REPEATED_SECTION_DEVELOPMENT`,
`EFFECT_FATIGUE_AVOIDANCE`, `LAYER_ESCALATION`, `FOCUS_HIERARCHY`,
`RESOURCE_AWARENESS`, and `ASYMMETRY_TOLERANCE`.

They are internal general candidates, not yet claimed to be independently
industry-validated. Promotion requires repeated evidence across sources and
at least two domains; one Case cannot overwrite this layer.

## Case Context

Case context may include current Groups, Fixture Types, verified resources,
geometry capability, asymmetric limitations, song structure and performance
requirements. It is useful for fit decisions but remains local to the Case.

Current Case-specific Group role assignments preserve:

- verified Group membership and Fixture identity;
- `ROLE != FIXTURE TYPE`;
- `INFERRED_FROM_GROUP_IDENTITY` confidence;
- `CASE_SPECIFIC` scope;
- proposed rig zones explicitly marked as unverified geometry.

## User Feedback

Normalized feedback values are:

`USER_LIKED`, `USER_DISLIKED`, `USER_PREFERRED_A_OVER_B`, `USER_NEUTRAL`,
and `USER_UNCERTAIN`.

A single observation is stored as `USER_FEEDBACK`, `CASE` scope, `LOW`
confidence and `USER_FEEDBACK_SINGLE_OBSERVATION` provenance. The formal
promotion result is `CASE_FEEDBACK_ONLY`; it cannot become a global rule or a
Style Profile.

## User preference promotion

The deterministic policy requires repeated feedback across songs, cases and
rigs (default threshold: at least 3 records, 2 cases and 2 rigs). Only then
is a `USER_PREFERENCE_CANDIDATE` created. This is still a candidate and does
not create `ZEN_STYLE_PROFILE` automatically.

The future path is:

`Case Feedback → repeated preference → cross-case consistency → ZEN_STYLE_CANDIDATE → explicit/strong evidence → ZEN_STYLE_PROFILE`

`ZEN_STYLE_PROFILE` is deliberately deferred in this round.

## A/B review evidence

A/B outcomes are normalized as:

`A_PREFERRED`, `B_PREFERRED`, `BOTH_ACCEPTABLE`, `BOTH_REJECTED`, or
`NO_PREFERENCE`.

A/B evidence is retained as a low-confidence case-local observation. It is
more useful for preference learning than an unexplained absolute rating, but
it still follows the same promotion thresholds.

## Cross-validation and conflict handling

Claims are evaluated with independent dimensions:

- `PROFESSIONAL_DESIGN_SCORE` — 0..1 or `UNKNOWN`;
- `CONTEXT_FIT_SCORE` — 0..1 or `UNKNOWN`;
- `USER_PREFERENCE_SCORE` — 0..1 or formal `UNKNOWN`;
- `EVIDENCE_CONFIDENCE` — qualitative evidence confidence.

No fixed weighted sum is imposed in this layer.

If Industry evidence supports a claim while Zen feedback dislikes it, both
remain intact and the result is `PROFESSIONALLY_VALID_USER_STYLE_DIVERGENCE`.
Future Designer choices may offer a general variant and a Zen variant; the
professional evidence is never deleted.

## Training Case 001 migration

`TRAINING_CASE_001_RESOURCE_RICH_KPOP_ORIENTED` is represented as a Case
source. Its anti-patterns retain provenance `INTERNAL_CASE_EVIDENCE` rather
than being declared universal industry laws. Its principles retain
`CURRENT_INTERNAL_GENERAL_PRINCIPLE` provenance and remain candidates for
future cross-domain validation.

## Rationale / reverse learning

Future plans may preserve `WHY_THIS_DESIGN` explanations such as:

- reserving an Impact layer because the previous section already uses motion;
- adding coverage or Aerial contrast instead of only increasing Dimmer;
- removing an Effect to avoid fatigue.

This records a reviewable explanation, not hidden chain-of-thought and not a
command-generation instruction.

## Future ingestion interface

The interface accepts documented professional show breakdowns, lighting plots,
cue sheets, human-annotated performance references and training datasets as
source-bound derived observations. Each import must provide source, domain,
context, confidence and copyright-safe provenance. No large external dataset
or network ingestion is implemented here.

## Designer boundary and safety

This round intentionally does not runtime-wire Industry evidence, Training
Cases or User Preference into Designer. The architecture only defines the
future context adapter. Any later adapter must return design knowledge and
typed intent, never raw Telnet, Lua or MA2 command strings. MA2 writes remain
exclusively behind the existing Builder, Preview, Approval and Verification
path.

## Current status

- Local schema and promotion logic: implemented and unit-tested.
- Training Case 001 evidence migration: implemented as metadata/provenance.
- Industry Reference Pack 001: six traceable sources and 17 derived observations are stored locally with source/domain/context/evidence/confidence/limitations. All records default to `HUMAN_REVIEW_REQUIRED`; no global promotion has occurred.
- Industry data ingestion runtime wiring: not implemented; the pack is a review artifact and future context-adapter input only.
- User Style Profile: deferred.
- Designer runtime wiring: not run.
- MA2 write audit: zero writes.
