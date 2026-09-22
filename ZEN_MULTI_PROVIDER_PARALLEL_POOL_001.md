# ZEN Multi-Provider Parallel Pool 001

> **2026-09-22 default-path update:** The provider-pool and parallel-role
> capabilities remain implemented, but they are no longer the default ordinary
> song-design path. `docs/ZEN_DESIGN_MODE.md` is authoritative for the normal
> product flow: one primary Lighting Designer call, optional one delta
> revision, then deterministic ZEN Compiler/Builder/readback. Parallel
> Designer/Critic fan-out is explicit deep/research mode only.
>
Status: **IMPLEMENTED IN REPOSITORY / FULL REGRESSION PENDING**

Date: 2026-09-20

## Decision

ZEN no longer assumes one local 7B model should carry the full autonomous
lighting-design pipeline.

Target inference architecture:

```text
RESEARCHER
→ role-routed cloud/free provider

LIGHTING_DESIGNER
→ provider candidate A ┐
                       ├→ parallel candidate set
→ provider candidate B ┘

CRITIC
→ provider candidate A ┐
                       ├→ parallel critique set
→ provider candidate B ┘

FINALIZER
→ canonical final synthesis

Local model
→ lightweight 3B-4B class offline/degraded fallback
```

The dependency chain between roles remains ordered:

```text
Researcher → Lighting Designer → Critic → Finalizer
```

Parallelism is used inside independent candidate stages rather than pretending
that dependent roles can all run simultaneously.

## Router changes

`zen_ma2_agent/llm/router.py` now supports:

- a bounded provider pool of up to 16 slots;
- `FREE_FIRST` routing mode;
- per-slot `PRIORITY`;
- per-slot `COST_CLASS`:
  - `FREE`
  - `LOCAL`
  - `UNKNOWN`
  - `PAID`
- per-slot response-format compatibility switch;
- role-scoped provider parallelism;
- bounded parallel fan-out using independent provider calls;
- deterministic result ordering after parallel completion;
- isolation of provider failure / quota failure.

`COST_CLASS` is configuration metadata, not billing discovery. Operators must
update it when a provider's current account/tier changes.

## Multi-agent runtime changes

The runtime can now generate parallel candidates for:

- `LIGHTING_DESIGNER`
- `CRITIC`

Each candidate:

1. comes from an independently eligible provider;
2. passes the existing typed output validator;
3. passes evidence-reference validation;
4. cannot contain provider secrets;
5. remains non-executable;
6. is checkpointed with provider provenance.

The preferred valid candidate remains the canonical step artifact for backwards
compatibility, while all valid parallel candidates are preserved in the step
envelope.

Critic receives the true parallel Designer candidate set when more than one
valid candidate exists.

Finalizer receives true parallel Designer and Critic candidate sets when they
exist.

Candidate presence never turns a claim into truth. Finalization remains bound
by evidence and the existing typed schema.

## Configuration

Two examples now exist:

```text
config/providers.private.env.example
→ simple lightweight local-only fallback example

config/providers.free_pool.env.example
→ expandable free-first multi-provider example
```

The free-pool example uses:

```text
ZEN_PROVIDER_MODE=FREE_FIRST
ZEN_PROVIDER_SLOT_COUNT=8
ZEN_PROVIDER_PARALLELISM=2
ZEN_PROVIDER_PARALLEL_ROLES=LIGHTING_DESIGNER,CRITIC
```

Example pool roles include Gemini, Groq, NVIDIA NIM, Mistral, OpenRouter,
Cerebras, another reserved OpenAI-compatible provider, and a local fallback.

Provider/model availability and free-tier terms are intentionally not encoded
as permanent product facts. Exact account availability must be verified when
keys are configured.

## Local fallback change

The historical local 7B example is no longer the preferred default.

The repository example now targets a lighter 3B-4B class Q4 model, with
`Qwen3-4B-Q4_K_M` used only as an example model id.

The actual model must be selected after Worker hardware/runtime verification.

Purpose of the local model:

- offline degraded operation;
- JSON/structure repair;
- classification / routing support;
- lightweight reasoning;
- emergency fallback.

It is not expected to match cloud frontier models as the primary artistic
Designer.

## Safety boundary unchanged

Nothing in this work grants a model MA authority.

Required path remains:

```text
LLM candidate
→ typed validation
→ evidence validation
→ later Safety
→ Resolver
→ deterministic Builder
→ Preview / Approval
→ MA transport
```

This work does not enable production MA writes.

```text
MA2_WRITES=0
```

No changes were made to:

- production Builder write path;
- protected objects;
- Fixture 9999 policy;
- SHEESH artistic content;
- production MA transport authorization.

## Tests added

Repository tests were added for:

- scalable provider pools beyond three slots;
- FREE_FIRST ordering;
- role priority;
- provider-specific response-format compatibility;
- bounded parallel fan-out;
- deterministic result order after concurrent completion;
- role-scoped parallelism;
- Designer/Critic parallel candidate propagation into Finalizer.

## Verification status

A container-side clone/test attempt could not run because that environment
could not resolve github.com.

Therefore the current status is:

```text
IMPLEMENTATION_COMMITTED=YES
STATIC_READBACK=PASS
FULL_REGRESSION_AFTER_THIS_CHANGE=NOT_YET_RUN
```

The next coding-agent / physical repo host must run:

```text
git pull --ff-only origin main
python -m unittest discover -s tests -v
python main.py --self-check
```

Do not claim the new parallel provider pool fully regression-verified until
that run passes.

## Product principle

```text
Cloud models provide creative/reasoning capacity.
Multiple model families reduce single-provider dependence.
Local lightweight inference preserves degraded/offline capability.
ZEN remains the reality, evidence, safety, and MA authority boundary.
```
