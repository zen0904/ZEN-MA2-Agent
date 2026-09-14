# ZEN Local Multi-Agent Smoke 002 Review

## Run identity and exact input

Smoke 002 reused the exact request file from Smoke 001 without edits:
`E:\ZEN_MA2_AGENT\projects\requests\local_multi_agent_smoke_001.txt`.
The request hash is identical in both run records:
`7454b1f0b5c1e359c2e47fb21f61c506decbfb69434d63e4d20ad22b926276f1`.
The run ID was `local-multi-agent-smoke-002`; Smoke 001 remains preserved and
was not overwritten. The USB repo was fast-forwarded to the required
`0c5362906b39dc59f55a1cb40a269978bf7b2220` before the controlled rerun.

The exact bounded context path was the existing `build_designer_context`
contract. It read these repo-owned inputs (when present):
`data/zen_project_control.json`,
`data/external_lighting_knowledge_pack_001.json`,
`data/external_lighting_knowledge_source_registry_001.json`,
`data/current_show_visual_relationships_001.json`,
`data/zen_show_bound_color_preset_applicability_001.json`,
`data/ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json`, and
`data/zen_real_ma2_test_show_sheesh_001_plan.json`, plus the bounded
constitution/workflow/MA2 documents. Smoke 001 recorded context hash
`6a984d105bc597a68e567ac1e6cf25978e5c82852745282158c32b3de865bf26`;
Smoke 002 recorded `5d5e6f12444974768e3fc6beaa8447b94f220b26be74f181acd79822df9e772c`.

## Provider and runtime checks

- Provider: `OPENAI_COMPATIBLE_LOCAL`
- Model: `Qwen2.5-7B-Instruct-Q4_K_M`
- Endpoint: `http://127.0.0.1:8080/v1`
- `/health`: HTTP 200 `{"status":"ok"}`
- `/v1/models`: HTTP 200; model served from the USB-local GGUF path
- Cloud fallback: not configured/used
- MA2/Telnet/Builder/Resolver: not invoked

The original Smoke 002 attempt (before Context Packaging Fix 001) ended at the
first role with an HTTPError and remains preserved in the USB restart archive.
The controlled rerun after the fix reached Researcher, Lighting Designer, and
Critic successfully, then exhausted three Finalizer attempts on local
`TimeoutError`. Its run record has `status = FAILED`, `LOCAL_MODEL_USED = YES`,
`CLOUD_REQUIRED = NO`, and `CODEX_ARTISTIC_INTERVENTION = NONE`; no output was
edited by Codex.

## Deterministic A/B facts

| Measure | Smoke 001 | Smoke 002 |
|---|---|---|
| Run status | COMPLETE | FAILED at FINALIZER (controlled rerun); original attempt failed at RESEARCHER |
| Git HEAD recorded | `bcedea28...` (older USB checkout) | `0c536290...` |
| Provider/model | Local Qwen2.5-7B Q4_K_M | Local Qwen2.5-7B Q4_K_M |
| Role attempts | researcher 1; designer 1; critic 1; finalizer 2 | researcher 1; designer 1; critic 1; finalizer 3 |
| Retry count | 1 (finalizer) | 2 (finalizer) |
| Total runtime | ~23m 52s | ~60m 00s (provider timeout) |
| Final schema | Valid `zen.autonomous_design.v0.1` | NOT_AVAILABLE (Finalizer exhausted retries) |
| MA2 writes | 0 | 0 |

Smoke 001 artifacts used for review are the actual USB files under
`projects/runs/local-multi-agent-smoke-001/` (`run.json`, four `steps/*.json`,
and `final_design.json`). Smoke 002 evidence is its `run.json` and
`failure.json`; no idealized or manually authored design substituted for the
missing B output.

## Smoke 001 structural observations

These are technical observations, not an artistic approval:

- The finalizer preserved the typed output schema and uncertainty wording, but
  its `virtual_rig` and `main_sequence` only used Groups 1 and 2.
- The researcher emitted two entries with the same `source_id` but one entry
  carried conflicting title/provenance metadata. Re-running current canonical
  source resolution rejects that artifact with a registry metadata conflict.
  This is **source contamination / provenance failure**.
