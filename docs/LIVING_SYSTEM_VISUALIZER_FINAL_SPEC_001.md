# ZEN / Mini Living System Visualizer Final Engineering Spec 001

Date: 2026-09-30
Status: APPROVED FOR PHASE-1 IMPLEMENTATION
Authority: OBSERVATION_ONLY

## 1. Product merge

This specification merges:
- Claude product/UX direction;
- Gemini visual design specification;
- current verified Mini runtime and Control Room implementation.

The product is a live AI operations workspace, not a dashboard and not a desktop pet.

Core questions the screen must answer:
1. Who is working?
2. What is the task doing now?
3. Is anything waiting, stuck or broken?
4. Is the Mini healthy?

## 2. Non-negotiable authority boundary

Visualizer is observation-only.

Execution remains:
Agent -> Policy/OpenShell -> ZEN Operator -> Preview -> Human Approval -> deterministic executor -> MA Bridge.

Visualizer MUST NOT:
- execute MA commands;
- approve tasks;
- become task routing authority;
- become required for headless operation;
- fabricate telemetry or provider activity.

Visualizer failure MUST NOT impact ZEN Ops, OpenClaw, SSH, Gateway, MA Bridge, Preview, Approval or deterministic execution.

## 3. Phase-1 rendering architecture

Chosen:
- semantic DOM + CSS for Stations, labels, Avatars and disclosure;
- SVG overlay for task paths / handoff traces / infrastructure links;
- lightweight CSS animation;
- no React dependency;
- no PixiJS / Phaser / WebGL in Phase 1.

Reason:
- current Mini is older Intel hardware;
- scene complexity is low enough for DOM/SVG;
- existing service is a single local Python HTTP server;
- no build pipeline is required;
- DOM preserves inspectability and progressive disclosure.

Escalate to Canvas/Pixi only if measured render cost becomes a real problem.

## 4. Performance budget

Target attached-display runtime:
- state poll: 1 Hz;
- idle animation: <= 2 FPS-equivalent visual changes;
- active motion: browser compositor transitions, target <= 30 FPS;
- no continuous full-canvas redraw loop;
- CPU overhead target: < 8% average attributable to Visualizer;
- memory target: < 250 MiB browser + backend delta over current baseline;
- hidden/inactive detail panels must not animate.

## 5. Mode model

### LIVING
Default attached-display mode.
- ChatGPT: 30%
- Visualizer: 70%
- full workspace visible;
- low-density telemetry;
- terminal hidden.

### CONTROL
Operator interacting with ChatGPT.
- ChatGPT: 55%
- Visualizer: 45%
- infrastructure deemphasized;
- active task/Core preserved.

### DIAGNOSTIC
Fault investigation.
- ChatGPT: 35%
- Visualizer: 65%
- future terminal/log drawer inside Visualizer;
- no automatic layout theft while user is actively typing.

Phase 1 implements deterministic mode-aware layout command and LIVING default.
Automatic typing/idle hysteresis controller is deferred until a trustworthy operator-activity signal is available.

## 6. Floor plan

Logical flow:
Think/Input -> Work/Execute -> Approval Gate -> Deploy.

Structural:
- ZEN Core near center-left;
- Browser/Research and Vision left;
- Coding/Git/OpenShell/OpenClaw middle;
- Approval Gate as structural separator;
- MA Bridge right of Gate;
- Compute/Network on upper perimeter;
- Storage/Logs on lower/right perimeter;
- Rest Lounge lower-left.

Whitespace is information. Idle state must remain visually quiet.

## 7. Entity model

Moving Avatars:
- ZEN Agent;
- ZEN Ops;
- Coding Agent;
- Research Agent;
- Git Worker;
- Vision Agent;
- OpenClaw when represented as worker.

Providers are NOT moving Avatars:
- GPT;
- Claude;
- Qwen.

Providers are fixed sockets inside the API Station and illuminate only with explicit runtime evidence.

## 8. State model

Frontend canonical states:
- IDLE
- WORKING
- WAITING
- RETRYING
- ERROR
- STUCK
- COMPLETE_TRANSIENT

Mapping rules:
- current running task -> WORKING;
- waiting_for_approval -> WAITING at Approval Gate;
- retry metadata/event -> RETRYING;
- failed/error/timeout -> ERROR unless stale/no-progress threshold marks STUCK;
- completion may show a short transient then return to IDLE.

No decorative fake work.

## 9. Task object

The current task is represented as a small capsule physically associated with its holder.

