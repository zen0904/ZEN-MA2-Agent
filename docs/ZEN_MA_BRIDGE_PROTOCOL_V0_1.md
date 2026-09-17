# ZEN MA-Initiated Bridge Protocol v0.1

Status: **PARSER + DEDUP + TCP DISPATCHER IMPLEMENTED / MA EXECUTION PENDING**

This document records the executable protocol boundary for MA-initiated ZEN requests.

```text
MA-side caller
   ↓ TCP text line
ZEN/1 parser
   ↓ typed BridgeRequest
bounded dedup + deterministic dispatcher
   ↓
future Safety / Resolver / Builder handoff
   ↓
future MA transport
```

The current implementation does not execute MA commands, invoke the LLM, or write to a show.

## Request grammar

```text
ZEN/1 REQ <request_id> <command> [KEY=VALUE ...]
```

Implemented commands:

```text
PING
STATUS
DIMMER GROUP=<positive integer> VALUE=<0..100>
DESIGN REQUEST=<bounded identifier>
```

Examples:

```text
ZEN/1 REQ 1001 PING
ZEN/1 REQ 1002 STATUS
ZEN/1 REQ 1003 DIMMER GROUP=4 VALUE=50
ZEN/1 REQ 1004 DESIGN REQUEST=NEXT_SECTION
```

## Current execution semantics

```text
PING    → READY <id> PONG
STATUS  → READY <id> <bounded deterministic status payload>
DIMMER  → READY <id> NOT_EXECUTED
DESIGN  → READY <id> NOT_IMPLEMENTED
```

No command in this module can reach Telnet, Art-Net, DMX, a shell, or a model.

## TCP server

`zen_ma2_agent.ma_bridge.server.BridgeServer` now provides a bounded line-oriented TCP server.

Defaults:

```text
host = 127.0.0.1
port = 8877
```

Non-loopback bind is rejected unless `allow_remote=True` is explicitly supplied. That flag is not a substitute for later authentication/private-network review.

The server has:

- bounded line reads;
- per-connection timeout;
- malformed-client isolation;
- multiple sequential/concurrent client handling through a bounded threaded TCP server;
- clean stop semantics;
- no MA or LLM dependency.

## Validation

The parser fails closed for:

- unknown protocol version;
- wrong message type;
- malformed or oversized request IDs;
- unknown commands;
- control characters;
- oversized lines;
- malformed KEY=VALUE arguments;
- duplicate arguments;
- missing required arguments;
- unsupported arguments;
- invalid Group numbers;
- dimmer values outside 0..100;
- unsafe/unbounded DESIGN identifiers.

The current line limit is 1024 UTF-8 bytes.

## Request identity and idempotency

Each parsed request gets a deterministic SHA-256 `payload_hash` over canonical JSON.

Behavior:

```text
new request_id + payload
→ process once and cache response

same request_id + same payload
→ return the original cached response

same request_id + different payload
→ REQUEST_ID_CONFLICT
```

Both request and response caches are bounded.

## OpenClaw status relationship

The OpenClaw-facing Operator API can now project Bridge runtime state when the Field Node composition supplies a BridgeServer instance:

```text
running=True  → ma.bridge_state=ONLINE
running=False → ma.bridge_state=OFFLINE
no instance   → ma.bridge_state=UNKNOWN
```

This does not make OpenClaw a dependency of the Bridge.

## Test status

The earlier isolated protocol tests were **17/17 passed**.

New repository tests cover dispatcher behavior, duplicate-response identity, request-ID conflict, loopback TCP roundtrip, and non-loopback default denial. The complete repository test suite still requires the normal development host and must be rerun before production use.

## Still pending

- real Field Node service composition;
- authenticated/private remote Bridge transport if ever required;
- DIMMER typed-intent handoff to Safety/Resolver/Builder;
- DESIGN job handoff;
- Approval integration;
- all real MA writes.

`MA2_WRITES=0` remains the current requirement.
