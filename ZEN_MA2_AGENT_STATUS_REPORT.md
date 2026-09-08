# ZEN MA2 Agent Status Report

Assessment date: 2026-09-08

Assessment implementation HEAD: `0a1a56cf4c2de7d1e2401848afcb59ecff52d7ad`

This report is based on source code, the runnable test suite, packaged EXE
smokes, Git history, and actual command allow-lists. No grandMA2 Show, Patch,
Fixture Type, Cue, Group, or Programmer was changed during this assessment.

## 1 Repository State

- Branch: `main`
- Assessment HEAD: `0a1a56c` - Add read-only show scanner and fixture draft POC
- Working tree before this report: clean except build-log artifacts removed by the assessment workflow.
- Runtime entry point: `main.py`
- Core package: `zen_ma2_agent/`
- Dependencies: PySide6 6.8.3, FastAPI/Uvicorn, qrcode.
- Portable bundle: `dist/ZEN_MA2_Agent/ZEN_MA2_Agent.exe`; the current build identity matches the assessment HEAD.

Important directories:

| Directory | Actual role |
| --- | --- |
| `zen_ma2_agent/` | AgentCore, Telnet runtime, state providers, workflows, desktop/mobile UI |
| `skills/builtin/` | Manifest-controlled workflow skills; only built-ins are executable |
| `gma2/plugins/` | grandMA2 3.9 XML/Lua import package for the read-only adapter |
| `web/` | paired LAN PWA assets |
| `scripts/` | portable build, fake packaged smoke, and explicit real-machine verifier scripts |
| `tests/` | 124 automated unit/integration-style tests using fake transports and temporary files |
| `scanner/`, `designer/`, `builder/`, `fixture_profiler/` under `zen_ma2_agent/` | new draft-only/read-only PoC modules |

Recent significant commits: Geometry Clone preview and isolated-test support (`ae35a1a` through `abe9a4a`), Timecode Offset v1 (`8156746` through `a7aeb0d`), and the scanner/fixture-draft PoC (`0a1a56c`).

## 2 Current Architecture

The real control path is:

```text
PySide6 Desktop or paired Phone PWA
  -> AgentCore.handle_request
  -> IntentRouter and deterministic parser
  -> SkillRegistry / typed WorkflowPlan
  -> preview + approval gate + verification strategy
  -> AgentRuntime
  -> MA2TelnetClient
```

`AgentRuntime.read_state()` accepts only an allow-list of `List` commands. Export-backed providers may use only Agent-owned temporary filenames for `Export Group` and `Export Layout`. Write-capable skills only receive commands from an already-approved `WorkflowPlan`; they never receive the Telnet client. Mobile HTTP/WebSocket calls the same `AgentCore`, not a separate control path.

`StateStore` is the shared read model. It records values, source, timestamp, stale status, error, and capability metadata. It currently contains Groups, Fixtures, ordered Group membership, Layouts, Layout CObjects, Presets, Effects, Sequences, Cues, Pages, Executors, Timecodes, Selection, and Programmer state.

Rollback is metadata/advice only. There is no generic automatic rollback executor. This is important for all future Builder work.

## 3 What Actually Works

The following have executable code paths and passing automated coverage:

- Connection settings, blank-password login, requested-user matching, ANSI/CRLF handling, reconnect protection, password non-persistence, and audit logging.
- Shared desktop/mobile state, pairing-protected LAN API and WebSocket events.
- SAFE state inventory: Groups, Fixtures, Layout inventory, Preset inventory, Effect inventory, Sequence/Cue metadata, Pages, Executors, and Timecode inventory.
- Ordered Group membership through a local onPC `Export Group` XML transaction. The XML parser preserves sparse Fixture IDs and native selection order.
- Layout CObject Export XML parsing with two explicitly validated token mappings: `17 -> CMD_PRESET -> preset` and `22 -> CMD_GROUP -> group`. Fixture geometry is deliberately not claimed.
- Show Diagnostics v1 deterministic findings, including stale/error capability handling.
- Effect Builder v1 only for a narrow Dimmer Chase workflow, with Preview, approval, label/pool partial verification, and a suggested manual rollback.
- Timecode Offset v1 only for a verified positive whole-show offset, with fingerprint refresh and partial/verified read-back depending on the list output.
- Geometry Clone ordered Group mapping and Preview. The normal skill remains disabled; its native write flow has not passed a real isolated-show write verification.
- Portable packaging includes Qt runtime, web/lua/skills/config/gma2 resources and has passing fake-transport packaged smokes.

