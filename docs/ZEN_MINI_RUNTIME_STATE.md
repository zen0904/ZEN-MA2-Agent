# ZEN Mini Runtime State

Verified: 2026-09-30 (Asia/Taipei)
Host: `zen-agent-server`
Scope: post-power-loss recovery, ZEN Ops result-plane persistence, and OpenClaw gateway boot persistence.

## Current verified runtime

The Mini runtime recovered after the power loss and the primary maintenance path is operational:

```text
ChatGPT -> GitHub zen-ops-control -> ZEN Ops Worker -> Mini
        -> ZEN Ops Result Server -> Tailscale Funnel -> result retrieval
```

Verified active services in the final post-repair health check:

- `zen-ops-worker`
- `zen-ops-results`
- `tailscaled`
- `zen-show-controller`
- `zen-lighting-operator-proxy`
- `zen-glances`
- `zen-sentinel`

Verified loopback listeners:

- `127.0.0.1:8876` - ZEN Show Controller / Operator API
- `127.0.0.1:18878` - Lighting Operator Proxy
- `127.0.0.1:18789` - OpenClaw Gateway
- `127.0.0.1:18991` - ZEN Ops Result Server

## ZEN Ops result plane

The persistent external result endpoint is intentionally isolated from the OpenClaw HTTPS surface:

```text
https://zen-agent-server.tail3e0394.ts.net:10000
  -> http://127.0.0.1:18991
```

`deploy/ops_tasks/repair_zen_ops_funnel.sh` must maintain HTTPS port `10000` explicitly. It must not claim the default Tailscale HTTPS listener on port `443`, because that listener can already be owned by the OpenClaw-managed Serve/Funnel surface.

Final repair verification:

- `zen-ops-results.service`: active
- `127.0.0.1:18991`: listening
- `tailscaled.service`: active
- Tailscale Funnel `:10000`: active
- local `latest.json` probe: pass
- repair job return code: `0`

The runtime updater remains enabled and periodically fast-forwards `/opt/zen/zen-ops-runtime` to committed `main` state.

## OpenClaw gateway persistence

Current OpenClaw runtime:

- version: `OpenClaw 2026.9.4 (3a9d69d)`
- gateway listener: `127.0.0.1:18789`
- runtime authority: root `systemd --user`
- cgroup: `user@0.service/app.slice/openclaw-gateway.service`
- root linger: `yes`

The existing OpenClaw-managed persistent user unit is retained. ZEN does not replace it merely because its `ExecStart` uses the installed Node entrypoint instead of the `/opt/node/bin/openclaw` wrapper.

Final persistence verification:

- existing persistent unit retained: yes
- OpenClaw gateway ExecStart validation: pass
- `systemd-analyze verify`: pass
- `default.target.wants/openclaw-gateway.service` enable link: present
- active `openclaw-gateway.service` cgroup: present
- `127.0.0.1:18789`: listening
- persistence helper: pass
- repair job return code: `0`

`REBOOT_VERIFICATION=PENDING` remains intentionally true. The persistence structure is configured and verified, but a second deliberate reboot was not performed solely to prove it again after this repair.

## Maintenance safety boundary

`zen-ops-worker.service` keeps `ProtectHome=true`. Do not weaken that sandbox just to maintain OpenClaw state under `/root`.

OpenClaw persistence maintenance is therefore performed through a constrained one-shot system service that invokes only:

`deploy/ops_tasks/install_openclaw_gateway_user_unit.sh`

The helper writes only the required OpenClaw user-unit persistence state, records a sanitized result under `/var/lib/zen-ops`, and exits. The temporary system-level maintenance unit is removed after the operation.

Legacy `repair_openclaw_boot_persistence.sh` now delegates to the canonical user-unit repair path so old jobs cannot accidentally create a second system-level OpenClaw gateway competing for port `18789`.

## Remote Desktop Commander role

Remote Desktop Commander is `FALLBACK_ONLY` for Mini operations.

Normal maintenance must use ZEN Ops. A rescue channel may be used only when the maintenance plane itself is unavailable or when GUI/native-host access is specifically required. Using a rescue channel does not change the primary architecture or grant it ongoing authority.

During this recovery, the Windows host was used only as a rescue result-retrieval path while external Funnel fetching was inconsistent. Repair execution itself remained on the GitHub control branch -> ZEN Ops Worker path.

## Durable repair commits

Key committed repairs from this recovery include:

- `cb0281b778f433e573ff1367b078bcdd064a1308` - keep ZEN Ops result Funnel on dedicated HTTPS `10000`
- `d89c2747d99916cf9a6bb6773b04e2a96ebdd7b4` - route legacy OpenClaw persistence repair to the canonical user-unit path
- `42c613d22a2d634a0244c685b220b7d0b60dff0a` - constrained one-shot maintenance boundary for OpenClaw persistence
- `cbe85dd7ce9b651935e05dabf9c8baa75bfd0474` - validate and preserve the existing OpenClaw-managed unit form

Intermediate diagnostic/repair attempts are evidence only and are superseded by the verified state above.
