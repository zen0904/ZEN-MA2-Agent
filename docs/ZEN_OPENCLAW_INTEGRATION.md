# ZEN OpenClaw Integration

Status: **LOCAL OPERATOR API + OPENCLAW TOOL PLUGIN IMPLEMENTED / LOCAL E2E VERIFIED**

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

The executable OpenClaw tool plugin now lives at
`integrations/openclaw/zen-ma2-plugin/`. It is pinned and validated against
OpenClaw 2026.9.4. The plugin is deliberately UI-agnostic: it exposes typed ZEN
capabilities while OpenClaw owns the native presentation surface.

## Current ZEN API layer

The legacy mobile PWA/server/pairing surface has been retired. The supported
operator-facing boundary is now the narrow, versioned OpenClaw Operator API:

```text
OpenClaw Operator API
= localhost-first
= bounded typed tools
= read-only observation plus ZEN-gated planning/approval
= no raw/direct MA command authority
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
zen.ma.visual
zen.ma.stage.visual
```

Implemented typed planning/approval tools:

```text
zen.design.request
zen.preview
zen.approve
```

These remain bounded by the ZEN Core path. OpenClaw may request planning, render
a Preview and relay explicit human approval, but it cannot bypass ZEN safety or
submit arbitrary MA commands.

There is no OpenClaw-facing generic shell, arbitrary filesystem operation, raw
MA command endpoint, raw Telnet endpoint, or unrestricted proxy.

`zen.ma.visual` is a read-only Visual Evidence path. On Windows it locates the
visible `grandMA2 onPC` top-level window and captures it with background
`PrintWindow` rendering, then asks the current OpenClaw model to describe only
visible pixels. ZEN wraps those notes as `VISUAL_OBSERVATION` with
`verified_physical_fact=false`. The vision call has no tools and no MA authority;
it cannot switch screens, click MA2, send Telnet, approve a Preview, or mutate
the Show. If Stage/3D is not visibly present, `stage_view_visible` must remain
false.

`zen.ma.stage.visual` is an opt-in, navigation-only Visual Evidence path. It
first enumerates and background-captures existing native MA2 `Screen 2` through
`Screen 6` windows. Vision only verifies the pixels; it receives no tools or MA
authority. If no existing window contains Stage/3D View, the bounded fallback
can address only the compiled Screen 2/3/4 buttons after exact HWND, class,
geometry, foreground, and ownership checks. The interface accepts no arbitrary
coordinate, key, text, MA command, playback, Preview, or Approval input.

## Security boundary

OpenClaw integration must never introduce:

- MA credentials in UI/tool results;
- a direct Worker-to-MA path;
- arbitrary process execution;
- arbitrary filesystem access;
- public unauthenticated operator API exposure;
- bypass of ZEN Safety / Preview / Approval / Resolver / Builder.

Status/visual integration verification remains write-free (`MA2_WRITES=0`).
Any later real mutation still requires the separate ZEN Preview -> explicit
human approval -> Builder/verification path.

## Deployment relationship

The currently validated deployment is:

```text
Windows/iPhone OpenClaw clients
        ↕ managed Tailscale HTTPS
Mac mini `zen-agent-server`
├─ OpenClaw Gateway 2026.9.4
├─ ZEN OpenClaw integration adapter
├─ ZEN Show Agent Controller
└─ loopback controller surfaces
        ↕ typed private transport
Windows `DESKTOP-AA2GR39`
├─ LIGHTING_GRANDMA2 adapter / Field Core
├─ grandMA2 onPC
├─ native export / Stage View evidence
└─ deterministic MA verification
        ↕
Primary Worker A / B when reachable
```

This supersedes the earlier deployment proposal in which the operator Windows
machine hosted the OpenClaw Hub/Gateway and a separate headless host was still
to be selected. The Mac mini is now the validated OpenClaw Gateway + Show Agent
Controller host. Windows remains the lighting execution/evidence host and may
run remote OpenClaw clients only.

This does not collapse authority boundaries. The Mini owns operator/runtime
state and orchestration; Windows keeps MA-local execution and verification.
Worker inference remains non-authoritative for MA control. The logical path is
still typed result/tool request -> ZEN Safety/Preview/Approval/Resolver/Builder
-> MA-local adapter -> native verification.

## Current OpenClaw host status

Current deployment is verified on the Mac mini Show Agent Controller host:

- OpenClaw Gateway runtime is version 2026.9.4 on `zen-agent-server`;
- the Gateway listens on Mini loopback `127.0.0.1:18789` and is published only through managed Tailscale Serve;
- Mini ZEN Controller Operator API listens on loopback `127.0.0.1:8876`;
- Mini `127.0.0.1:18878` proxies only to the Windows typed lighting operator facade;
- Windows full ZEN Operator API remains loopback `127.0.0.1:8876` beside grandMA2;
- `zen-ma2` v0.1.0 loads as a native OpenClaw tool plugin;
- the Gateway tool catalog contains the bounded `zen_*` tools;
- an OpenClaw agent successfully invoked `zen_status` end-to-end;
- `zen_ma_visual` is registered as the ninth bounded tool and has passed a real
  OpenClaw-agent end-to-end call through ZEN Field Core;
- after FieldHost headless MA polling was enabled, the same OpenClaw path
  reported `MA connection: READY` and `ZEN field: ONLINE`;
- the real visual E2E captured the current `grandMA2 onPC` window in the
  background and GPT-5.6 Sol correctly returned `capture_readable=true`,
  `stage_view_visible=false`, bounded UI observations, and `ma2_writes=0`;
- the bounded Stage Visual prototype enumerated native MA2 windows, captured
  existing `Screen 6` with `PRINTWINDOW_RENDERFULLCONTENT`, and returned
  `stage_view_visible=true`, `write_authority=NONE`, and `ma2_show_writes=0`
  without replaying or approving any MA Action;
- when no configured portable Lean provider exists, FieldHost can use an
  isolated OpenClaw SDK completion as the one-shot Designer fallback. That
  completion receives no tools and still returns through ZEN validation,
  compiler, Preview and Approval boundaries;
- the live SHEESH design request has now passed end-to-end through current-Show
  discovery, compound FixtureType evidence, Designer, typed compiler, safe
  allocation and Builder validation into a real `PENDING_APPROVAL` Preview:
  20 Cues, unused Sequence 302, allocated Executor 2.8, and zero MA writes;
- Preview success does not authorize execution. `zen.approve` remains a separate
  explicit human authority transition and was not invoked in this verification;
- the earlier Windows-local Gateway remains historical development evidence only;
  Gateway state, agents, workspace, credentials and the active `zen-ma2` plugin
  have migrated to the Mini, while Windows keeps the MA-local adapter role;
- Windows OpenClaw Gateway autostart is retired; Windows Tray/CLI may connect to
  the Mini as remote clients without owning Gateway state.

No custom ZEN desktop/mobile/dashboard shell should be added merely to duplicate
an OpenClaw-native surface.

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
