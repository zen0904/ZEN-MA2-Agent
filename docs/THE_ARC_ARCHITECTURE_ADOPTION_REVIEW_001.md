# THE ARC Architecture Adoption Review 001

Status: **ARCHITECTURE REVIEW COMPLETE / NO CORE REFACTOR AUTHORIZED**

Reviewed upstream: jasontzeng123/the-arc
Upstream main SHA: 264550c29d8167d1e55e9ddfa1f44a1d50297e41
Review date: 2026-09-30

## Purpose

THE ARC is useful to ZEN as an architecture reference for deterministic audiovisual timing, not as a runtime dependency and not as an MA2 programming authority.

The useful idea is:

    shared musical / semantic timeline
      -> subsystem-specific interpretation
      -> deterministic resolved state
      -> reproducible output

ZEN must preserve its existing authority boundary:

    Artistic Intent
      -> Resource Resolver
      -> ZEN Compiler
      -> strict typed ShowPlan
      -> Preview
      -> Human Approval
      -> deterministic Builder
      -> Field Core
      -> MA2
      -> native readback / verification

No THE ARC renderer, WebGL scene, Playwright renderer, browser runtime, or generated film code belongs in the MA2 write path.

## Upstream evidence that is worth learning from

THE ARC exposes several clean architectural ideas:

- app/src/timeline.ts owns a simple canonical edit timeline.
- app/src/engine/audio.ts provides beat/downbeat arrays plus beatAt(t), timeOfBeat(i), barAt(t), and nearest-beat lookup.
- app/src/engine/scene.ts gives scenes a consistent frame context with absolute time, local scene time, beat/bar position, phases, and audio features.
- app/src/engine/engine.ts resolves active timeline entries deterministically at arbitrary song time.
- music/score.py writes shared timing/event data to data/audio.json; picture consumes the same data instead of separately guessing timing.
- Upstream explicitly treats deterministic frame output and shared musical event timing as core design properties.

The architecture is attractive because one semantic timing source feeds multiple consumers without forcing those consumers to share rendering code.

## ZEN evidence and gap classification

| Capability | ZEN state | Evidence / interpretation |
|---|---|---|
| Canonical Show Timeline | **PARTIAL** | song_analysis/schema.py has timed sections and events; production docs already refer to shared timeline concepts, but there is no single formal canonical show-event timeline abstraction used across execution modes. |
| Section Model | **EXISTS** | Song analysis normalizes section id/name/role/start/end/energy/density/accent and validates ordering/overlap. |
| Musical Events | **PARTIAL** | Song analysis supports absolute-time ACCENT, BREAK, and HIT; vocabulary and musical-position representation remain narrow. |
| Musical Clock | **MISSING AS FORMAL ABSTRACTION** | ZEN has absolute seconds and section timing, but no equivalent formal beatAt/timeOfBeat/barAt clock object that can survive tempo changes and arrangement edits. |
| Choreography Events | **PARTIAL / REFERENCE-LEVEL** | Reference cases reason about choreography-specific visual responses, but there is no canonical choreography-event runtime model shared with song timing. |
| Narrative Events | **MISSING / WEAK** | Narrative intent can appear in briefs/notes, but there is no typed canonical narrative-event layer. |
| Scene World | **PARTIAL / DESIGN-KNOWLEDGE** | Lighting reference analysis clearly distinguishes sustained Base Scene / Scene World behavior, but the ordinary runtime does not yet expose a first-class Scene World state model. |
| Event Layer | **PARTIAL / DESIGN-KNOWLEDGE** | Lighting Reference Case 001 explicitly separates short event layers from sustained scene identity. It is not yet a general runtime resolver abstraction. |
| Scene + Event Resolver | **MISSING AS FORMAL SHARED RESOLVER** | ZEN can compile artistic cue intent to typed ShowPlan, but there is no formal resolver that combines persistent Scene World plus transient Event Layer into one resolved semantic lighting state before compilation. |
| Free Cue Model | **PARTIAL** | Operator/product direction preserves busking/manual operation and reference analysis discusses reusable short actions, but there is no canonical typed Free Cue model that cleanly spans Manual/Trigger/Timecode. |
| Execution Strategy | **PARTIAL** | Production docs explicitly recognize Timecode / Trigger / Busking, but execution strategy is not yet a clean independent layer downstream of one canonical event timeline. |
| Timecode / Trigger / Manual mapping | **PARTIAL** | Product workflow acknowledges all three modes. The semantic event meaning is not yet formally separated from how that event is fired. |
| Spatial Intent | **EXISTS / EXPANDING** | Spatial vNext and position_target already establish semantic spatial intent upstream of raw PAN/TILT. |
| Deterministic Programming Plan | **EXISTS** | Artistic plan compiles into strict typed ShowPlan; Builder remains the deterministic execution boundary. |
| Preview / Approval / Verification | **EXISTS** | Existing product contract already requires preview, explicit human approval and native verification before writes. |

