# MA GitHub Reuse Audit 001

Status: RESEARCH / SHADOW-ONLY / NO MA WRITE AUTHORITY
Review date: 2026-09-30

## Purpose

Survey current public GitHub work around grandMA2 and grandMA3 for components and ideas that can improve ZEN without creating a second MA programming authority.

Research follows the repository Continuous Learning Policy. Nothing in this review changes the canonical ZEN path:

Primary Lighting Designer -> artistic intent -> Resource Resolver / Compiler -> strict ShowPlan -> Preview -> Human Approval -> deterministic Builder -> Field Core -> MA -> native readback.

## Highest-value findings

### chienchuanw/gma2-mcp

Classification: HIGH-VALUE MA2 IMPLEMENTATION REFERENCE / POSSIBLE SELECTIVE CODE REUSE.
License: Apache-2.0.

Useful components observed:
- persistent Telnet transport;
- structured parser for List output and inline Error #NN replies;
- pure verified ExecutionResult construction;
- show-aware List Attribute introspection and friendly-name resolution;
- fixture-profile / GDTF XML resolver for strobe, iris, frost, prism and similar functions;
- command builders separated from transport;
- previewable command-sequence composition.

ZEN relevance:
- compare its response/error parser with ZEN readback;
- study its attribute resolver for current-Show capability normalization;
- study fixture-profile function resolution for future Beam/Gobo/Prism/Frost/Strobe typed resources;
- reuse only bounded pure logic after tests and license review.

Reject as authority:
- raw MCP-to-Telnet control;
- arbitrary raw command tools;
- any model path bypassing ZEN Compiler / Builder / Preview / Approval.

### thisis-romar/ma2-onPC-MCP / GrandPA2-Buddy

Classification: ARCHITECTURE + TEST-CORPUS REFERENCE.
License: Business Source License 1.1 until its change date; do not copy source without explicit license review.

Interesting architecture:
- broad MA2 tool surface;
- large test corpus;
- SAFE_READ / SAFE_WRITE / DESTRUCTIVE risk tiers;
- permission intersection;
- RAG over MA2 help material;
- invocation telemetry and skill-improvement loop.

Its embedded autonomous agent/orchestrator overlaps ZEN Strong Primary Brain and is not an adoption target.

### DD-cLD/The3-MCP

Classification: HIGH-VALUE MA3 KNOWLEDGE + SAFETY REFERENCE / SELECTIVE APACHE CODE STUDY.
Code: Apache-2.0. Documentation/corpus: CC BY 4.0.
Upstream claims live attestation against grandMA3 onPC 2.4.2.2.

Useful areas:
- hundreds of version-stamped MA3 concepts;
- bounded MCP server;
- command tiering and exact confirm gates;
- readback after mutation batches;
- showfile snapshot/checkpoint discipline;
- real song build through timecode;
- MAtricks / Phaser / import evidence;
- GDTF/MVR patch-pipeline research;
- runtime object-address resolution rather than hardcoded version-dependent paths.

Strongly compatible principle:
language is the model's job; syntax is deterministic code; schema is the stable joint; console writes require validation and readback.

Do not import its fixed role vocabulary as universal artistic truth.

### Pahegi/ma3-mcp

Classification: EXPERIMENTAL TRANSPORT REFERENCE.
The project identifies itself as prototype / proof of concept.

Interesting bridge:
Python MCP outside MA3 -> file IPC -> Lua plugin inside MA3.

Useful as a transport pattern only, not a production authority.

### open-stage/python-gdtf

Classification: HIGH-VALUE LIBRARY CANDIDATE.
License: MIT.

Direct ZEN value:
- fixture physical/channel/function data;
- DMX modes and channels;
- geometry tree;
- standardized attribute definitions;
- future capability-profile normalization.

Strong candidate for Spatial vNext, Show Import Normalization and Fixture Capability work.

### open-stage/python-mvr

Classification: HIGH-VALUE LIBRARY CANDIDATE.
License: MIT.

Direct ZEN value:
- fixture placement and patch data;
- layers/classes;
- embedded GDTF references;
- scene geometry normalization;
- future MVR import/export adapters.

Prefer evaluating this before inventing a custom MVR parser.

### mvrdevelopment/spec + libMVRgdtf

Classification: CANONICAL STANDARD REFERENCE + NATIVE LIBRARY OPTION.

Use the spec as format authority. libMVRgdtf is a possible later native/C++ option; Python is lower-friction for current Mini-side analysis.

### smartoo-dev grandMA3 Phaser / Preset family

Repositories reviewed:
- grandma3-position-phasers
- grandma3-dimmer-phasers
- grandma3-color-phasers
- grandma3-preset-banks

Classification: HIGH-VALUE MOVEMENT / EFFECT GRAMMAR REFERENCE.
Reviewed repositories report MIT licensing.

Important ideas:
- relative Position movement separated from absolute focus;
- Relative Pan/Tilt makes motion portable around the current baseline;
- Phaser shape and per-fixture phase distribution are separate concerns;
- concrete shape semantics such as circle, figure-8, sweeps, diagonal, square, ballyhoo and nod;
- Width, Transition, Accel, Decel, Speed and Phase are independent dimensions;
- Universal / Global / Selective behavior must be treated explicitly.

