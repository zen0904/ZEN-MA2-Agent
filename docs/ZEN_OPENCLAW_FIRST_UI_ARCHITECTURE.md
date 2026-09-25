# ZEN OpenClaw-First UI Architecture

Status: **IMPLEMENTED / LOCAL END-TO-END VERIFIED ON OPENCLAW 2026.9.4**

This document records the current UI decision for ZEN MA2 Agent.

## Decision

ZEN will not build and maintain a complete standalone operator frontend unless OpenClaw proves unable to provide a required capability.

The default architecture is:

```text
OpenClaw
= primary operator UI
= chat surface
= dashboard/control shell
= session/operator interaction layer

ZEN
= independent backend
= lighting-design Brain
= worker router
= Safety
= Resolver
= deterministic Builder
= MA Bridge
= artifact/show-state authority
```

The operating principle is:

> Reuse OpenClaw for the human-facing interface. Keep ZEN independent for control, safety, state, design reasoning, and MA integration.

## Hard boundary

OpenClaw must never become the safety-critical runtime dependency for ZEN.

The following invariant is required:

```text
OPENCLAW_AVAILABLE=NO
FIELD_CORE_AVAILABLE=YES
```

when the local ZEN Field Core itself is healthy.

An OpenClaw crash or UI failure must not directly disable:

- MA Bridge
- Safety
- Resolver
- Builder
- worker registry/router
- local artifact cache
- cached show/design artifacts
- deterministic local recovery paths

OpenClaw is an adapter and operator surface, not the authority that writes directly to MA2.

## Intended topology

```text
Operator-visible Windows machine
└─ OpenClaw Windows Hub
   ↕
Headless OpenClaw Gateway host
└─ ZEN OpenClaw integration adapter
   ↕
ZEN Field Node API / control plane
   ├─ MA Bridge
   ├─ Watchdog
   ├─ Safety
   ├─ Resolver
   ├─ Builder
   ├─ Worker Router
   ├─ Artifact Store
   └─ Show State
        ↕
 authenticated private network later
        ↕
Primary AI Workers (headless)
```

The Windows machine the operator watches should use the native Hub as the
human-facing surface. It is not required to host the standalone OpenClaw CLI or
Gateway. Gateway placement is a separate deployment decision.

Field hardware is intentionally not fixed to one machine.

Current Gateway / Field Host candidates include only hosts the operator
actually intends to use and that can be verified against the Field Core
requirements. The 2012 Mac mini is explicitly excluded from current
consideration. The operator-visible Windows machine remains Hub-only. Worker A
is explicitly permitted as a co-host candidate for Gateway + ZEN Field Core +
Worker runtime, but D2.6 is blocked until that physical machine returns and
real OS/network/service verification can be performed.

Primary AI compute is provided by two dedicated Worker hosts. Known hardware
currently includes one 16 GB / GTX 1650 4 GB system and another 16 GB system
with weaker/unknown GPU. Their actual current operating systems must be
verified when the machines are physically available; do not assume Ubuntu.

These two Workers are the main inference tier for Researcher / Designer /
Critic / Finalizer and other heavy AI jobs. Their inference runtime is not an
MA command authority and must not bypass the Field Node's Safety / Resolver /
Builder boundary. If Worker A co-hosts the Field Core, process/role boundaries
still remain separate.

The product invariant is the Field Node role and safety boundary, not the
chassis. The primary-compute role of the two Worker hosts is intentional, while
the exact Field Node host remains selectable from actually intended,
evidence-backed candidates.

## What OpenClaw should provide

Use OpenClaw for as much of the operator experience as practical:

- chat
- navigation
- dashboard shell
- status panels
- session/operator interaction
- approvals where the product surface is suitable
- logs/status display where suitable
- mobile/browser access where supported

ZEN should not independently rebuild these features merely to own a custom frontend.

## What ZEN must still provide

ZEN remains responsible for backend semantics and authority:

- typed status API
- typed design requests
- pipeline state
- Worker state
- artifact identity/provenance
- Safety gates
- Preview/Approval semantics
- Resolver
- deterministic Builder
- MA Bridge
- protected-object policy
- production-write boundary

The OpenClaw integration must call explicit typed ZEN APIs/tools. It must not receive unrestricted shell access or raw MA command authority.

## Candidate ZEN tools exposed to OpenClaw

