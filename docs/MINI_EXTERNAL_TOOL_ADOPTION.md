# Mini External Tool Adoption and Replacement Track

Status: **OWNER-APPROVED / REUSE-FIRST / NON-BLOCKING**

Owner direction: 2026-09-29

## Purpose

The Mini and ZEN ecosystem should prefer mature existing open-source tools over
reimplementing generic infrastructure. New external tools are not merely
references: where practical they should be integrated into the Mini tool fabric,
and overlapping ZEN/OpenClaw/custom infrastructure should be removed or reduced
after replacement behavior is verified.

This track is intentionally non-blocking for the current M4 MA2 acceptance gate.
It must not silently change the stable operator workflow, bypass ZEN Builder/
Preview/Approval/readback, or grant external tools MA2 authority.

## Adoption rule

For every candidate, classify it as one or more of:

- `REPLACE` — verified external component may delete/simplify an equivalent
  custom implementation.
- `INTEGRATE` — keep the external component as an active shared service/tool.
- `ON_DEMAND` — install/prepare it, but start only when a task needs it.
- `REFERENCE` — retain as read-only implementation/knowledge source; do not
  grant runtime authority.

Do not keep two primary implementations merely because both exist. Prefer one
primary component plus a compatibility shim where required.

## Current owner-approved adoption set

### Operations / infrastructure

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| Glances | Mini host telemetry, Web/API, MCP system status | INTEGRATE |
| restic | Mini state/config/artifact backup | INTEGRATE |
| Docker MCP Gateway | Central MCP lifecycle, isolation, tool profiles, secrets, logging | REPLACE + INTEGRATE |
| Supergateway | stdio/SSE/Streamable-HTTP compatibility bridge | INTEGRATE as compatibility shim |
| Codebase Memory MCP | Structural code intelligence | INTEGRATE (already adopted) |

### Model / coding-agent fabric

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| LiteLLM | Provider transport, normalized APIs, fallback/routing primitives, budget/spend/telemetry | REPLACE + INTEGRATE |
| Agent Client Protocol (ACP) | Common control protocol for coding agents | REPLACE + INTEGRATE |
| codex-acp | Codex CLI ACP adapter | INTEGRATE |
| Gemini CLI ACP mode | Gemini coding-agent control | INTEGRATE |

ZEN must retain its own thin policy layer for role eligibility, FREE/LOCAL/PAID
policy, evidence validation, provider-independent artistic contracts, and MA2
authority boundaries. Generic provider HTTP, retries/fallback primitives,
telemetry, and client-specific coding-agent glue are replacement candidates.

### Knowledge / research ingestion

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| Crawl4AI | Web discovery/crawl -> LLM-ready Markdown, MCP | ON_DEMAND + INTEGRATE |
| Microsoft MarkItDown | Fast lightweight document-to-Markdown conversion | INTEGRATE |
| Docling / Docling MCP | Rich document parsing, layout/table/image/OCR extraction | ON_DEMAND + INTEGRATE |

MarkItDown remains the fast path; Docling is the richer path for manuals,
tables, figures, scanned/complex PDFs and structured extraction.

### Show-control / lighting protocol

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| MIDIMonster | Art-Net/sACN/OSC/MIDI/RTP-MIDI/MQTT translation/diagnostics | INTEGRATE |
| Open Lighting Architecture (OLA) | DMX-over-IP abstraction, protocol gateway, RDM-related capability | ON_DEMAND + INTEGRATE |
| rtpmidid | AppleMIDI/RTP-MIDI daemon | INTEGRATE |
| libltc + ltc-tools | SMPTE LTC encode/decode, LTC/MTC utilities, trigger/timeline evidence | INTEGRATE |
| Chataigne | High-level show-control routing/state/timeline/dashboard experiments | ON_DEMAND |
| ossia score | Interactive show sequencing/research platform | ON_DEMAND |
| grandMA2 Hub | Art-Net/Telnet/timecode/3D implementation reference | REFERENCE |
| chienchuanw/gma2-plugins | grandMA2 3.9.60 Lua/plugin reference | REFERENCE |
| GrandMA2 API/Lua documentation repos | MA2 Lua/API research corpus | REFERENCE |

