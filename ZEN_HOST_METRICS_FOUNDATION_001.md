# ZEN Host Metrics Foundation 001

Status: **IMPLEMENTED FOUNDATION / OPERATOR THRESHOLDS PENDING**

Date: 2026-09-18

## Purpose

Expose Field Host health data to ZEN/OpenClaw without maintaining custom
platform-specific system-monitoring code.

Reuse-first decision:

```text
psutil
-> CPU
-> RAM
-> disk
-> supported temperature sensors

ZEN
-> typed read-only projection
-> Watchdog availability state
-> OpenClaw tool
```

No custom /proc parser, macOS shell scraper, Windows WMI wrapper, or duplicate
monitoring daemon was created.

## Dependency

```text
psutil>=7.2,<8
```

The selected dependency is a mature cross-platform system/process monitoring
library. Temperature is best-effort because sensor support varies by OS.

## Implemented

New module:

```text
zen_ma2_agent/host_metrics.py
```

Read-only tool:

```text
zen.host.status
```

Schema:

```text
zen.host_status.v0.1
integrations/openclaw/contracts/zen_host_status_v0_1.schema.json
```

Current data:

- CPU percent;
- RAM percent;
- RAM available/total MB;
- disk percent;
- disk free/total MB;
- temperature C when the OS exposes supported sensors;
- bounded collection errors.

If temperature is unsupported, `temperature_c=null` and the host is not
marked degraded merely for lacking a sensor API.

CPU/RAM/disk collection failure marks the host-metrics adapter `DEGRADED`
without crashing Field Core.

## Watchdog integration

FieldHost now contributes a non-required `host_metrics` Watchdog component.

Current behavior intentionally does **not** invent fixed CPU/RAM/disk/thermal
warning thresholds. ZEN reports the real metrics and adapter health. Alert
threshold policy remains a separate operator/deployment decision.

This avoids encoding arbitrary thresholds as product truth.

## Safety

```text
zen.host.status = read only
host_metrics Watchdog component = read only
automatic MA action from host metrics = NONE
MA2 write authority = unchanged
```

## Verification artifacts

Focused tests cover:

- successful CPU/RAM/disk/temperature collection;
- unsupported temperature without false degradation;
- failed core metric collection -> DEGRADED;
- missing psutil -> DEGRADED;
- OpenClaw host-status tool projection;
- Operator API host-status provider;
- Field Watchdog inclusion.

The repository has no GitHub Actions workflow. Full repository regression
therefore remains a development-host task before production use.

## Pending

- operator-approved warning/critical thresholds;
- optional network latency/packet-loss metrics;
- exact Field Host deployment selection;
- full repository regression;
- OpenClaw visual dashboard binding.