Initial adapter surface may include:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.design.request
zen.preview
zen.approve
```

Only operations backed by real ZEN functionality may report success.

Unfinished operations must return a structured `NOT_IMPLEMENTED` or equivalent state rather than fake completion.

## UI state principles

OpenClaw UI must render real backend state and preserve uncertainty.

Examples:

```text
FIELD_CORE         ONLINE / OFFLINE
MA_BRIDGE          ONLINE / OFFLINE / NOT_IMPLEMENTED
MA2                CONNECTED / DISCONNECTED / NOT_CONFIGURED
REMOTE_AI          AVAILABLE / UNAVAILABLE
WORKER_A           ONLINE / OFFLINE / DEGRADED / UNKNOWN
WORKER_B           ONLINE / OFFLINE / DEGRADED / UNKNOWN
RESEARCHER         IDLE / RUNNING / DONE / FAILED / UNKNOWN
DESIGNER           IDLE / RUNNING / DONE / FAILED / UNKNOWN
CRITIC             IDLE / RUNNING / DONE / FAILED / UNKNOWN
FINALIZER          IDLE / RUNNING / DONE / FAILED / UNKNOWN
```

Do not convert unknown state into an invented positive state for UI convenience.

## Native-surface adaptation rule

ZEN does not choose a presentation surface. It exposes typed semantic capabilities
and structured state; OpenClaw chooses the native surface appropriate to the
current client and interaction.

Examples include chat/tool calls, native status/dashboard views, progress UI,
approval interaction, mobile/desktop clients, and later OpenClaw surfaces that
can consume the same tool contracts.

This means:

- ZEN status is semantic state, not a ZEN-owned status widget.
- ZEN Preview is semantic plan/safety/command data, not a custom preview window.
- ZEN Approval is an explicit authority transition, not a custom button stack.
- ZEN progress/errors/verification remain structured data so OpenClaw can render
  them differently on different clients.
- no OpenClaw surface receives raw Telnet, arbitrary MA command, shell, Patch,
  Address or Fixture-identity authority.

A new OpenClaw client/surface should normally require zero ZEN Core changes.

## No duplicate full frontend

Unless a concrete OpenClaw limitation is verified, do not start a separate project for:

- custom ZEN SPA shell
- custom chat frontend
- custom sidebar/navigation framework
- custom session UI
- custom generic settings UI
- custom mobile frontend shell
- custom dashboard framework

Small purpose-built views remain acceptable if OpenClaw genuinely cannot express a required live-show interaction.

## Integration strategy

The preferred sequence is:

1. Install the native OpenClaw Windows Hub on the operator-visible Windows machine.
2. Select and prepare the headless Gateway / Field Host separately.
3. Record the exact OpenClaw/Gateway version on the host that actually runs the Gateway.
4. Validate Hub-to-Gateway and plugin capabilities for that exact tested version.
5. Pin the tested version for production compatibility.
6. Build a thin `integrations/openclaw/` adapter/plugin on the Gateway side.
7. Connect it to the stable versioned ZEN local API.
8. Render real ZEN status through the Windows Hub.
9. Add safe typed actions gradually.
10. Keep MA2 writes disabled until the independent Safety/Resolver/Builder path is verified.

Do not install a standalone CLI on the operator Windows machine solely to
satisfy a version-check step. Version verification belongs to the component
that actually hosts the Gateway/runtime.

## Versioning rule

OpenClaw UI/plugin APIs may change over time. Production show systems must not silently follow an untested latest version.

Record at minimum:

```text
OPENCLAW_TESTED_VERSION=<exact version>
ZEN_OPENCLAW_ADAPTER_VERSION=<version>
```

Upgrades should be compatibility-tested before deployment to the Field Node.

## Current implementation status

As of this decision:

```text
OPENCLAW_FIRST_UI=IMPLEMENTED
OPENCLAW_WINDOWS_HUB=VERIFIED_2026.9.4
OPENCLAW_DEV_GATEWAY=WINDOWS_LOOPBACK_127.0.0.1_18789
OPENCLAW_PRODUCTION_GATEWAY_HOST=STILL_SEPARATE_DEPLOYMENT_DECISION
ZEN_OPENCLAW_PLUGIN=IMPLEMENTED_V0.1.0
ZEN_OPERATOR_API=127.0.0.1_8876
ZEN_NATIVE_SURFACE_ADAPTATION=ENABLED_BY_TYPED_TOOL_CONTRACTS
OPENCLAW_TO_ZEN_STATUS_E2E=PASS
MA2_HEADLESS_AUTO_CONNECT=READY_VERIFIED
FULL_CUSTOM_ZEN_FRONTEND=NOT_PLANNED
RAW_OPENCLAW_TO_MA_COMMAND_AUTHORITY=NO
```

The current computer being off does not block architecture/documentation work in Git, but it does block actual OpenClaw installation, local plugin loading, browser/UI verification, and local test execution.

## Non-goals of this decision

This document does not authorize:

- direct OpenClaw-to-MA2 arbitrary command execution
- exposing MA credentials to OpenClaw plugins
- public Internet exposure of ZEN/OpenClaw services
- replacing the independent ZEN backend with OpenClaw
- claiming OpenClaw compatibility before testing an exact installed version
- production MA writes
- changing artistic prompts or knowledge

## Summary

The chosen default is:

```text
OpenClaw = interface
ZEN      = brain + control core
```

Reuse the existing UI platform first. Build custom UI only when a verified ZEN requirement cannot be satisfied cleanly through OpenClaw.