No third-party show-control tool becomes a second ZEN MA2 programming authority.
ZEN deterministic Builder/Preview/Approval/native readback stays authoritative.

### Media / lighting-reference analysis

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| Essentia | Music information retrieval: onset/rhythm/tonal/spectral evidence | ON_DEMAND + INTEGRATE |
| PySceneDetect | Shot/transition boundaries and representative frames | ON_DEMAND + INTEGRATE |

These tools provide evidence only. They must not promote simplistic rules such
as `chorus = chase` or confuse camera cuts with lighting cues.

### Audio / REAPER / AoIP

| Tool | Intended role | Initial classification |
| --- | --- | --- |
| danishaft/reaper-mcp | Typed/safe REAPER control with preflight, undo and file policy | INTEGRATE on REAPER host |
| dschuler36/reaper-mcp-server | Read-only RPP/project/FX analysis | INTEGRATE on REAPER host |
| Open Sound Meter | Measurement engine with remote data/API opportunities | INTEGRATE on measurement host |
| AES67 Stream Monitor | AES67/RAVENNA/ST2110-30 monitoring; Dante AES67 interoperability | ON_DEMAND |

REAPER tools belong on the machine that actually runs/owns REAPER projects, not
blindly on the Mini. The Mini may consume them remotely through the MCP fabric.

## Replacement audit priorities

### 1. ZEN ProviderRouter

Current custom code handles generic concerns including OpenAI-compatible HTTP,
provider slot parsing, fallback ordering, bounded parallel fan-out, timeouts and
diagnostics.

Target direction:

```text
ZEN Provider Policy
  - role eligibility
  - FREE / LOCAL / PAID allow/deny
  - artistic contract
  - evidence and image provenance
        ↓
LiteLLM gateway
  - provider adapters
  - request transport
  - retry/fallback primitives
  - provider/model telemetry
  - budgets/spend/rate controls
        ↓
OpenAI / Gemini / OpenRouter / NVIDIA / local OpenAI-compatible endpoints
```

Do not delete the current router until parity tests prove that the thin ZEN
policy adapter preserves fail-closed behavior and current provider provenance.

### 2. Coding-agent wrappers

Prefer ACP instead of custom per-agent process/event protocols:

```text
ZEN/OpenClaw development orchestration
        ↓ ACP
  Codex via codex-acp
  Gemini CLI via --acp
  future ACP-capable agents
```

Git commit remains the ZEN project handoff authority. ACP standardizes transport
and events; it does not alter risk-tiered collaboration or grant coding agents
artistic/MA authority.

### 3. MCP transport / lifecycle

Prefer Docker MCP Gateway as the primary Mini MCP service manager where it fits:

```text
GPT / OpenClaw / Codex / Gemini / other clients
                 ↓
         Docker MCP Gateway
       profiles / auth / isolation
       lifecycle / logging / secrets
                 ↓
          MCP tool services
```

Use Supergateway only where a stdio/SSE/Streamable-HTTP compatibility bridge is
still needed. Existing ZEN typed operator facades remain until an MCP
replacement is proven at least as restrictive; standardization alone is not
sufficient reason to weaken or replace a verified safety boundary.

### 4. Document ingestion

Do not write a custom universal parser.

- MarkItDown: lightweight first pass.
- Docling: rich/complex document path.
- Crawl4AI: web path.

ZEN should own provenance/classification/promotion policy, not low-level parsing.

### 5. Protocol / media utilities

Do not reimplement LTC, RTP-MIDI, generic OSC/MIDI/Art-Net/sACN routing,
scene-cut detection, generic MIR feature extraction, or basic host telemetry
unless a ZEN-specific capability is genuinely missing.

## Removal rule

A custom ZEN/Mini component may be deleted or reduced only when:

1. the replacement is pinned/configured reproducibly;
2. required behavior is covered by parity tests;
3. security/authority is no broader than before;
4. failure/degraded mode is understood;
5. rollback is documented;
6. current operator workflow remains unchanged unless the owner separately
   approves a workflow change.

The objective is **less custom infrastructure**, not merely more dependencies.
