# ZEN Legacy UI Removal 001

Status: **IMPLEMENTED / OPENCLAW-FIRST**

ZEN no longer maintains its own operator frontend as a product surface.

## Decision

```text
OpenClaw = primary operator UI / chat / dashboard / session shell
ZEN      = independent Field Core / Brain / Safety / Resolver / Builder / MA Bridge
```

OpenClaw is not a Field Core dependency. Stopping OpenClaw must not stop ZEN's
headless control plane.

## Removed

The following legacy UI implementation is retired:

- PySide6 desktop workspace
- Tkinter MVP UI
- mobile PWA HTML/JS/CSS/service worker
- mobile FastAPI UI server
- desktop automation bridge used only to drive PySide6 tests
- packaged-desktop UI smoke scripts
- PySide6 runtime hook
- PySide6 and qrcode runtime dependencies

These components duplicated capabilities now assigned to OpenClaw and increased
Windows packaging size and maintenance cost.

## Preserved

The removal does not delete:

- AgentCore
- typed intent/workflow logic
- Safety / approval semantics
- Telnet transport
- state providers
- deterministic Builder
- Researcher / Designer / Critic / Finalizer
- Worker registry/router
- artifact/cache contracts
- Operator API
- MA-Initiated Bridge
- USB-portable runtime/state layout

The legacy PairingManager and a small amount of compatibility state inside
AgentCore remain temporarily because core code still references them. They no
longer have a frontend or network surface and can be removed in a later
core-only cleanup after the full development-host regression suite runs.

## New runtime

`main.py` now launches a headless Field Core:

- ZEN Operator API: loopback `127.0.0.1:8876`
- MA-Initiated Bridge: loopback `127.0.0.1:8877`

Both require explicit opt-in before non-loopback binding.

OpenClaw will connect to the Operator API through the version-pinned integration
plugin once the development host is online and the exact OpenClaw version has
been installed and verified.

## Safety

This cleanup adds no MA execution path.

```text
MA2_WRITES=0
CODEX_ARTISTIC_INTERVENTION=NONE
```

DIMMER remains parse-only and DESIGN remains parse-only in the MA-Initiated
Bridge foundation.
