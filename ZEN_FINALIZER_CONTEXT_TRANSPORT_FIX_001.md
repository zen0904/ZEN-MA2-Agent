# ZEN Finalizer Context & Transport Fix 001

Status: implemented as runtime infrastructure only. No local LLM was called and no MA2 operation was performed.

## Evidence and root cause

Smoke 002 recorded Finalizer model-facing payloads of 30,870, 31,376, and 31,410 UTF-8 bytes. Each request reached the 900-second provider timeout and the previous policy repeated the same transport request three times. The payload contained complete upstream role envelopes and duplicated metadata in addition to the information needed for finalization.

## Deterministic Finalizer projection

The Finalizer now receives structural projections, without LLM summarization or arbitrary character truncation:

- Researcher: `research_status`, `subject`, `transferable_design_observations`, `constraints`, `uncertainties`, `evidence_refs`, and source identity pairs (`source_id`/`record_id`). Resolved source metadata and envelope diagnostics are excluded from the model payload.
- Designer: `design_intent`, `visual_strategy`, `resource_considerations`, `uncertainties`, and `evidence_refs`.
- Critic: `strengths`, `problems`, `severity`, `revision_requests`, and `evidence_refs`.
- Finalization context: verified fixture capability, bounded rig/spatial evidence, and workflow/MA2 handover constraints. Product narrative and duplicated hard-constraint/ledger copies are not repeated here.

Finalizer retrieval remains deterministic from the complete canonical store, with a bounded seven-record selection because three upstream artifacts are already present. The complete 140-record knowledge store, full Evidence Ledger, and full source registry remain in runtime context for validation and provenance resolution; they are not model-facing Finalizer data.

The synthetic 140-record regression fixture measured:

| payload | UTF-8 bytes |
| --- | ---: |
| previous full-envelope shape | 80,973 |
| projected Finalizer shape | 23,383 |
| reduction | 71.12% |

The historical Smoke 002 payload sizes above remain the production-like baseline; its failed responses did not leave completed role artifacts from which a post-run exact projected payload could be reconstructed.

## Transport and diagnostics

Output/schema/evidence validation failures retain the existing bounded structural retry behavior. Provider transport failures are classified separately. A timeout (`TimeoutError`, `socket.timeout`, or equivalent timeout diagnostic) fails fast after the first request, so identical timeout retries are zero (one total attempt). Other provider errors retain the bounded retry limit.

Each model-context diagnostic now records `provider_elapsed_seconds` and `failure_class` (`SUCCESS`, `OUTPUT_VALIDATION`, `TRANSPORT_TIMEOUT`, `TRANSPORT_ERROR`, or `PROVIDER_ERROR`) in addition to the existing bounded context metadata. No API keys, authorization headers, or full prompt dumps are recorded.

## Verification

- Focused runtime tests: 19 passed.
- Full repository suite: 417 passed, 2 warnings, 18 subtests; no provider call is part of the test path.
- Full runtime ledger validation remains enabled (`FULL_LEDGER_RUNTIME_VALIDATION=YES`).
- Full ledger is not model-facing (`FULL_LEDGER_MODEL_FACING=NO`).
- No MA2 imports were added to the LLM runtime and no MA2 writes occurred.

This change addresses payload size, retry waste, and observability only. It makes no claim about Qwen reasoning quality or artistic output.
