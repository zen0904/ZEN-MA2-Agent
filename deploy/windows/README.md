# ZEN Windows headless deployment skeleton

Status: **REPOSITORY PREPARED / HOST INSTALL NOT PERFORMED**

Use this only if a returned Worker/Gateway candidate is actually running
Windows. The operator-visible Windows machine remains OpenClaw Hub-only and is
not the target of this deployment skeleton.

## Reuse-first rule

Use existing Windows facilities:

- PowerShell for launch wrappers;
- Windows Task Scheduler for startup if a Windows host is ultimately selected;
- existing ZEN `main.py` / `FieldHost`;
- existing `zen_ma2_agent.worker.cli`;
- official OpenClaw Gateway installation/runtime for the exact tested Windows
  host, if officially supported for that deployment.

Do not create a custom Windows service framework merely to keep ZEN running.

## First host check

From the repository:

```powershell
python scripts\host_preflight.py
python -m unittest discover -s tests -v
python main.py --self-check
```

Optional reachability:

```powershell
python scripts\host_preflight.py --target ma=<MA_HOST>:30000 --target peer=<OTHER_WORKER>:8878
```

## Manual Field Core smoke

```powershell
.\deploy\windows\start-field-core.ps1 -RepoRoot C:\path\to\ZEN-MA2-Agent -ZenHome C:\ZEN
```

Optional Worker endpoints can be supplied after the real addresses are known.

## Manual Worker smoke

```powershell
.\deploy\windows\start-worker.ps1 -RepoRoot C:\path\to\ZEN-MA2-Agent -WorkerId worker-a
```

The default Worker bind is loopback-only. A non-loopback bind requires
`-AllowRemote` and should only be used after the private-network/security
decision is explicit.

## Autostart later

Do not register autostart until the host has passed real-machine smoke tests.

If Windows is selected for long-running headless use, prefer Windows Task
Scheduler's native "At startup" trigger to a new custom supervisor. Record the
exact Python/venv path, repository path and `ZEN_HOME` used by the task.

OpenClaw Gateway startup should follow the official runtime/service method for
the exact tested version rather than a ZEN-created replacement.

## Safety

These wrappers only launch existing ZEN processes.

They do not:

- install packages;
- change firewall/network/VPN;
- enable MA writes;
- grant Worker inference direct MA authority;
- install OpenClaw.
