# ZEN Field Watchdog Foundation 001

Status: **IMPLEMENTED FOUNDATION / FULL REPOSITORY REGRESSION PENDING**

Date: 2026-09-18

## Purpose

Add a host-neutral, non-authoritative Watchdog layer to the ZEN Field Core
without changing the current MA write boundary or depending on OpenClaw.

The Field Node chassis remains selectable. The two Worker hosts remain the
primary AI inference tier; Worker failure must degrade AI availability without
taking down the local Field Core.

## Implemented

New runtime module:

```text
zen_ma2_agent/watchdog.py
```

It provides:

- bounded component observations;
- `ONLINE / OFFLINE / DEGRADED / UNKNOWN` state;
- required vs optional component classification;
- edge-triggered events only when a component first appears unhealthy or
  changes state;
- `INFO / WARNING / CRITICAL` severity;
- bounded recent-event queue;
- independent polling thread with clean stop semantics;
- observation exceptions isolated from the Field Core process.

Current FieldHost observations:

```text
field_core     required
ma_bridge      required
ma_connection  optional
worker:<id>    optional
```

Worker loss therefore reports a Warning/Degraded state rather than turning a
remote inference failure into a Field Core failure.

## OpenClaw / Operator API

A new read-only tool is available:

```text
zen.watchdog.status
```

Result schema:

```text
zen.watchdog_status.v0.1
```

Contract:

```text
integrations/openclaw/contracts/zen_watchdog_status_v0_1.schema.json
```

The tool has no MA write authority, no LLM authority, no shell access and no
filesystem proxy.

## Safety

No change to the execution boundary:

```text
MA2_WRITES=0
OpenClaw -> typed ZEN API only
Workers -> no direct MA authority
Watchdog -> read-only local state only
```

The watchdog thread must never be allowed to crash Field Core because one probe
or adapter fails.

## Verification

Focused isolated Watchdog logic was executed in the assistant environment:

- state transition handling: passed;
- required OFFLINE -> CRITICAL: passed;
- optional Worker OFFLINE -> WARNING/DEGRADED: passed;
- recovery event -> INFO: passed;
- bounded event queue: passed;
- polling thread start/stop: passed.

The assistant environment could not resolve github.com for a repository clone,
and this repository has no CI status attached to the implementation commit.
Therefore the complete repository suite is **not claimed as run**.

Required next verification on a powered development host:

```text
python -m unittest discover -s tests -v
python main.py --self-check
```

Then exercise `zen.watchdog.status` through the local Operator API.

## Deliberately pending

- CPU / RAM / disk / thermal host probes;
- network latency / packet-loss probes;
- active authenticated Worker health probing;
- notification transport / OpenClaw alert presentation;
- persistence/acknowledgement policy for operator alerts;
- MA-specific deeper telemetry beyond current connection state;
- any production MA write.

These are separate bounded tasks and should not be inferred as implemented by
this foundation.
