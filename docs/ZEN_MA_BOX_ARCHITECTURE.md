# ZEN MA Box Architecture

Status: **ARCHITECTURE_PROPOSAL / NOT_IMPLEMENTED**

Product idea in one sentence:

> **把 ZEN 接到 MA 上，MA 就有腦。**
>
> Connect ZEN to grandMA2 so the console can initiate requests to ZEN, ZEN can reason behind a strict typed/safety boundary, and the result can return to MA without making an LLM itself the command transport.

This document defines the long-term **MA-initiated** hardware/runtime architecture for ZEN MA2 Agent. It does **not** replace the current ZEN-initiated workflow. Both directions should eventually terminate in the same typed Intent / Resolver / Builder / Safety system.

---

## 1. Product intent

The current ZEN architecture primarily treats MA2 as a controlled target: an operator uses ZEN from a desktop/mobile/runtime entry point, ZEN plans an operation, and a guarded transport sends the final allow-listed MA2 command.

ZEN MA Box adds the reverse entry path:

```text
grandMA2
   │
   │ ZEN request + bounded current-show context
   ▼
ZEN MA Box
   │
   ├─ MA ingress / protocol parser
   ├─ request router
   ├─ deterministic fast path OR ZEN Brain
   ├─ Designer / Critic / Finalizer when needed
   ├─ Typed Intent / typed Design Plan
   ├─ Safety / Resolver
   ├─ Builder
   └─ MA egress / verification
   │
   ▼
grandMA2 executes approved result
```

The desired operator experience is that MA itself appears to have an attached reasoning system. The operator should not need to open five applications before using the Agent. The appliance should boot, self-check, join the configured MA network, expose its bridge, and become available to approved MA-side Macro/Plugin entry points.

This is an **external brain**, not an attempt to embed arbitrary AI code inside grandMA2.

---

## 2. Architectural invariant: LLM output is never the MA command boundary

The MA-initiated direction does not weaken any existing ZEN safety rule.

The forbidden path is:

```text
MA → free-form request → LLM → arbitrary MA command string → immediate execution
```

The required path is:

```text
MA
→ authenticated/bounded request envelope
→ parser / request classifier
→ typed request
→ optional ZEN reasoning
→ typed Intent / typed design artifact
→ deterministic validation
→ Resolver
→ Builder
→ Preview / Approval gate when write-producing
→ allow-listed MA operation
→ MA
→ read-back / verification when available
```

An LLM may propose artistic or semantic intent. It must not gain raw Telnet, shell, Lua, filesystem, service-control, or unrestricted command-generation authority.

Production writes remain subject to the same policy already used elsewhere in ZEN:

- typed schema
- deterministic validation
- fresh show-state checks where required
- protected object exclusions
- Preview / Approval for modifying actions
- explicit capability gates
- read-back or verification strategy where available
- fail-closed behavior on ambiguity, stale state, transport failure, unsupported capability, or evidence mismatch

---

## 3. Two input directions, one core

ZEN should eventually support both of these without duplicating artistic or safety logic.

### 3.1 ZEN-initiated

```text
Desktop / Phone / API / Autonomous workflow
→ AgentCore / ZEN Brain
→ Typed Intent
→ Resolver / Builder
→ MA2
```

### 3.2 MA-initiated

```text
MA Macro / Plugin / MA-side trigger
→ ZEN MA Bridge
→ AgentCore / ZEN Brain
→ Typed Intent
→ Resolver / Builder
→ MA2
```

The difference is the **input adapter**, not the authority model.

The MA-side bridge must not become a shortcut around AgentCore, Safety, Preview/Approval, Resolver, Builder, or verification.

---

## 4. First appliance target: 2012 Mac mini

The first-generation hardware target is an existing **2012 Mac mini** repurposed as a dedicated headless ZEN appliance.

Current known hardware state from the owner:

- machine: 2012 Mac mini
- RAM: **reported as probably 16 GB; exact amount must be verified before deployment documentation is finalized**
- storage: **original HDD currently installed**
- CPU SKU: not yet confirmed in this architecture record
- built-in Gigabit Ethernet: intended MA-network interface
- Wi-Fi and/or later USB Ethernet: intended management / Internet path

Target deployment:

