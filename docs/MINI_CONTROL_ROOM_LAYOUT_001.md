# Mini Control Room Layout and Living Workspace Direction 001

Date: 2026-09-30
Owner decision: ZEN
Status: DESIGN SPECIFICATION ONLY

## Decision

When a monitor is attached, the Mini should not boot into a full-screen terminal and should not default to full-screen ChatGPT alone.

The default visible mode is **ZEN Control Room**:

```text
+---------------------------------------------------------------+
|                         |                                     |
|                         |   SYSTEM / AGENT STATUS             |
|      CHATGPT            |   ZEN Ops / MCP / OpenClaw         |
|      PRIMARY UI         |   Tailscale / SSH / RDC            |
|                         |   current task / queue              |
|      approx. 65%        |                                     |
|                         |-------------------------------------|
|                         |                                     |
|                         |   TERMINAL / RECENT ACTIVITY        |
|                         |   logs / git / service diagnostics  |
|                         |                                     |
+---------------------------------------------------------------+
                    approx. 35%
```

The exact split may adapt to resolution, but the intent is:
- ChatGPT remains the main human-facing surface;
- system state is visible without opening another app;
- a terminal/activity view is always immediately available;
- the Mini remains useful even when nobody is actively operating it.

## Why not full-screen ChatGPT

Full-screen ChatGPT hides infrastructure state.

It does not immediately show whether ZEN Ops is alive, which Agent/tool is running, whether Tailscale/SSH is healthy, current task/queue state, or failures that need attention.

ChatGPT remains the largest pane, but not the only pane.

## Why not full-screen terminal

The Mini is primarily an Agent/control-plane host, not a keyboard-first Linux workstation.

A raw terminal as the default screen over-prioritizes manual administration, is poor at showing system-wide state, and does not fit the long-term Living System Visualizer direction.

Terminal remains visible and ready, but secondary.

## Operating modes

### HEADLESS

Condition:
- no monitor attached, or display intentionally unused.

Behavior:
- all ZEN, OpenClaw, MCP, network, SSH and remote-control services continue normally;
- no remote capability may depend on the GUI session;
- GUI failure must not affect ZEN execution or remote administration.

This is the normal physical state most of the time.

### CONTROL_ROOM

Condition:
- monitor attached and active.

Default composition:
- left ~65%: ChatGPT GUI;
- right top: compact system/Agent state;
- right bottom: terminal/recent activity/logs.

This is the default visible boot/session mode until the Living System Visualizer is ready.

### DIAGNOSTIC

Purpose:
- maintenance and fault investigation.

Behavior:
- terminal/log area may temporarily expand;
- service state and network diagnostics become more prominent;
- ChatGPT remains available but does not need to dominate the screen.

### LIVING_IDLE — future

Purpose:
- visually show the AI system operating when the Mini is not being actively used.

Behavior:
- Living System Visualizer may become the primary idle display;
- user interaction or an active operator session can return immediately to CONTROL_ROOM;
- this remains observation-only.

This mode is design-only at present. Do not implement it merely because this document defines it.

## Current display baseline

Verified display:
- output: `HDMI-3`;
- resolution: 1920x1080;
- rotation: 180 degrees / `inverted`.

The display rotation is applied before the normal ChatGPT GUI session and is persistent across GUI restarts.

Layout code must be orientation-independent. The desktop should reason in logical 1920x1080 coordinates after rotation, not duplicate rotation logic in every UI component.

## Boot/session behavior

Desired startup:

```text
Boot
 -> network/system services
 -> Tailscale / SSH / ZEN Ops / OpenClaw / MCP
 -> X11 session
 -> persistent 180-degree display rotation
 -> Openbox
 -> Control Room windows
 -> ChatGPT ready
```

Remote services must start independently of the display path.

A failure in Xorg, Openbox, ChatGPT GUI, terminal UI, dashboard, or the Living Visualizer must not stop ZEN Ops, zen-mini MCP runtime availability where applicable, OpenClaw, Tailscale, SSH, department adapters, or the MA safety/Preview/Approval path.

## Window composition

### Left: ChatGPT

Purpose:
- primary operator conversation;
- project continuation;
- high-level Agent interaction;
- visual confirmation that the Mini-hosted ChatGPT runtime is alive.

Requirements:
- restore to the intended workspace after GUI restart where practical;
- avoid modal dialogs blocking unattended startup;
- remain usable at 1920x1080.

### Right top: system / Agent status

Show concise states, not a wall of numbers.

