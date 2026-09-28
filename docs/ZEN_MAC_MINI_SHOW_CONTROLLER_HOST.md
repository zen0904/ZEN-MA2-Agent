# ZEN Mac mini Show Agent Controller Host

Status: **VALIDATED HOME / PORTABLE CONTROL-PLANE HOST**  
Validated: **2026-09-28**

## Role

`zen-agent-server` (Macmini6,2 / 2012 Mac mini) is the validated Home/Portable
host for the ZEN Show Agent Controller control plane.

This role includes:

- OpenClaw Gateway 2026.9.4 as the primary operator hub/runtime;
- loopback ZEN Operator API;
- loopback MA Bridge process boundary;
- show/controller state and cache;
- Codebase Memory MCP structural code intelligence;
- remote administration / recovery;
- logs, health and lifecycle checkpoints;
- show-wide orchestration above independently verified department adapters.

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
→ static `10.0.0.50/8` (`255.0.0.0`)
→ reserved for MA / Production LAN
→ no DHCP, DNS, or default Internet route

IPv4 forwarding = off
IPv6 forwarding = off
```

Known Wi-Fi profiles are auto-connect profiles; Ethernet remains the production
network path and must not steal the default Internet route. Tailscale provides a
stable private overlay for controller/department-adapter transport across home
Wi-Fi, iPhone hotspot, or other Internet uplinks; it does not replace the
Production LAN used by show hardware.

## Runtime

Installed host services include:

```text
zen-show-controller.service
zen-controller-readonly-facade.service
zen-lighting-operator-proxy.service
OpenClaw official systemd-user gateway service
```

Validated local endpoints:

```text
OpenClaw Gateway            127.0.0.1:18789
ZEN Controller Operator API 127.0.0.1:8876
MA Bridge boundary          127.0.0.1:8877
Controller read-only facade 127.0.0.1:18876
Lighting operator proxy     127.0.0.1:18878
```

The full ZEN Controller Operator API remains loopback-only and is **not**
published directly through Tailscale. The bounded controller facade on `18876`
is the tailnet-visible ZEN status surface.

OpenClaw Gateway is the primary operator runtime on the Mini. It is installed
with OpenClaw's official systemd-user service, with root linger enabled so the
Gateway survives logout. The Gateway remains loopback-bound and OpenClaw owns a
Tailscale Serve HTTPS endpoint at `wss://zen-agent-server.tail3e0394.ts.net`.

The Windows lighting host keeps grandMA2-local execution and evidence. It
publishes two separate Tailscale-only adapter surfaces:

- `18877`: read-only health/operator-status facade used by
  `zen.department.status`;
- `18878`: typed ZEN operator facade, allowlisted to the Mini's Tailscale client
  address and reached from Mini loopback `127.0.0.1:18878` through
  `zen-lighting-operator-proxy.service`.

The typed operator facade exposes only named read/plan/Preview ZEN tools. It
does not provide a generic HTTP proxy, remote shell, credential forwarding, raw
MA command surface, cross-host `zen.approve`, or cross-host semantic-binding
mutation. Preview delegation remains `REMOTE_PREVIEW_ONLY`, reports
`ma2_writes = 0`, and cannot authorize execution.

Acceptance evidence on 2026-09-28:

- `zen-show-controller.service` enabled + active;
- `/healthz` returns OK;
- Field Core reports ONLINE;
- MA Bridge process boundary reports ONLINE while MA connection remains DISCONNECTED;
- forced controller process kill is recovered by systemd and health returns;
- `982/982` unit tests PASS after read-only department-adapter federation;
- repository self-check reports `ma2_writes: 0`;
- repository worktree clean before host-role documentation update.

## Code intelligence

Codebase Memory MCP 0.11.0 is installed and validated locally.

ZEN indexing acceptance:

- 7,355 nodes;
- 28,826 edges;
- architecture/search/trace/coverage checks PASS;
- no `.codebase-memory/` artifact is written into the tracked repository;
- auto-index / auto-watch enabled, UI disabled.

ToolRush was reviewed as an optimization reference. Its warm-shell, direct
search, bounded-read, parallel read-only batching, kill-switch and fail-closed
ideas are approved for later **ZEN-native** adaptation. The upstream Hermes / Windows/MSYS runtime is not installed on this Ubuntu host.

## Read-only department federation

The controller may register a department-local ZEN Operator API with
`--department-adapter ADAPTER_ID=BASE_URL`. The current validated adapter is
`LIGHTING_GRANDMA2`, reached through Mini loopback `127.0.0.1:18878` and the
authenticated Tailscale path to Windows. Federation is intentionally narrow:
`zen.department.status` projects the fixed status contract, while
`zen.department.preview` delegates only the fixed Preview allowlist. There is
no generic HTTP proxy, credential forwarding, remote shell, cross-host
`zen.approve`, cross-host `zen.position.semantic.bind`, or raw MA command path.
Delegated Preview declares `REMOTE_PREVIEW_ONLY` and `ma2_writes = 0`.

## Production authority gate

Before this Mac mini can ever be promoted from controller host to a production
Field Host, all of the following require an explicit owner decision and fresh
evidence:

1. production Ethernet `10.0.0.50/8` profile validated against the real show network;
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