```text
2012 Mac mini
→ Ubuntu Server
→ no permanent desktop GUI requirement
→ headless 24/7 service host
→ systemd-managed ZEN services
→ wired MA network
→ optional separate Internet / management path
```

This machine is designated **ZEN MA Box Gen 0 / Development Appliance**. It is intended to validate the architecture before considering Raspberry Pi, newer mini PCs, or custom hardware.

### 4.1 RAM assessment

If the installed RAM is confirmed to be **16 GB**, memory capacity is considered good for the appliance role:

- MA bridge
- watchdog
- telemetry
- resolver
- builder
- API / Web UI
- show-state cache
- knowledge store
- Python runtime
- cloud / remote LLM router
- modest local GGUF experiments

RAM is therefore not the first expected bottleneck if 16 GB is confirmed.

Large-model performance must not be inferred from RAM alone. CPU generation and model size/quantization will dominate local inference latency.

### 4.2 Original HDD assessment

The original HDD is **not a blocker for an initial non-production PoC**, but it is not the preferred permanent storage for a 24/7 appliance.

Reasons an SSD is strongly preferred before treating the Mac mini as a reliable field box:

- faster boot and service recovery
- faster Python environment / package startup
- faster model loading and mmap behavior
- lower latency for logs, cache, indexes, knowledge data, run artifacts, and checkpoints
- reduced impact from concurrent logging + inference + state persistence
- better responsiveness during package updates and restart recovery
- lower dependence on an aging mechanical disk as a single failure point

Recommended hardware order:

1. **Verify actual RAM and CPU.**
2. **Back up current disk before repurposing.**
3. Initial architecture PoC may run on the HDD if needed.
4. Before sustained 24/7 or field use, replace the HDD with a SATA SSD.
5. Re-run storage health, reboot/recovery, service-start, and local inference benchmarks after the SSD change.

The architecture must not assume that the SSD exists yet. Deployment scripts should detect/report storage characteristics instead of silently treating slow I/O as an Agent failure.

---

## 5. Hardware comparison: Mac mini vs Raspberry Pi

Two hardware directions remain valid:

### 5.1 2012 Mac mini

Preferred first implementation because:

- hardware already exists
- x86_64 Linux is close to the current Python / llama.cpp development environment
- fewer ARM-specific package surprises
- adequate RAM if the reported 16 GB is confirmed
- built-in Ethernet is suitable for the MA-side network
- easier reuse of existing x86_64 tooling
- provides a realistic always-on appliance environment

Disadvantages:

- old CPU
- power use higher than a Pi-class appliance
- original HDD should be treated as temporary
- local LLM inference may be slow
- physical size is larger than an eventual embedded box

### 5.2 Raspberry Pi 5

Potential later target after the architecture is proven.

Advantages:

- small
- low power
- appliance-like
- inexpensive to duplicate

Disadvantages for first port:

- ARM64 dependency surface
- possible differences in Python wheels / native dependencies / llama.cpp build behavior
- weaker CPU inference expectation
- additional hardware/thermal/storage choices

Decision for Gen 0: **prove the architecture on the Mac mini first; optimize hardware later.**

---

## 6. Service decomposition

The appliance must not run as one giant process where an LLM crash can take down MA communications.

Proposed long-term service split:

```text
zen-ma-bridge.service
zen-watchdog.service
zen-builder.service
zen-agent.service
zen-web.service
```

Optional later service:

```text
zen-supervisor.service
```

### 6.1 `zen-ma-bridge.service`

Responsibility:

- MA → ZEN ingress
- ZEN → MA transport coordination
- request framing
- protocol versioning
- request IDs
- acknowledgement / response routing
- reconnect behavior
- duplicate-request protection
- transport health

Requirements:

- must not depend on a running LLM
- must not import artistic logic
- must not execute arbitrary free-form MA command strings from an LLM
- should remain responsive even while `zen-agent.service` is performing long inference
- should fail closed if the Builder/Resolver path is unavailable for a write-producing request

### 6.2 `zen-watchdog.service`

Responsibility:

- MA availability
- bridge state
- MA Telnet connectivity
- network latency / packet loss
- known node reachability where a verified monitoring mechanism exists
- ZEN service health
- CPU / RAM / disk usage
- disk health indicators where available
- machine temperature where reliably accessible
- Internet / configured cloud-provider reachability
- local model endpoint health
- state freshness / stale-cache conditions

