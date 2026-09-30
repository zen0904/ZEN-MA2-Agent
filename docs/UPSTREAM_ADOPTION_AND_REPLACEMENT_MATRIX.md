# Upstream Adoption and Replacement Matrix

Status: **OWNER-APPROVED / MINI-FIRST / ADOPT-ALL-USEFUL-UPSTREAM**

Date: 2026-09-29

## Owner direction

Every useful mature upstream identified by the reuse audit is approved for
adoption. The Mini is the mandatory first installation/integration point.

If a tool benefits from local workstation resources (REAPER session, audio I/O,
GPU, measurement interface, etc.), install it on the Mini **and** add a second
execution node on the relevant workstation. Workstation placement never means
"not on Mini".

When upstream functionality overlaps weaker custom ZEN code, upstream becomes
the preferred implementation after parity/safety verification. The custom
implementation is then removed or reduced to a thin ZEN-specific adapter.

Do not turn "adopt all" into "run all daemons forever". Use always-on,
on-demand, client-only, or reference mode according to the tool.
## Agent / model / tool fabric

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| OpenClaw native MCP | PRIMARY | optional clients | custom OpenClaw ZEN TS plugin |
| MCP Python SDK | PRIMARY | as needed | custom tool transport |
| ACP | PRIMARY | coding workstations | custom coding-agent protocols |
| codex-acp | PRIMARY | coding workstations | Codex-specific glue |
| Gemini CLI ACP | PRIMARY | coding workstations | Gemini-specific glue |
| OpenClaw model.run/provider routing | PRIMARY candidate | no | ProviderRouter transport/auth/fallback |
| LiteLLM | INSTALLED/ON_DEMAND | optional | non-OpenClaw gateway gaps |
| Docker MCP Gateway | INSTALLED/ON_DEMAND | optional | multi-client MCP lifecycle/isolation gaps |
| Supergateway | INSTALLED/ON_DEMAND | optional | MCP transport conversion |
| Codebase Memory MCP | PRIMARY | optional | repeated repo structural rescans |
| Basic Memory | INSTALLED/ON_DEMAND | optional | generic cross-agent note memory |
| Beads | INSTALLED/ON_DEMAND | coding workstations | generic task/dependency graph tracking |
## Operations / persistence

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| Glances + MCP | PRIMARY telemetry | useful on workstations | generic host_metrics collection |
| systemd | PRIMARY supervisor | Linux hosts | custom restart/supervision loops |
| restic | PRIMARY backup engine | useful on workstations | ad-hoc backup scripts/manual copying |

ZEN retains only the semantic projection it uniquely needs, such as mapping
health into ONLINE/DEGRADED/OFFLINE and preserving MA-specific invariants.

## Knowledge / ingestion

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| MarkItDown | PRIMARY fast parser | optional | generic document conversion |
| Docling / Docling MCP | ON_DEMAND rich parser | optional | complex PDF/layout/OCR parsing |
| Crawl4AI | ON_DEMAND crawler | optional | generic web extraction |

ZEN keeps provenance, evidence classification, copyright-safe derived records,
promotion/review policy and design applicability. It does not own low-level
document/browser parsing.
## Show-control / lighting protocol

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| MIDIMonster | PRIMARY protocol lab/router | useful on show PCs | generic Art-Net/sACN/OSC/MIDI routing |
| OLA | INSTALLED/ON_DEMAND | useful on show PCs | generic DMX-over-IP/RDM transport |
| rtpmidid | INSTALLED/ON_DEMAND | Mac/Linux show hosts | custom RTP-MIDI plumbing |
| libltc + ltc-tools | PRIMARY utilities | playback hosts | custom LTC/MTC plumbing |
| Chataigne | INSTALLED/ON_DEMAND | show workstation | generic interactive show routing experiments |
| ossia score | INSTALLED/ON_DEMAND | show workstation | generic show timeline experiments |
| grandMA2 Hub | CLONED/INDEXED | optional | implementation/reference only |
| gma2-plugins | CLONED/INDEXED | optional | MA2 Lua/plugin reference |
| MA2 API/Lua docs repos | CLONED/INDEXED | optional | MA2 API research corpus |

No upstream protocol tool becomes a second MA programming authority. ZEN
Builder/Preview/Approval/protected-object/native-readback boundaries remain.
## Media / lighting-reference analysis

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| Essentia | ON_DEMAND analysis | audio workstation optional | generic MIR/DSP extraction |
| PySceneDetect | ON_DEMAND analysis | video workstation optional | generic shot/cut detection |

These produce evidence, not artistic rules. A camera cut is not a lighting cue,
and a detected chorus/onset is not an instruction to fire a chase.

## Audio / REAPER / network audio

