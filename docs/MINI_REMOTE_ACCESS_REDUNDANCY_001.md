# Mini Remote Access Redundancy and Transport Priority 001

Date: 2026-09-30
Owner decision: ZEN
Status: CANONICAL DESIGN / IMPLEMENTATION GUIDANCE

## Purpose

The Mini must remain reachable and operable even when one remote-control product, network path, quota-limited service, or UI layer is unavailable.

This document defines the canonical access priority. It is deliberately transport-redundant. No single remote tool is allowed to become the only administration path.

This does not change ZEN execution authority. MA2/MA3 programming still preserves Preview -> Human Approval -> deterministic execution -> native readback. Remote administration is not MA authority.

## Canonical priority

### Tier 1 — Co-primary Mini control plane

`zen-mini MCP` and `ZEN Ops` are co-primary, parallel paths.

They are not ordered as primary/backup against each other. Use whichever is directly exposed and appropriate in the current runtime context, and allow both to exist concurrently.

#### zen-mini MCP

Role:
- local/on-box Mini tool surface;
- bounded Mini status and project inspection;
- direct integration with the Mini-hosted ChatGPT/Codex runtime;
- low-latency local execution when the MCP is surfaced.

Verified:
- `zen-mini` is registered and enabled in the Mini Codex/ChatGPT MCP list;
- Mini ChatGPT GUI is active on the host;
- remote/mobile ChatGPT requests have been observed to cause work on the Mini through the connected control architecture.

Do not treat absence of `zen-mini` tools in a particular remote ChatGPT runtime as evidence that the Mini is offline.

#### ZEN Ops

Role:
- durable remote execution plane;
- Git-backed job intake;
- bounded shell/repo/service tasks;
- auditable result publication.

Verified remote loop:

```text
ChatGPT
 -> GitHub connector
 -> zen-ops-control/ops/job.json
 -> zen-ops-worker
 -> bounded task
 -> HTTPS result funnel
 -> ChatGPT
```

Verified services include `zen-ops-worker`, `zen-ops-results`, `zen-show-controller`, `zen-controller-readonly-facade`, `zen-lighting-operator-proxy`, and `tailscaled`.

The ZEN Ops result surface is externally readable. Never emit secrets, credentials, private keys, cookies, bearer tokens, or other sensitive material into the public result payload.

### Tier 2 — Secure shell plane

`Gateway SSH` and `Tailscale SSH / OpenSSH` are the next preferred administration layer. Both are ahead of Remote Desktop Commander.

#### Gateway SSH

Role:
- direct Linux administration over SSH;
- systemd/service inspection and recovery;
- bounded command execution;
- file and SSH-key administration;
- independent recovery path when ZEN Ops or GUI layers are degraded.

Current state:
- Gateway connector capability exists;
- Mini has not yet been onboarded into Gateway;
- therefore Gateway is not yet an accepted operational path.

Acceptance gate:
1. Create a Gateway server entry for `zen-agent-server`.
2. Independently verify the current Mini OpenSSH host-key fingerprint before trusting first connection.
3. Install/verify the Gateway managed public key without exposing private key material.
4. Confirm `hostname` over Gateway SSH.
5. Confirm read-only systemd status for `zen-ops-worker.service` and `tailscaled.service`.
6. Confirm one bounded file read under an approved path.
7. Confirm disconnect/reconnect without changing ZEN, OpenClaw, MA, or network authority.
8. Record the Gateway canonical server ID in repo state.
9. Keep Gateway as administration transport, not MA execution authority.

#### Tailscale SSH / OpenSSH

Role:
- private-overlay SSH path;
- recovery when LAN addressing changes;
- independent network path for direct shell administration;
- preferred before RDC for normal SSH-level maintenance.

Current verified facts:
- `tailscaled.service` is active on Mini;
- Mini Tailscale identity is part of the canonical control-plane state;
- TCP/22 has previously been reachable on both LAN and tailnet paths;
- direct Windows SSH authentication was not previously accepted by the key available there.

Acceptance gate:
1. Inspect current `sshd` state and listener.
2. Choose the canonical private SSH mode: OpenSSH over the Tailscale address and/or Tailscale SSH under tailnet policy.
3. Verify current host identity through an independent trusted channel.
4. Use key-based authentication for persistent automation.
5. Verify direct shell login from an authorized client.
6. Verify `hostname`, `uptime`, and read-only systemd status.
7. Verify recovery when LAN addressing changes but Tailscale remains connected.
8. Do not expose SSH publicly on the WAN.
9. Preserve a separate break-glass path if Tailscale control-plane access is unavailable.

