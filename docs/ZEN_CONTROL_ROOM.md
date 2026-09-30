# ZEN Control Room / Room Mode

Status: ACTIVE IMPLEMENTATION
Date: 2026-09-30

## Purpose

Room Mode extends the existing tty1/tmux `zenmon` interface without replacing
the proven SYSTEM monitor or MA_AGENT view.

The visual metaphor is spatial:

- idle/available workers stay in the **REST LOUNGE**;
- active workers occupy named **WORK SEATS**;
- **OPENCHATX STUDIO** is a dedicated local-workshop area;
- **MA TOOL BAY** is a dedicated deterministic MA pipeline area;
- **TOOL RACK** exposes installed/capability-registry tools and highlights those
  currently observable as in use;
- **CURRENT WORK** shows the brokered task identity, not hidden model reasoning;
- **ACTIVITY STREAM** shows recent OPS/Git events.

## Windows and keys

The existing tmux session remains `zenmon`.

- `F10` -> ROOM
- `F11` -> MONITOR
- `F12` -> MA_AGENT

The old MONITOR window remains intact: btop/system telemetry, AI LIVE,
COMMANDS, GIT and RECENT FILE WRITES are preserved.

ROOM becomes the preferred human-readable overview for a new tty1 session.

## Room semantics

### Rest Lounge

Represented workers:

- GPT LEAD
- API AUX
- CODEX
- OPENCLAW
- OPENCHATX
- OPS

The lounge is not process fiction. A worker leaves the lounge only when the
dashboard has observable evidence of active work, such as a running OPS job,
a live Codex process, or a recognized API Designer runtime process.

### Round Table / Work Positions

The first layout is intentionally lightweight:

```text
                         [ DESIGN POD ]
                    GPT LEAD       API AUX
                           |
[ OPENCHATX STUDIO ] -- [ ZEN CORE ] -- [ MA TOOL BAY ]
                           |
                       CODEX   OPS
                    [ DEV / OPS BENCH ]
```

A small spinner animates only active seats.

### OpenChatX Studio

Shows:

- service health;
- local endpoint 127.0.0.1:18001;
- worker/ready state;
- local toolbox classes;
- explicit `MA authority = NONE`.

### MA Tool Bay

Shows the deterministic path components independently:

- Field Core / controller;
- MA Bridge;
- Operator proxy;
- Compiler;
- Preview gate;
- Builder;
- native Readback.

The bay also exposes a compact MA Lab list containing the locally installed MA2
and MA3 research/reference tooling, including gma2-mcp, The3-MCP, GDTF/MVR,
Phaser/Effect references, Chataigne/Companion, Timecode adapters and
XYZ/StageMarker/PSN references.

## Tool Rack

The rack merges:

- `data/zen_upstream_tool_registry.json`;
- `data/zen_agent_tool_capabilities.json`.

States are rendered compactly:

- active spinner = observable use;
- open circle = ready/live/verified;
- dot = parked, disabled, fallback, or host-dependent;
- cross = failed/down/broken.

Tool presence is not authority. Reference-only repositories remain references.

## Current Work provenance

ROOM reads the current/public OPS result and the current control job.

A control job may optionally carry:

```json
{
  "meta": {
    "actor": "CHATGPT_LEAD",
    "summary": "Deploy ZEN Control Room",
    "tools": ["OPS", "GitHub", "tmux"]
  }
}
```

The current OPS worker safely ignores unknown top-level metadata, while ROOM can
use it for human-readable provenance. This does not alter execution semantics.

Future API broker work should use actor `API_AUX` when it submits bounded work.

## Performance

ROOM is a local text UI:

- one-second refresh target;
- ANSI in-place redraw;
- no Electron;
- no browser;
- no WebGL;
- no GPU renderer;
- short systemctl/socket/process probes only.

It is deliberately cheaper than the existing btop-heavy MONITOR view.

## Safety

ROOM is observability only.

It does not:

- expose hidden model chain-of-thought;
- provide shell/Telnet/Lua input;
- mutate MA2 or MA3;
- bypass Preview/Approval;
- give OpenChatX or external MCP projects MA authority.

Only observable task summaries, process/service state, tool use evidence,
repository activity and deterministic MA pipeline state are shown.
