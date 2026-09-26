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

The implementation in `zen_ma2_agent/designer/lean_design_mode.py` assembles
this bounded context deterministically. Its compact artifact contains only
selected song, spatial, Group, Preset, capability, and accepted-plan fields;
the stable context hash permits reuse when those authoritative inputs are
unchanged. Delta revision selects the requested Cue and its immediate
neighborhood, then retains only the referenced resources. Both the primary
design and delta revision budgets are one call at most. Context assembly is
provider-free and rejects raw MA2/Telnet/Lua transport fields rather than
turning the cache into a command channel.

## Compiler boundary

The provider-facing contract is intentionally compact but must not cripple the
artistic vocabulary.

Provider owns artistic choices such as:

- cue structure when the calling task allows it;
- Group participation;
- intensity;
- Color;
- Position and Focus;
- Beam / Gobo / Prism / Zoom / Frost intent;
- Effect / Movement / Strobe intent;
- fade;
- density, hierarchy, contrast, restraint, and impact.

Preset and Effect pool objects are implementation resources, not the artistic
ontology. ARTISTIC_CUES_V0_2 may select only verified current-Show resources
for executable actions; unsupported dimensions remain explicit rather than
being silently replaced with Dimmer or a generic Preset.

ZEN owns operational representation such as:

- internal schema;
- cue numbering and internal IDs;
- Sequence allocation;
- Executor addressing;
- exact typed target shape;
- command syntax;
- strict validation and readback.

Song-specific constraints belong to the calling task, not the generic compiler.
For example, the bounded SHEESH runner is a six-cue smoke test and may require
six named sections, but `compile_artistic_cue_plan()` must not encode "six
cues" as a universal product rule.

The active expressive-path specification is `docs/FULL_ARTISTIC_PATH_001.md`.

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

The `show.program` root may enter `LEAN_SINGLE_DESIGNER` when an injected,
provider-independent design-intelligence service is available. It receives
one bounded request and compact verified context, returns artistic JSON only,
and then hands the result to ZEN's deterministic compiler and existing
`show.builder` approval path. Without injection, broad requests remain
`NEEDS_INTELLIGENCE`; deterministic requests remain model-free.

### Portable ProviderRouter integration

FieldHost may adapt the existing portable `ProviderRouter` into the
`LEAN_SINGLE_DESIGNER` seam. Loading provider configuration performs no
network call. Normal show programming accepts only provider slots explicitly
declared `COST_CLASS=FREE` or `COST_CLASS=LOCAL` for the
`LIGHTING_DESIGNER` role. `UNKNOWN` and `PAID` slots are excluded rather than
inferred from model/provider names.

The ordinary path remains one logical Lighting Designer request. Ordered
transport fallback may occur only across eligible FREE/LOCAL slots; parallel
Designer candidate generation remains explicit deep/research mode. Deterministic
requests continue to bypass the provider entirely.

### Position Preset application is separately verified

The `position_preset` artistic action remains in the generic cue contract, but
the ordinary Designer sees a Group/Position Preset pair only after exact native
Cue-content evidence is recorded in
`zen.position_preset_application_binding.v0.1`. FixtureType POSITION capability
and Position-pool inventory alone do not establish applicability. The current
PoC is Preview-only; see `docs/POSITION_APPLICATION_EVIDENCE_POC_001.md`.

The separate Raw Position Cue PoC can prove that explicit Pan/Tilt programmer
values reach native CueData, but that transport proof does not create a
Group/Position Preset binding or expose Position to the ordinary Designer.
