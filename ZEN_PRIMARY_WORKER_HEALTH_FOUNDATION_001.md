# ZEN Primary Worker Health Foundation 001

Status: **IMPLEMENTED FOUNDATION / REAL INFERENCE PENDING**

Date: 2026-09-18

## Purpose

Connect the two primary AI Worker hosts to the Field Node using the Worker
service contracts that already existed in the repository.

This task intentionally follows the reuse-first rule:

```text
existing Worker /health + /capabilities
+ existing httpx dependency
+ existing WorkerRegistry
+ existing Watchdog
= no new health protocol
```

## Implemented

New module:

```text
zen_ma2_agent/worker_health.py
```

It provides:

- bounded Worker endpoint configuration;
- existing `GET /health` polling;
- existing `GET /capabilities` polling;
- Worker identity validation;
- schema validation;
- timeout/failure handling;
- Registry state updates;
- background polling service;
- no MA authority;
- no shell authority;
- no new Worker protocol.

FieldHost now accepts optional Worker endpoints. With no endpoints configured,
it performs no Worker network access.

Example:

```text
python main.py \
  --worker worker-a=http://10.0.0.10:8878 \
  --worker worker-b=http://10.0.0.20:8878
```

The addresses are examples only and are not hard-coded.

## Truthful availability correction

A pre-existing false-positive condition was corrected.

Before:

```text
Worker HTTP ONLINE
-> REMOTE_AI_AVAILABLE=YES
-> router could select Worker
```

even when `model_runtime_available=false`.

Now:

```text
Worker state ONLINE
AND model_runtime_available=true
-> REMOTE_AI_AVAILABLE=YES
-> eligible for Worker routing
```

A reachable Worker without a confirmed model runtime remains visible as a
healthy host but is not advertised as usable AI inference capacity.

## Health semantics

```text
/health fails
-> Worker OFFLINE

/health succeeds
/capabilities fails
-> Worker DEGRADED

/health + /capabilities succeed
model_runtime_available=false
-> Worker ONLINE
-> REMOTE_AI_AVAILABLE remains NO

/health + /capabilities succeed
model_runtime_available=true
-> Worker ONLINE
-> eligible for routing
```

Watchdog consumes WorkerRegistry state, so no duplicate Worker monitoring path
was created.

## Security / safety boundary

Worker endpoint configuration rejects:

- non-http(s) schemes;
- embedded credentials;
- URL query strings;
- fragments;
- extra URL paths.

This foundation does not claim authenticated remote transport. Production
remote deployment still requires the separate private-network/authentication
decision already documented by the project.

Workers remain non-authoritative:

```text
Worker
-> AI result only
-> Field Node validation / Safety / Resolver / Builder
-> MA
```

No Worker has direct MA command authority.

## Verification artifacts

Added focused tests:

- online Worker + valid capability contract;
- capability failure -> DEGRADED;
- unreachable Worker -> OFFLINE;
- Worker identity mismatch -> fail closed;
- unsafe endpoint URL rejection;
- endpoint must map to a registered Worker;
- Router requires confirmed model runtime;
- FieldHost Worker endpoint registration.

The repository currently has no GitHub Actions workflow, so no CI result is
available for these commits. Full repository regression remains required on a
powered development host before production use.

## Deliberately pending

- actual model runtime serving on Worker A/B;
- authenticated/private remote transport;
- real inference job execution;
- job retry/requeue policy;
- queue depth and latency-aware routing;
- CPU/RAM/disk/thermal host metrics;
- full repository regression;
- production MA writes.

This foundation does not change the current M2 artistic acceptance gate.