- The draft and final output used group labels as visual descriptions
  ("hybrid ... dynamic visual coverage", "spot ... focused visual coverage")
  despite no Show-specific spatial evidence. This is fixture-role locking risk,
  not a verified role mapping.
- Colors (`blue`, `red`, `green`, `yellow`) and intensity words were proposed
  without song evidence. They read as generic recipe-like choices rather than
  traceable context decisions.
- The critic did identify uncertainty and requested clarification, but also
  requested specific color choices despite the evidence boundary. The finalizer
  retained the original generic choices instead of adding richer evidence.
- Unknown information was at least surfaced as uncertainty about applicability
  outside theatre; no instrumentation, harmony, staging, or choreography facts
  were fabricated in the final artifact.

## Smoke 002 structural result (original failed attempt)

There is no Researcher, Lighting Designer, Critic, or Finalizer artifact to
grade. Therefore these are `NOT_AVAILABLE`, not passes: knowledge utilization,
design hierarchy, negative space, depth/layering, repeated-section development,
unknown preservation in output, critic usefulness, finalizer hallucination, and
retry degradation after a completed role.

The only deterministic finding for the original attempt is a provider failure
at Researcher after three attempts, with no cloud fallback and no partial role
artifacts. This remains historical evidence and does not prove a Qwen design
ceiling.

## Smoke 002 controlled rerun after Context Packaging Fix 001

The exact request was read from the unchanged USB file. Raw file SHA256 was
`bc70432407646ae763296934cda39e60ea517da74bc4c898eb4d654e449b0ce7`; the
runtime canonical request hash was
`7454b1f0b5c1e359c2e47fb21f61c506decbfb69434d63e4d20ad22b926276f1`, matching
the recorded Smoke 001/002 identity. No request text was changed.

The fixed runtime used the full canonical store (`140` records) for each role
and exposed bounded role context (`8` selected records and `8` evidence entries
per request). Context diagnostics are preserved under
`E:\\ZEN_MA2_AGENT\\projects\\runs\\local-multi-agent-smoke-002\\diagnostics\\`:

| Role / attempt | Selected records | Evidence entries | Payload UTF-8 bytes | Result |
|---|---:|---:|---:|---|
| Researcher 1 | 8 | 8 | 17,161 | completed |
| Lighting Designer 1 | 8 | 8 | 28,468 | completed |
| Critic 1 | 8 | 8 | 23,679 | completed |
| Finalizer 1 | 8 | 8 | 30,870 | TimeoutError |
| Finalizer 2 | 8 | 8 | 31,376 | TimeoutError |
| Finalizer 3 | 8 | 8 | 31,410 | TimeoutError |

The completed role artifacts are the actual USB files under `steps/`. The
Researcher resolved all three supplied source IDs through the canonical full
registry; no source metadata conflict was reported. The Designer preserved
uncertainties and contextual language without adding executable fields. The
Critic identified missing section-specific detail and execution uncertainty.
These are structural observations only, not an artistic quality approval.

Finalizer produced no validated artifact, so no end-to-end design comparison
or artistic verdict is possible. The failure evidence is explicit:
`FAILED_ROLE=finalizer`, `ATTEMPTS=3`, `HTTP_STATUS=NOT_AVAILABLE`,
`SAFE_PROVIDER_ERROR=TimeoutError`, final attempt `PAYLOAD_UTF8_BYTES=31410`,
`SYSTEM_CHARACTERS=1183`, `USER_CHARACTERS=29453`,
`SELECTED_KNOWLEDGE_COUNT=8`, `EVIDENCE_ENTRY_COUNT=8`.

## A/B review matrix (Smoke 001 vs controlled Smoke 002)

