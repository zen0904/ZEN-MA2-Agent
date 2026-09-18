# ZEN Legacy UI Retirement Plan

Status: **SUPERSEDED / RETIREMENT COMPLETED**

This file is retained only as historical planning context.

The deletion gate described in the original plan has been completed. Current
authoritative state is recorded in:

- `docs/ZEN_LEGACY_UI_REMOVAL_001.md`
- `docs/ZEN_OPENCLAW_FIRST_UI_ARCHITECTURE.md`
- `docs/ZEN_OPENCLAW_INTEGRATION.md`

The retired presentation stack no longer exists on current `main`:

- PySide6 desktop workspace;
- Tkinter MVP UI;
- mobile PWA assets;
- mobile FastAPI UI server;
- desktop-only automation bridge;
- packaged desktop UI smoke/runtime-hook plumbing;
- QR/pairing frontend flow.

The final core-only compatibility remnants were also removed:

- `zen_ma2_agent/pairing.py`;
- `AgentCore.pairing`;
- `phone_connected` snapshot state;
- `AgentCore.phone_urls()`.

The product boundary is now:

```text
OpenClaw = operator presentation / chat / dashboard shell
ZEN      = independent backend / Field Core / Brain / Safety / Resolver /
           deterministic Builder / MA Bridge / Worker Router / Watchdog
```

OpenClaw replaces the presentation shell only. Safety, approval semantics,
typed backend contracts, MA transport, state providers, Worker routing and
artifacts remain ZEN-owned.

No production MA write authority is introduced by this retirement.