The watchdog must not use an LLM for its basic decisions.

Normal operation should be quiet. Alerts should be state-transition based rather than constant polling spam.

Example alert state machine:

```text
NORMAL
  ↓ first threshold crossing
WARNING  → notify once
  ↓ remains warning
WARNING  → do not spam
  ↓ recovers
NORMAL   → recovery notification
```

Critical example:

```text
CRITICAL
MA Telnet connection lost
Recovered after 2.7 s
No command executed during outage
```

### 6.3 `zen-builder.service`

Responsibility:

- receive only validated typed operations
- deterministic MA command compilation
- allow-list enforcement
- protected object enforcement
- Preview / Approval token validation where required
- write sequencing
- execution audit
- verification/read-back orchestration

The Builder must remain usable independently of cloud LLM availability.

### 6.4 `zen-agent.service`

Responsibility:

- Researcher
- Lighting Designer
- Critic
- Finalizer
- local / cloud / remote provider routing
- knowledge retrieval
- visual/reference reasoning
- autonomous design workflows

This process is allowed to fail without killing the MA bridge, watchdog, or deterministic Builder.

### 6.5 `zen-web.service`

Responsibility:

- headless management UI
- status dashboard
- approval interface
- logs and diagnostics
- provider status
- show-state visibility
- appliance setup
- maintenance actions that are explicitly authenticated and allow-listed

The Web UI is a management surface, not a raw Telnet terminal.

### 6.6 Optional `zen-supervisor.service`

If introduced, the supervisor may:

- observe process health
- restart failed ZEN services according to policy
- expose aggregate status
- coordinate controlled shutdown/restart

It must not become an alternate MA-command transport.

---

## 7. Failure-domain isolation

A central product requirement is that AI availability is not equivalent to appliance availability.

Required behavior matrix:

| Failure | Bridge | Watchdog | Builder | AI design | Expected operator state |
|---|---|---|---|---|---|
| Internet lost | UP | UP | UP | Local-only / unavailable depending provider | deterministic MA operations remain available |
| Cloud API lost | UP | UP | UP | degraded/unavailable | no MA transport outage |
| Local LLM crash | UP | UP | UP | unavailable until recovery | bridge remains alive |
| `zen-agent` hung | UP | UP | UP | unavailable | request timeout, no unsafe write |
| Web UI crash | UP | UP | UP | unaffected | manage via recovery path |
| Builder unavailable | UP | UP | DOWN | reasoning may continue but writes blocked | fail closed |
| MA Telnet lost | ingress may remain UP | reports CRITICAL | writes blocked | reasoning may continue offline | no command attempted until verified recovery |
| Mac mini network loss | DOWN from MA perspective | local watchdog records event | blocked | local process may continue | MA side must time out safely |

No recovery mechanism is allowed to replay a write automatically unless the request protocol explicitly proves idempotence and the Builder has a fresh-state policy for that operation.

---

## 8. Fast path vs AI path

Not every request should invoke a model.

### 8.1 Deterministic fast path

Example intent:

```text
ZEN GROUP 4 DIMMER 50
```

Desired internal route:

```text
MA
→ bridge
→ fixed parser
→ typed SET_DIMMER intent
→ safety
→ resolver
→ builder
→ MA
```

The LLM is not involved.

This path should target low and predictable latency and remain available during model or Internet failure.

### 8.2 Reasoning path

Example semantic request:

```text
ZEN DESIGN NEXT CHORUS
```

Desired internal route:

```text
MA
→ bridge
→ typed DESIGN_REQUEST
→ bounded show context / evidence
→ ZEN Agent
→ Designer
→ Critic
→ Finalizer
→ typed design plan
→ Preview / Approval
→ Resolver
→ Builder
→ MA
```

Long inference is acceptable here. It must not block deterministic bridge handling for unrelated requests.

---

## 9. MA → ZEN transport strategy

The first PoC may use the grandMA2 ability under investigation to initiate outbound Telnet text to an external `IP:Port` and send a bounded string.

Candidate example from current design discussion:

```text
Telnet 192.168.0.50:9000 "ZEN ..."
```