## 4 Partially Implemented

| Capability | Actual limit |
| --- | --- |
| Fixture inventory | `List Fixture` returns number, label, and an optional textual type only. No Fixture Type structure or patch model. |
| Group membership | Supported locally through Export XML, but blocked on remote consoles without import/export filesystem access. |
| Layout | Exported CObjects with XY/size/rotation may be parsed; real MA2 export is known to omit visible Fixture elements, so fixture geometry is unsupported. |
| Presets | Pool/type/name inventory only; no stored values, fixture applicability, or raw/physical values. |
| Effects | Pool/name and occasional list metadata only; no line parameter reader. |
| Cues | Number/name and text-parsed trigger/fade/delay only; no stored values, preset/effect calls, tracking, or MIB. |
| Executors | Inventory and visible assignment parsing only. |
| Lua plugin | Package, UserVar mailbox, and bounded diagnostic/probe code exist; no general object-tree or Fixture Type provider consumes it. |
| Effect Builder | Write path has fake packaged approval coverage but only partial read-back. |
| Timecode Offset | Narrow, documented whole-show positive offset only. |
| Geometry Clone | Deterministic mapping + Preview are present, but normal write execution is intentionally disabled pending the isolated real-machine verifier. |

## 5 Not Implemented or Blocked

- Fixture Type, module, instance, attribute, DMX channel, Channel Function, Channel Set, wheel, slot, coarse/fine, and physical value providers.
- Fixture Type creation, clone, edit, export, or import.
- Fixture Stage XYZ, fixture rotation, per-fixture Pan/Tilt, and fixture-level Layout geometry.
- Preset content/value inspection, including semantic Position Preset Pan/Tilt expansion.
- Effect lines/form/low/high/speed/phase/groups/blocks/wings reader.
- MAtricks reader/writer.
- Cue stored values, tracking, MIB, effect/preset call reader, or Cue builder.
- A showfile parser/decompiler. Existing showfile research is not a provider.
- CSV import/export.
- Automatic rollback.
- Any automatic inference of DMX range boundaries or coarse/fine relationships.

## 6 Test Results

| Validation | Result | Evidence |
| --- | --- | --- |
| Full automated suite | PASS - 124/124 | `python -m unittest discover -s tests -v` |
| Portable chat routing smoke | PASS | packaged PySide6 path, fake MA2 transport |
| Portable Effect approval smoke | PASS | Preview/approval and explicitly PARTIAL verification contract |
| Portable Timecode approval smoke | PASS | fake MA2 transport, guarded offset contract |
| Portable process smoke | PASS | EXE stayed alive for five seconds |
| Real MA2 hardware integration | NOT RUN this round | verifier scripts require explicit `--real-machine`; the assessment made no real connection |

There are no skipped tests in the `unittest` run. The only non-failing warning is FastAPI/Starlette's deprecation warning about the installed `httpx` import path. It does not change test assertions. A packaged Effect smoke initially failed because it expected the obsolete word `VERIFIED`; source and unit tests correctly define Effect parameter read-back as `PARTIAL`. The smoke assertion was tightened to require `PARTIAL` plus a matching label instead of being weakened.

## 7 MA2 Read Capability Matrix