This directly informs ZEN MOVEMENT_TEXTURE_ACTION_GRAMMAR, but the canned shapes are examples, not a mandatory artistic checklist.

### smartoo-dev/grandma2-preset-banks

Classification: MA2 EFFECT-GRAMMAR REFERENCE.

Useful because it documents the structural split:
- MA2 Effects are Effect-pool objects built from lines/forms/ranges/phase/width/rate.
- MA3 dynamic behavior is Phaser data in Presets/Cues.

This supports one artistic movement vocabulary with separate MA2 and MA3 native adapters.

### Naostage/grandma2-autozoom-plugin

Classification: SPATIAL / TRACKING REFERENCE.

Interesting mechanisms:
- MA2 XYZ;
- Stage Markers;
- PSN tracking;
- dynamic Zoom/Iris based on fixture-to-target geometry;
- physical Pan/Tilt/Zoom metadata quality.

Potential future relevance to performer tracking, semantic target following and distance-aware beam sizing.

### Chataigne MA2 / MA3 modules

Repositories:
- DJFPaul/grandMA2-Chataigne-Module
- yastefan/grandMA3-Chataigne-Module

Classification: OPERATOR / PROTOCOL REFERENCE.

Useful evidence:
- MA2 Web Remote feedback/control;
- MA3 OSC feedback/control;
- executor fader/button states;
- Blind/Freeze/Preview surfaces;
- rate limiting;
- BPM / SpeedMaster synchronization;
- beat-synchronized executor behavior.

Useful for operator integration, not programming authority.

### Bitfocus Companion MA2 / MA3 modules

Classification: PROTOCOL + OPERATOR SURFACE REFERENCE.

Worth mining for connection lifecycle, feedback state, executor/page semantics, rate limiting and version compatibility.

### Timecode / marker tools

Examples reviewed:
- Tozsers/ma3-marker-import
- damianvandoom/reapma3
- kinglevel/TimecodeBPMConvertMA3
- LeoKuenne/GrandMA2-ExportTimecode
- oje-studio/ma2-tc-cut

Classification: TIMELINE ADAPTER REFERENCES.

Especially useful lesson from ma3-marker-import: reject SMPTE input when frame rate is unknown rather than guessing. This aligns with ZEN fail-closed timing and Canonical Timeline / Musical Clock work.

### MA3 TypeScript plugin ecosystem

Repositories:
- ma3-pro-plugins/grandma3-ts-types
- ma3-pro-plugins/ma3-ts-plugin-template
- ma3-pro-plugins/ma3-pro-plugins-lib

Classification: FUTURE MA3 DEVELOPER TOOLING REFERENCE.

Useful ideas:
- typed Object API / Object-Free API;
- TypeScript-to-Lua plugin development;
- build/package workflow;
- error handling;
- coroutine mutex;
- MA variable wrappers;
- show-scoped singleton patterns.

Caution: reviewed type definitions explicitly identify themselves as open alpha and include older MA3 version mappings. Version verification is mandatory.

### Layout / Selection Grid tools

Examples:
- gabe927/gma3-subfixture-layout
- MoBrot/grandMA3-LayoutToSelectionGrid

Classification: SPATIAL SELECTION REFERENCE.

Potential value:
- converting physical/layout relationships into Selection Grid structure;
- subfixture handling;
- geometry-aware ordering for MAtricks/Phaser distribution.

Modern MA3 may supersede portions of older plugins, so treat them mainly as algorithm references.

## Immediate ZEN research order

Tier A:
1. chienchuanw/gma2-mcp response parser, introspection and profile resolver.
2. DD-cLD/The3-MCP knowledge/safety/readback and MAtricks/Phaser evidence.
3. open-stage/python-gdtf.
4. open-stage/python-mvr.
5. smartoo Phaser family to derive a cross-MA Movement model.

Tier B:
- Chataigne and Companion modules;
- Timecode marker/cut/convert tools;
- MA3 TypeScript plugin tooling;
- Stage Marker / PSN / AutoZoom.

Tier C:
- external autonomous agent cores;
- generic raw command MCP authority;
- fixed fixture-role artistic systems;
- old plugins superseded by native MA features.

## Cross-MA opportunity

A promising shared artistic MovementIntent can sit above separate console adapters:

MovementIntent:
- shape;
- axes;
- amplitude;
- rate or musical rate;
- phase distribution;
- transition character;
- acceleration / deceleration;
- symmetry / direction;
- baseline semantic Position target;
- entry behavior;
- exit / return behavior.

MA2 adapter:
Effect lines / Form / Low / High / Phase / Width / Rate / verified native resources.

MA3 adapter:
Phaser Steps / Absolute-Relative layers / Width / Transition / Accel / Decel / Speed / Phase / MAtricks.

This would let one Primary Lighting Designer think in one artistic language without pretending MA2 and MA3 implement movement the same way.

This is research direction only. No schema implementation or MA write is authorized by this audit.

## Promotion boundary

Before any external behavior becomes production ZEN behavior:
1. pin upstream version/commit;
2. classify license and provenance;
3. compare with current ZEN implementation;
4. add bounded offline tests;
5. prove on test Show/onPC;
6. preserve Preview + explicit approval;
7. require native readback;
8. record version-specific evidence;
9. never grant an external project independent MA programming authority.
