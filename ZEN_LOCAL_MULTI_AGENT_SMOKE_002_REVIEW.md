# ZEN Local Multi-Agent Smoke 002 Review

## Run identity and exact input

Smoke 002 reused the exact request file from Smoke 001 without edits:
`E:\ZEN_MA2_AGENT\projects\requests\local_multi_agent_smoke_001.txt`.
The request hash is identical in both run records:
`7454b1f0b5c1e359c2e47fb21f61c506decbfb69434d63e4d20ad22b926276f1`.
The run ID was `local-multi-agent-smoke-002`; Smoke 001 remains preserved and
was not overwritten. The USB repo was fast-forwarded to the required
`bb9058725a42bbdda363098351b498b457957abd` before the successful attempt.

## Provider and runtime checks

- Provider: `OPENAI_COMPATIBLE_LOCAL`
- Model: `Qwen2.5-7B-Instruct-Q4_K_M`
- Endpoint: `http://127.0.0.1:8080/v1`
- `/health`: HTTP 200 `{"status":"ok"}`
- `/v1/models`: HTTP 200; model served from the USB-local GGUF path
- Cloud fallback: not configured/used
- MA2/Telnet/Builder/Resolver: not invoked

Smoke 002 ended at the first role. The formal launcher returned:
`researcher failed after 3 attempts: slot 1: Provider slot 1 request failed: HTTPError`.
Its run record has `status = FAILED`, `role_execution = []`,
`LOCAL_MODEL_USED = NO` (no role completed), `CLOUD_REQUIRED = NO`, and
`CODEX_ARTISTIC_INTERVENTION = NONE`. The failed run and its restart archive
remain on the USB; no output was edited.

## Deterministic A/B facts

| Measure | Smoke 001 | Smoke 002 |
|---|---|---|
| Run status | COMPLETE | FAILED at RESEARCHER |
| Git HEAD recorded | `bcedea28...` (older USB checkout) | `bb905872...` |
| Provider/model | Local Qwen2.5-7B Q4_K_M | Local Qwen2.5-7B Q4_K_M |
| Role attempts | researcher 1; designer 1; critic 1; finalizer 2 | researcher 3; remaining roles 0 |
| Retry count | 1 (finalizer) | 2 (researcher) |
| Total runtime | ~23m 52s | ~0.24s after launcher start |
| Final schema | Valid `zen.autonomous_design.v0.1` | NOT_AVAILABLE (no final artifact) |
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

## Smoke 002 structural result

There is no Researcher, Lighting Designer, Critic, or Finalizer artifact to
grade. Therefore these are `NOT_AVAILABLE`, not passes: knowledge utilization,
design hierarchy, negative space, depth/layering, repeated-section development,
unknown preservation in output, critic usefulness, finalizer hallucination, and
retry degradation after a completed role.

The only deterministic finding is a provider failure at Researcher after three
attempts, with no cloud fallback and no partial role artifacts. This prevents
an artistic A/B conclusion and does not prove a Qwen design ceiling.

## A/B review matrix

| Criterion | Result | Artifact evidence |
|---|---|---|
| Research provenance | WORSE | Smoke 001 researcher artifact fails current canonical metadata resolution; Smoke 002 produced none. |
| Knowledge utilization | WORSE / NOT_AVAILABLE | Smoke 001 used one generic color claim; Smoke 002 had no role output. |
| Design hierarchy | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Negative space / restraint | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Depth / layering | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Color reasoning | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Movement reasoning | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Repeated-section development | NOT_AVAILABLE | No Smoke 002 Designer output. |
| Fixture-role locking | SAME RISK / NOT_AVAILABLE | Label-driven risk is present in Smoke 001; Smoke 002 has no output. |
| Unknown preservation | NOT_AVAILABLE | No Smoke 002 artifact to inspect. |
| Critic usefulness | NOT_AVAILABLE | Critic did not run in Smoke 002. |
| Finalizer hallucination | NOT_AVAILABLE | Finalizer did not run in Smoke 002. |
| Retry degradation | WORSE operationally | Smoke 002 exhausted 3 Researcher attempts on HTTPError before any checkpoint. |
| Overall professional plausibility | INCONCLUSIVE | A failed run cannot establish design quality. |

No `BETTER` artistic result can be claimed. Smoke 001 is the only completed
design artifact and already contains the provenance and generic-recipe
weaknesses listed above.

## Required final fields

```text
RUN_ID=local-multi-agent-smoke-002
GIT_HEAD=bb9058725a42bbdda363098351b498b457957abd
MODEL=Qwen2.5-7B-Instruct-Q4_K_M
LOCAL_MODEL_USED=NO (no role completed; local endpoint was verified)
CLOUD_REQUIRED=NO
TOTAL_RUNTIME=~0.24s
ROLE_ATTEMPTS=researcher:3; lighting_designer:0; critic:0; finalizer:0
RETRY_COUNT=2
FINAL_SCHEMA_VALID=NO / NOT_AVAILABLE
SOURCE_CONTAMINATION=NOT_AVAILABLE in Smoke 002; Smoke 001 researcher artifact had canonical metadata conflict
UNKNOWN_PRESERVED=NOT_AVAILABLE in Smoke 002; limited uncertainty present in Smoke 001 final
FIXTURE_ROLE_LOCKING=NOT_AVAILABLE in Smoke 002; label-driven risk present in Smoke 001
ARTISTIC_RECIPE_CONTAMINATION=NOT_AVAILABLE in Smoke 002; generic color/intensity recipe risk present in Smoke 001
MA2_WRITES=0
CODEX_ARTISTIC_INTERVENTION=NONE
```

## Conclusion

`QWEN_7B_DESIGNER = INCONCLUSIVE` (no completed Smoke 002 Designer artifact).
`QWEN_7B_CRITIC = INCONCLUSIVE` (not reached).
`QWEN_7B_FINALIZER = INCONCLUSIVE` (not reached).

This smoke does not justify production readiness, model replacement, prompt
changes, fine-tuning, or a third smoke. Any future rerun requires human
direction on the provider/runtime failure and the same exact-input rule; no
artistic remediation was performed here.

Safety: no MA2 objects, fixtures, presets, sequences, executors, or Show state
were modified. No cloud call, training, or local-model design output was
fabricated. Existing cache directories and Smoke 001 artifacts remain intact.
