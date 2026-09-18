# ZEN Linux/systemd deployment skeleton

Status: **REPOSITORY PREPARED / HOST INSTALL NOT PERFORMED**

This directory prepares ZEN for a possible Linux/systemd Gateway, Field Core,
and/or Worker host without modifying any real machine.

It is intentionally host-neutral. Do not assume the 2012 Mac mini or assume
that Worker A/B currently run Linux. Actual OS is verified only when the
physical machines return.

## Current deployment direction

- Operator-visible Windows machine: OpenClaw Windows Hub only.
- Preferred next Gateway / Field Host candidate to verify: Worker A.
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
- private-network transport;
- actual model runtime;
- real remote inference;
- production MA writes.

`MA2_WRITES=0` remains required during integration.
