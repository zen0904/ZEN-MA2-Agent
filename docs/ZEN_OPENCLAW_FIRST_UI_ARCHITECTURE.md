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

## Current validated topology

```text
Operator clients
├─ iPhone / mobile OpenClaw client
└─ Windows Tray / CLI as remote clients
          ↕ Tailscale HTTPS
Mac mini `zen-agent-server`
├─ OpenClaw Gateway 2026.9.4
├─ ZEN OpenClaw integration adapter
├─ ZEN Show Agent Controller
├─ CBM / state / cache / recovery
└─ loopback ZEN control surfaces
          ↕ typed private adapter links
Windows `DESKTOP-AA2GR39`
├─ LIGHTING_GRANDMA2 adapter / Field Core
├─ grandMA2 onPC
├─ native export / GUI / Stage View evidence
└─ deterministic MA verification
          ↕
Primary AI Workers when available
```

The 2012 Mac mini is now the validated Home/Portable OpenClaw Gateway + Show
Agent Controller host. This supersedes the earlier Windows-Hub/headless-Gateway
placement proposal. The Windows machine is no longer a Gateway host; it remains
the MA-local lighting adapter and may run only remote OpenClaw clients.

Field hardware is still intentionally not fixed to one machine. Selecting the
Mini as the control-plane/OpenClaw host does not promote it to production MA
write authority. The department adapter beside grandMA2 retains execution and
verification authority, and heavy AI Workers remain non-authoritative compute.

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
zen.ma.visual
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

The current validated sequence is:

1. Host OpenClaw Gateway on `zen-agent-server` with the official OpenClaw service.
2. Keep the Gateway loopback-bound and publish its operator endpoint with managed Tailscale Serve.
3. Keep ZEN Controller full Operator API on Mini loopback only.
4. Install `zen-ma2` on the Mini and route controller tools to local ZEN.
5. Route MA-local tools through Mini loopback `18878` to the Windows typed lighting facade.
6. Keep grandMA2 execution, native exports and visual evidence on Windows.
7. Use Windows/iPhone OpenClaw surfaces as remote clients of the Mini Gateway.
8. Add safe typed department tools gradually; never add generic shell/raw MA transport.
9. Preserve explicit human Preview/Approval and post-write verification semantics.
10. Keep `MA2_WRITES=0` for integration acceptance until a separately approved production write test.

The earlier Windows-hosted Gateway remains historical development evidence, not
the current deployment topology.

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
OPENCLAW_GATEWAY_HOST=ZEN_AGENT_SERVER
OPENCLAW_GATEWAY_VERSION=2026.9.4
OPENCLAW_GATEWAY_LOOPBACK=127.0.0.1_18789
OPENCLAW_GATEWAY_REMOTE_SURFACE=TAILSCALE_SERVE_HTTPS
WINDOWS_OPENCLAW_GATEWAY=RETIRED
ZEN_OPENCLAW_PLUGIN=IMPLEMENTED_V0.1.0
ZEN_CONTROLLER_API=127.0.0.1_8876_LOOPBACK_ONLY
ZEN_LIGHTING_OPERATOR_PROXY=127.0.0.1_18878
WINDOWS_LIGHTING_TYPED_FACADE=TAILSCALE_18878
ZEN_NATIVE_SURFACE_ADAPTATION=ENABLED_BY_TYPED_TOOL_CONTRACTS
OPENCLAW_TO_ZEN_STATUS_E2E=PASS
OPENCLAW_TO_REMOTE_ZEN_MA_STATUS_E2E=PASS
MA2_BACKGROUND_WINDOW_CAPTURE=PRINTWINDOW_VERIFIED
MA2_HEADLESS_AUTO_CONNECT=READY_VERIFIED
FULL_CUSTOM_ZEN_FRONTEND=NOT_PLANNED
RAW_OPENCLAW_TO_MA_COMMAND_AUTHORITY=NO
MA2_WRITES=0
```

The earlier Windows-local OpenClaw verification remains valid historical
evidence for the plugin and MA-local adapter. Gateway authority/state has since
migrated to the Mini without moving grandMA2 execution authority away from the
Windows lighting adapter.

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