Handoff:
- holder changes;
- capsule moves or transmits toward next Station;
- brief trail fades within about 1 second;
- full history remains progressive disclosure.

Phase 1 supports one primary live task object from current ZEN Ops metadata.
Multi-task identity is deferred until runtime exposes stable task IDs for parallel work.

## 10. Approval Gate

Visual-only.

WAITING_FOR_APPROVAL:
- task/Agent stops at Gate;
- amber low-frequency breathing;
- preview summary may be displayed read-only.

APPROVED:
- Gate visual opens only after external runtime reports approval.

No button. No click-to-approve.

## 11. Visual system

Art direction:
- dark;
- premium;
- matte industrial;
- cinematic;
- calm;
- low-noise.

Base:
- floor near #0A0A0C;
- stations near #1C1C21;
- minimal borders;
- small radius / machined feel.

Semantic color budget:
- active: cyan/white;
- waiting: amber;
- error: crimson;
- stuck: desaturated ice blue;
- provider identity colors only inside API sockets and only when active.

Color indicates meaning, not decoration.

## 12. Telemetry embedding

Compute Station:
- CPU load -> lit matrix density;
- CPU temp -> subtle temperature tone;
- fan RPM -> micro-ring speed;
- RAM/Load/Uptime -> inspect layer;
- GPU slot -> explicit N/A / No Sensor when unavailable.

Network Station:
- real RX/TX -> restrained moving particles;
- Tailscale/service state -> connection indicator;
- exact values in inspect layer.

Storage:
- capacity fill level.

Global health:
- one restrained ambient health indicator.

No Grafana-like card wall.

## 13. Typography

UI labels:
- Inter/Geist-like system sans fallback;
- small uppercase Station labels.

Data:
- JetBrains Mono/Fira Code/monospace fallback.

Three textual levels maximum in normal mode.

## 14. Motion budget

- Station activation: 180-260 ms;
- panel/disclosure: cubic-bezier(0.16,1,0.3,1);
- Avatar travel: distance-based, approx 150 px/sec;
- API pulse: approx 200 ms;
- handoff trail fade: <= 1 s;
- waiting breathe: slow and calm;
- no bounce, shake, perpetual walking or decorative busy loops.

## 15. Progressive disclosure

Always visible:
- active/idle/waiting identity;
- current task holder;
- Approval state;
- error/stuck presence;
- global health;
- current mode.

On inspect:
- CPU/RAM/Disk/RX/TX exact numbers;
- fan/load/uptime;
- event stream;
- detailed provider state;
- logs/terminal/service details.

## 16. Window-layout implementation

Existing real OS windows remain separate:
- ChatGPT Linux GUI;
- Chrome app Visualizer.

Use Openbox/wmctrl layout controller.

Supported command:
zen-control-room-layout {living|control|diagnostic}

Ratios:
- living: 30/70;
- control: 55/45;
- diagnostic: 35/65.

Default session mode: living.

Visualizer is not allowed to resize OS windows itself.

## 17. Failure behavior

Visualizer backend down:
- Chrome may show unavailable state;
- ChatGPT and remote control remain usable.

Missing telemetry:
- show N/A / No Sensor;
- never fabricate.

Stale task:
- visually distinguish STUCK from ERROR.

Chrome crash:
- session/repair path may relaunch it;
- ZEN execution unaffected.

Headless:
- no Visualizer dependency.

## 18. Phase plan

### Phase 1
- new visual system;
- new floor plan;
- provider sockets;
- integrated system telemetry;
- current-task object;
- approval/error/waiting visual states;
- mode-aware layout script;
- LIVING default.

### Phase 2
- normalized richer event adapter;
- task handoff history;
- retry counters;
- stale/stuck detection;
- inspect overlays;
- diagnostic drawer.

### Phase 3
- trustworthy operator-activity detector;
- automatic CONTROL/LIVING hysteresis;
- diagnostic escalation without stealing active typing;
- richer provider latency/token metadata where source exists.

## 19. Acceptance tests

Required:
- all idle;
- real ZEN Ops task;
- Research-like task;
- Coding task;
- Git task;
- waiting-for-approval metadata;
- error state;
- provider call metadata;
- missing GPU telemetry;
- network throughput changes;
- Visualizer restart;
- Chrome relaunch;
- headless operation;
- MA2_WRITES=0;
- MA3_WRITES=0.

## 20. Current implementation authority

This spec authorizes Phase-1 UI/Control-Room implementation only.
It does not authorize any MA execution-path change.
