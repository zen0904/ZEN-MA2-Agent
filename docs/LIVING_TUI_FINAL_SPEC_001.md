# ZEN / Mini Living TUI Final Spec 001

Date: 2026-09-30
Status: LIVE VERIFIED
Authority: OBSERVATION_ONLY
Supersedes: docs/LIVING_SYSTEM_VISUALIZER_FINAL_SPEC_001.md as the default attached-display frontend

## Product decision

The Mini attached-display experience is now:

- left 30%: real ChatGPT Linux GUI;
- right 70%: terminal-native ZEN Living Workspace TUI;
- fixed window ratio;
- no browser-based Living Visualizer;
- no Chrome app dependency for the observation workspace.

The Mini remains headless-first. The display is optional.

## Runtime

Right-side TUI:
- executable: `/usr/local/bin/zen-living-tui`
- implementation: Python stdlib `curses`
- terminal host: `xterm`
- terminal type: `xterm-256color`

The previous web service:
- `zen-living-visualizer.service`
- status: retired from default runtime
- live state: inactive
- code retained as historical prototype/evidence

## Window geometry

Verified live:
- ChatGPT: `0,0,576,1038`
- Living TUI: `576,0,1344,1038`
- logical display: 1920×1080 with persistent 180-degree rotation path
- ratio: 30% / 70%

The three internal views remain:
- Living
- Control
- Diagnostic

These change only TUI information hierarchy. They do not resize the two OS windows.

## Registry-driven entity model

The TUI renders normalized generic entities rather than hardcoded brands.

Canonical entity shape:
- kind
- id
- name
- raw state
- normalized state
- group
- parent
- metadata
- display hints
- state_since

Kinds are strings, not enums.

Known kinds:
- provider
- agent
- tool
- service

Unknown kinds remain visible under Other / Unassigned.

Malformed registry entries remain visible with parse-error state.

Canonical registry:
- `data/ZEN_RUNTIME_ENTITY_REGISTRY.json`

State normalization:
- `data/ZEN_TUI_STATE_MAP.json`

Optional runtime registry overlays:
- `/var/lib/zen-ops/public/entity-registry.json`
- `/var/lib/zen-ops/public/registry.json`

Future providers, agents, tools or services can be added through registry data without modifying TUI rendering code.

## Provider extensibility

Providers are data, not code.

Current seed registry includes provider entries for the currently relevant provider families, but the renderer has no brand-specific layout dependency.

Future examples:
- Gemini
- new Claude models
- OpenAI models
- Qwen variants
- Ollama
- vLLM
- Vision providers
- Audio providers
- future ZEN workers

New kinds and states remain visible even when the TUI has never seen them before.

## State priority

Priority:
1. error
2. waiting
3. active
4. unknown
5. idle

Idle provider groups collapse by default.

Items promoted out of idle become visible immediately.

Other / Unassigned is never silently dropped.

## TUI design direction

Style:
- Claude-like
- calm
- editorial
- warm-neutral
- typography-first
- low-noise
- terminal-native
- minimal box drawing
- no cyberpunk / neon / hacker styling

Motion:
- state change is the motion;
- no fake walking;
- no continuous decorative animation;
- no 60 FPS render loop;
- redraw only when visible state changes.

Keyboard:
- 1 = Living
- 2 = Control
- 3 = Diagnostic
- Enter = expand/collapse idle provider list
- q = quit TUI process

## Telemetry

Live terminal telemetry includes:
- CPU
- CPU temperature
- fan RPM
- memory
- disk
- network interface
- RX
- TX
- uptime
- load

GPU:
- usage: N/A until a trustworthy source exists
- temperature: No Sensor until a trustworthy source exists

No fabricated data.

## Performance

Measured live after migration:
- `zen-living-tui`: about 23 MB RSS, about 0.7% CPU
- `xterm`: about 16 MB RSS, about 0.1% CPU
- combined: about 39 MB RSS, about 0.8% CPU at audit time

This replaces the browser-based visualizer path.

## Safety

The TUI is observation-only.

It MUST NOT:
- approve actions;
- execute MA commands;
- write MA objects;
- become routing authority;
- become required for headless operation.

Production execution remains:
Agent -> Policy/OpenShell -> ZEN Operator -> Preview -> Human Approval -> deterministic executor -> MA Bridge.

MA2_WRITES=0
MA3_WRITES=0