This is currently a **PoC transport direction**, not yet a production dependency. The exact real-console syntax, behavior, reconnect characteristics, length limits, quoting rules, concurrency behavior, and security properties must be verified on the actual grandMA2 environment before it becomes a capability gate.

The reverse direction already aligns with ZEN's existing external MA Telnet control model:

```text
ZEN Box → grandMA2 Telnet Remote
```

Therefore the conceptual full-duplex system is:

```text
MA outbound text / Plugin / future adapter
             ↓
        ZEN ingress
             ↓
      typed processing
             ↓
        ZEN Builder
             ↓
      MA Telnet Remote
```

Future transports may include a dedicated MA-side Plugin/Lua adapter or another verified network adapter. Transport replacement must not alter the typed request and safety contracts above it.

---

## 10. Do not use free-form natural language as the permanent wire protocol

Natural language can exist at the operator/Agent layer, but the MA-to-box network protocol should become deterministic.

Proposed wire family:

```text
ZEN/1 <TYPE> <REQUEST_ID> <FIELDS...>
```

Examples:

```text
ZEN/1 REQ 8392 DIMMER GROUP=4 VALUE=50
ZEN/1 REQ 8393 DESIGN TARGET=NEXT_CHORUS
ZEN/1 CANCEL 8393
```

Candidate responses:

```text
ZEN/1 ACK 8392
ZEN/1 ACCEPTED 8393
ZEN/1 WORKING 8393
ZEN/1 NEED_APPROVAL 8393 PLAN=sha256:...
ZEN/1 DONE 8392
ZEN/1 ERROR 8393 CODE=MA_OFFLINE
ZEN/1 ERROR 8393 CODE=UNSUPPORTED
ZEN/1 ERROR 8393 CODE=STATE_CHANGED
```

The protocol should eventually define:

- version
- request ID
- request type
- bounded field grammar
- maximum payload length
- response types
- timeout semantics
- cancellation
- duplicate request behavior
- idempotence classification
- authentication / trusted-network policy
- approval-token correlation
- error vocabulary
- structured telemetry correlation ID

A protocol parser must reject unknown/oversized/unparseable requests instead of forwarding arbitrary strings to an LLM.

---

## 11. Request classes

Recommended request classes:

### `QUERY`

Read-only state or diagnostics. No MA write.

Examples:

- MA online?
- node health
- selected known show state
- current service state

### `SAFE_ACTION`

Deterministic allow-listed operation already classified as SAFE by the existing safety system.

### `MODIFY_ACTION`

Write-producing operation requiring Preview / Approval or the existing explicit approval contract.

### `DESIGN_REQUEST`

Asks ZEN Brain for artistic/semantic reasoning. Never directly executable.

### `SYSTEM_REQUEST`

Restricted appliance operations such as health, diagnostics, service status. Must never become a generic shell interface.

Raw `COMMAND` where the payload is an arbitrary grandMA2 command should not be part of the public MA-to-ZEN protocol.

---

## 12. Approval model for MA-initiated writes

MA-initiated workflows must make approval correlation explicit.

Possible lifecycle:

```text
MA: ZEN/1 REQ 9001 DESIGN TARGET=NEXT_CHORUS
ZEN: ACK 9001
ZEN: WORKING 9001
ZEN: NEED_APPROVAL 9001 PLAN=<hash>

Operator reviews plan in MA-side surface or Web UI.

MA/Web: APPROVE 9001 PLAN=<same hash>
ZEN: verify current Show fingerprint
ZEN: build
ZEN: execute
ZEN: verify
ZEN: DONE 9001
```

Approval must be invalidated when relevant show state changes after Preview if the operation requires a fresh fingerprint.

An old approval token must never authorize a newly regenerated plan.

---

## 13. Watchdog scope

The ZEN MA Box should become useful even when no AI request is running.

Desired monitored domains:

### MA/session

- MA reachability
- Telnet readiness
- session/connection identity where a verified read-only accessor exists
- reconnect timing
- stale state

### Network

- interface link state
- ping latency to configured MA endpoints
- packet loss trend
- bridge socket status
- duplicate/replayed request counts

### Nodes / endpoints

Where reliable discovery/state evidence exists:

