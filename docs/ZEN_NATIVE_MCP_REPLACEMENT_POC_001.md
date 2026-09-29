# ZEN Native MCP Replacement POC 001

Status: **CUTOVER VERIFIED / NATIVE MCP PRIMARY / LEGACY PLUGIN DISABLED FOR ROLLBACK / NO APPROVE OR MA WRITE AUTHORITY / NO OPERATOR WORKFLOW CHANGE**

Date: 2026-09-29
Host: `zen-agent-server`
OpenClaw: `2026.9.4 (3a9d69d)`
Python MCP SDK: `2.2.0`

## Purpose

Test whether OpenClaw's native MCP support can replace the custom OpenClaw
TypeScript tool-plugin layer without weakening ZEN's existing typed authority
boundaries.

This POC does **not** replace the Windows lighting facade, ZEN Safety,
Preview/Approval, Builder, protected-object policy, MA transport, or native
readback. It only standardizes the Mini/OpenClaw-facing tool transport.

## Existing path

```text
OpenClaw
  -> custom zen-ma2 TypeScript plugin
  -> ZEN HTTP tool envelope
  -> Mini controller / Windows lighting typed facades
  -> ZEN core
```

The TypeScript plugin duplicates tool names, parameter schemas, endpoint
routing, result unwrapping, and transport glue that MCP already standardizes.
## POC path

```text
OpenClaw 2026.9.4
  -> native MCP stdio client
  -> zen_ma2_agent/mcp_operator_server.py
  -> existing loopback typed HTTP facades
     - controller 127.0.0.1:18876
     - lighting operator proxy 127.0.0.1:18878
  -> existing ZEN authority boundary
```

No new persistent MCP daemon is required. OpenClaw launches the stdio MCP
process on demand. Streamable HTTP remains available only as a debug or
future cross-client transport.

## Exposed POC tools

The MCP surface now matches the current OpenClaw plugin catalog with 14 tools:

- status/health: `zen_status`, `zen_ma_status`, `zen_department_status`,
  `zen_worker_status`, `zen_watchdog_status`, `zen_host_status`;
- visual observation: `zen_ma_visual`, `zen_ma_stage_visual`;
- design/preview: `zen_design_request`, `zen_preview`,
  `zen_position_preview`, `zen_position_raw_preview`,
  `zen_position_calibration_preview`;
- semantic readback: `zen_position_semantic_bindings`.

`zen_approve` is deliberately absent. No shell, filesystem, raw MA command,
Patch/Address/Fixture mutation, or approval bypass is exposed.

Read-only tools use read-only/idempotent/non-destructive annotations. Visual
observation tools remain non-destructive but are not claimed idempotent.
Preview-producing tools are explicitly not read-only, but remain
non-destructive and closed-world. The controller delegation is accepted only
when it proves `REMOTE_PREVIEW_ONLY` and `ma2_writes=0`.

The adapter also accepts only loopback upstream endpoints and rejects unexpected
tool-result schemas or mismatched tool identities.

## Runtime verification

### OpenClaw discovery

`openclaw mcp probe zen-native-stdio --json` discovered the complete
14-tool MCP catalog:

```text
tools=14
diagnostics=[]
```

After the annotations were added, the earlier missing-annotation warning was
absent.

### Real stdio tool call

The official Python MCP Client called `zen_ma_status` through stdio. The live
bounded result reported:

```text
bridge_state=ONLINE
connection_state=READY
target=127.0.0.1:30000
```

The live call was read-only. Preview-producing tools may create bounded ZEN
Preview state through the already-verified controller delegation, but the MCP
surface has no approval tool and no direct MA write authority.
## Regression

Targeted MCP tests:

```text
6 tests / OK
```

Final repository regression with stdio as the default transport and the
14-tool parity surface:

```text
1004 tests / OK
```

The targeted suite covers loopback-only upstreams, exact tool-result identity,
preview-only delegation, rejection of broadened remote authority, catalog
parity, and MCP safety annotations.

## Replacement conclusion

The custom OpenClaw TypeScript tool plugin is now a **disabled rollback-only layer**.
OpenClaw native stdio MCP is the verified primary ZEN tool transport on the Mini.

Preferred direction:

```text
OpenClaw native MCP
  -> one thin ZEN MCP adapter
  -> existing verified ZEN typed authority surfaces
```

The current 14-tool OpenClaw plugin catalog is represented by the MCP surface.
The controlled cutover was completed on 2026-09-29: plugin `zen-ma2` is disabled
in runtime config but retained on disk/config for rollback.
Do not add `zen_approve` merely for symmetry. Any future approval-capable MCP
tool requires its own explicit authority review and must not inherit the
preview/read-only policy.

The Windows cross-host typed facades remain. MCP standardization on the Mini is
not evidence that those boundaries are redundant.
## Infrastructure reduction

The POC deliberately rejected a permanent `127.0.0.1:18879` MCP service
after proving Streamable HTTP interoperability. Native stdio works and removes
one listening port, one daemon lifecycle, and one restart/health surface.

The temporary HTTP MCP configuration was removed after the stdio proof.
A draft `zen-mcp-operator.service` for the earlier port-18879 design was
explicitly not adopted because native stdio makes that daemon unnecessary.

## Controlled cutover verification

After disabling the legacy `zen-ma2` TypeScript plugin and restarting the
OpenClaw Gateway through its real root user systemd-user service:

```text
legacy plugin       = disabled
primary MCP server  = zen-native-stdio
MCP catalog         = 14 tools
MCP diagnostics     = []
zen_approve exposed = NO
persistent MCP port = NONE
```

A real Gateway agent run then invoked
`zen-native-stdio__zen_status` successfully. The terminal receipt recorded the
tool in `successfulToolNames`, proving the actual OpenClaw runtime used native
MCP after the legacy plugin was disabled.

That same agent turn did not produce a final natural-language reply because the
effective NVIDIA provider timed out in the provider phase after approximately
121 seconds. This is a **separate provider-completion blocker** and does not
invalidate MCP transport/tool execution. The run performed no MA2 write and no
approval action.

Temporary duplicate MCP configurations were removed. Runtime now exposes only
`zen-native-stdio`. The legacy plugin configuration remains disabled as the
intentional rollback path; its disabled-config warning is therefore accepted.

Rollback, if needed, is to re-enable the existing `zen-ma2` plugin and restart
the Gateway. No plugin uninstall or destructive config removal was performed.

## Next replacement audits

1. Replace generic provider transport/fallback with a dedicated tool-less
   OpenClaw ZEN Designer route where current model policy can be preserved.
3. Retire the unfinished custom AI Worker API in favor of standard model
   runtimes/endpoints once FieldHost status is migrated.
4. Replace generic host telemetry with Glances while retaining only ZEN-specific
   semantic health projection.
5. Move crawling/document/media parsing to mature upstream tools while keeping
   ZEN provenance, promotion, artistic reasoning, Builder and native readback.

This side-track does not replace the current M4 acceptance gate.
