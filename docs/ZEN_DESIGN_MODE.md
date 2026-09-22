# ZEN Design Mode

## Status

Default design path for home/offline show creation.

This document supersedes the old assumption that every design run should use
the full multi-role pipeline. The multi-agent runtime remains available as an
explicit research/deep-review tool, but it is not the default product path.

## Product shape

ZEN has four core responsibilities:

1. **LLM Brain** — artistic reasoning and design choices.
2. **Knowledge / State** — verified Show facts, fixture capabilities, Groups,
   Presets, prior accepted designs, user feedback, and cached song/show context.
3. **ZEN Compiler / Builder** — deterministic conversion from artistic intent
   into strict internal plans and native MA2 programming.
4. **Readback / Watcher** — verify writes and compare live state with expected
   state.

The default home design loop is:

```text
Knowledge / cached context
        ↓
one primary Lighting Designer call
        ↓
artistic cue intent
        ↓
optional one delta revision when genuinely needed
        ↓
ZEN Compiler
        ↓
strict internal plan
        ↓
deterministic MA2 Builder
        ↓
readback
```

## Call budget

The default design path should normally require:

- **1 primary design call**;
- **0 or 1 delta revision call**;
- **0 model calls** for schema formatting, backend metadata, Sequence
  allocation, Executor addressing, validation, command construction, or
  readback.

Time may be traded for design quality at home. Provider calls should not be
spent on representation repairs that deterministic code can perform safely.

A second model call is justified when the artistic result itself needs
revision. It is not justified merely because a number was returned as a
string, a backend-owned field was omitted, or an internal JSON shape differs.

## Context discipline

Do not use the LLM as a database.

The model should receive the smallest useful context assembled from verified
state and cache, such as:

- song/performance summary;
- current rig and spatial summary;
- verified Group and Preset vocabulary;
- relevant capability summary;
- accepted style/design history;
- the specific cues/regions being revised.

Do not resend the complete Show dump when a compact summary or delta is enough.

## Revision

Revision is delta-first.

A request such as "Cue 4 is too full before the drop" should normally send the
model the affected cue neighborhood and relevant resources, not restart song
analysis, spatial design, rig design, research, Critic, and Finalizer.

## Compiler boundary

The provider-facing contract is intentionally small.

Provider owns artistic choices such as:

- cue structure when the calling task allows it;
- Group participation;
- intensity;
- verified Preset choice;
- fade;
- density, hierarchy, contrast, restraint, and impact.

ZEN owns operational representation such as:

- internal schema;
- cue numbering and internal IDs;
- Sequence allocation;
- Executor addressing;
- exact typed target shape;
- command syntax;
- strict validation and readback.

Song-specific constraints belong to the calling task, not the generic compiler.
For example, a bounded SHEESH six-cue experiment may require six named sections,
but `compile_artistic_cue_plan()` must not encode "six cues" as a universal
rule.

## Safety that remains

Simplifying Design Mode does **not** weaken the real safety boundary.

Keep fail-closed behavior for:

- protected Fixture 9999 and other protected objects;
- unverified Group or Preset references;
- unsupported artistic operations;
- out-of-range values;
- raw MA2/Telnet/Lua command text from providers;
- Patch, Address, Fixture identity/type mutation without an explicit verified
  path;
- write/readback mismatch.

Deterministic code must not silently substitute artistic meaning. For example,
`SET_COLOR -> CALL_PRESET`, an unknown Group -> a known Group, or dimmer
`150 -> 100` are not representation fixes.

## Multi-agent runtime

The historical Researcher / Rig Designer / Position Designer / Lighting
Designer / Critic / Finalizer pipeline is retained for:

- research experiments;
- spatial bootstrap work that explicitly needs those roles;
- difficult investigations where independent critique is deliberately chosen;
- regression/evidence comparison with historical runs.

It is **not** automatically invoked for ordinary song programming.

Do not reintroduce the full role chain merely because a primary design call
fails formatting or because a local deterministic compiler can resolve a
representation mismatch.

## Live mode

Live operation has the opposite optimization target:

```text
MA2 live state
    ↓
local deterministic watcher / diff
    ↓
only meaningful event or ambiguity
    ↓
small-context fast LLM call
```

Routine state comparison should cost zero model calls. The model is used when
human-style interpretation is useful, not as a polling loop.

## Default principle

```text
LLM provides intelligence.
Knowledge/State provides memory and reality.
Agent loop provides reasoning flow.
Compiler/Builder provides deterministic hands.
Everything else must justify its existence.
```
