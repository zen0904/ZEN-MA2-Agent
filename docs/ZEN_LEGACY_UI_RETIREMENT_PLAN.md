# ZEN Legacy UI Retirement Plan

Status: **AUDITED / DO NOT DELETE YET**

OpenClaw is now the intended primary operator interface. ZEN should not maintain two full UI stacks indefinitely. However, the current repository still actively depends on the legacy PySide6 desktop and mobile PWA, so deleting them before OpenClaw cutover would break the only verified operator surface and the Windows portable build.

## Candidate UI code to retire later

### PySide6 desktop shell

Primary candidates:

- `zen_ma2_agent/desktop.py`
- `zen_ma2_agent/desktop_automation.py`
- desktop-only UI tests
- PySide6-specific portable smoke plumbing that exists only to drive the desktop UI

These are UI shell code, not the ZEN Brain/Safety/Builder contract.

### Mobile PWA shell

Primary candidates:

- `web/index.html`
- `web/app.js`
- `web/style.css`
- `web/manifest.json`
- `web/sw.js`
- `web/icon.svg`
- phone/QR/pairing UI flows that exist only for the old PWA

### Legacy combined mobile server surface

`zen_ma2_agent/web_server.py` is a mixed case. It currently serves both static PWA assets and mobile API/write-capable routes. The static/PWA role should retire after OpenClaw cutover. Reusable backend behavior must not be deleted until every needed operation has a stable ZEN backend/OpenClaw adapter path.

## Why deletion is blocked today

Current `main.py` directly imports and starts:

- `ZenDesktop`
- `MobileServer`

The Windows portable build also explicitly bundles the `web/` directory. Existing mobile and portable tests assert that these assets and flows exist.

Deleting those files now would therefore create a deliberate regression before OpenClaw is installed and verified.

## Keep permanently

Do not delete merely because OpenClaw becomes the UI:

- `AgentCore`
- Safety / Preview / Approval semantics
- Resolver / Builder
- MA transport and state providers
- `operator_api.py`
- `operator_server.py`
- MA Bridge
- worker registry/router
- artifact/cache contracts
- any reusable typed schemas and validation

OpenClaw replaces the presentation/operator shell, not ZEN's control authority.

## Cutover gate before deleting old UI

Legacy UI deletion becomes safe only after all of the following are verified on the development host:

1. OpenClaw exact version installed and pinned.
2. ZEN OpenClaw plugin loads successfully.
3. `zen.status`, Worker status, MA status, and artifact status render correctly.
4. Required Preview/Approval workflow has a real typed OpenClaw path or an explicitly retained fallback.
5. OpenClaw can fail without taking down ZEN Field Core.
6. Windows/Ubuntu deployment no longer starts `ZenDesktop` or the old PWA by default.
7. Portable build/tests are updated to the new operator model.
8. Full test suite passes after the removal diff.

## Expected removal phase

When the gate is satisfied, perform one dedicated task:

`ZEN LEGACY UI RETIREMENT 001`

That task should remove only presentation-specific code, update launchers/build scripts/tests/docs, and preserve the backend and safety contracts.

Until then, mark the old UI as **LEGACY FALLBACK**, not current product direction.
