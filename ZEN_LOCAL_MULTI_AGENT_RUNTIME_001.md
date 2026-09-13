# ZEN Local Multi-Agent Runtime 001

## Scope

This is the first executable, portable, sequential local-model path:

```text
RESEARCHER -> LIGHTING_DESIGNER -> CRITIC -> FINALIZER
```

It stops after validating and saving `zen.autonomous_design.v0.1`. It does not
import a Builder, Resolver, Telnet client, or any MA2 write path.

## Runtime and portability

`zen_ma2_agent.llm.multi_agent_runtime` reuses `ProviderRouter`,
`portable_state_path()`, `build_designer_context()`, the existing final design
validator, and run checkpoint helpers. A single
`OPENAI_COMPATIBLE_LOCAL` slot can serve every role sequentially; no cloud
provider, API key, GPU, or second loaded model is required.

All mutable run evidence is under:

```text
ZEN_HOME/projects/runs/<run_id>/
  run.json
  steps/researcher.json
  steps/lighting_designer.json
  steps/critic.json
  steps/finalizer.json
  final_design.json
```

`run.json` records the Git HEAD, request/context hashes, provider-safe identity
(never a secret), per-role artifact hashes, host OS, timestamps, local/cloud
classification, final hash, and `CODEX_ARTISTIC_INTERVENTION = NONE`.

## Role boundaries

Each role receives a narrow context slice and must return structured JSON:

- `RESEARCHER` creates a provenance-bearing evidence artifact. Without live
  retrieval it must state `OFFLINE_CACHED_CONTEXT`, not fabricate sources.
- `LIGHTING_DESIGNER` creates an intent/strategy draft from the request,
  evidence, and bounded Show context.
- `CRITIC` records strengths, problems, severity-bearing problem entries, and
  revision requests; it is explicitly instructed not to rubber-stamp.
- `FINALIZER` receives the previous artifacts and is the only role validated
  against the existing `zen.autonomous_design.v0.1` contract.

Intermediate and final artifacts reject executable command fields. No artistic
content is embedded as a Codex-authored default; artistic output originates
only from the configured provider at runtime.

## Resume and retries

Normal reuse of a run id reads checkpoints in sequence and resumes at the first
missing role. Existing completed artifacts are never overwritten. A completed
and valid `final_design.json` returns without any provider call.

`--restart-run` is the explicit opt-in to regenerate an existing run id. A
normal resume fails closed if the request or bounded Designer Context has
changed, preventing mixed-run provenance.

Each role has at most three attempts. Invalid JSON, invalid role shape,
forbidden executable fields, and final-schema failures retry with the bounded
validation error. Exhaustion preserves completed checkpoints and writes
`failure.json`; no invalid final design is accepted.

## USB CLI

From the portable Windows launcher:

```text
run_zen_windows.cmd --multi-agent-design <request_file>
run_zen_windows.cmd --multi-agent-design <request_file> --run-id <run_id>
run_zen_windows.cmd --multi-agent-design <request_file> --run-id <run_id> --restart-run
```

The existing `--design-request` single-call path is unchanged. The new command
uses the USB-local `providers.private.env` through the existing router; secrets
are not printed or stored in run artifacts.

## Verification boundary

Deterministic tests cover sequential execution, a single local provider serving
all four roles, role eligibility filtering, USB-local artifact storage,
interruption/resume, completed-run no-op behavior, invalid JSON retry,
final-schema fail-closed behavior, cloud unavailability with local fallback,
secret exclusion, provenance hashes, local-model provenance, and no executable
MA2 command acceptance.

The next blocker before a real local SHEESH run is operational rather than
architectural: configure and start the CPU-local OpenAI-compatible model on the
USB host, then run the new command with an explicit request file. The resulting
design must remain human-reviewed before any separately authorized Resolver or
MA2 action work.