| Upstream | Mini role | Extra host copy | Replacement target |
| --- | --- | --- | --- |
| danishaft/reaper-mcp | INSTALLED/client-ready | REAPER host required for live project control | generic safe REAPER control glue |
| dschuler36/reaper-mcp-server | INSTALLED/client-ready | REAPER host required for live project readback | custom RPP/read-only analysis glue |
| Open Sound Meter | INSTALLED/reference/API client | measurement workstation for live I/O | custom measurement parsing |
| AES67 Stream Monitor | INSTALLED/ON_DEMAND | AoIP workstation optional | generic AES67 stream monitoring |
| AVB / TSN Linux stack | INSTALLED / DIAGNOSTIC | future AVB-capable host/NIC | generic gPTP/AVTP discovery and transport experiments |

Mini remains the orchestration point even when execution must occur next to a
local DAW, interface or measurement device.
## Replacement order

1. OpenClaw ZEN TypeScript plugin -> native MCP. **Verified replacement candidate.**
2. ProviderRouter generic transport/auth/fallback -> dedicated OpenClaw
   `zen-designer` route. Keep only ZEN policy/evidence/artistic contract.
3. host_metrics generic collection -> Glances; retain thin semantic adapter.
4. unfinished Worker API/registry -> standard model runtimes + provider health
   + Glances/systemd health where parity is sufficient.
5. generic document/web/media parsing -> MarkItDown/Docling/Crawl4AI/
   Essentia/PySceneDetect.
6. generic protocol plumbing -> MIDIMonster/OLA/rtpmidid/libltc.
7. REAPER generic control/readback -> upstream REAPER MCP tools.

## Deletion gate

Custom code is deleted/reduced only after:
- reproducible installation/version pin;
- parity tests;
- equal-or-narrower authority;
- understood failure mode;
- rollback path;
- no unapproved operator-workflow change.

The objective is fewer custom moving parts and more time spent on ZEN's actual
differentiators: lighting design intelligence, current-show resource reasoning,
spatial design, deterministic MA2 building, Preview/Approval and native readback.


## Verified Mini runtime snapshot — 2026-09-29

The following state was verified on `zen-agent-server`. Installed does not mean
always-on; heavyweight or GUI components remain on-demand unless stated.

| Component | Verified state |
| --- | --- |
| ZEN native MCP | PRIMARY; 14 ZEN tools; 0 diagnostics; legacy TS plugin disabled |
| Glances 4.5.7 | ACTIVE loopback systemd telemetry; REST API healthy; MCP SSE connected with 0 diagnostics |
| MarkItDown 0.1.8 | INSTALLED; OpenClaw MCP connected; conversion tool available |
| Docling MCP 3.2.1 | INSTALLED; OpenClaw MCP connected; 20 tools; 0 diagnostics |
| Basic Memory 0.23.2 | INSTALLED; OpenClaw MCP connected; 21 tools; 0 diagnostics |
| Codebase Memory MCP 0.11.0 | INSTALLED portable; OpenClaw MCP connected; 17 tools; 0 diagnostics |
| ZEN Codebase Memory index | READY; 7,627 nodes / 29,707 edges; 15.20 s initial index; parse partial/unusable = 0 |
| Crawl4AI 0.9.4 | INSTALLED with Playwright runtime; doctor real-crawl PASS; use library/CLI on demand while upstream self-host server/MCP remains in transition |
| LiteLLM 1.103.0 | INSTALLED / ON_DEMAND; not primary ZEN routing layer |
| Essentia 2.1-beta6-dev | INSTALLED; `RhythmExtractor2013` import PASS |
| PySceneDetect 0.7.1 | INSTALLED; CLI/version PASS; ffmpeg available |
| restic 0.16.4 | INSTALLED; backup repository intentionally not invented without a real destination |
| Docker 29.1.3 | INSTALLED; service disabled/inactive by design |
| Docker MCP Gateway 0.44.1 | INSTALLED Docker CLI plugin / ON_DEMAND |
| Supergateway 4.0.0 | INSTALLED / ON_DEMAND |
| codex-acp 2.0.0 | INSTALLED |
| Gemini CLI 0.61.0 | INSTALLED; native `--acp` confirmed |
| Beads 1.3.0 | INSTALLED only; `bd init` not run because it would alter repo workflow/hooks |
| OLA 0.10.9 | INSTALLED / ON_DEMAND |
| libltc 1.3.2 + ltc-tools | INSTALLED; `ltcgen`, `ltcdump`, `jltc2mtc`, `jltctrigger` available |
| MIDIMonster 0.7-dist | FULL build installed with Art-Net, sACN, OSC, MIDI, RTP-MIDI, MQTT, MA Web, OLA, JACK, Lua/Python and related backends |
| rtpmidid | BUILT/INSTALLED from source; CLI smoke PASS; daemon not enabled by default |
| Chataigne 1.10.4 | AppImage INSTALLED / ON_DEMAND; GUI execution requires graphical session |
| Open Sound Meter 1.5.2 | AppImage INSTALLED / ON_DEMAND; live measurement requires appropriate local audio I/O |
| ossia score 3.8.2 | AppImage INSTALLED / ON_DEMAND; GUI execution requires graphical session |
| AES67 Stream Monitor 1.0.0-beta2 | Debian package INSTALLED / ON_DEMAND |
| danishaft/reaper-mcp 0.1.0 | INSTALLED on Mini; second copy required on live REAPER host for local session control |
| reaper-mcp-server 0.1.0 | INSTALLED on Mini; second copy required on live REAPER host for local project/readback access |
| MA2 reference corpus | `grandma2-hub`, `gma2-plugins`, GrandMA2 API docs, Lua ldoc and Ma2-API cloned on Mini as REFERENCE only |
| ZEN Sentinel | ACTIVE deterministic monitor; ~6.5 MB observed RAM; no model calls; writes /run/zen-sentinel/state.json |
| ZEN console MA view | ACTIVE; tmux MONITOR + MA_AGENT windows; F12 toggle and zen-console-mode command |
| AVB/TSN tools | linuxptp, libavtp, Avahi installed; OpenAvnu/libavtp reference cloned; built-in BCM57766/tg3 has no exposed PHC under Ubuntu and is not accepted as a production AVB endpoint |
| GitHub self-hosted runner | v2.337.0 package downloaded and checksum-verified; allowlisted repo workflow/dispatcher committed; registration remains blocked only by the one-time repository runner registration token |

