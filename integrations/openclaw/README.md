# ZEN ↔ OpenClaw integration groundwork

Status: **CONTRACT / VERSION-BOUND IMPLEMENTATION PENDING**

This directory is the integration boundary between OpenClaw and ZEN MA2 Agent.
It deliberately does **not** contain ZEN's lighting-design Brain, Safety,
Resolver, Builder, MA transport authority, or show-state authority.

## Product boundary

```text
OpenClaw Control UI / Chat
        ↓
ZEN OpenClaw adapter
        ↓
ZEN local/versioned API
        ↓
ZEN Field Core
        ├─ MA Bridge
        ├─ Safety
        ├─ Resolver / Builder
        ├─ Worker Router
        └─ Artifact / Show State
```

Required invariant:

```text
OPENCLAW_AVAILABLE=NO
FIELD_CORE_AVAILABLE=YES
```

when the local ZEN Field Core itself is healthy.

OpenClaw is the primary operator UI. It is not the safety-critical ZEN runtime.

## Why no plugin implementation is committed yet

OpenClaw's plugin SDK and native Control UI contracts are explicitly
experimental. The host version must therefore be installed, recorded, pinned,
and tested before this repository commits a concrete plugin manifest/runtime
against that API.

As of the architecture review on 2026-09-17, current OpenClaw documentation
supports feature plugins that can contribute pages, navigation, session
actions, panels, dashboard widgets, and other Control UI surfaces. User-installed
native Control UI is a trusted surface and is disabled by default until the
Custom plugin UI lab is enabled.

Implementation must start only after the development host is online and the
exact installed OpenClaw version is known.

Official references used for this boundary:

- https://docs.openclaw.ai/plugins/feature-plugins
- https://docs.openclaw.ai/plugins/sdk-overview
- https://docs.openclaw.ai/plugins/manage-plugins
- https://docs.openclaw.ai/plugins/manifest

## Existing ZEN HTTP surface

ZEN already has a FastAPI mobile/LAN surface in
`zen_ma2_agent/web_server.py`. It currently exposes pairing-protected state,
skill, chat, approval/cancel, and WebSocket endpoints and serves the existing
PWA.

That existing server is evidence that ZEN does **not** need another full web
frontend merely for OpenClaw.

However, it is not yet declared to be the stable OpenClaw API because:

- it was designed for the mobile PWA, not plugin compatibility;
- `MobileServer.start()` currently binds to `0.0.0.0` for LAN/mobile use;
- it includes approval/write-capable routes that a first OpenClaw integration
  should not receive by default;
- its response shapes are internal/mobile shapes rather than a versioned
  OpenClaw-facing contract.

The first OpenClaw implementation should therefore reuse ZEN state/core logic
while adding a narrow, versioned, localhost-first adapter instead of exposing
all existing mobile routes wholesale.

## Initial read-only contract

The first adapter should prioritize read-only state:

- Field Core availability
- MA connection / MA Bridge status
- remote AI availability
- Worker A / Worker B state
- current pipeline role state
- latest artifact identity/metadata

Unknown information must remain `UNKNOWN`; the adapter must not invent state.

See `contracts/zen_operator_status_v0_1.schema.json`.

## Future OpenClaw tools

Candidate tools:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.design.request
zen.preview
zen.approve
```

Only tools backed by a real ZEN API may report success. Unimplemented actions
must return a structured `NOT_IMPLEMENTED` result.

The plugin must never expose:

- arbitrary shell execution;
- arbitrary filesystem access;
- raw MA command execution;
- MA credentials;
- generic unrestricted proxying to ZEN internals.

## Local implementation handoff

When the development computer is online:

1. Install OpenClaw using its current official instructions.
2. Record the exact `openclaw --version` output.
3. Pin that tested host version in ZEN compatibility documentation.
4. Scaffold against the installed version's current Feature Plugin SDK.
5. Keep the plugin thin; call ZEN through a versioned local adapter.
6. Keep development binds loopback-only by default.
7. Run plugin build/validate plus the existing ZEN test suite before merging
   implementation code.

Until those steps are completed, this directory is a contract and handoff, not
a claim that the OpenClaw plugin is operational.