| Criterion | Result | Artifact evidence |
|---|---|---|
| Research provenance | BETTER | Smoke 002 Researcher sources resolve against the canonical registry; Smoke 001 had a metadata conflict. |
| Knowledge utilization | BETTER | Smoke 002 Researcher emitted seven topic observations from role-scoped records; no final design claim is made. |
| Design hierarchy | NOT_AVAILABLE | Designer draft exists, but no validated Finalizer output for a complete comparison. |
| Negative space / restraint | NOT_AVAILABLE | Draft references restraint; end-to-end design artifact is absent. |
| Depth / layering | NOT_AVAILABLE | Draft references hierarchy/layering; no final artifact to assess. |
| Color reasoning | NOT_AVAILABLE | No validated final design comparison. |
| Movement reasoning | NOT_AVAILABLE | No validated final design comparison. |
| Repeated-section development | NOT_AVAILABLE | No validated final design comparison. |
| Fixture-role locking | BETTER / UNRESOLVED | Current role prompts and draft retain capability-vs-role boundary; no final output exists to verify behavior. |
| Unknown preservation | BETTER | Researcher and Designer preserve explicit uncertainties; Finalizer behavior is unavailable. |
| Critic usefulness | BETTER | Critic ran and identified missing specificity/role clarity; human review is still required. |
| Finalizer hallucination | NOT_AVAILABLE | Finalizer timed out before producing an artifact. |
| Retry degradation | WORSE operationally | Three Finalizer attempts consumed the run without a validated final artifact. |
| Overall professional plausibility | INCONCLUSIVE | Partial role completion cannot establish design quality or production readiness. |

No artistic `PASS` is claimed. The controlled rerun demonstrates that the
context/provenance fix allowed three roles to execute locally, but the
Finalizer timeout prevents a complete A/B design judgment and does not by
itself establish a Qwen reasoning ceiling.

## Required final fields

```text
RUN_ID=local-multi-agent-smoke-002
GIT_HEAD=0c5362906b39dc59f55a1cb40a269978bf7b2220
MODEL=Qwen2.5-7B-Instruct-Q4_K_M
LOCAL_MODEL_USED=YES (researcher, designer, and critic completed locally)
CLOUD_REQUIRED=NO
TOTAL_RUNTIME=~3600s (60m; finalizer timeout)
ROLE_ATTEMPTS=researcher:1; lighting_designer:1; critic:1; finalizer:3
RETRY_COUNT=2 (finalizer)
FINAL_SCHEMA_VALID=NO / NOT_AVAILABLE
SOURCE_CONTAMINATION=NO observed in completed Smoke 002 Researcher; Finalizer unavailable
UNKNOWN_PRESERVED=YES in completed Researcher/Designer artifacts; Finalizer unavailable
FIXTURE_ROLE_LOCKING=UNRESOLVED (no completed final design)
ARTISTIC_RECIPE_CONTAMINATION=UNRESOLVED (no completed final design)
RETRY_DEGRADATION=YES operationally (Finalizer timeout after 3 attempts)
MA2_WRITES=0
CODEX_ARTISTIC_INTERVENTION=NONE
```

## Conclusion

`QWEN_7B_RESEARCHER = PASS` (local artifact validated and canonical sources resolved).
`QWEN_7B_DESIGNER = BORDERLINE` (artifact validated, but specificity remains limited and no final assembly completed).
`QWEN_7B_CRITIC = BORDERLINE` (artifact validated and issues were identified; human usefulness review remains).
`QWEN_7B_FINALIZER = INCONCLUSIVE` (three local attempts timed out before a validated artifact).

This smoke does not justify production readiness, model replacement, prompt
changes, fine-tuning, or a third smoke. Any future rerun requires human
direction on the provider/runtime failure and the same exact-input rule; no
artistic remediation was performed here.

Safety: no MA2 objects, fixtures, presets, sequences, executors, or Show state
were modified. No cloud call or training occurred, and no local-model design
output was fabricated. Existing cache directories, Smoke 001 artifacts, and
the original failed Smoke 002 attempt remain intact.

## Smoke 002 post-Finalizer-fix rerun

This section records the latest successful run and does not erase the earlier
failed attempts above. The exact unchanged request file was used. Its runtime
canonical request hash was `7454b1f0b5c1e359c2e47fb21f61c506decbfb69434d63e4d20ad22b926276f1` and the USB working copy was fast-forwarded to `3d49578d2c5411b10b6177e6b6219e6ec91795b8` before launch. Local `/health` and `/v1/models` both returned HTTP 200 for Qwen2.5-7B-Instruct-Q4_K_M. Cloud was neither configured nor used, and MA2 was not invoked.

