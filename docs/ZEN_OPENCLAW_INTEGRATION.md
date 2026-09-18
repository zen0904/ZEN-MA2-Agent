# ZEN OpenClaw Integration

Status: **LOCAL OPERATOR API IMPLEMENTED / OPENCLAW HOST PLUGIN PENDING**

## Decision

```text
OpenClaw = operator UI / chat / dashboard shell
ZEN      = independent backend / Brain / Safety / Resolver / Builder / MA Bridge
```

OpenClaw is the primary human-facing interface, but it is not a safety-critical
runtime dependency. A healthy ZEN Field Core must remain usable when OpenClaw
is unavailable.

## Implemented repository foundation

The repository now contains:

- `docs/ZEN_OPENCLAW_FIRST_UI_ARCHITECTURE.md`
- `docs/CODEX_HANDOFF_OPENCLAW_FIRST_001.md`
- `docs/ZEN_OPERATOR_LOCAL_API.md`
- `integrations/openclaw/README.md`
- `integrations/openclaw/compatibility.json`
- `integrations/openclaw/contracts/zen_operator_status_v0_1.schema.json`
- `integrations/openclaw/contracts/zen_tool_result_v0_1.schema.json`
- `zen_ma2_agent/operator_api.py`
- `zen_ma2_agent/operator_server.py`
- focused operator API/server tests

No executable OpenClaw Feature Plugin is claimed yet because the exact installed
OpenClaw version must be verified and pinned first.

## Current ZEN API layer

The legacy mobile PWA/server/pairing surface has been retired. The supported
operator-facing boundary is now the narrow, versioned OpenClaw Operator API:

```text
OpenClaw Operator API
= localhost-first
= read-only today
= no direct MA write authority
```

ZEN core services remain independent of OpenClaw, but there is no second
ZEN-owned mobile or desktop frontend stack to maintain.

## Local Operator API

The OpenClaw-facing local boundary is implemented in
`zen_ma2_agent/operator_server.py`.

Default bind:

```text
127.0.0.1:8876
```

Current endpoints:

```text
GET  /healthz
GET  /zen/v0.1/status
POST /zen/v0.1/tools/{tool_name}
```

The server rejects non-loopback binds by default. A future remote deployment
requires an explicit opt-in plus a separate authenticated-network review.

## Initial status mapping

The status contract exposes bounded state only:

```text
FIELD CORE
MA BRIDGE
MA2 connection
REMOTE AI
Workers
Researcher
Designer
Critic
Finalizer
Latest artifact metadata
```

Unknown information remains `UNKNOWN`.

The current Core adapter deliberately does not call `AgentCore.snapshot()` so a
UI status poll does not cause unrelated Internet-status checks.

Current conservative mappings:

- Field Core is available when the local Core/provider is running.
- MA runtime connection state is mapped to the bounded operator enum.
- MA Bridge state is projected from the local Bridge runtime.
- Remote AI availability is projected from the Worker registry.
- Watchdog exposes bounded edge-triggered Field/Bridge/MA/Worker state through
  `zen.watchdog.status`.
- Pipeline roles remain `UNKNOWN` until real pipeline state is wired.
- Latest artifact remains null until a real artifact source is wired.

## Tool boundary

Implemented read-only tools:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.watchdog.status
```

Reserved but intentionally not implemented:

```text
zen.design.request
zen.preview
zen.approve
```

Reserved actions return structured `NOT_IMPLEMENTED` rather than synthetic
success.

There is no OpenClaw-facing generic shell, arbitrary filesystem operation, raw
MA command endpoint, raw Telnet endpoint, or unrestricted proxy.

## Security boundary

OpenClaw integration must never introduce:

- MA credentials in UI/tool results;
- a direct Worker-to-MA path;
- arbitrary process execution;
- arbitrary filesystem access;
- public unauthenticated operator API exposure;
- bypass of ZEN Safety / Preview / Approval / Resolver / Builder.

`MA2_WRITES=0` remains the integration-phase requirement.

## Deployment relationship

Intended placement is role-based rather than tied to one chassis:

```text
Selected Field Host
├─ OpenClaw Gateway + Control UI
└─ ZEN Field Core
    ├─ Local Operator API
    ├─ MA Bridge
    ├─ Safety / Resolver / Builder
    ├─ Worker Router
    └─ Artifact cache
         ↕ private authenticated network later
       Primary Worker A / GTX1650 / 16 GB
       Primary Worker B / GPU UNKNOWN / 16 GB
```

The selected Field Host may be the operator's current Mac, the 2012 Mac mini,
or a future replacement. The two Worker hosts are the primary AI inference
compute tier. They remain non-authoritative for MA control and must not be
required for Field Core availability: if both workers are unavailable, heavy
AI capability may be unavailable, but local Safety, Bridge, Resolver/Builder
and deterministic recovery remain alive.

## Still pending on the powered development host

- install OpenClaw using current official guidance;
- record `openclaw --version`;
- pin that exact tested version in `compatibility.json`;
- scaffold the Feature Plugin against that installed SDK/API;
- enable the trusted custom plugin UI only as required;
- connect the plugin to the localhost Operator API;
- verify the Control UI in a browser;
- run the full repository test suite.

## Later runtime work

Separate future work remains for:

- real remote inference job execution beyond the existing Worker registry/router and health/capability probing;
- MA-Initiated Bridge execution beyond the existing parser/TCP foundation;
- pipeline progress source wiring;
- artifact-store source wiring;
- authenticated private networking;
- real production approval/write integration after separate validation.

OpenClaw failure must continue to satisfy:

```text
OPENCLAW_AVAILABLE=NO
FIELD_CORE_AVAILABLE=YES
```

when the ZEN Field Core itself is healthy.
