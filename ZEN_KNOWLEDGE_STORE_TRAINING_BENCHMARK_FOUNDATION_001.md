# ZEN Knowledge Store, Training Dataset, and Benchmark Foundation 001

## Outcome

This bounded foundation adds reusable storage and evaluation boundaries without
calling a model, training, changing the Production Designer, or touching MA2.
The existing external-lighting Pack 001 and Source Registry remain intact and
are loaded as canonical inputs rather than copied into a second corpus.

## Canonical Knowledge Store

`zen_ma2_agent/knowledge_store.py` implements `zen.knowledge_store.v0.1`.
`load_canonical_store()` validates the existing Source Registry and Pack, then
normalizes records losslessly while deriving a category. The five supported
categories are:

- `GLOBAL_LIGHTING_DESIGN_KNOWLEDGE`
- `MA2_TECHNICAL_KNOWLEDGE`
- `FIXTURE_TECHNICAL_KNOWLEDGE`
- `SHOW_FACTS`
- `ZEN_STYLE_AND_WORKFLOW_KNOWLEDGE`

Pack 001 currently supplies the first three categories (design, console
maintainability, and fixture-provenance topics). The latter two are explicit
extension categories and remain empty until verified Show facts or reviewed
workflow evidence is ingested; no facts were invented in this task.

Source identity is registry-owned. Unknown source IDs fail closed. Records are
not overwritten by a projection: agent context retains `record_id`, claim,
scope, exclusions, confidence, promotion state, and summary. Retrieval is
deterministic, role-aware, request/context-aware, and capped per topic so topic
diversity survives. Professional knowledge is no longer represented by a blind
first-N character excerpt in the multi-agent runtime.

The Evidence Ledger keeps `VERIFIED_FACT`, `DESIGN_KNOWLEDGE`,
`ARTISTIC_PROPOSAL`, and `UNKNOWN` separate. A verified fact requires explicit
source and evidence; an artistic proposal does not acquire fake proof; an
unknown remains legal and cannot be resolved through an unknown ledger ref.

## Training Dataset Pipeline

`zen_ma2_agent/training_dataset.py` defines
`zen.training_sample.v0.1`. Portable directories are present at:

```text
training/raw/
training/reviewed/
training/rejected/
training/exports/
```

Each sample preserves source run/commit, provider/model, context hash,
knowledge references, human review and approval state, creation time, and
`CODEX_ARTISTIC_INTERVENTION = NONE`. Statuses are `RAW`, `AUTO_COLLECTED`,
`NEEDS_REVIEW`, `APPROVED`, `REJECTED`, and `SUPERSEDED`. Only samples with
`APPROVED` status are exported to JSONL, and approval must name a non-Codex
approver. No artistic training data was self-approved or exported, and no
training was run. Positive and negative examples remain representable without
declaring synthetic artistic truth.

## Structural Benchmark Foundation

`zen_ma2_agent/benchmark.py` and `data/benchmark_cases_001.json` provide small,
non-artistic cases. The deterministic scorer reports schema validity, forbidden
command count, unknown source count, unsupported fact count, uncertainty
preservation, fixture-role locking, evidence-reference integrity, retrieval
coverage and topic diversity, retry count, runtime, and output size. It does
not assign an artistic quality score. The seeded cases check typed output,
uncertainty/evidence boundaries, and the console-command boundary.

## Multi-agent integration

The role runtime now receives a role-specific projected Knowledge Context for
researcher, designer, critic, and finalizer. Critic and finalizer are not
excluded. Knowledge remains context/shadow input and still cannot bypass
Design Intent, typed plan validation, Resolver, or Builder boundaries. A future
revision-patch role may use these interfaces but was not implemented here.

## Safety and acceptance

- Local LLM call: `NOT_RUN` (explicitly prohibited for this task).
- Model training: `NOT_RUN`.
- Cloud calls: `0`.
- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`.
- MA2/Telnet/Builder/Resolver execution: `NOT_RUN`.
- MA2 objects modified: `NONE`; MA2 write audit: `ZERO_WRITES`.
- `CODEX_ARTISTIC_INTERVENTION`: `NONE`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- No vector database, LangChain, LFS, media archive, or expensive CI was added.

## Verification

Focused Knowledge Store, training, benchmark, multi-agent, and external-pack
tests pass. The full repository suite passes with `396 passed, 2 warnings, 18
subtests passed`.

## Remaining limitations

The foundation does not populate Show-specific facts or Zen workflow records,
does not create an artistic training corpus, does not perform embedding-based
retrieval, and does not claim that external principles are production rules.
Human review and bounded case evaluation remain required before promotion or
any production Designer activation.
