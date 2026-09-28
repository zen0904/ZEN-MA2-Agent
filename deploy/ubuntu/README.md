# ZEN Linux/systemd deployment skeleton

Status: **GENERIC DEPLOYMENT PREPARED / MAC MINI CONTROLLER HOST VALIDATED**

This directory prepares ZEN for a possible Linux/systemd Gateway, Field Core,
and/or Worker host without modifying any real machine.

It is intentionally host-neutral. Do not assume the 2012 Mac mini or assume
that Worker A/B currently run Linux. Actual OS is verified only when the
physical machines return.

## Current deployment direction

- Validated Home/Portable Show Agent Controller host: 2012 Mac mini (`zen-agent-server`) running Ubuntu 24.04.5. It hosts OpenClaw Gateway 2026.9.4, the loopback-only ZEN control plane, code intelligence, cache/state and remote administration.
- Operator-visible Windows remains the MA-local `LIGHTING_GRANDMA2` adapter host. Its OpenClaw Gateway role is retired; Windows Tray/CLI may remain only as remote clients of the Mini Gateway.
- This Mac mini selection does **not** grant production Field Host or MA write authority. `MA2_WRITES=0` remains required during integration.
- Preferred next production Gateway / Field Host candidate to verify remains Worker A.
- Worker A may physically co-host OpenClaw Gateway + ZEN Field Core + Worker
  runtime if host checks pass.
- Worker B remains primarily an AI Worker.
- Physical co-location does not merge MA authority with Worker inference.

## Reuse-first deployment

Use existing platform/runtime facilities:

- systemd for Linux service lifecycle;
- `main.py` / `FieldHost` for the ZEN Field Core;
- `zen_ma2_agent.worker.cli` for Worker control plane;
- official OpenClaw Gateway installation/service guidance for the exact tested
  host version.

Do not create a custom supervisor when systemd is available.

## Host preflight

The canonical cross-platform preflight is:

```bash
python3 scripts/host_preflight.py
```

Optional reachability probes:

```bash
python3 scripts/host_preflight.py \
  --target ma=<MA_HOST>:30000 \
  --target peer=<OTHER_WORKER_IP>:8878
```

`deploy/ubuntu/check_host.py` remains only as a compatibility entrypoint and
delegates to that canonical script.

## Service templates

Templates under `systemd/` are not installed automatically.

Primary templates:

- `zen-show-controller.service` — loopback-only Show Agent Controller control-plane service for a validated headless controller host. It reuses the existing FieldHost runtime without granting production MA authority.
- `zen-controller-readonly-facade.service` — optional loopback-only facade for authenticated private transport. It exposes health/status GET plus `zen.department.status` POST only; it does not expose preview/approval/write tools.
- `zen-lighting-operator-proxy.service` — loopback-only proxy from Mini `127.0.0.1:18878` to the Windows lighting host's Tailscale-restricted typed operator facade on `18878`. This keeps the OpenClaw plugin's local-URL policy while preserving Windows-local MA execution.
- `zen-field-core.service` — normal ZEN FieldHost process. It owns Operator
  API, MA Bridge, Watchdog, Host Metrics and Worker Registry.
- `zen-worker.service` — Worker HTTP control plane.

`zen-ma-bridge.service` is retained only for isolated Bridge testing. Do not
run it alongside `zen-field-core.service` on the same bind/port.

Replace placeholders before installation:

- `@ZEN_USER@`
- `@ZEN_GROUP@`
- `@ZEN_ENV_FILE@`
- `@ZEN_APP_DIR@`
- `@ZEN_VENV_DIR@`
- `@ZEN_HOME@`

The templates do not:

- call sudo;
- install packages/drivers;
- change firewall/VPN/network configuration;
- install OpenClaw;
- enable MA writes.

## Environment

Start from `env.example` and create a host-specific EnvironmentFile outside
Git. Do not commit secrets or MA credentials.

The normal Field Core keeps Operator API and MA Bridge on loopback by default.
Remote exposure requires an explicit authenticated-network decision.

A Show Agent Controller may read a department-local ZEN Operator API with
`--department-adapter ADAPTER_ID=BASE_URL`. The endpoint is restricted to a
literal loopback, private-LAN, or Tailscale CGNAT address. The federation path
reads only the fixed remote status contract and exposes `zen.department.status`;
it does not forward `zen.approve`, shell access, raw MA commands, credentials,
or arbitrary HTTP paths. Tailscale Serve can publish a loopback Operator API to
an authenticated tailnet without changing the underlying ZEN bind from
`127.0.0.1`.

Worker API also stays loopback-only by default. If a later private-network
deployment requires a non-loopback Worker bind, use the existing
`--allow-remote` flag only after that network/security decision is made.

## First real-machine sequence

When a physical host returns:

```text
1. git pull --ff-only origin main
2. python3 scripts/host_preflight.py
3. python3 -m pip install -r requirements.txt
4. python3 -m unittest discover -s tests -v
5. python3 main.py --self-check
6. manual Worker smoke if applicable
7. select Gateway host only if evidence passes
8. install native service templates only after selection
9. install OpenClaw Gateway using official guidance for the actual OS
10. verify/pin exact Gateway version
```

## Still pending until hardware returns

- actual OS for Worker A/B;
- actual service/autostart behavior;
- MA and peer reachability;
- OpenClaw Gateway support/version on the selected host;
- production acceptance of private-network transport beyond the validated Mac mini ↔ Windows lighting-adapter path;
- actual model runtime;
- real remote inference;
- production MA writes.

`MA2_WRITES=0` remains required during integration.