### Replacement status

- **Completed:** custom OpenClaw ZEN TypeScript tool surface -> native MCP primary path.
- **In progress / blocked by provider acceptance:** generic `ProviderRouter` transport/auth/fallback -> dedicated OpenClaw `zen-designer` infrastructure. Do not delete the existing router yet.
- **Candidate after parity:** generic host metric collection -> Glances plus a thin ZEN semantic projection.
- **Candidate after parity:** unfinished remote Worker API/registry -> standard model runtimes/provider health plus systemd/Glances.
- **Adopted upstream instead of new custom implementation:** document parsing, crawling, MIR/DSP, scene detection, LTC, RTP-MIDI and generic Art-Net/sACN/OSC/MIDI routing.

### Explicit non-adoptions

- No external framework becomes ZEN product authority or the ordinary artistic brain.
- No upstream protocol tool gets raw MA programming authority.
- No permanent multi-agent committee is introduced for ordinary song programming.
- No Docker/Crawl4AI/LiteLLM/Supergateway daemon is kept running merely because the package is installed.
- No Beads repo initialization is performed without a separate workflow decision.
- No restic destination or secret is fabricated when no real backup destination has been selected.

## Primary remote execution plane

The Mini no longer depends on Remote Desktop Commander as its normal maintenance
transport.

Primary machine-operation path:

```text
ChatGPT / GitHub connector
        ↓
zen-ops-control branch
        ↓
ZEN Ops Worker on Mini
        ↓
typed job execution
        ↓
persistent result JSON
        ↓
Tailscale Funnel read-only result plane
```

The control branch is writable only through GitHub repository permissions. The
worker polls only that exact branch and does not execute PR content or arbitrary
public Issue text. Normal shell jobs run as the unprivileged `zenops` account;
root maintenance remains typed. The Ops plane is not an MA2 write authority and
must not bypass ZEN Compiler / Preview / Approval / Builder boundaries.

The worker runs from an independent `/opt/zen/zen-ops-runtime` clone and a
systemd timer updates it from `main` every 60 seconds. Therefore future
maintenance capabilities can be deployed without using Remote Desktop Commander.

Tailscale SSH and MeshCentral remain the direct human/RMM control surfaces.
Remote Desktop Commander is fallback-only for ChatGPT-native GUI/visual or
emergency access.

## Architecture-only reference: THE ARC

`jasontzeng123/the-arc` is recorded as an **ARCHITECTURE REFERENCE ONLY**, not as a ZEN runtime dependency. See `docs/THE_ARC_ARCHITECTURE_ADOPTION_REVIEW_001.md`.

Keep/adapt: canonical shared semantic timeline, beat/bar clock concepts, Scene World + Event Layer separation, deterministic state resolution, and reproducible shared event timing. Do not adopt as ZEN Core: three.js/WebGL, browser/Playwright frame rendering, the film-scene runtime, fixed-BPM assumptions, or any alternate MA programming authority. The existing ZEN Compiler, Builder, Preview, Approval, and verification boundaries stay unchanged.
