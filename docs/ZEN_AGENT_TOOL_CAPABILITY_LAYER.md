# ZEN Agent Tool Capability Layer

Status: ACTIVE CATALOG / DIRECT API TOOL BROKER NOT YET ENABLED
Date: 2026-09-30

## Purpose

Give interactive ChatGPT and API-hosted ZEN brains one shared description of
available analysis/research/show-input capabilities without accidentally granting
raw execution authority.

Canonical registry:

`data/zen_agent_tool_capabilities.json`

Model-facing loader:

`zen_ma2_agent/tool_capabilities.py`

## Current behavior

Interactive ChatGPT can use connected tools and the Mini through ZEN OPS.

The ordinary Lean API Designer is intentionally different: its current provider
adapter is a zero-tool completion boundary. The model receives the compact tool
catalog for awareness, but `lean_api_designer_direct=false` means it cannot
claim or perform a direct invocation.

Both ordinary compact Design Mode and the older autonomous Designer context now
receive the same tool-capability catalog.

This makes statements such as these possible:

- GDTF parsing is available to the ZEN runtime.
- MVR parsing is available to the ZEN runtime.
- audio/video analysis capability exists.
- MA2/MA3 implementation references are locally available.
- a runtime adapter/broker must acquire the evidence before the model may use
  its result as fact.

It does NOT mean the provider model owns shell, MCP, Telnet, Lua, or console
tools.

## Required authority boundary

```text
Primary Brain / API Designer
        |
        | semantic need for evidence
        v
ZEN Tool Broker / deterministic preflight
        |
        | allowlisted adapter
        v
tool result + provenance
        |
        v
Designer context / same design session

MA write path remains separate:

Artistic Intent
 -> Resource Resolver / Compiler
 -> Preview
 -> Human Approval
 -> deterministic Builder
 -> Field Core
 -> MA
 -> native readback
```

The Tool Broker must never become an alternate MA programming authority.

## Capability classes

### Direct runtime candidates

Suitable for future bounded broker adapters:

- GDTF parsing via pygdtf
- MVR parsing via pymvr
- audio analysis via Essentia
- video scene segmentation via PySceneDetect
- document conversion via MarkItDown / Docling
- code intelligence via Codebase Memory
- bounded web extraction/research
- REAPER inspection when running on an actual REAPER host

### Reference-only

These inform implementation or review but are not executable model tools:

- external MA2 MCP implementations
- The3-MCP corpus/code reference
- MA2/MA3 Phaser and preset-bank repositories
- Chataigne / Companion protocol references
- timecode adapter repositories
- MA3 TypeScript plugin tooling
- Stage Marker / PSN / AutoZoom references

Reference-only repositories never gain MA authority merely because they are
cloned on the Mini.

## Direct API tool calling future gate

Before the Lean API Designer can truly call tools:

1. add an allowlisted semantic Tool Broker;
2. give every adapter a typed input/output contract;
3. classify each tool READ_ONLY / ANALYSIS / MUTATING;
4. reject raw shell/MCP/Telnet/Lua passthrough;
5. attach provenance and current-Show identity where relevant;
6. bound output size and execution time;
7. preserve FREE_FIRST/provider cost rules;
8. keep MA mutation out of the broker;
9. update Design Mode's one-call/session contract explicitly rather than
   silently adding hidden model turns;
10. add offline and live acceptance tests.

Until that gate is closed, API Designers know what the ZEN runtime can provide
but only consume tool results that the runtime has already supplied as context.