## KEEP

Adopt these ideas directly at the architecture level:

1. **One canonical shared semantic timeline.**
   Musical, choreography, narrative and lighting events should refer to one timeline identity instead of carrying unrelated timing guesses.

2. **Shared semantic event references.**
   A section/event should have stable identity so Lighting, Video, Laser or future adapters can refer to the same moment without sharing implementation code.

3. **Scene World and Event Layer separation.**
   Persistent section identity and transient punctuation must stay separable.

4. **Deterministic state resolution.**
   Given the same verified inputs and timeline position, ZEN should resolve the same semantic state before the deterministic Builder stage.

5. **Reproducibility.**
   Timing analysis and execution planning should be inspectable and replayable from stored semantic artifacts.

6. **One timing source feeding multiple subsystems.**
   Audio/song analysis should create shared timing evidence instead of each downstream adapter independently re-deriving beat/event positions.

## ADAPT

THE ARC assumptions must be generalized before they fit live production.

### 1. Musical Clock

Do not copy the constant-120-BPM assumption.

ZEN Musical Clock should support:

- absolute seconds;
- beat and fractional beat;
- bar and fractional bar;
- tempo segments / tempo changes;
- rubato or uncertain tempo;
- arrangement cuts;
- repeated sections;
- manual anchors;
- optional absent musical grid;
- provenance/confidence.

The conversion relationship must be explicit:

    musical position <-> absolute timeline time

but either side may be partial when evidence is incomplete.

### 2. Canonical Event Timeline

A future canonical event should be semantic, for example:

    event id
    event type
    section id
    absolute time or musical position
    duration/window
    strength
    provenance/confidence
    choreography/narrative references
    execution eligibility

It must not contain raw MA commands.

### 3. Scene + Event resolution

Adapt THE ARC's deterministic per-time state concept into a lighting-semantic resolver:

    Base Scene / Scene World
      + active Event Layer(s)
      + spatial intent
      + resource availability
      -> Resolved Lighting State
      -> typed artistic / ShowPlan compilation

This resolver must not bypass the existing Resource Resolver, safety validation, Preview/Approval, or Builder.

### 4. Execution strategy remains separate

The same semantic event may later execute through:

- TIMECODE
- TRIGGER
- MANUAL / BUSKING

Therefore:

    Timecode != Timeline
    Trigger != Event meaning
    Manual != absence of semantic structure

A semantic timeline describes what the moment means. Execution strategy describes how the operator/system fires it.

### 5. Free Cue remains valid in all modes

Free Cue must not be treated as a Timecode exception.

A Free Cue can be available:

- during Timecode;
- during Trigger operation;
- during Manual/Busking;
- across multiple songs when semantically reusable;
- song-specific when context requires it.

The canonical timeline may describe an opportunity window, section, safety constraint, or context for a Free Cue without forcing a fixed second.

## REJECT

Do not adopt these as ZEN Core:

- three.js/WebGL renderer;
- browser scene runtime;
- headless Chrome/Playwright render pipeline;
- frame-by-frame video renderer;
- THE ARC scene modules;
- code-generated film runtime;
- assumption that all state is a pure audiovisual function of one fixed offline timeline;
- assumption that BPM is constant;
- assumption that every important event should be quantized to a beat;
- any path where upstream timing code gains MA2 command authority.

These are implementation details of a deterministic film renderer, not reusable MA programming infrastructure.

## DEFER

Do not start these from this review:

- full audiovisual renderer;
- complete previs renderer;
- unified Lighting/Video/Laser renderer;
- browser-based show engine;
- full Production Model;
- complete Spatial UI;
- whole-show Position rewrite.

They remain separate future decisions after Spatial vNext proves the shared-world boundary.

## Proposed ZEN sequence

This review does **not** authorize a broad refactor.

The safe order is:

1. finish the current Spatial vNext acceptance gate when the Field Core runtime is available;
2. keep the current verified MA2 deterministic core unchanged;
3. define a small Musical Clock artifact;
4. define a canonical semantic Event Timeline artifact using current Song Analysis as migration input;
5. define Scene World + Event Layer as semantic design state, not MA objects;
6. define a deterministic Resolved Lighting State;
7. map resolved semantic events to existing ShowPlan / Compiler boundaries;
8. add execution strategy mapping for Timecode / Trigger / Manual;
9. preserve Free Cue as a parallel operator capability in every execution mode;
10. validate with one bounded real-song case before generalizing.

## Current decision

    THE ARC = ARCHITECTURE REFERENCE
    dependency = NO
    runtime authority = NONE
    MA2 authority = NONE
    shared timeline concepts = KEEP
    Musical Clock = ADAPT
    Scene/Event deterministic resolver = ADAPT
    WebGL/browser renderer = REJECT
    full AV renderer = DEFER
    current verified MA2 core = PRESERVE

No MA2 writes, operator workflow changes, or production object changes are authorized by this review.