- node present/missing
- last seen time
- affected configured universes or logical scope only when this mapping is verified

Example:

```text
WARNING
Node 2 disconnected
Last seen 1.2 s ago
Universe 5-8 may be affected
```

The phrase `may be affected` must remain conditional unless the node→universe binding is actually known.

### Host

- CPU load
- RAM usage
- disk usage
- disk errors / filesystem state where available
- process health
- temperature where the hardware/driver exposes a reliable value
- reboot reason / service restart count where available

### AI/provider

- local model endpoint health
- provider latency
- provider unavailable
- Internet reachability
- cloud API unavailable
- inference queue depth

AI/provider failures are warnings about AI capability, not automatic MA-control critical events.

---

## 14. Network architecture

Recommended early deployment:

```text
                  ┌──────────────────────┐
                  │     ZEN MA Box       │
                  │   2012 Mac mini      │
                  └──────────┬───────────┘
                             │ built-in Ethernet
                             │
                       MA isolated LAN
                             │
                    grandMA2 / Nodes

Management / Internet:
Mac mini Wi-Fi
or later dedicated USB Ethernet
```

Long-term preferred separation:

- **MA interface**: deterministic static addressing, only MA/control traffic
- **Management/Internet interface**: SSH, updates, Web management, cloud provider traffic

The MA network must not depend on Internet routing.

Cloud-provider traffic should not require the MA interface to have Internet access.

Recommended firewall posture:

- bind MA ingress only on the configured MA interface/address
- allow only known protocol port(s)
- restrict source IPs to the intended console/onPC hosts where practical
- bind administrative SSH/Web surfaces to the management network when possible
- no public Internet exposure of MA bridge ports
- no UPnP requirement
- no default port forwarding

Network examples in docs are illustrative. Do not hard-code a site-specific `192.168.x.x` address into core logic.

---

## 15. Ubuntu Server deployment model

Target OS: **Ubuntu Server, headless**.

The purpose is not to recreate the Windows Desktop UI on Linux. The appliance should run as services and expose only the interfaces needed for operation and maintenance.

Proposed filesystem model while preserving `ZEN_HOME` concepts:

```text
/opt/zen/                    immutable-ish application checkout/build
/var/lib/zen/                mutable ZEN_HOME/state
/var/lib/zen/knowledge/
/var/lib/zen/show_context/
/var/lib/zen/projects/
/var/lib/zen/cache/
/var/lib/zen/models/
/var/log/zen/                logs or symlink/journal-backed policy
/etc/zen/                    system configuration
/etc/zen/secrets/            protected provider credentials
```

Exact paths are deployment policy, not core assumptions. The Python core should continue using portable/path abstractions rather than literal Linux or Windows paths.

Ubuntu responsibilities:

- Python venv or controlled runtime environment
- x86_64 Linux llama.cpp build when local model is enabled
- `systemd` service lifecycle
- journald/log rotation policy
- firewall
- static MA-side network configuration
- optional Wi-Fi/management network
- unattended reboot policy only after explicit design; never reboot during live control without operator policy

---

## 16. `systemd` behavior expectations

Example dependency philosophy, not final unit files:

```text
network-online.target
 ├─ zen-ma-bridge.service
 ├─ zen-watchdog.service
 ├─ zen-builder.service
 ├─ zen-web.service
 └─ zen-agent.service
```

Avoid making the bridge require the AI service.

Preferred restart behavior:

- bridge: restart on unexpected failure, bounded backoff
- watchdog: restart on unexpected failure
- builder: restart on unexpected failure, but never replay pending writes automatically
- agent: restartable independently
- web: restartable independently

A restarted service must reconstruct state from durable artifacts only where safe. In-flight modifying requests should default to `UNKNOWN / REQUIRES_REVIEW`, not auto-resume into execution.

---

## 17. Local LLM policy on the Mac mini

The ZEN MA Box does not require a large local model for its base value.

Must remain fully local/deterministic:

- MA bridge
- protocol parser
- watchdog
- show-state cache
- safety classification
- resolver
- builder
- approval tracking
- verification
- logging / telemetry

May use Local LLM / remote workstation / cloud depending policy:

- lighting design
- song analysis
- Researcher
- Critic
- Finalizer
- complex natural-language interpretation

