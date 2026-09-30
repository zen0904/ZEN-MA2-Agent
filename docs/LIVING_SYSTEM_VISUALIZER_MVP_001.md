# ZEN / Mini Living System Visualizer MVP 001

Date: 2026-09-30
Status: RUNNING MVP
Authority: OBSERVATION_ONLY

## Purpose

Provide a live, game-like visual workspace for the Mini where Agents, provider workers and tools are represented as moving Avatars and Stations driven by real runtime state.

The Visualizer is not an execution authority.

If the Visualizer stops, ZEN Ops, OpenClaw, SSH, Gateway, MA Bridge, Preview, Human Approval and deterministic execution continue independently.

## Current runtime

Service:
- `zen-living-visualizer.service`
- status: active
- listen: `127.0.0.1:18992`
- health: `/health`
- state: `/api/state`

Schema:
- `zen.living_visualizer.health.v0.1`
- `zen.living_visualizer.state.v0.1`

Authority header:
- `X-ZEN-Authority: observation-only`

## Current stations

- Rest Lounge
- Browser / Research
- Logs / Monitoring
- Terminal
- File Storage
- Coding
- Git / GitHub
- AI Model / API
- GPU / Compute
- Vision
- MA Bridge / ZEN Operator
- Sandbox / OpenShell
- OpenClaw
- Network / SSH
- Approval Gate
- ZEN Core

## Current Avatars

- ZEN Agent
- ZEN Ops
- OpenClaw
- Coding Agent
- Research Agent
- Git Worker
- Vision Agent
- GPT Provider
- Qwen Provider
- Claude Provider

Provider Avatars are only marked WORKING when the current task/runtime metadata explicitly identifies that provider. The resident ChatGPT GUI process alone is not treated as provider activity.

## Current event behavior

Real runtime state is mapped into:
- Agent idle state
- Agent working state
- Station occupancy
- task summary
- current tool context
- error state
- recent event stream

Existing ZEN Ops activity and current job metadata are reused instead of inventing a parallel event source.

## Current system telemetry

Verified live on 2026-09-30:

- CPU utilization: 9%
- CPU package temperature: 66°C
- fan: 5005 RPM
- memory: 3.2 / 7.7 GiB
- root disk: 51 / 233 GiB
- network interface: `wlp2s0b1`
- live network RX/TX: verified
- uptime: 3h 49m
- load: 0.57 / 0.54 / 0.58
- ZEN Ops: active
- OpenClaw: active
- Tailscale: active
- RDC: active
- ChatGPT GUI: active

GPU:
- Intel integrated GPU model is detected.
- GPU utilization: N/A until a trustworthy source exists.
- GPU temperature: N/A until a trustworthy source exists.

Do not substitute unrelated Apple SMC sensor values for GPU temperature.

## Data-source policy

Use real data only:
- `/proc/stat` for CPU utilization
- kernel thermal zones for CPU temperature
- Apple SMC / `sensors` for fan RPM when available
- `/proc/meminfo` for memory
- `statvfs` for disk
- `/proc/net/route` + `/proc/net/dev` for active interface and throughput
- systemd/ports for service state
- ZEN Ops activity/current-job metadata for task/Agent movement

No fake activity animation may imply a tool/provider is working when no runtime evidence exists.

## Safety boundary

The Visualizer must not:
- execute MA commands;
- approve MA actions;
- mutate ZEN routing;
- replace Preview or Human Approval;
- become required for headless operation;
- expose secrets through the public ZEN Ops result funnel.

MA2_WRITES=0
MA3_WRITES=0

## Next phase

1. Integrate the visualizer into the Mini Control Room display as a visible local window.
2. Add a normalized event adapter for richer events such as TOOL_REQUESTED, TOOL_STARTED, API_REQUEST, WAITING_FOR_APPROVAL and TASK_COMPLETE.
3. Add queue and handoff visualization.
4. Add click-to-inspect task/tool details.
5. Add provider latency/token metadata where a trustworthy telemetry source exists.
6. Preserve current observation-only authority.
