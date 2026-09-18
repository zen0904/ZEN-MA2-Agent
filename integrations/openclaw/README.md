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

The legacy mobile/PWA server has been retired. ZEN now exposes a dedicated,
narrow, versioned Operator API for OpenClaw integration:

```text
GET  /healthz
GET  /zen/v0.1/status
POST /zen/v0.1/tools/{tool_name}
```

Default bind is loopback-only at `127.0.0.1:8876`.

The integration must use this typed boundary rather than reintroducing the
retired mobile server or exposing ZEN internals wholesale.

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

Current deployment split:

- operator-visible Windows machine: verified OpenClaw Windows Hub 2026.9.4;
- standalone CLI/Gateway is not required on that Windows operator machine;
- Gateway / Field Host remains unselected until a real host returns and passes
  preflight;
- Worker A is the preferred first co-host candidate to verify, not a selected
  host.

After the actual Gateway host is selected:

1. install OpenClaw Gateway using current official instructions for that OS;
2. record the exact Gateway/OpenClaw version on that host;
3. pin that tested Gateway version in ZEN compatibility documentation;
4. scaffold against that installed version's current Feature Plugin SDK;
5. keep the plugin thin and call the versioned ZEN Operator API;
6. keep development binds loopback-only by default where co-located;
7. run plugin validation plus the existing ZEN test suite before merging.

Until those steps are completed, this directory is a contract and handoff, not
a claim that the OpenClaw plugin is operational.
