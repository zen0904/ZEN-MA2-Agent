# ZEN Design Mode

## Status

Default design path for home/offline show creation.

This document supersedes the old assumption that every design run should use
the full multi-role pipeline. The multi-agent runtime remains available as an
explicit research/deep-review tool, but it is not the default product path.

## Primary brain principle

ZEN's ordinary intelligence path is a **Strong Primary Brain**, not a permanent
committee of Agents.

The primary Lighting Designer should receive high-quality verified context across
music, current Show resources, fixture topology/capability, stage/spatial state,
Reference Lighting, accepted design history, operator workflow, and neighboring
Cue context. It owns the coherent artistic reasoning for the whole design.

Specialized Agents/workers remain available for work that benefits from
independent specialization: coding, research, spatial bootstrap, deep review,
regression/evidence comparison, audio/video/vision extraction, and other bounded
tasks. They return evidence or implementation results to the primary brain; they
do not become a default Researcher -> Designer -> Critic -> Finalizer relay.

Mature external projects should be adopted as infrastructure, workers, or tools
where they are stronger than custom generic plumbing. They may replace transport,
parsing, telemetry, protocol, memory/indexing, provider-routing, or worker
infrastructure after parity verification. They do **not** replace ZEN product
authority, the artistic contract, Compiler/Builder/Safety/Preview/Approval, or
native MA2 readback.

Short form: Strong Primary Brain + Mature Agent/Tool Infrastructure + Specialized
Workers when valuable + Deterministic MA Execution.

## Interactive primary brain and autonomous runtime

The Strong Primary Brain is a role, not a requirement that ZEN must always
delegate design to a separate API Agent.

When the owner is actively working with ChatGPT on ZEN, ChatGPT may directly
occupy the Primary Lighting Designer role: it may reason across the song,
current Show, rig/spatial state, Reference Lighting, accepted design history,
operator feedback, and neighboring Cue context, then produce the artistic
intent consumed by the ZEN Compiler. In this mode, ChatGPT is not merely
teaching or supervising another Designer Agent; it is participating in the
design itself.

For unattended/offline runtime, the same role may be filled by one strong
provider model through the same bounded artistic contract and verified context.
That runtime model is an autonomous substitute for the interactive Primary
Brain, not a second competing brain and not a permanent multi-agent committee.

### Interactive Lead Designer + Auxiliary API Designer

When the owner is actively working with ChatGPT, the artistic hierarchy is
explicit:

```text
Human Owner
    ↓
ChatGPT = Lead / Primary Lighting Designer
    ↕
optional API Designer = auxiliary co-designer
    ↓
one unified artistic plan
```

The auxiliary API Designer may help with alternatives, critique, research
interpretation, section ideas, mechanism suggestions, and structured draft
generation. It does not own the final artistic direction, does not replace the
Lead Designer, and does not form a co-equal two-brain voting system.

API availability is never a prerequisite for interactive design. If the API
provider is unavailable, out of quota, rate-limited, or intentionally disabled,
ChatGPT continues the complete design process from the same verified context and
tool-capability layer. This is a graceful quality/throughput degradation, not a
product failure and not a reason to block programming.

Short form:

```text
CHATGPT_LEAD_DESIGNER = REQUIRED_IN_INTERACTIVE_MODE
API_AUXILIARY_DESIGNER = OPTIONAL
API_FAILURE_BLOCKS_ARTISTIC_WORK = NO
FINAL_ARTISTIC_INTEGRATION = CHATGPT_LEAD
```

The auxiliary model may never gain raw MA execution authority merely because it
participates in design. Its output remains evidence/advice/draft intent until
the Lead Designer integrates it into the single artistic plan consumed by the
normal ZEN Compiler path.

Specialized workers may be invoked by the Primary Brain for coding, research,
audio/video/vision evidence, structural code intelligence, critique, or other
bounded work. Their outputs return to the Primary Brain as evidence,
implementation results, or review. They do not own the whole-song artistic
decision unless the owner explicitly chooses a deep/research workflow.

This distinction does not broaden execution authority. Whether the artistic
intent originates from interactive ChatGPT or an autonomous provider model, it
must still pass through the same verified-resource boundary, ZEN Compiler,
strict typed ShowPlan, Preview, explicit Approval, deterministic Builder, and
native MA2 readback. The Primary Brain never becomes a raw MA command channel.

## Optional Visual Director artistic brief

ZEN may optionally place a provider-independent **Visual Director** upstream of
the Primary Lighting Designer. Gemini is the current preferred candidate because
of its visual/art-direction strengths, but the architecture must not depend on a
provider name.

The Visual Director produces a whole-song artistic brief: visual thesis,
scene/world arc, meaningful Visual Events, relationships between those events,
and deliberate withholding. It may suggest lighting mechanisms artistically,
but it must not receive or invent implementation-specific Group, Fixture,
Preset, Effect, Sequence, Executor, Pan/Tilt or MA command truth.

A Visual Event is not automatically a Cue. The Primary Lighting Designer remains
the only role that sees both the artistic brief and verified Show/Spatial/Resource
Map context and therefore owns resource-aware mechanism realization. Compiler,
Resolver and Builder remain non-artistic deterministic authority.

Exact timing is separate: the Visual Director may name a semantic landmark such
as `SECOND_CHORUS_FIRST_HIT`, but authoritative `start_seconds` must come from
audio/timeline/operator evidence. Unbound events remain unbound rather than
receiving invented seconds.

This optional pre-analysis does not change the default lean path, does not
restore a permanent multi-agent committee, and does not authorize a new schema
or production implementation by itself. Validate the brief on representative
songs before promoting it into a maintained machine contract.

See `docs/VISUAL_DIRECTOR_ARTISTIC_BRIEF_001.md`.

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
Test Show has real-machine content verification for exact Group 1 / Preset
`2.13 ZEN_POSITION_CAL_P13`; that binding remains executable only while current
Show identity, exact Group membership, Preset identity/type/label, and retained
evidence all still match. See `docs/POSITION_APPLICATION_EVIDENCE_POC_001.md`.

The separate Raw Position Cue proof establishes that explicit Pan/Tilt
programmer values can reach native CueData, but that transport proof alone does
not create a Group/Position Preset binding. The existing-Cue dynamic route may
reuse the separately verified calibration baseline for bounded relative
Position patterns while preserving the same fail-closed identity checks. It
does not infer physical aim, XYZ sign mapping, high/low, or performer zones.