If the Mac mini truly has 16 GB RAM, a small/quantized GGUF can be tested. However, the 2012 CPU must not be assumed to provide acceptable show-design latency until benchmarked.

For the current Qwen2.5-7B Q4_K_M class, memory capacity may be sufficient, but latency on the exact Mac mini CPU is an empirical question. The product architecture therefore supports:

```text
LOCAL deterministic services always
+
LOCAL small model when acceptable
+
REMOTE stronger machine / cloud optional for expensive reasoning
```

No cloud provider is allowed to become a dependency for bridge/watchdog/builder availability.

---

## 18. Cross-platform coding rules from this point forward

New core work should follow these rules so the Ubuntu migration remains a deployment port instead of a rewrite.

### Core code must not assume

- `E:\...`
- a fixed Windows drive letter
- `.cmd` existence
- PowerShell availability
- `start`/Explorer semantics
- Windows process names
- Windows-only service management
- a GUI session

### OS-specific behavior belongs in adapters / launchers

Examples:

```text
scripts/windows/
scripts/linux/
deploy/systemd/
platform adapters
```

Existing `.cmd`/PowerShell tools may remain for Windows. They should not become the canonical representation of Agent state or business logic.

The current `ZEN_HOME` portable-state principle should be preserved: knowledge, show context, projects, logs, cache, temp, secrets, and models are durable runtime concerns independent of the frontend OS.

---

## 19. State and data ownership

The box should distinguish:

### Repository-owned

- schemas
- runtime code
- protocol definitions
- deterministic validators
- static docs
- tests

### Appliance mutable state

- provider config
- secrets
- show context
- current connection config
- knowledge indexes
- run artifacts
- approvals
- telemetry
- cache
- model files

### MA authoritative state

- actual live Show state
- fixture/group/preset/sequence state
- session state
- execution outcome

The Agent must never treat stale cached state as more authoritative than a fresh verified MA source.

---

## 20. Security boundary

MA-initiated control creates a new ingress surface and therefore requires an explicit security model.

Minimum rules:

- no arbitrary shell endpoint
- no arbitrary filesystem endpoint
- no arbitrary Telnet pass-through
- no raw MA command endpoint exposed to MA-side callers
- protocol payload size limits
- source allow-list / trusted network policy
- request rate limits appropriate for the transport
- logs redact secrets
- cloud API keys never go to MA or model prompt
- management endpoints authenticated
- approval records correlate request ID + plan hash + current state requirements

Because a show-control LAN may be physically trusted but operationally fragile, the protocol should prioritize deterministic failure behavior over complex network magic.

---

## 21. Telemetry and logs

Every MA-initiated request should eventually have a correlation record containing only safe metadata such as:

- request ID
- protocol version
- ingress source identity/IP where appropriate
- request class
- parsed typed intent hash
- received timestamp
- acknowledgement timestamp
- role/provider used if AI was invoked
- selected evidence IDs when relevant
- Preview plan hash
- approval status
- Builder execution status
- verification status
- error code
- completion timestamp

Do not log:

- provider API keys
- Authorization headers
- unnecessary full model prompts
- unrestricted raw Telnet sessions
- passwords

---

## 22. Suggested implementation phases

This architecture is intentionally not implemented during the current autonomous-design smoke-debugging work.

### Phase 0 — architecture capture

Current phase.

Deliverables:

- this document
- cross-platform coding constraint acknowledged
- no runtime behavior change

### Phase 1 — MA → Box ingress PoC, read-only

Goal:

- prove actual MA can send a bounded request to the box
- parse protocol
- return/log ACK
- **zero MA writes**

Acceptance:

- repeated request IDs are detected
- malformed payload rejected
- no LLM required
- bridge restart does not corrupt state

### Phase 2 — deterministic round-trip PoC

Goal:

```text
MA → ZEN typed deterministic request → existing Safety/Resolver/Builder → MA
```

Use an explicitly safe disposable test target only.

No autonomous artistic inference required.

### Phase 3 — approval handshake

Goal:

- request
- Preview
- approval correlation
- current-state revalidation
- execute
- verify

### Phase 4 — watchdog / telemetry

Goal:

- MA status
- bridge status
- service health
- network health
- edge-triggered alerts

