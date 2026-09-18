# Portable USB Runtime

ZEN's portable runtime is now headless. OpenClaw is the operator UI; the USB
bundle carries ZEN's backend/runtime, MA integration resources and mutable state.

`ZEN_HOME` is the directory containing the portable launch scripts. Launchers
derive it from their own location; neither a drive letter nor a user home
directory is part of the contract.

The source working copy lives at:

```text
ZEN_HOME/repo/ZEN-MA2-Agent
```

Mutable state stays under:

```text
ZEN_HOME/{config,knowledge,show_context,projects,logs,cache,temp,secrets,models}
```

Provider secrets remain USB-local and must never be committed.

## Windows runtime

The launcher may start `main.py`, which now runs the headless Field Core.

Default local services:

```text
Operator API  127.0.0.1:8876
MA Bridge     127.0.0.1:8877
```

OpenClaw is a separate operator surface and is not bundled into the Windows
PyInstaller core.

## Portable build

```powershell
.\.venv\Scripts\python.exe scripts\build_portable.py
.\.venv\Scripts\python.exe scripts\smoke_portable.py
```

The bundle intentionally does not include the retired PySide6 desktop or mobile
PWA.

## Autonomous boundary

The provider receives bounded, provenance-bearing context and returns typed
artifacts. Raw MA2, Telnet, Lua and shell command fields remain outside the
model-authority boundary. Safety / Resolver / deterministic Builder remain the
only route toward future MA execution.
