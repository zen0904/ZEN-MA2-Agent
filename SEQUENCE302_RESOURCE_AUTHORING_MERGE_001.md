# Sequence 302 Resource Authoring Merge 001

Status: OFFLINE_HARDENED, FRESH PREVIEW/APPROVAL REQUIRED

## Scope

This is a deliberately narrow integrated transaction for the current operator request:

- existing Sequence `302`, Cues `1-29` only;
- exact Group `1` membership `101.1-108.1` only;
- create new Agent-owned Position Presets from the explicit raw PAN/TILT matrices in `data/sequence302_resource_merge_raw_plan.json`;
- create Effects `2500-2502` only when fresh evidence proves all three pool identities absent and all three line contents empty;
- use only the proven no-selection template-Effect syntax and require show-bound Group 1 `Dim` applicability plus content-verified `At Effect <id>` Cue application grammar;
- apply Position Presets and Effects only with `Store Cue ... Sequence 302 /merge /cueonly /nc`;
- never allocate or assign a Sequence/Executor and never touch Fixture `9999`;
- reject Actions `97d3a82f1220` and `a9dd416ef92b` as legacy replay sources.

Names are identity checks only. Effect content is accepted only from fresh Effect-line `QTY` evidence plus the `Dim` attribute. Position Preset content is accepted only when a post-write native Sequence Export contains the approved raw PAN/TILT values and Position Preset references for every exact Group member.

## Approval boundary

`build_sequence302_resource_merge_preview()` is pure and sends no commands. `AgentCore.preview_sequence302_resource_merge()` validates the artifact and queues it through the normal `ActionRecord` Preview/Approval path. It does not approve or execute.

At approval time, AgentCore re-exports Sequence 302, re-reads Cue metadata, the complete Sequence 302 Executor assignment identity, Group membership, Position Preset targets, and each reserved Effect 2500-2502 through direct pool plus Effect-line reads. Any drift rejects the approved Preview before a write. Execution stops on the first rejected command or failed resource readback. Each Position Preset identity is read immediately after creation. Each Effect is read immediately after labeling and must show nonempty explicit `QTY=None` template evidence and `Dim` content before any Cue application is reached.

After the merge, one retained native Sequence Export verifies:

- all `29 * 8 * 2 = 464` raw PAN/TILT values;
- the expected Position Preset identity on every exact fixture row;
- the exact expected Effect identity set on every target fixture row;
- all unrelated CueData unchanged;
- Cue metadata unchanged.

No automatic deletion or rollback command is generated.

## Generate a live Preview

A live Preview must be generated inside the running Field Core process so the same connected runtime owns the fresh reads and Action registration. After deploying this commit and restarting Field Core:

1. Fresh-export Sequence 302 and collect exact Cue labels for Cues 1-29.
2. Fresh-read Group 1 and require exact ordered refs `101.1-108.1`.
3. Expand `data/sequence302_resource_merge_raw_plan.json` with `expand_explicit_raw_plan(artifact, fresh_cue_labels)`. The artifact supplies raw values; fresh native state supplies labels.
4. Fresh-read all Position Presets and prove every proposed `2.x` identity is absent.
5. Fresh-read Effect pool identities `2500-2502` and each `List Effect 1.<id>.*`; require explicit absent pool identity and empty line content for every ID. A matching or attractive label is not evidence.
6. Supply show-bound Group 1 exact-member `Dim` applicability and the persisted `REAL_MACHINE_CONTENT_VERIFIED / AT_EFFECT_POOL_CALL` capability.
7. Call `AgentCore.preview_sequence302_resource_merge(...)` with those fresh artifacts. It returns a new Action ID in `PENDING_APPROVAL`, with `ma2_writes=0`.
8. Inspect the Action through the existing `zen.preview` path. Do not use either legacy Action ID.
9. Only the operator may explicitly approve the new exact Action. Approval-time revalidation runs again before any write.

The current already-running Field Core loaded the pre-change Python modules, so this integration cannot safely register the new Preview without a restart. No live Preview was created during implementation.

## Tests

Focused:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_sequence302_resource_merge.py -q
```

Authoritative Windows suite:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

## Convergence hardening

The mainline convergence pass added two approval-time fail-closed gates that were missing from the original implementation:

- Executor ownership/assignment for Sequence 302 is re-read and must exactly match the approved Preview;
- Effects 2500-2502 are each re-read directly (`List Effect <id>` plus `List Effect 1.<id>.*`) so a generic pool listing cannot hide newly occupied or populated content.

The shared preservation verifier also now uses exact fixture/subfixture channel identities, verifies Effect attribute families, and protects Position-family changes on unrelated fixtures.

Authoritative converged Windows suite: `954 tests / OK`.

`MA2_WRITES_DURING_CONVERGENCE=0`.
