# ZEN Mac mini Show Agent Controller Host

Status: **VALIDATED HOME / PORTABLE CONTROL-PLANE HOST**  
Validated: **2026-09-28**

## Role

`zen-agent-server` (Macmini6,2 / 2012 Mac mini) is the validated Home/Portable
host for the ZEN Show Agent Controller control plane.

This role includes:

- loopback Operator API;
- loopback MA Bridge process boundary;
- show/controller state and cache;
- Codebase Memory MCP structural code intelligence;
- remote administration / recovery;
- logs, health and lifecycle checkpoints;
- future show-wide orchestration that remains above department adapters.

This role explicitly does **not** grant production MA execution authority.
During integration, `MA2_WRITES=0` remains required.

## Validated host baseline

- Ubuntu 24.04.5 LTS
- kernel 6.8.0-142-generic
- Intel Core i7-3615QM, 4C/8T
- 8 GB visible RAM + 4 GB swap
- Intel 545s 256 GB SSD; SMART + short self-test PASS
- persistent system journal with bounded storage
- host-state and lifecycle checkpoints under `/var/lib/zen-agent`
- owner-controlled power-on / reboot policy; unattended upgrades may not reboot automatically

## Network split

```text
Wi-Fi
→ Internet / API / GitHub / Remote administration

Ethernet
→ reserved for MA / Production LAN
→ no default Internet route

IPv4 forwarding = off
IPv6 forwarding = off
```

Known Wi-Fi profiles are auto-connect profiles; Ethernet remains the production
network path and must not steal the default Internet route.

## Runtime

Installed host service:

```text
zen-show-controller.service
```

Validated endpoints:

```text
Operator API  127.0.0.1:8876
MA Bridge     127.0.0.1:8877
```

Acceptance evidence on 2026-09-28:

- `zen-show-controller.service` enabled + active;
- `/healthz` returns OK;
- Field Core reports ONLINE;
- MA Bridge process boundary reports ONLINE while MA connection remains DISCONNECTED;
- forced controller process kill is recovered by systemd and health returns;
- `977/977` unit tests PASS;
- repository self-check reports `ma2_writes: 0`;
- repository worktree clean before host-role documentation update.

## Code intelligence

Codebase Memory MCP 0.11.0 is installed and validated locally.

ZEN indexing acceptance:

- 7,310 nodes;
- 28,678 edges;
- architecture/search/trace/coverage checks PASS;
- no `.codebase-memory/` artifact is written into the tracked repository;
- auto-index / auto-watch enabled, UI disabled.

ToolRush was reviewed as an optimization reference. Its warm-shell, direct
search, bounded-read, parallel read-only batching, kill-switch and fail-closed
ideas are approved for later **ZEN-native** adaptation. The upstream Hermes / Windows/MSYS runtime is not installed on this Ubuntu host.

## Production authority gate

Before this Mac mini can ever be promoted from controller host to a production
Field Host, all of the following require an explicit owner decision and fresh
evidence:

1. production Ethernet / MA subnet profile validated on the real show network;
2. MA reachability and current-show identity verified;
3. deterministic adapter write path verified for the intended scope;
4. Preview + explicit human approval remains mandatory;
5. post-write native verification remains authoritative;
6. protected-object boundaries remain enforced;
7. no role promotion is inferred merely because the controller service is online.

Until then, the authoritative interpretation is:

```text
Mac mini = Show Agent Controller control-plane host
Mac mini != automatically production MA authority
MA2_WRITES = 0 during integration
```
