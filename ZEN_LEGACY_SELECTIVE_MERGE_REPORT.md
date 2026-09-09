# ZEN MA2 Agent — Legacy Selective Merge Audit

**Audit date:** 2026-09-09  
**Current source of truth:** `main` at `08d74d8362ce626e7870c0a4aca78d494ff4e0eb`  
**User-nominated current milestone:** `2f140157d6e5ecdc59f29f6531a7267f05280e16`  
**Legacy reference:** `fd1d2c37338ec770b711de0b1585a6d82f781397`  
**Test result at audit:** `161/161 PASS`

## Scope and method

This is a selective-merge audit, not a merge.  No old revision was checked out,
no runtime source was copied from the legacy revision, and no MA2 command was
sent during this audit.

Git establishes that `fd1d2c3` is an ancestor of the current `main` history:
the merge-base of the two revisions is exactly `fd1d2c3`.  The nominated
`2f14015` milestone is also an ancestor of current `main`.  Consequently,
there is no divergent legacy branch to merge.  The only valid action would be a
targeted restoration of a proven regression.  No such regression was found.

Classifications used below:

| Classification | Meaning |
| --- | --- |
| PRESERVE | Current implementation retains the hardened behavior; do not change it. |
| IMPROVED | Current implementation preserves the behavior and extends it safely. |
| ADAPT | Retain the module, but connect it to new typed schemas only through the existing core/safety boundary. |
| SUPERSEDED | A newer verified implementation replaces the old conclusion or representation. |
| RESEARCH_ONLY | Keep historical evidence, but do not use it in production paths. |

## Commit and file map

The post-legacy history adds fixture/subfixture geometry, normalization,
semantic presets, scanner/profile schemas, the typed First Song Builder, and
structured song analysis.  It also extends the bounded Lua diagnostic adapter
and the packaged test bridge.  It does not remove the legacy Telnet client,
mailbox, export providers, diagnostics, Effect Builder, Timecode Offset,
ordered clone planner, automation bridge, or safety workflow.

Important later commits include:

- `f5a3f9a` — verified Fixture Geometry Scanner
- `a76cd57` — deterministic geometry normalization
- `2f14015` — First Song Builder proof of concept
- `df384fe` — structured song analysis pipeline
- `08d74d8` — real song-analysis build verification record

## Module audit

