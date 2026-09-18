# ZEN MA2 Agent

ZEN is an OpenClaw-first, headless grandMA2 assistant runtime.

```text
OpenClaw
= operator UI / chat / dashboard / session shell

ZEN
= Brain / Field Core / Safety / Resolver / Builder / MA Bridge / Worker Router
```

The operator frontend is no longer implemented inside this repository. The
legacy PySide6 desktop and mobile PWA were retired to avoid maintaining a second
UI stack.

## Current runtime

Run the Field Core:

```powershell
.\.venv\Scripts\python.exe main.py
```

Default local endpoints:

```text
ZEN Operator API   127.0.0.1:8876
MA-Initiated Bridge 127.0.0.1:8877
```

Both are loopback-only by default.

Quick self-check:

```powershell
.\.venv\Scripts\python.exe main.py --self-check
```

Optional primary Worker registration reuses each Worker's existing
`/health` and `/capabilities` API:

```text
python main.py \
  --worker worker-a=http://10.0.0.10:8878 \
  --worker worker-b=http://10.0.0.20:8878
```

The addresses above are examples only; deployment does not hard-code Worker IPs.
A Worker counts toward `REMOTE_AI_AVAILABLE=YES` only when it is ONLINE and
reports `model_runtime_available=true`.

The Field Core is intentionally independent of OpenClaw. If OpenClaw is
stopped, ZEN's local backend, Safety boundary, Worker state, artifacts and MA
control infrastructure remain available.

## OpenClaw integration

The integration boundary lives in:

```text
integrations/openclaw/
docs/ZEN_OPENCLAW_INTEGRATION.md
docs/ZEN_OPENCLAW_FIRST_UI_ARCHITECTURE.md
```

The repository already exposes a narrow, versioned Operator API for the future
OpenClaw plugin:

```text
GET  /healthz
GET  /zen/v0.1/status
POST /zen/v0.1/tools/{tool_name}
```

Read-only tool contracts currently include:

```text
zen.status
zen.worker.status
zen.ma.status
zen.artifact.latest
zen.watchdog.status
zen.host.status
```

Mutation-facing OpenClaw tools remain reserved until they have a real typed
backend path.

## MA-Initiated Bridge

Protocol:

```text
ZEN/1 REQ <request_id> <command> [KEY=VALUE ...]
```

Current commands:

```text
PING
STATUS
DIMMER GROUP=<positive integer> VALUE=<0..100>
DESIGN REQUEST=<bounded identifier>
```

Current semantics:

```text
PING    -> deterministic PONG
STATUS  -> deterministic Field/Remote status
DIMMER  -> parse only, NOT_EXECUTED
DESIGN  -> parse only, NOT_IMPLEMENTED
```

No Bridge command currently performs a real MA write or calls the LLM.

## Distributed target

```text
Venue:
Selected host / hardware TBD
-> ZEN Field Node
-> OpenClaw operator UI
-> MA Bridge / Safety / Resolver / Builder / cache

Available compute:
Gateway / Field Host remains unselected pending D2.6 verification
Preferred next candidate: Primary AI Worker A / OS TO VERIFY / 16 GB / GTX 1650 4 GB
Worker A may co-host Gateway + ZEN Field Core + Worker runtime if host checks pass
Primary AI Worker B / OS TO VERIFY / 16 GB / GPU model UNKNOWN remains Worker-focused
2012 Mac mini is excluded from current Gateway / Field Host consideration
Operator Windows machine remains OpenClaw Hub-only

The two Worker hosts are the primary AI inference/compute tier. Field Core
availability must still remain independent of them for safety-critical and
deterministic local operation.
```

Home compute is optional. The required invariant is:

```text
REMOTE_AI_AVAILABLE=NO
FIELD_CORE_AVAILABLE=YES
```

## Portable core

The historical USB runtime remains supported as a headless core/runtime bundle.
It no longer packages a duplicate frontend.

Build on Windows:

```powershell
.\.venv\Scripts\python.exe scripts\build_portable.py
```

Smoke-test the packaged core:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_portable.py
```

Mutable state remains under `ZEN_HOME`; core code must not depend on a fixed
drive letter.

## Safety boundary

ZEN does not allow an LLM or OpenClaw plugin to emit arbitrary MA commands and
execute them directly.

Target path:

```text
human/OpenClaw
-> typed request
-> ZEN backend
-> validation / Safety
-> Resolver
-> deterministic Builder
-> MA transport
```

Fixture 9999 and production protections remain outside the UI layer.

## Tests

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The normal development host must run the full suite after dependency and
packaging changes.

Key architecture docs:

- `docs/ZEN_OPENCLAW_INTEGRATION.md`
- `docs/ZEN_FIELD_HOME_DISTRIBUTED_ARCHITECTURE.md`
- `docs/ZEN_MA_BRIDGE_PROTOCOL_V0_1.md`
- `docs/ZEN_LEGACY_UI_REMOVAL_001.md`
- `docs/PORTABLE_USB_RUNTIME.md`
