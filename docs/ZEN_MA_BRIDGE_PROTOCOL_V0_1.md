# ZEN MA-Initiated Bridge Protocol v0.1

Status: **PARSER + DEDUP FOUNDATION IMPLEMENTED / TCP SERVER + MA EXECUTION PENDING**

This document records the first executable protocol boundary for MA-initiated
ZEN requests.

```text
MA-side caller
   ↓ text line
ZEN/1 parser
   ↓ typed BridgeRequest
future dispatcher
   ↓
Safety / Resolver / Builder
   ↓
MA transport
```

The current implementation stops at the typed request / dedup boundary. It does
not execute MA commands, invoke the LLM, or write to a show.

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
PING    = parseable typed request
STATUS  = parseable typed request
DIMMER  = parse-only, no MA write
DESIGN  = parse-only, no LLM call
```

No command in this module can reach Telnet, Art-Net, DMX, a shell, or a model.

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

## Request identity

Each parsed request gets a deterministic SHA-256 `payload_hash` over canonical
JSON containing:

- protocol version;
- request ID;
- command;
- normalized arguments.

Equivalent argument ordering therefore produces the same identity.

## Dedup

`RequestDeduplicator` is bounded and defaults to 256 entries.

Behavior:

```text
new request_id + payload
→ NEW

same request_id + same payload
→ DUPLICATE

same request_id + different payload
→ REQUEST_ID_CONFLICT
```

This layer only classifies requests. It never executes them.

## Response helpers

The foundation includes bounded formatting helpers for:

```text
ZEN/1 READY <request_id> [payload]
ZEN/1 ERROR <request_id> <ERROR_CODE>
```

Actual dispatch/status response policy belongs to the later Bridge server.

## Test status

The isolated protocol tests were executed outside the development host after
creation: **17/17 passed**.

The complete repository test suite still requires the normal development host
and must be rerun before production use.

## Next Bridge slice

Still pending:

- TCP line server;
- deterministic PING/STATUS dispatcher;
- integration with ZEN Field Core status;
- request timeout policy;
- connection lifecycle;
- Bridge health state exposed to the Operator API;
- DIMMER typed-intent handoff;
- DESIGN typed job handoff;
- Safety/Approval integration;
- all real MA writes.

`MA2_WRITES=0` remains the current requirement.