Status meanings: **SUPPORTED** = implemented provider and automated evidence; **PARTIAL** = implemented but only a restricted subset; **UNVERIFIED** = diagnostic/manual code but not a normal provider; **NOT_IMPLEMENTED** = absent; **BLOCKED** = intentionally denied without a verified safe source.

| Read item | Status | Module / code path | Evidence and limit |
| --- | --- | --- | --- |
| Fixture ID and name | SUPPORTED | `FixtureProvider -> List Fixture` | parser/provider tests |
| Fixture Type name | PARTIAL | `FixtureProvider` optional parenthetical text | no Type structure |
| Fixture Type modules/attributes/DMX mapping | NOT_IMPLEMENTED | none | no provider or parser |
| Coarse/fine, Channel Function, Channel Set, Wheels, Instances | NOT_IMPLEMENTED | none | no evidence source integrated |
| Fixture Stage XYZ / rotation | BLOCKED | `LayoutFixtureProvider` | known unavailable from current export/object-tree sources |
| Fixture Pan/Tilt capability | NOT_IMPLEMENTED | none | no per-fixture attribute provider |
| Group ID/name | SUPPORTED | `GroupProvider -> List Group` | parser tests |
| Group Fixture order | SUPPORTED locally | `ExportFileGroupMembershipProvider` | native `Subfixture@fix_id` order preserved; remote filesystem unavailable |
| Attribute inventory | NOT_IMPLEMENTED | none | Effect list attributes are not Fixture attributes |
| Preset pool/type/name | PARTIAL | `PresetProvider -> List Preset <type>` | no content/value reader |
| Preset raw/decimal/physical values | UNVERIFIED | `PresetExportProvider -> Export Preset <type.id>` | guarded local-onPC acquisition and XML schema discovery implemented; no real MA2 3.9 sample or value parser yet |
| Position/Color/Gobo/Beam/Dimmer Presets | PARTIAL | `PresetProvider`, `PresetExportProvider` | inventory available; content export transport is local-onPC only and schema-unverified |
| Effect ID/name/basic kind/attributes | PARTIAL | `EffectProvider -> List Effect` | only fields emitted by List output |
| Effect lines/form/low/high/speed/speed group/phase/groups/blocks/wings | NOT_IMPLEMENTED | none | no line inspector |
| Absolute/relative/selective/template | PARTIAL | `EffectProvider` | only if visible List metadata says it |
| Sequence inventory | SUPPORTED | `SequenceProvider -> List Sequence` | parser tests |
| Cue ID/name/trigger/fade/delay | PARTIAL | `CueProvider -> List Cue <sequence>` | text parser, no stored data |
| Cue values/preset/effect calls/tracking/MIB | NOT_IMPLEMENTED | none | no safe reader |
| Executor assignment | PARTIAL | `ExecutorProvider -> List Executor` | only visible textual assignment |
| Page inventory | SUPPORTED | `PageProvider -> List Page` | parser tests |
| MAtricks | NOT_IMPLEMENTED | none | no reader or writer |
| Layout CObjects | PARTIAL | `LayoutExportProvider -> Export Layout XML` | CObjects only; 17/22 validated mapping |
| Layout fixture geometry | BLOCKED | `LayoutFixtureProvider` | actual export omitted a visible Fixture; no false empty result |
| Command feedback | SUPPORTED | `MA2TelnetClient`, runtime audit | connection/ANSI/CRLF tests; hardware not run this round |
| MA2 object tree | UNVERIFIED | bundled Lua probe only | diagnostic plugin code exists but no normal data provider |

## 8 MA2 Write Capability Matrix