Run state is `COMPLETE`; the validated final artifact is the actual
`E:\\ZEN_MA2_AGENT\\projects\\runs\\local-multi-agent-smoke-002\\final_design.json`.
Prior evidence remains under `restart_archive/`; a stale diagnostic was moved
there after the run so current diagnostics contain only current attempts.

| Role | Attempts | Selected records | Evidence entries | Payload bytes | Elapsed seconds | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Researcher | 1 | 8 | 8 | 17,161 | 493.500 | SUCCESS |
| Lighting Designer | 1 | 8 | 8 | 28,440 | 648.891 | SUCCESS |
| Critic | 1 | 8 | 8 | 23,819 | 630.468 | SUCCESS |
| Finalizer | 2 | 7 | 7 | 26,858 / 27,349 | 853.109 / 717.562 | OUTPUT_VALIDATION / SUCCESS |

Total runtime was 3,343.902 seconds (~55m44s), versus the prior controlled
rerun's approximately 3,600 seconds (~60m), an operational reduction of about
7.11%. Finalizer attempt 1 returned content but failed structural validation;
attempt 2 was a bounded validation repair and succeeded. No Finalizer
transport timeout occurred, so timeout fail-fast was not exercised and no
identical timeout retry was sent.

The Finalizer diagnostics show the deterministic projection: seven selected
knowledge records/evidence entries, projected upstream fields, and no full
source registry in the model-facing payload. Runtime validation still used the
full canonical ledger and source registry. The final artifact is schema-valid
(`zen.autonomous_design.v0.1`) but sparse: it preserves `UNKNOWN` for position,
main sequence, and free-cue details. This is an artifact observation, not an
artistic approval.

### Latest A/B matrix (Smoke 001 vs successful Smoke 002 rerun)

| Criterion | Result | Artifact evidence |
|---|---|---|
| Research provenance | BETTER | Researcher source IDs resolved through the canonical registry. |
| Knowledge utilization | BETTER | Role-scoped records/evidence were retrieved from the 140-record store. |
| Design hierarchy | BETTER / HUMAN REVIEW REQUIRED | Designer and Finalizer describe hierarchy and contrast; human judgment remains required. |
| Negative space / restraint | BETTER / HUMAN REVIEW REQUIRED | Intent and strategy mention restraint/quiet scenes. |
| Depth / layering | BETTER / HUMAN REVIEW REQUIRED | Designer strategy references visual depth. |
| Color reasoning | BETTER / CONTEXTUAL ONLY | Color is treated as a separable dimension, not a fixed recipe. |
| Movement reasoning | BETTER / UNKNOWN-SAFE | Movement is selectively activated without invented implementation. |
| Repeated-section development | BETTER / NOT DEMONSTRATED | No concrete repeated section exists in the synthetic request. |
| Density/intensity headroom | BETTER / BOUNDED | Artifacts reference reserving dimensions for later contrast. |
| Fixture-role locking | BETTER | No permanent role is assigned from Group labels. |
| Unknown preservation | BETTER | Finalizer keeps `UNKNOWN` for position, main sequence, and free-cue layer. |
| Critic usefulness | BETTER | Critic identifies missing song/spatial context and strategy clarity. |
| Finalizer hallucination | BETTER | No fabricated geometry, position target, or executable command appears. |
| Retry degradation | BETTER operationally | One structural retry succeeded after projection; no timeout repetition. |
| Overall professional plausibility | INCONCLUSIVE | Schema-valid output exists, but artistic quality remains for human review. |

Role verdicts remain evidence-bound: `QWEN_7B_RESEARCHER=PASS`,
`QWEN_7B_DESIGNER=BORDERLINE`, `QWEN_7B_CRITIC=BORDERLINE`,
`QWEN_7B_FINALIZER=BORDERLINE` (schema-valid and uncertainty-preserving, but
sparse). This is not a production-readiness claim.

`MA2_WRITES=0` and `CODEX_ARTISTIC_INTERVENTION=NONE`.
