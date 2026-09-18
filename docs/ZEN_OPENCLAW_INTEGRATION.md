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
- Host CPU/RAM/disk/available-temperature metrics are exposed read-only through
  `zen.host.status` using psutil; unsupported temperature sensors remain unknown.
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
zen.host.status
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

The operator-visible Windows machine is intentionally separated from the
headless Gateway / Field Core role.

```text
Operator Windows machine
└─ OpenClaw Windows Hub
   └─ visual operator surface only

Headless Gateway / Field Host
├─ OpenClaw Gateway
├─ ZEN OpenClaw integration adapter
└─ ZEN Field Core
    ├─ Local Operator API
    ├─ MA Bridge
    ├─ Safety / Resolver / Builder
    ├─ Worker Router
    └─ Artifact cache
         ↕ private authenticated network later
       Primary Worker A / OS TO VERIFY / GTX1650 / 16 GB
       Primary Worker B / OS TO VERIFY / GPU UNKNOWN / 16 GB
```

The operator Windows machine is not required to install or host the standalone
OpenClaw CLI/Gateway merely to provide the visible UI. It should use the
Windows Hub and connect to the selected Gateway host.

The Gateway / Field Host remains selectable. The 2012 Mac mini is explicitly
excluded from current Gateway / Field Host candidates. The operator Windows
machine remains Hub-only. Current realistic candidates include the operator's actually intended hosts
and, by explicit decision, Worker A as a co-host candidate for OpenClaw Gateway
+ ZEN Field Core + its Worker runtime once that physical machine is back and
its actual OS/network/service state can be verified. This is a hardware co-location decision,
not a trust-boundary collapse. Worker B remains a primary AI Worker and is not
the preferred Gateway candidate. The Worker inference role remains non-authoritative for MA control even if
Worker A physically co-hosts the Gateway / Field Core. The logical path remains
typed Worker result -> Field Core validation / Safety / Resolver / Builder ->
MA. A Worker runtime crash must not be allowed to bypass or inherit Field Core
authority.

## Current OpenClaw host status

- OpenClaw Windows Hub is installed and verified on the operator-visible
  Windows machine, version 2026.9.4;
- no standalone OpenClaw CLI/Gateway is installed on the operator Windows machine;
- select the actual headless Gateway / Field Host;
- install and verify the Gateway on that selected host;
- record the exact tested Gateway/OpenClaw version from the host that actually runs it;
- pin that tested version in `compatibility.json`;
- scaffold the Feature Plugin against that installed SDK/API;
- connect the plugin to the ZEN Operator API;
- verify the Hub can operate against the real Gateway/plugin path;
- do not require a standalone CLI installation on the operator Windows machine
  unless a later concrete need justifies it.

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