| Write item | Status | Module / constraints |
| --- | --- | --- |
| Fixture selection | PARTIAL | deterministic `Fixture first Thru last` parser/workflow; no current hardware run |
| Group selection | PARTIAL | deterministic Group command workflow; no current hardware run |
| Attribute value | PARTIAL | only group dimmer `At <level>` intent; not general fixture attributes |
| Preset calls / creation | NOT_IMPLEMENTED | no workflow |
| Sequence/Cue creation or editing | NOT_IMPLEMENTED | only `Go Sequence` exists |
| Effect creation | PARTIAL | Dimmer Chase only; approval-gated and partially verified |
| Executor write | NOT_IMPLEMENTED | no workflow |
| MAtricks write | NOT_IMPLEMENTED | no workflow |
| Fixture Clone | PARTIAL | deterministic pair commands exist; normal skill disabled pending real isolated test |
| Stage/Position write | NOT_IMPLEMENTED | Auto Position is a disabled placeholder |
| Fixture Type / Channel Function / Channel Set write | NOT_IMPLEMENTED | no commands, no builder, no draft apply |
| Fixture Type export | NOT_IMPLEMENTED | no schema or export path |
| Lua Plugin package | PARTIAL | import XML/Lua is bundled and unit-tested; runtime data protocol remains narrow/read-only |

## 9 Scanner Feasibility

The best current hybrid Scanner backends are:

| Scanner subject | Best current backend | Readiness |
| --- | --- | --- |
| Fixtures | Telnet `List Fixture` | inventory only |
| Groups and selection order | Telnet `List Group` + local `Export Group` XML | ready locally |
| Layout CObjects | local `Export Layout` XML | partial; not fixture geometry |
| Preset inventory | Telnet `List Preset <type>` | names/type only |
| Effects inventory | Telnet `List Effect` | basic metadata only |
| Sequence/Cue inventory | Telnet `List Sequence` / `List Cue` | metadata only |
| Page/Executor | Telnet `List Page` / `List Executor` | partial assignment parsing |
| Fixture Type / DMX details | candidate: Fixture Type export XML or verified Lua/object API | no implementation/evidence path yet |
| Stage XYZ / Rotation | candidate: a verified MA2 geometry source | currently blocked |
| Position Preset Pan/Tilt | `PresetExportProvider` candidate | BLOCKED pending a retained real 3.9 XML sample proving Fixture/Attribute/value identity |
| Effect parameters | candidate: effect export/List report/object API | currently not implemented |

The new `ShowScanner` exports only existing `StateStore` evidence as `zen.show_profile.v0.1`. It does not itself refresh state; callers first use existing allow-listed providers. It preserves Group order, resource timestamps/source/capabilities, and writes unavailable fields instead of fabricating values.

## 10 Scanner PoC Readiness

For **one Fixture + five/six Position Presets + one Effect**, the answer is **PARTIAL**:

- Fixture ID/name and optional textual Fixture Type: available.
- Position Preset pool names/types: available.
- Effect ID/name and occasional top-level metadata: available.
- Fixture Stage XYZ, rotation, HOME/LEFT/CENTER/RIGHT/UP/DOWN Pan/Tilt, Preset raw values, and Effect line parameters: not yet proven. The guarded local-onPC `Export Preset` transport can now acquire a sample, but its XML schema intentionally remains unparsed until a real sample is retained.

The resulting profile is useful as an inventory/capability report, not yet as a semantic aiming or effect-parameter model.

## 11 Fixture Profiler Feasibility

The new `FixtureProfiler` is deliberately a **draft-only evidence normalizer**. Given structured observations such as `Fixture 101, COLOR_RED, COLOR1, observed_dmx 37, VERIFIED_PRESET`, it emits `zen.fixture_profile_draft.v0.1` and channel-set candidates with:

- `observed_dmx: 37`
- `range: UNKNOWN`
- explicit evidence and confidence
- `coarse_fine_relation: UNVERIFIED_FINE_MAPPING` unless evidence supplies a verified relation.

It cannot yet collect those raw observations from MA2. The new `PresetExportProvider` is a local-onPC, read-only schema-discovery transport; it refuses to invent an observation from unknown XML. It also cannot edit or export a Fixture Type.

