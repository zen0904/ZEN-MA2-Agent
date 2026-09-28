# ZEN Windows headless deployment skeleton

Status: **WINDOWS LIGHTING ADAPTER VALIDATED / GENERIC WORKER DEPLOYMENT PREPARED**

The operator-visible Windows machine (`DESKTOP-AA2GR39`) currently hosts the
OpenClaw Hub plus the MA-local `LIGHTING_GRANDMA2` adapter/Field Core. It is not
the Show Agent Controller. Keeping the lighting adapter beside grandMA2 onPC is
intentional because native exports, filesystem evidence, GUI/Stage View capture,
and deterministic MA verification are local to that Windows host.

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

To expose the bounded `zen.ma.stage.visual` native-screen navigation/capture path on a verified Windows MA2 host, opt in explicitly:

```powershell
.\deploy\windows\start-field-core.ps1 -RepoRoot C:\path\to\ZEN-MA2-Agent -ZenHome C:\ZEN -EnableMA2GuiNavigation
```

The stage-visual path has no MA command/write authority. It first attempts background capture of existing native MA2 Screen windows and only falls back to the bounded Screen 2/3/4 navigation rail when required.

Optional Worker endpoints can be supplied after the real addresses are known.

## Controller-facing read-only facade

`lighting-readonly-facade.py` is the narrow controller-facing surface for the
Windows lighting host. It binds `127.0.0.1:18877` and proxies only:

- `GET /healthz`
- `GET /zen/v0.1/status`

All mutation methods return HTTP 405 and other paths return 404. The validated
host publishes this facade, not the full Operator API, through Tailscale Serve.
The full Windows ZEN Operator API remains on local `127.0.0.1:8876` for the
Windows/OpenClaw lighting workflow.

Validated 2026-09-28 topology:

```text
Mac mini Show Agent Controller
→ authenticated Tailscale overlay
→ Windows :18877 read-only facade
→ Windows ZEN :8876 loopback
→ grandMA2 onPC :30000 loopback
```

The facade is a visibility boundary only. It does not create cross-host
`zen.approve`, shell, raw MA command, credential-forwarding, or generic HTTP
proxy authority.

## Controller loopback proxy for OpenClaw

`mini-controller-proxy.py` gives the Windows OpenClaw plugin a loopback-only
path to the Mini controller facade while preserving the plugin's loopback URL
policy. The validated Windows task runs:

```text
python mini-controller-proxy.py --listen-port 18876
```

The script resolves the Tailscale peer named `zen-agent-server` and connects to
peer port `18876`. Therefore the validated path is:

```text
OpenClaw zen_department_status
→ Windows 127.0.0.1:18876
→ mini-controller-proxy.py
→ Tailscale peer zen-agent-server:18876
→ Mini controller read-only facade
→ Mini Controller 127.0.0.1:8876
```

Do not point this proxy at Mini port `8876`; that would bypass the controller
read-only facade. MA-local tools continue to use Windows `127.0.0.1:8876`.

Validated Task Scheduler entries on `DESKTOP-AA2GR39`:

- `ZEN Field Core`
- `ZEN Lighting ReadOnly Facade`
- `ZEN Mini Controller Proxy`

All three use logon triggers on the current test host. Production service
semantics remain a separate acceptance decision.

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
