# ZEN Antseed Integration 001

Date: 2026-09-30
Status: **CLOSED SUCCESS / LIVE MINI VERIFIED**
Host: `zen-agent-server` (Ubuntu Mini)
MA authority change: **NONE**
Paid provider authority: **NONE**

## Purpose

Add Antseed as a local, free-only inference source on the Mini without changing
ZEN's deterministic MA2 authority boundary or the operator's default model.

## Installed runtime

- Antseed CLI: `0.1.165`
- Dedicated service: `zen-antseed-buyer.service`
- Local API bind: `127.0.0.1:8377`
- Service data: `/var/lib/zen-antseed`
- OpenClaw provider id: `antseed`
- Verified OpenClaw model: `antseed/deepseek-v4-flash`

The buyer remains loopback-only. No public Antseed endpoint was created.

## Free-only policy

The live buyer was verified with:

- `routingPreferences.preferFreePeers = true`
- `routingPreferences.minTrustScore = 0`
- `maxPricing.defaults.inputUsdPerMillion = 0`
- `maxPricing.defaults.outputUsdPerMillion = 0`
- settlement/payment path disabled by the ZEN service environment

This means the ZEN integration must fail closed rather than route to a priced
offer.

## Verification

### Buyer/catalog

The install acceptance returned:

- service active
- `GET /v1/models` PASS
- 269 catalog entries at that observation
- `deepseek-v4-flash` present
- `glm-5.3-flash` was present in the install-time catalog

The Antseed catalog is dynamic. A model observed once must not be treated as
permanently available.

### Direct inference

A free-route request to the local OpenAI-compatible chat-completions endpoint
returned successfully for `deepseek-v4-flash`.

### OpenClaw integration

OpenClaw 2026.9.4 was configured with:

- base URL `http://127.0.0.1:8377/v1`
- bearer-header auth using the local non-secret placeholder key
- API mode `openai-completions`
- model `deepseek-v4-flash`
- Antseed model added to the visible model catalog
- existing default model left unchanged

OpenClaw reported that no gateway restart was required.

End-to-end acceptance:

```text
OpenClaw infer model run
  -> provider: antseed
  -> model: deepseek-v4-flash
  -> text output: OK
  -> PASS
```

## Operations path

After the owner correction, Mini changes and verification used the repository
ZEN Ops control plane:

```text
GitHub zen-ops-control
  -> zen-ops-worker
  -> allowlisted repo_task / protected one-shot helper
  -> sanitized result receipt
```

Remote Desktop Commander is not part of this integration path.

Because `zen-ops-worker.service` intentionally has `ProtectHome=true`,
OpenClaw configuration under root's home is modified only through a bounded
temporary systemd one-shot helper with `ProtectHome=false`. The worker itself
does not gain general access to root home.

## Safety / authority

Antseed is inference infrastructure only.

It does not receive:

- raw MA2 command authority
- ZEN approval authority
- Builder authority
- write authority over MA objects
- payment authority

Normal ZEN Preview / Approval / deterministic Builder / native readback
boundaries remain unchanged.

## Separate runtime drift discovered

OpenClaw config validation currently reports:

```text
plugins.entries.zen-ma2: plugin disabled (disabled in config) but config is present
```

This was **not changed by the Antseed task**. It is a separate OpenClaw/ZEN
runtime-state drift because the committed project evidence contains prior live
acceptance of the `zen-ma2` OpenClaw plugin. Resolve it as a separate bounded
runtime repair rather than hiding it inside provider installation.
