# ZEN Field + Home Distributed Architecture

Status: **ARCHITECTURE FOUNDATION PARTIALLY IMPLEMENTED / REAL REMOTE INFERENCE PENDING**

This document records a possible next-stage deployment model for ZEN MA2 Agent. It is intentionally a design note, not an implementation commitment. The purpose is to preserve the idea in Git so it can be evaluated and refined later without interrupting the current validated ZEN development path.

## 1. Core idea

The operator-facing Windows machine is the visible control surface and uses the
OpenClaw Windows Hub. The ZEN Field/Gateway runtime may live on a separate
headless host. Heavier AI compute remains on one or more headless Primary AI
Workers.

```text
Venue / field

 Operator Windows machine
 - OpenClaw Windows Hub
 - visible UI only
        ↕
 Headless Gateway / ZEN Field Node
 selected host / hardware TBD
 - OpenClaw Gateway
 - MA Bridge
 - Watchdog
 - Safety
 - Resolver / Builder
 - request router
 - show-state cache
 - knowledge / artifact cache
 - logs / telemetry
    ↕
 Internet / private overlay network
    ↕
Home

 AI Worker A
 DDR3 PC / 16 GB RAM / GTX 1650 4 GB

 AI Worker B
 DDR3 PC / 16 GB RAM / second older GPU (exact model TBD)
```

The two Worker hosts are the primary heavy-compute tier for ZEN AI inference.
The design goal is still not to make field safety depend on them. The Field Node
remains the authoritative local control and safety boundary, while the Workers
provide the main Researcher / Designer / Critic / Finalizer compute whenever
reachable.

## 2. Current known hardware

### 2.1 Field Node candidates

The Field Node role is not assigned permanently to one chassis.

Current decision:

- the operator-visible Windows machine is Hub-only and is not the Gateway / Field Host;
- the 2012 Mac mini is explicitly excluded from current Gateway / Field Host consideration;
- Worker A/B remain primary AI compute and are not Gateway authorities by default;
- only actually intended, physically available hosts with verified networking,
  service/autostart and maintenance characteristics should be considered.

The product therefore targets a host-neutral Field Core contract. Headless
operation is supported, but OS-specific deployment details belong in adapters
and service packaging rather than in core logic.

### 2.2 Primary AI Worker A

Known target:

- DDR3-generation desktop PC
- planned 16 GB RAM
- NVIDIA GTX 1650, 4 GB VRAM
- remains at home
- intended role: primary local inference worker

The GTX 1650 does not provide enough VRAM to assume the full current Qwen 7B model plus runtime state will fit entirely in VRAM. Partial GPU offload / CPU+GPU inference is expected unless later benchmarks prove otherwise.

### 2.3 Primary AI Worker B

Known target:

- DDR3-generation desktop PC
- planned 16 GB RAM
- second older discrete GPU
- exact GPU model is currently unknown and must be measured before assigning a role
- remains at home

Do not assume the two GPUs combine into a single larger VRAM pool. Unless a future inference backend explicitly supports distributed model execution, each worker is an independent compute node.

## 3. Hard architectural rule: field operation must survive home failure

The following path is forbidden as a production dependency:

```text
MA → Field Node → Internet → Home AI → required response → MA
```

because a venue network outage, home power outage, VPN failure, worker crash, or ISP problem would then disable ZEN at the console.

The required behavior is:

```text
Fast / deterministic / safety-critical operation
→ handled locally on the Field Node

Heavy research / redesign / multi-agent reasoning
→ may use Home AI Workers when reachable

Remote workers unavailable
→ remote AI capability becomes unavailable
→ Field Node core remains available
→ cached artifacts and deterministic functions remain usable
```

Suggested status semantics:

```text
FIELD_CORE_AVAILABLE=YES
REMOTE_AI_AVAILABLE=YES|NO
WORKER_A=ONLINE|OFFLINE|DEGRADED
WORKER_B=ONLINE|OFFLINE|DEGRADED
```

`REMOTE_AI_AVAILABLE=NO` must never imply `FIELD_CORE_AVAILABLE=NO`.

## 4. What belongs on the Field Node

The Field Node should host components that must remain available beside the console:

- MA ingress / bridge
- MA egress boundary
- Watchdog
- health checks
- request router
- typed request validation
- Safety / approval gates
- Resolver
- deterministic Builder
- protected-object policy
- current-show cache
- completed design artifacts
- evidence / knowledge cache needed for local operation
- telemetry / logs
- remote-worker availability state
- optional local Web/API used from phone, tablet, or laptop

The Field Node must not require a graphical desktop. Headless Ubuntu managed by
systemd and SSH is one valid target; the current Mac may also host the role
when appropriate. The operator-visible Windows machine is expected to use the
OpenClaw Windows Hub rather than serving as the required CLI/Gateway host.
OpenClaw remains the primary operator surface, so core logic must not depend on
a local desktop GUI.

## 5. What belongs on Home AI Workers

Home workers are compute resources, not MA command authorities.

Appropriate responsibilities include:

- Researcher inference
- Lighting Designer inference
- Critic inference
- Finalizer inference
- song/context analysis
- retrieval preprocessing
- optional embeddings / indexing jobs
- preproduction batch work
- alternative design generation
- expensive second-pass critique

A home worker must never receive unrestricted raw MA command execution authority.

Expected boundary:

```text
Field Node
→ typed AI job envelope
→ Remote Worker
→ model inference
→ typed/result artifact
→ Field Node validation
→ local Safety / Resolver / Builder
→ MA
```

The worker can propose reasoning or design intent. It cannot bypass the Field Node's validation or directly control MA2.

## 6. Preproduction-first workflow

The preferred operating model is to perform expensive work before arriving at the venue.

```text
At home
songs / show context
→ Home AI Workers
→ Research / Design / Critique / Finalization
→ validated artifacts
→ synchronize to Field Node

At venue
Field Node already carries:
- song analysis
- design intent
- cue plan / proposed sequence structure
- relevant knowledge/evidence refs
- cached final artifacts
```

This allows the operator to continue even if the venue has no useful Internet connection.

A venue-time heavy redesign can be sent to the home workers only when connectivity exists. Small deterministic adjustments should remain local whenever possible.

## 7. Remote connectivity

Remote transport is **TBD** and must be selected after security and reliability testing.

Current candidates include:

- WireGuard
- Tailscale or another WireGuard-based private overlay
- equivalent authenticated private network

Do not expose an unauthenticated inference or MA-related service directly to the public Internet.

Remote worker traffic should be limited to a typed job protocol and health/status channel. The Field Node remains the trust boundary for anything that could eventually produce an MA write.

Current foundation reuses the Worker's existing HTTP `/health` and
`/capabilities` endpoints. The Field Node may register Worker endpoints at
runtime without hard-coded addresses. Worker identity and schema are checked
before registry state is updated. A reachable HTTP service is not enough to
declare AI capability: routing requires `model_runtime_available=true`.

## 8. Job routing

Initial routing should remain simple. Do not begin with a complex distributed scheduler.

Possible first routing model:

```text
Worker A available
→ send heavy AI job to Worker A

Worker A unavailable and Worker B compatible
→ use Worker B

No worker available
→ mark REMOTE_AI_AVAILABLE=NO
→ retain Field Core
```

Later, routing may account for:

- worker benchmark results
- model availability
- GPU / CPU capability
- available RAM / VRAM
- queue depth
- current inference latency
- role suitability
- thermal state
- health state

The exact GPU in Worker B must be identified before defining preferred role placement.

## 9. Parallelism and realistic performance expectations

Two home workers do not automatically halve end-to-end runtime if the workflow remains strictly sequential:

```text
Researcher → Designer → Critic → Finalizer
```

The latest successful local Smoke 002 baseline on the existing CPU-only development environment was approximately 55 minutes 44 seconds end to end. Most of that time was actual model inference.

Future speed improvements can come from two independent sources:

1. GPU-accelerated inference on the home workers.
2. Restructuring only genuinely independent work into parallel stages.

Potential later parallelizable examples:

```text
             ┌─ song/context analysis ─┐
Research ----┤                         ├→ Designer
             └─ knowledge retrieval ───┘

Designer
   ↓
┌──────────────┬────────────────┐
Critic A       Critic B         deterministic technical checks
└──────────────┴────────────────┘
               ↓
            Finalizer
```

This is a future optimization. Do not change the current validated artistic pipeline merely to claim parallelism.

## 10. Failure isolation

Required behavior:

### Home Worker crash