### Phase 5 — Ubuntu Mac mini deployment

Goal:

- headless boot
- services start automatically
- network interfaces configured
- power-loss recovery tested
- no GUI dependency
- no Windows path dependency

SSD upgrade is strongly recommended before this phase is considered a field-deployment milestone.

### Phase 6 — MA-initiated ZEN Brain requests

Goal:

- DESIGN_REQUEST from MA
- bounded context retrieval
- Designer/Critic/Finalizer
- typed result
- no raw command generation
- Preview/Approval before production write

### Phase 7 — reliability / productization

- protocol hardening
- version migration
- watchdog policy
- field update/rollback
- hardware image / installer
- multi-show test
- network isolation test
- failure injection
- recovery drills

Only after these phases should smaller hardware such as Raspberry Pi or a custom appliance become a primary optimization target.

---

## 23. Acceptance criteria for the ZEN MA Box concept

The concept is successful only if all of the following can eventually be demonstrated:

1. MA can initiate a request without opening the desktop ZEN UI first.
2. The request reaches the ZEN Box through a bounded, versioned protocol.
3. Deterministic requests do not require an LLM.
4. AI requests cannot bypass typed Intent / typed design schemas.
5. No LLM can directly execute arbitrary MA command text.
6. Bridge/watchdog/builder remain functional when Internet, cloud, or local LLM are unavailable.
7. Modifying operations preserve Preview/Approval and fresh-state safety.
8. MA transport failure cannot cause blind command replay.
9. Service restart cannot silently resume an uncertain write.
10. Operator receives useful abnormal-state alerts without normal-state spam.
11. Core logic runs without Windows-specific path assumptions.
12. Ubuntu deployment works headlessly after reboot.
13. The Mac mini can function as a development appliance even if local AI inference is slow.
14. Local or remote AI provider choice does not change MA safety semantics.
15. The system remains manually recoverable using native MA resources if the Agent disappears.

---

## 24. Explicit non-goals for Gen 0

Gen 0 does not require:

- embedding a model inside grandMA2
- replacing grandMA2 networking
- making all MA commands available through ZEN
- removing operator approval
- making the Mac mini the sole show-control device
- large-model real-time inference
- Raspberry Pi optimization
- custom PCB/hardware
- automatic writes during transport recovery
- cloud-required show control

---

## 25. Relationship to current autonomous-designer work

Current work is still focused on proving whether the ZEN Brain can reason well enough:

```text
Knowledge Store
→ role-specific retrieval
→ Researcher
→ Lighting Designer
→ Critic
→ Finalizer
→ typed autonomous design artifact
```

ZEN MA Box is the deployment and interaction architecture that can host that Brain later.

Do not mix the two validation questions:

1. **Can ZEN design/reason well enough?**
2. **Can MA reliably initiate and safely consume ZEN capability through an appliance?**

A model-quality failure should not be diagnosed as a bridge failure. A bridge failure should not be diagnosed as a model-quality failure.

---

## 26. Current decision record

As of this architecture proposal:

```text
MA_INITIATED_ARCHITECTURE = PLANNED
IMPLEMENTATION = NOT_STARTED
FIRST_BOX = 2012_MAC_MINI
TARGET_OS = UBUNTU_SERVER_HEADLESS
CURRENT_RAM = PROBABLY_16_GB_UNVERIFIED
CURRENT_STORAGE = ORIGINAL_HDD
SSD_FOR_INITIAL_POC = OPTIONAL
SSD_FOR_24_7_FIELD_APPLIANCE = STRONGLY_RECOMMENDED
BUILT_IN_ETHERNET_ROLE = MA_NETWORK
MANAGEMENT_INTERNET_PATH = WIFI_OR_FUTURE_SECOND_NIC
LLM_REQUIRED_FOR_BRIDGE = NO
LLM_REQUIRED_FOR_WATCHDOG = NO
LLM_REQUIRED_FOR_BUILDER = NO
RAW_LLM_TO_MA_COMMAND = FORBIDDEN
PRODUCTION_WRITE = PREVIEW_APPROVAL_SAFETY_BOUNDARY
```

The defining product principle remains:

> **把 ZEN 接到 MA 上，MA 就有腦。**