### Tier 3 — Remote Desktop Commander

RDC is a direct interactive fallback, not the canonical primary path.

Role:
- quick file edits;
- interactive troubleshooting;
- GUI/session repair;
- bounded direct commands when higher-priority paths are inconvenient or broken.

Verified:
- `zen-agent-server` was restored to Online on 2026-09-30;
- `desktop-commander-remote.service` is active/running;
- direct ping, hostname, and service-status calls succeeded;
- its package runtime was repaired after a Node runtime replacement removed the current global Desktop Commander package.

Why RDC is lower priority:
- external quota/usage limits;
- it is a convenience/control product rather than the canonical Mini execution plane;
- loss of RDC must never imply loss of Mini control.

### Tier 4 — Legacy / emergency-only paths

Examples include TRIGGERcmd, historical self-hosted GitHub issue workflows, and temporary bootstrap connectors.

## Failure routing matrix

| Failure | Preferred response |
| --- | --- |
| Remote ChatGPT does not expose local MCP | Use ZEN Ops |
| ZEN Ops worker unavailable | Use Gateway SSH or Tailscale/OpenSSH |
| GitHub queue unavailable | Use zen-mini MCP locally or secure SSH plane |
| LAN address changed | Use Tailscale/private overlay |
| RDC quota exhausted/offline | Ignore RDC and use Tier 1/2 |
| GUI/ChatGPT Desktop crashed | Use ZEN Ops or SSH; repair GUI separately |
| Tailscale unavailable | Use LAN OpenSSH/Gateway if reachable |
| SSH auth broken | Use ZEN Ops or RDC to repair authorized keys |
| Visualizer/dashboard broken | No execution impact; observation layer only |

## Network failover: Wi-Fi -> mobile hotspot

Desired behavior:

```text
Primary Wi-Fi lost
 -> NetworkManager sees stored mobile-hotspot profile
 -> hotspot profile autoconnects
 -> Internet returns
 -> Tailscale reconnects
 -> ZEN Ops / Gateway / RDC recover independently
```

Configuration acceptance:
- phone hotspot SSID exists as a saved NetworkManager profile;
- autoconnect is enabled;
- autoconnect priority does not steal connectivity while the preferred network is healthy;
- Tailscale remains enabled as a boot service;
- ZEN Ops and RDC remain boot-persistent;
- no deliberate network-drop test is required unless explicitly requested.

Do not claim hotspot failover is accepted until the saved profile and autoconnect state have been read from the Mini.

## Transport invariants

1. Multiple transports may exist in parallel.
2. READ tasks may be checked through more than one path.
3. A mutating task executes through exactly one claimed transport.
4. Cross-transport retries of ambiguous mutations require authoritative proof that the first attempt did not execute.
5. High-risk operations remain bounded and auditable.
6. None of these transports bypass ZEN Safety, Preview, Human Approval, deterministic Builder, department adapter, or native readback.
7. The Living System Visualizer is observation-only and never becomes a transport or execution authority.

## Current verified snapshot

As of 2026-09-30:
- `zen-mini MCP`: ENABLED on Mini.
- `ZEN Ops`: VERIFIED end-to-end.
- `tailscaled`: ACTIVE.
- `Remote Desktop Commander / zen-agent-server`: ONLINE after repair.
- `Gateway SSH`: CONNECTOR AVAILABLE, MINI NOT YET ONBOARDED.
- `Tailscale SSH / OpenSSH`: NETWORK REACHABILITY EVIDENCE EXISTS, FINAL AUTH/ACCEPTANCE NOT YET CLOSED.
- display: HDMI-3 1920x1080, persistent 180-degree rotation.
- MA2 writes during remote-control recovery work: 0.
- MA3 writes during remote-control recovery work: 0.

## Next implementation acceptance gate

Close Tier 2 by proving both:
1. Gateway-managed SSH to Mini; and
2. direct private SSH via Tailscale/OpenSSH.

Then verify the saved mobile-hotspot profile and autoconnect policy without deliberately dropping the current network.