| Module | Legacy status / evidence | Current status and evidence | Classification | Recommended action | Risk |
| --- | --- | --- | --- | --- | --- |
| Telnet transport | Real-machine hardened login state machine, blank-password login, ANSI/CRLF handling, reconnect protection, audit logging. | `telnet_client.py` retains `requested_username` and `current_session_user`; READY is only entered when the two match. `runtime.py` logs requested user without password. | PRESERVE | No merge action. Keep requested-user matching as a non-negotiable acceptance test. | High if weakened: guest/default sessions could become READY. |
| ZEN_AGENT Plugin mailbox | Direct Plugin argument callback was proven `nil`; whitespace UserVar mailbox was adopted. | Both packaged Lua copies read and clear `ZEN_AGENT_REQUEST`; `runtime.read_adapter_state()` emits `SetUserVar ...` then `Plugin <configured slot>`, serializes requests, validates slot and locks concurrent access. Plugin package tests cover it. | PRESERVE | Do not restore direct Plugin arguments or pipe-delimited mailbox input. | High: protocol regression would break verified state probes. |
| Export Coordinator | Agent-owned Group/Layout exports needed a shared lock, unique filename, freshness and XML validation. | `AgentRuntime.export_transaction()` is shared by Group, Layout, and Preset export providers. Runtime restricts filenames by export kind; providers enforce fresh mtime, non-zero/stable size, well-formed XML, diagnostics, and best-effort cleanup. | IMPROVED | Keep all future Fixture/Patch exports behind this coordinator. Do not create per-provider locks. | High: stale/wrong XML could be misattributed to current state. |
| GroupMembershipProvider | Real-machine verified `Export Group` XML parser uses `Subfixture@fix_id` and preserves selection order; a legal empty Group is empty, not malformed. | `state/providers/group_membership.py` remains present with XML stability/validation and explicit empty-membership behavior covered by tests. | PRESERVE | No restore. Keep empty-Group and sparse-ID regression tests. | High: false membership blocks clone/diagnostics safety. |
| Layout CObject provider and resolver | Verified mappings only: token `17` = preset and `22` = group; all other tokens remain unknown. Layout XML is partial. | Layout provider/resolver remains separate from fixture geometry. Current scanner explicitly publishes `layout_fixture_geometry: UNSUPPORTED` for this backend; later FixtureGeometryProvider is a different source. | ADAPT | Preserve `17`/`22` registry and unknown-token behavior. Never infer fixtures from Layout Export. | Medium: false fixture locations or false “zero fixtures.” |
| StateStore | Source, timestamp, stale/error/capability state was the common contract. | `StateStore` retains the contract and adds `fixture_geometry` without removing legacy resources. | IMPROVED | Extend only this model; do not introduce a second state cache. | Medium: split freshness/ownership semantics. |
| Show Diagnostics | SAFE deterministic findings for empty/duplicate Groups, duplicate fixtures, unresolved Layout CObjects, aggregate unlabeled pools, sequence/cue evidence, and provider health. | `diagnostics.py` and enabled `diagnostics.show` manifest remain. It reports provider error/stale/unsupported states and preserves the Layout fixture-geometry limitation rather than claiming no fixtures. | PRESERVE | Reuse `DiagnosticFinding`; enrich only with verified scanner evidence. | Low-to-medium: misleading health conclusions. |
| Effect Builder v1 | Real-machine verified, MODIFY, enabled Dimmer Chase workflow: resolve resources → free slot → preview → approval → build → `List Effect` verification; existence/label verified, parameter readback partial. | `effect_builder.py` and enabled manifest remain unchanged in responsibility. Its spec is typed, its workflow is approval-gated, it refuses overwrite/deletion, and verification remains deliberately partial. | PRESERVE | Do not delete because parameter readback is partial. | High if Designer bypasses it with raw effect commands. |
| Timecode Offset v1 | Real-machine verified positive whole-object offset, 30 FPS/10 ms representability, preview/approval, fingerprint and read-back. | `timecode_offset.py` and enabled manifest remain; bounds explicitly reject unsupported negative/event/range semantics. | PRESERVE | Reuse as the future Song workflow timecode boundary, without expanding scope. | High: unverified event-level shifts could corrupt playback. |
| Geometry Clone, ordered mode | Ordered Group membership mapping, equal-count protection, fingerprints, preview/approval; real write remained intentionally gated. | `geometry_clone.py` retains fingerprints, `ORDERED_1_TO_1`, `COUNT_MISMATCH`, and command allow-list. Manifest remains disabled until a dedicated safe real-MA2 target is verified. | ADAPT | Name this **ORDERED_GROUP_CLONE_MODE**. Retain it; add geometry-matched mode only as a future typed planner, never as a fallback write path. | High: production fixture writes. |
| Fixture Geometry, new mode | Old line concluded XYZ was unavailable from Layout Export. | Current FixtureGeometryProvider has real-machine evidence for Fixture/Subfixture PosX/Y/Z and RotX/Y/Z, mutation/read-back, normalized geometry, order/center/rows/mirror pairs, and Show Profile integration. | SUPERSEDED | Preserve current geometry implementation. | High if old unsupported claims are restored. |
| Programmer Inspect | No verified non-mutating read accessor. | Manifest remains SAFE but disabled. Fixture object-tree progress does not claim to unlock Programmer reads. | PRESERVE | Keep disabled until independent real-machine evidence exists. | High: destructive probing could alter a live programmer. |
| TEST-ONLY Desktop Automation Bridge | Explicit opt-in, localhost-only, no raw Telnet, fixed actions through `ZenDesktop.connect()`/`submit()`. | `desktop_automation.py` retains flag/env gate, loopback binding and fixed-action dispatch. Current addition exposes a read-only state snapshot only; execute still invokes the normal Desktop handler. | IMPROVED | Keep it test-only and prohibit arbitrary action IDs, commands, Python, or password readout. | High: a bypass would invalidate packaged UI proof. |
| Build identity and portable resources | Previous stale-dist and missing `gma2/plugins` regressions required build HEAD/timestamp/resource assertions. | Build identity and portable resource tests remain; packaging scripts and smoke scripts were extended for newer assets. Current source identifies the runtime build separately from source HEAD. | PRESERVE | Keep clean-build resource assertions including both ZEN_AGENT XML/Lua. | Medium: source/dist mismatch gives false verification claims. |
| Safety, approval, ownership, verification | Shared SAFE/MODIFY preview/approval, fingerprints, narrow rollback and agent-owned namespaces. | Current typed Builder and song analysis use the existing ActionPlan/WorkflowPlan path; First Song Builder uses allocated agent-owned Sequence and narrow ownership rollback. | IMPROVED | Do not create another safety layer. Extend existing action lifecycle only. | High: duplicate approval models invite bypasses. |