## 12 Fixture Profiler Capability Matrix

| Profiler item | Status | Evidence |
| --- | --- | --- |
| Preset name extraction | PARTIAL | pool name from `PresetProvider`; observation input accepts name |
| Attribute extraction | NOT_IMPLEMENTED automatically | accepted only in structured evidence input |
| Raw DMX extraction | UNVERIFIED | Preset Export acquisition exists; no verified XML field mapping |
| Decimal16 extraction | UNVERIFIED automatically | no real XML field mapping; schema accepts a supplied integer only |
| Coarse/fine relation | BLOCKED_BY_EVIDENCE_POLICY | defaults to `UNVERIFIED_FINE_MAPPING` |
| Current channel mapping | NOT_IMPLEMENTED | no Fixture Type reader |
| Channel Function / Channel Set draft | PARTIAL | draft candidate aggregation only |
| Range inference | BLOCKED | explicitly remains `UNKNOWN` |
| Physical values | NOT_IMPLEMENTED | no source |
| Wheels / slots / prism metadata | NOT_IMPLEMENTED | no source |
| Fixture Type clone / creation / export | NOT_IMPLEMENTED | no write or XML builder |

## 13 Fixture Profiler PoC Readiness

For **one Fixture + three to five named Presets**, automatic observation capture without copying values is **BLOCKED_PENDING_REAL_SAMPLE**. The prerequisite transport is now available locally, but one real MA2 3.9 export must prove Fixture/Attribute/raw-value fields before it can emit an observation.

The present milestone is still useful: once such records have a verified source, the draft generator already preserves evidence, confidence, unknown ranges, and fine-channel uncertainty without a production Fixture Type mutation.

## 14 Proposed Integration

Keep all four modules within `zen_ma2_agent/` and use existing core ownership:

```text
existing read-only providers -> StateStore -> scanner.ShowScanner
Designer JSON -> designer.validate_show_plan -> builder.ShowPlanBuilder
`PresetExportProvider` (schema discovery only) -> verified future value parser -> fixture_profiler.FixtureProfiler -> draft JSON
```

`AgentCore.scan_show_profile(path)` is the first integration point. It writes a local `ZEN_SHOW_PROFILE.json` only from current cached evidence and never opens MA2 transport. Designer rejects any embedded `command`, `telnet`, or raw MA command key. Builder returns an existing `WorkflowPlan` with no steps, no commands, no approval gate, and `executable=False`. Fixture Profiler has no apply path.

Before a future Builder can execute, add a separately reviewed resolver that maps typed design intent to known Fixture/Preset/Effect references and produces commands only after an explicit capability contract and Preview.

## 15 Proposed Data Flow

```text
Lighting
MA2 read-only providers
  -> StateStore
  -> ZEN_SHOW_PROFILE.json
  -> Designer ZEN_SHOW_PLAN.json
  -> Builder validation/resolution
  -> Preview -> Approval -> Build -> Verify
  -> suggested/manual rollback until a verified rollback executor exists

Fixture Library
Temporary Fixture Type + named, hardware-tested Presets
  -> verified preset-value scanner (future)
  -> fixture_observations.json
  -> FixtureProfiler ZEN_FIXTURE_PROFILE_DRAFT.json
  -> validate/diff/approval
  -> separate draft Fixture Type builder (future)
  -> export library only after real-MA2 verification
```

## 16 Risks

- grandMA2 output varies by version, view, and locale; text parsers must remain conservative.
- Telnet feedback is not a structured state API; response framing and export stability must be preserved.
- MA2 XML schemas and plugin behavior are version-sensitive.
- Fixture Type corruption or patch changes can affect a live show; draft-only remains mandatory until isolated testing exists.
- A single observed DMX point proves a point, not a range or physical unit.
- Adjacent channels do not prove coarse/fine pairing.
- Layout CObject data is partial and must not be treated as fixture geometry.
- Showfile binary research must not become a runtime parser without repeatable identity + value evidence.
- Fixture Type objects can have dependencies on modules, wheels, instances, and modes that must survive cloning/export.

