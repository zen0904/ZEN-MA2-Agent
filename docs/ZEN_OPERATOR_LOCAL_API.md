# ZEN Local Operator API

Status: **IMPLEMENTED / OPENCLAW PLUGIN + LOCAL E2E VERIFIED**

This is the narrow local API boundary intended for the OpenClaw adapter. It is
separate from the existing LAN/mobile API in `zen_ma2_agent.web_server`.

```text
OpenClaw plugin
    ↓ localhost
ZEN Operator API
    ↓
ZEN Operator contract
    ↓
ZEN Field Core
```

The API exposes no raw/direct MA write authority. Read-only tools remain read-only;
planning is bounded, and approval delegates only to ZEN Core's existing explicit
approval/Builder boundary. The HTTP transport itself has no LLM dependency.

## Current endpoints

`GET /healthz`

Returns only the local API health envelope:

```json
{"schema":"zen.operator_http_health.v0.1","status":"OK"}
```

`GET /zen/v0.1/status`

Returns `zen.operator_status.v0.1`.

`POST /zen/v0.1/tools/{tool_name}`

Accepts only:

```json
{
  "arguments": {},
  "request_id": "optional"
}
```

Current read-only tools:

- `zen.status`
- `zen.worker.status`
- `zen.ma.status`
- `zen.artifact.latest`
- `zen.watchdog.status`
- `zen.host.status`
- `zen.ma.visual`

The normal design entry is `show.program`, reached through the bounded
`zen.design.request` tool. Internal Skills, read-only providers, resolution,
design, compilation, and verification are implementation capabilities and are
not separate operator steps.

- `zen.design.request` accepts `{"request":"..."}` and plans only;
- `zen.preview` accepts no arguments or an optional bounded `action_id`;
- `zen.approve` accepts a bounded `action_id` and boolean `danger_confirmed`.

These three tools remain `NOT_IMPLEMENTED` when Field Core handlers are not
injected. When injected, design delegates to AgentCore planning, preview is
read-only, and approval delegates to AgentCore's existing approval boundary.

`zen.ma.visual` is independently read-only. When its provider is available it
captures the current visible `grandMA2 onPC` top-level window, runs a zero-tool
vision observation, and returns bounded pixel-grounded evidence. Those visual
notes are not promoted into verified fixture/patch/capability/physical facts
and the path has no MA write authority.

Unknown tools are rejected. There is no generic shell, filesystem, HTTP proxy,
raw Telnet, or raw MA command endpoint.

## Field Core independence

`status_provider_from_core()` reads only the local runtime fields needed for the
operator contract. It intentionally does not call `AgentCore.snapshot()`, so a
status poll does not trigger unrelated Internet-status probing.

Current mapping is deliberately conservative:

- a running local Core maps to `FIELD_CORE_AVAILABLE=true`;
- current MA runtime connection state is mapped to the bounded operator enum;
- MA Bridge runtime state is projected from the local Bridge server;
- remote AI availability is projected from the Worker registry;
- Watchdog status is available as a separate read-only tool with bounded,
  edge-triggered events;
- pipeline role states remain `UNKNOWN` until a real pipeline-state source is wired;
- credentials are never copied into the operator result.

## Binding policy

`OperatorServer` defaults to:

```text
127.0.0.1:8876
```

A non-loopback bind is rejected unless code explicitly passes
`allow_remote=True`.

That flag is only an escape hatch for later controlled integration work. It is
not production authorization to expose the API. Do not enable a remote bind
until authenticated private transport has been implemented and reviewed.

The intended OpenClaw deployment keeps OpenClaw and this API on the same Field
Node, so loopback is the normal path.

## What remains pending

- broader browser/Control UI verification beyond the verified native chat/tool path;
- authenticated private-network policy if a future remote bind is needed;
- operator-tuned alert thresholds for CPU/RAM/disk/thermal metrics;
- authenticated/private Worker transport beyond the existing health probe;
- pipeline progress source wiring;
- artifact-store source wiring.

Status and visual-observation verification remain write-free (`MA2_WRITES=0`).
Any real mutation remains behind ZEN Preview -> explicit human approval ->
Builder/readback; the Operator API still exposes no raw MA/Telnet/shell path.