## Data model mapping

| Legacy model | Current counterpart | Merge policy |
| --- | --- | --- |
| `EffectSpec` | Typed effect-creation boundary | KEEP; expose it to Designer only through a resource-resolver stage. |
| `TimecodeOffsetSpec` | Future Song/Timecode adapter | KEEP; whole-object positive offsets only. |
| `GeometryCloneSpec` | `ORDERED_GROUP_CLONE_MODE`; future geometry-matched interface | EXTEND; do not replace current ordered mode. |
| `DiagnosticFinding` | Show Diagnostics and scanner-derived evidence | KEEP; do not create another health model. |
| `ActionPlan` / `WorkflowPlan` | Current Builder approval/execution lifecycle | KEEP. |
| `StateStore` | Adds geometry, semantic presets, profiles | EXTEND in place. |
| — | `ZEN_SHOW_PROFILE` | KEEP as current scanner source of truth. |
| — | semantic preset registry | KEEP; semantic target and physical geometry remain separate layers. |
| — | `ZEN_SONG_ANALYSIS` / `ZEN_SHOW_PLAN` | KEEP; Designer intent must not contain raw MA commands. |

## Integration assessments

### Effect Builder → Designer

**Readiness: PARTIAL / design-ready.**  The safe boundary already exists:
`EffectSpec` produces an approved, agent-owned, verified Effect reference.
The current First Song Builder intentionally does not compile an effect call
because effect-call grammar/read-back is not yet part of its typed plan.

The next integration must be: Designer visual intent → Effect resource resolver
→ existing verified Effect or `EffectBuilderSkill` → preview/approval → verified
effect reference → typed Show Plan.  Designer must never generate raw Effect
commands and Effect creation must never be implicit inside a cue build.

### Timecode Offset → future Song workflow

**Readiness: READY within its narrow verified scope.**  Future Song workflows
may delegate a positive whole-object offset to the existing Timecode skill.
Event-level shifts, negative offsets, and range shifts remain unsupported.

### Ordered Clone → Geometry Clone

**Readiness: PARTIAL.**  Ordered Group mapping is ready as Mode 1 and remains
safe only under its equal-count/fingerprint/approval gates.  Current physical
geometry can later produce Mode 2 (`GEOMETRY_MATCHED`) candidates, but there is
no approved Mode 2 MA write implementation.  It must not be silently selected
as a fallback.

## Explicit deny-list: legacy claims not to restore

- `Fixture XYZ = UNSUPPORTED`
- `Stage Geometry = NOT IMPLEMENTED`
- `True spatial geometry = NOT IMPLEMENTED`
- `Layout Export is the only possible geometry source`
- `fd1d2c` as source of truth
- Direct `Plugin <slot> "argument"` transport
- Pipe-delimited UserVar mailbox serialization
- Any Programmer access inferred from Fixture geometry access

These have either been disproven by newer real-machine evidence or explicitly
abandoned by real-machine protocol evidence.

## Selective restoration result

**No runtime module was restored or merged.**  The legacy revision is already
in the current history, and the full test suite found no regression that
justifies source changes.  This report is the sole audit artifact.

## Test coverage used for the audit

`python -m unittest discover -s tests -q` completed **161/161 PASS**.
The suite includes focused coverage for Group export/membership, Layout/Effect
chat behavior, Show Diagnostics, Effect Builder, Timecode Offset, Geometry
Clone, Plugin package/mailbox, portable resources, Desktop automation, Fixture
Geometry, geometry normalization, semantic presets, First Song Builder, and
structured song analysis.

## Recommended next implementation

Implement the **typed Effect Resource Resolver** for Designer/Builder:
resolve an existing compatible Effect first; if none exists, prepare a separate
`EffectSpec` preview requiring its own approval; only then return the verified
Effect reference to a Show Plan.  This reuses the hardened Effect Builder
without weakening the current Builder, transport, or safety model.