## 17 Recommended Next Step

Run `scripts/verify_real_preset_export.py --real-machine --fixture <id> --preset <type.id> --keep-export` once on a controlled Preset. It permits only `List Fixture` and `Export Preset`; it neither selects nor changes Programmer. Preserve the acquired agent-cache XML as the first real parser fixture only after reviewing it. Do not start Fixture Type creation until this scanner proves Fixture identity, Attribute identity, and raw value provenance.

## 18 CHATGPT HANDOFF

CHATGPT_HANDOFF_BEGIN

Project: ZEN MA2 Agent
Branch: main
HEAD: 0a1a56cf4c2de7d1e2401848afcb59ecff52d7ad (pre-Preset-Scanner baseline; current worktree adds guarded scanner PoC)
Tests: baseline 124/124 unittest PASS; Preset Export schema-discovery tests added this round. Packaged rebuild remains pending after the new code. Real MA2 hardware scripts were not run because no user-specified Fixture/Preset pair was supplied.

Current working features: PySide6 Desktop; paired mobile PWA; Telnet authentication; shared AgentCore; guarded Preview/Approval; Group/Fixture inventories; local Export XML Group order; partial Layout CObjects; Preset/Effect/Sequence/Cue/Page/Executor inventories; Show Diagnostics; narrow Effect Builder and Timecode Offset; Geometry Clone mapping/preview; new read-only Scanner and draft-only Designer/Builder/FixtureProfiler PoC.

Current blockers: Preset Export XML schema is not yet proved from a real sample; no Fixture Type/DMX/Channel Set provider; no per-fixture XYZ/rotation; no fixture Layout geometry; no Effect line reader; no automatic rollback; Geometry Clone real isolated write test incomplete.

Scanner readiness: Inventory/capability profile ready; semantic values and Fixture Type details unavailable.

Fixture XYZ status: BLOCKED; current Layout Export is known incomplete for visible Fixture elements.

Position preset Pan/Tilt status: BLOCKED_PENDING_REAL_EXPORT_SAMPLE; acquisition is ready, parser intentionally absent.

Effect parameter status: PARTIAL inventory only; line parameter readback is NOT_IMPLEMENTED.

Fixture Type read status: PARTIAL textual Fixture type label only; modules/channels/functions/sets/wheels unavailable.

Preset raw DMX read status: UNVERIFIED; local Export Preset XML acquisition is ready, no field mapping is proved.

Fixture observation capture status: Draft normalizer supported from verified structured observations; automatic MA2 capture BLOCKED_PENDING_REAL_EXPORT_SAMPLE.

Channel Set generation status: Draft candidates only; no range inference, apply, or Fixture Type editing.

Fixture Type build/export status: NOT_IMPLEMENTED.

Existing reusable modules: AgentCore, StateStore, state providers, local Export transaction, WorkflowPlan, Safety classification, SkillRegistry, audit logger, portable resources, desktop/mobile shared route.

Files added/changed this round: previous assessment files plus `zen_ma2_agent/state/providers/preset_export.py`, `zen_ma2_agent/runtime.py`, `zen_ma2_agent/state/providers/__init__.py`, `scripts/verify_real_preset_export.py`, and `tests/test_preset_export_discovery.py`.

Recommended next implementation: run the guarded verifier once with a user-selected Fixture/Preset pair, then add a parser only for the evidenced XML fields.

Questions requiring MA2 real-hardware verification: Which documented/exported source exposes Preset values per Fixture and Attribute? Can it expose raw 8/16-bit values without selection/programmer mutation? Which Fixture Type export schema safely contains channels/functions/sets/wheels? Does it preserve fixture identity, mode, and coarse/fine relations?

CHATGPT_HANDOFF_END