Suggested fields:
- Mini hostname / online state;
- ZEN Ops;
- zen-mini MCP;
- OpenClaw;
- Tailscale;
- Gateway SSH status;
- Remote Commander status;
- current task;
- queue depth;
- last task result;
- CPU / RAM / disk / network summary;
- current provider/model when available.

Use clear status semantics:
- ACTIVE;
- IDLE;
- WORKING;
- WAITING;
- DEGRADED;
- ERROR;
- OFFLINE.

### Right bottom: terminal / recent activity

Purpose:
- immediate inspection without taking over the whole display.

Suggested default:
- a persistent tmux terminal;
- recent ZEN Ops activity;
- service/log quick view;
- git/repo state on demand.

Do not continuously stream noisy logs by default. Show recent meaningful events and allow expansion for diagnostics.

## Existing Mini UI assets to reuse

Prefer existing infrastructure where useful:
- `zen-control-room`;
- `zenmon`;
- tmux session/window model;
- existing F10/F11/F12 control-room bindings;
- Mini ChatGPT X11 session;
- current Openbox/Xinit runtime.

Do not replace working services just to create a prettier boot screen.

## Living System Visualizer

Long-term product name:

**ZEN / Mini Living System Visualizer**

Purpose:
- make the AI/control system legible as a living workspace;
- show real runtime activity without reading raw logs;
- create an intuitive visual model of Agent/tool handoffs.

### Observation-only invariant

The Visualizer subscribes to events/telemetry only.

It must never become execution authority, MA command authority, approval authority, or routing authority required for task completion.

If the Visualizer crashes, ZEN/OpenClaw/Agents/MA Bridge continue normally.

### Conceptual entities

Avatars may represent ZEN Agent, OpenClaw, Coding Agent, Vision Agent, Research Agent, Git/GitHub worker, GPT/Claude/Qwen provider workers, MA-related workers, and future APIs/Agents.

Stations may represent Browser/Web Research, Terminal, Coding, Git/GitHub, File Storage, Vision, AI Model/API, MA Bridge, ZEN Operator, OpenClaw, Network/SSH, Logs/Monitoring, Approval Gate, Sandbox/OpenShell, and GPU/Compute.

### Runtime events

The Visualizer should consume normalized real events such as:
- `AGENT_IDLE`
- `AGENT_ASSIGNED`
- `AGENT_THINKING`
- `TOOL_REQUESTED`
- `TOOL_STARTED`
- `TOOL_RUNNING`
- `TOOL_FINISHED`
- `TOOL_FAILED`
- `WAITING_FOR_APPROVAL`
- `APPROVED`
- `API_REQUEST`
- `API_RESPONSE`
- `RETRYING`
- `ERROR`
- `TASK_COMPLETE`

Example:

```text
TOOL_REQUESTED=GitHub
 -> Avatar moves to GitHub Station

WAITING_FOR_APPROVAL
 -> Avatar waits at Approval Gate

API_REQUEST=Qwen
 -> Qwen worker becomes active

TASK_COMPLETE
 -> Avatar returns to idle/rest state
```

### Visual style

Target:
- 2D / 2.5D top-down;
- small office/studio/workspace;
- game-like readability without childish styling;
- modern/simple animation;
- low visual noise;
- useful first, entertaining second.

Do not fake work with decorative animations. Idle animation is allowed, but work-state animation must be driven by real runtime state.

## Future Control Room evolution

Phase A — current:
- ChatGPT + status + terminal.

Phase B — observation integration:
- replace the simple status pane with structured event/activity widgets.

Phase C — Living Visualizer:
- Living System Visualizer becomes the main idle canvas;
- ChatGPT and terminal remain one action away;
- active operator mode can return to the CONTROL_ROOM split immediately.

## Acceptance criteria for future implementation

A future implementation is acceptable only if:
1. Mini remote services work headlessly with the screen unplugged.
2. Plugging in a monitor produces a stable Control Room automatically.
3. Display remains 180-degree rotated after GUI restart.
4. ChatGPT starts and remains usable.
5. system/Agent status is visible without reading raw logs.
6. terminal is immediately accessible.
7. no dashboard/visualizer failure affects ZEN execution.
8. no new execution authority is created.
9. Living Visualizer reads real runtime events.
10. operator can switch between CONTROL_ROOM, MONITOR, MA view and future LIVING_IDLE without relearning the ZEN workflow.

## Explicit non-goals for this design task

Do not yet:
- implement the Living System Visualizer;
- alter ZEN production execution path;
- change MA2/MA3 authority;
- introduce a new mandatory Agent orchestrator;
- make the GUI required for headless operation;
- replace existing monitoring only for visual novelty.

This document captures the intended operator/display experience so future implementation can be bounded and reviewed.