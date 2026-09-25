# ZEN MA2 OpenClaw Plugin

ZEN does not ship a second operator UI. OpenClaw is the operator surface.

The plugin exposes typed ZEN capabilities and returns structured semantic data. OpenClaw decides how that data appears on its native surfaces, such as chat/tool calls, approval flows, status views, mobile/desktop clients, and future OpenClaw UI surfaces.

## Surface rule

- ZEN owns MA state, planning, safety, Preview, Approval, Builder, execution and verification.
- OpenClaw owns presentation, conversation, device/client adaptation and native UI surfaces.
- The plugin must not expose raw Telnet, shell, arbitrary MA commands, Patch/Address mutation, or a parallel custom ZEN dashboard.
- Write authority stays behind `zen_preview` -> explicit human approval -> `zen_approve`.
- Structured ZEN results should remain UI-agnostic so OpenClaw can render them differently across clients without changing ZEN Core.

## Tools

- `zen_status`
- `zen_ma_status`
- `zen_ma_visual`
- `zen_design_request`
- `zen_preview`
- `zen_approve`
- `zen_worker_status`
- `zen_watchdog_status`
- `zen_host_status`

`zen_ma_visual` is read-only. It asks ZEN to capture the current grandMA2 onPC
window and return bounded pixel-grounded observations; the vision model receives
no MA tools or write authority.

Default development endpoint: `http://127.0.0.1:8876`.

## Build

```bash
npm install
npm run plugin:build
npm run plugin:validate
npm test
```

The plugin is version-pinned to OpenClaw 2026.9.4 while the plugin API is experimental.
