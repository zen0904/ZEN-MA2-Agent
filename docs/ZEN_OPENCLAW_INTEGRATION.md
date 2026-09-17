# ZEN OpenClaw Integration

Status: **GROUNDWORK COMPLETE / LOCAL HOST IMPLEMENTATION PENDING**

This document narrows the implementation path for using OpenClaw as ZEN's
primary operator interface.

## Decision

```text
OpenClaw = operator UI / chat / dashboard shell
ZEN      = independent backend / Brain / Safety / Resolver / Builder / MA Bridge
```

OpenClaw must not become a safety-critical dependency. A healthy local ZEN
Field Core must remain usable when OpenClaw is unavailable.

## Current repository groundwork

The repository now contains:

- `docs/ZEN_OPENCLAW_FIRST_UI_ARCHITECTURE.md`
- `docs/CODEX_HANDOFF_OPENCLAW_FIRST_001.md`
- `integrations/openclaw/README.md`
- `integrations/openclaw/contracts/zen_operator_status_v0_1.schema.json`
- `integrations/openclaw/contracts/zen_tool_result_v0_1.schema.json`

No OpenClaw plugin runtime has been claimed as implemented yet.

## Current ZEN web/API reality

ZEN already ships FastAPI infrastructure in `zen_ma2_agent/web_server.py` and
mobile/PWA tests in `tests/test_agent_core_mobile.py`.

The existing API currently provides pairing-protected state, skills, chat,
approval/cancel, and WebSocket updates. This should be reused as architectural
evidence and shared Core logic, not blindly exposed as the OpenClaw contract.

Important distinction:

```text
Existing mobile API
= current LAN/mobile operator surface

Future OpenClaw adapter API
= narrow, versioned, localhost-first integration surface
```

The existing `MobileServer` intentionally binds to `0.0.0.0` for LAN/mobile
access. The first OpenClaw adapter should default to loopback because OpenClaw
and ZEN are expected to run on the same Field Node in the intended deployment.

## OpenClaw capability facts checked on 2026-09-17

Current official OpenClaw documentation states that Feature Plugins can add
Control UI pages, navigation, session actions, panels, dashboard widgets, and
other UI contributions. OpenClaw also states that plugin SDK and native Control
UI APIs are experimental and host versions should be pinned and tested.

User-installed native Control UI is a trusted surface and is disabled by
default until the Custom plugin UI lab is enabled.

These facts justify an OpenClaw-first UI architecture, but they also mean the
exact plugin scaffold should be generated against the exact OpenClaw version
installed on the development host rather than guessed in advance.

Official references:

- https://docs.openclaw.ai/plugins/feature-plugins
- https://docs.openclaw.ai/plugins/sdk-overview
- https://docs.openclaw.ai/plugins/manage-plugins
- https://docs.openclaw.ai/plugins/manifest

## First implementation slice when the development host is online

1. Install OpenClaw from current official guidance.
2. Record and pin the exact host version.
3. Scaffold a Feature Plugin using that installed version's CLI/SDK.
4. Keep the plugin thin.
5. Add a localhost-first ZEN adapter that emits
   `zen.operator_status.v0.1`.
6. Start with read-only tools/status only.
7. Return `NOT_IMPLEMENTED` for design/preview/approval operations not yet
   backed by stable typed APIs.
8. Validate that OpenClaw can stop while ZEN Field Core remains healthy.
9. Run plugin build/validate and the existing ZEN Python tests before merging
   executable plugin code.

## Initial status mapping

The OpenClaw surface should display, without inventing facts:

```text
FIELD CORE      ONLINE / OFFLINE / DEGRADED / UNKNOWN
MA BRIDGE       ONLINE / OFFLINE / DEGRADED / UNKNOWN
MA2             READY / CONNECTING / DISCONNECTED / DEGRADED / UNKNOWN
REMOTE AI       AVAILABLE / UNAVAILABLE
WORKER A        ONLINE / OFFLINE / DEGRADED / UNKNOWN
WORKER B        ONLINE / OFFLINE / DEGRADED / UNKNOWN
Researcher      IDLE / RUNNING / DONE / FAILED / UNKNOWN
Designer        IDLE / RUNNING / DONE / FAILED / UNKNOWN
Critic          IDLE / RUNNING / DONE / FAILED / UNKNOWN
Finalizer       IDLE / RUNNING / DONE / FAILED / UNKNOWN
Latest artifact known / none
```

## Initial tool boundary

Candidate names are reserved by the contract:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.design.request
zen.preview
zen.approve
```

The first implementation should expose only operations that have a real typed
ZEN backend path. A UI button is not authorization to invent or bypass a
backend capability.

## Security boundary

OpenClaw integration must not introduce:

- raw MA command execution;
- arbitrary shell execution;
- arbitrary filesystem operations;
- unrestricted generic HTTP proxying;
- MA credentials in UI/tool results;
- a direct Worker-to-MA path.

Production MA writes remain behind ZEN's own Safety / Preview / Approval /
Resolver / Builder boundary.

## Deployment relationship

Intended later placement:

```text
2012 Mac mini / Ubuntu
├─ OpenClaw Gateway + Control UI
└─ ZEN Field Core
    ├─ MA Bridge
    ├─ Safety / Resolver / Builder
    ├─ Worker Router
    └─ Artifact cache
         ↕ private authenticated network later
       Home Worker A / GTX1650 / 16 GB
       Home Worker B / GPU UNKNOWN / 16 GB
```

Only the Mac mini travels. Remote workers remain optional compute and must not
be required for Field Core availability.

## Not implemented yet

- exact OpenClaw host version pin;
- generated OpenClaw plugin scaffold;
- plugin manifest/runtime;
- Custom plugin UI enablement;
- browser rendering verification;
- dedicated localhost ZEN adapter route;
- remote-worker inference;
- real MA-Initiated Bridge execution;
- production MA writes.

`MA2_WRITES=0` remains the integration-phase requirement.
