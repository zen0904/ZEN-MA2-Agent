# ZEN Host Return Quickstart

Status: **READY FOR HARDWARE RETURN**

Purpose: when Worker A/B physically return, gather the remaining deployment
facts quickly without redesigning the system.

This procedure is intentionally read-only until a host is selected.

## 1. Update the repository

```text
git pull --ff-only origin main
git status
```

Do not delete unrelated cache directories merely to make the tree look clean.

## 2. Install existing Python dependencies if needed

Use the repository's existing dependency definition:

```text
python -m pip install -r requirements.txt
```

Do not create a second dependency list.

## 3. Run one-shot host preflight

Basic:

```text
python scripts/host_preflight.py
```

With known network targets:

```text
python scripts/host_preflight.py \
  --target operator=<WINDOWS_HUB_IP>:443 \
  --target ma=<MA_HOST>:30000 \
  --target peer=<OTHER_WORKER_IP>:8878
```

Use only targets that actually exist in the current network. The operator Hub
port may differ depending on the official OpenClaw connection method; do not
invent a port merely to satisfy this example.

The script reports:

- actual OS/version;
- CPU / cores / RAM / disk;
- Python and existing ZEN package versions;
- IPv4 interfaces and link state;
- existing service manager;
- SSH/sshd hints;
- optional TCP reachability;
- `ma2_writes = 0`.

It does not install software, alter services, or write to MA.

## 4. Run ZEN regression/self-check

```text
python -m unittest discover -s tests -v
python main.py --self-check
```

Do not proceed with deployment if the full suite regresses.

## 5. Worker service smoke

For a machine intended to run a Worker service, start the existing Worker
control plane manually first:

```text
python -m zen_ma2_agent.worker.cli \
  --worker-id worker-a \
  --host <LAN_IP> \
  --port 8878 \
  --allow-remote
```

Use `worker-b` on the second machine.

Then verify the existing contracts:

```text
GET /health
GET /capabilities
```

Do not create a new health protocol.

## 6. Gateway / Field Host decision

Worker A remains the preferred candidate to inspect first, but is not selected
until the real machine proves:

- stable service/autostart capability;
- network reachability needed by the deployment;
- ZEN full tests/self-check pass;
- official OpenClaw Gateway support for its actual OS;
- acceptable remote administration/reboot recovery.

If those facts are not established, keep:

```text
gateway_host = UNSELECTED_HEADLESS_HOST
tested_openclaw_version = null
```

## 7. Only after a host is selected

Then and only then:

1. install the official OpenClaw Gateway for that actual OS;
2. obtain its exact Gateway version;
3. pin `integrations/openclaw/compatibility.json`;
4. verify Hub -> Gateway;
5. build the thin read-only ZEN adapter/plugin;
6. configure native OS autostart using the existing service manager.

Do not create a custom process supervisor.

## Safety

Always preserve:

```text
OpenClaw != MA authority
Worker inference != MA authority
LLM != MA authority
MA2_WRITES=0 during integration
```

Physical co-hosting of Gateway, Field Core, and Worker runtime does not merge
their logical authority boundaries.
