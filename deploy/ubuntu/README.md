# ZEN Ubuntu deployment skeleton

Status: **REPOSITORY PREPARED / HOST INSTALL NOT PERFORMED**

This directory prepares ZEN for the planned field/home topology without modifying any real Ubuntu host.

## Current target roles

- Field Node: 2012 Mac mini, Ubuntu, i7-3615QM, 8 GB RAM, Intel 545s 256 GB SSD.
- Home Worker A: Ubuntu, 16 GB RAM, GTX 1650 4 GB.
- Home Worker B: Ubuntu, 16 GB RAM, GPU model still UNKNOWN.

Only the Field Node travels to the venue. Home workers are optional compute and are not required for Field Core availability.

## Implemented repository components

- `zen_ma2_agent.ma_bridge.protocol`: strict ZEN/1 parser + bounded request dedup.
- `zen_ma2_agent.ma_bridge.server`: localhost-first TCP dispatcher. `PING` and `STATUS` are deterministic; `DIMMER` is parse-only and `DESIGN` is NOT_IMPLEMENTED.
- `zen_ma2_agent.operator_server`: localhost-first OpenClaw-facing ZEN Operator API.
- `zen_ma2_agent.worker.server`: worker `/health`, `/capabilities`, and `/jobs` control plane with `ECHO_TEST` plus `INFERENCE_RESERVED`.
- `zen_ma2_agent.artifacts`: local artifact metadata/cache and stale-result checks.
- `check_host.py`: non-destructive host readiness report.

## Service templates

`systemd/*.service` are templates, not drop-in units. Replace these placeholders before installation:

- `@ZEN_USER@`
- `@ZEN_GROUP@`
- `@ZEN_ENV_FILE@`
- `@ZEN_APP_DIR@`
- `@ZEN_VENV_DIR@`
- `@ZEN_HOME@`

The templates intentionally do not call `sudo`, alter firewall rules, install packages, install drivers, configure VPNs, or change network settings.

## Environment

Start from `env.example` and create a host-specific environment file outside Git. Do not commit secrets or MA credentials.

Field Node defaults should keep Operator API and MA Bridge on loopback. Worker API also defaults to loopback until a private authenticated network is deliberately configured.

## Host check

Run from a cloned repository:

```bash
python3 deploy/ubuntu/check_host.py
```

This only inspects OS/Python/CPU/RAM/free disk/tool availability and optional `nvidia-smi` output. It performs no installation or configuration.

## Not implemented yet

- actual Ubuntu package/systemd installation;
- OpenClaw installation and plugin scaffold against a pinned host version;
- private-network transport between field and home;
- Qwen/llama.cpp on either worker;
- CUDA setup/benchmark;
- authenticated worker transport;
- actual remote inference job;
- DIMMER execution;
- DESIGN execution;
- any production MA2 write.

`MA2_WRITES=0` remains required in this phase.