- Field Node stays alive.
- MA Bridge stays alive.
- Watchdog stays alive.
- deterministic Builder stays alive.
- remote job is failed/requeued according to policy.
- no MA write occurs from an incomplete remote result.

### Internet / VPN loss

- remote workers marked unavailable.
- cached artifacts remain usable.
- local deterministic actions remain available.
- no repeated notification spam; state transitions should be edge-triggered.

### Field Node restart

- services should restore automatically.
- worker state is re-discovered.
- no pending remote result may become an MA write without fresh validation and any required approval.

### Stale remote result

A remote result must be checked against the relevant request identity / show context / version before it can enter downstream validation. Stale output must fail closed.

## 11. Artifact synchronization

A future synchronization layer may copy validated preproduction artifacts from home to the Field Node.

Requirements:

- explicit artifact version / hash
- request or project identity
- conflict-safe behavior
- atomic replacement where possible
- no automatic destructive overwrite of operator-edited show data
- offline-readable local copy on the Field Node
- enough provenance to distinguish cached results from newly generated results

Do not use Git itself as the runtime synchronization protocol for live show artifacts unless explicitly justified later. Git remains appropriate for source code and architecture documentation.

## 12. Security boundary

Remote workers should have the minimum authority necessary.

They should not receive:

- raw MA Telnet credentials / unrestricted MA transport
- shell access to the Field Node through the ZEN job protocol
- arbitrary filesystem paths
- arbitrary command execution
- production-write authority

The Field Node should accept only authenticated, schema-validated worker responses tied to an outstanding request.

## 13. Headless Gateway / Field Node is acceptable

The absence of a local graphical interface is not a blocker.

Target operational behavior:

```text
power on Field Node
→ Ubuntu boots
→ systemd starts ZEN services
→ services self-check
→ MA network / remote worker status becomes available
→ operator interacts through MA-side entry points and/or Web UI from another device
```

SSH should be an administration and recovery path, not a requirement for normal show operation.

## 14. Suggested phased implementation

This proposal should be implemented only after the current ZEN baseline remains stable.

### Phase 0 — Documentation only

Current state.

- preserve architecture idea
- identify Worker B GPU
- do not change current validated Brain pipeline

### Phase 1 — Field Node foundation

- headless service layout
- local Bridge / Watchdog / Safety boundaries
- local cache
- no remote AI dependency

### Phase 2 — Single remote worker PoC

- one authenticated remote worker
- one typed test job
- response returned to Field Node
- no MA writes
- failure and timeout handling

### Phase 3 — Real inference worker

- same current Qwen model / controlled benchmark
- measure actual inference latency
- compare with CPU-only baseline
- record RAM / VRAM / swap / thermals

### Phase 4 — Second worker

- discover capability
- health reporting
- simple availability-based routing
- no unnecessary distributed scheduler

### Phase 5 — Artifact synchronization and offline workflow

- preproduction artifacts synchronized before travel
- offline cache semantics
- stale-result protection

### Phase 6 — Optional parallel workflow research

Only after benchmark evidence shows where parallel work is useful.

## 15. Non-goals for now

This proposal does not authorize or imply:

- immediate Ubuntu migration of the current Windows development machine
- replacing the validated current runtime
- public Internet exposure
- distributed VRAM pooling
- changing artistic prompts for speed
- automatic production MA writes from home
- removing Preview / Approval boundaries
- assuming venue Internet availability
- assuming Worker B performance before its GPU is identified

## 16. Decision snapshot

Current working direction to preserve for later discussion:

```text
Field hardware:
Selected host / hardware TBD
→ ZEN Field Node / Master / Coordinator
→ local safety-critical services
→ actually intended evidence-backed host only
→ 2012 Mac mini EXCLUDED
→ operator Windows machine HUB-ONLY

Primary AI compute:
Worker A / 16 GB / GTX 1650
Worker B / 16 GB / GPU TBD
→ main ZEN inference / heavy-compute tier

Field Node:
actual selected headless/service-capable host
→ local Safety / MA Bridge / Resolver / Builder / cache / recovery

Design principle:
Home compute accelerates ZEN.
Home compute is never required for field safety/core operation.
```

No implementation should begin solely because this file exists. Future work should first confirm the second GPU, remote-network constraints, desired offline behavior, and whether this distributed model still offers enough practical benefit compared with a single stronger portable inference machine.