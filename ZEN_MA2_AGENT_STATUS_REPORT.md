# ZEN MA2 Agent Status Report

Assessment date: 2026-09-08

Assessment implementation HEAD: `f51f39f2f668e9271f5edbc346290fc4b41408f1` before the real-machine Preset Value Scanner follow-up.

This report is based on source code, the runnable test suite, packaged EXE
smokes, Git history, and actual command allow-lists. The original assessment
did not alter the Show; the later, explicitly authorized real-machine follow-up
is recorded separately in section 20, including its limited Agent-owned writes
and cleanup.

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
Tests: 131/131 unittest PASS. Packaged chat-routing and 5-second EXE smoke PASS for build `01aba4332f42ab6913de15e2aa590e1ef3e17522`. Real MA2 hardware scripts were not run because no user-specified Fixture/Preset pair was supplied.

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

## 19 Preset Value Scanner PoC Handoff

PRESET_VALUE_SCANNER_HANDOFF_BEGIN

HEAD: 01aba4332f42ab6913de15e2aa590e1ef3e17522 (runtime/scanner implementation build)

Tests: 131/131 unittest PASS; 7 Preset Export discovery tests; packaged chat-routing and EXE smoke PASS.

Backends tested: A. `Export Preset <type.id> "<Agent-owned filename>" /nc` is implemented as a local-onPC transaction and protected by a unique filename, stable-file wait, XML well-formedness gate, audit log, and cleanup. B. Lua object tree was not changed or invoked. C. List Preset remains metadata-only. D. Extract remains excluded because the official MA2 documentation says it places hard values in Programmer.

Export Preset XML result: TRANSPORT_READY_SCHEMA_UNVERIFIED. Unknown XML becomes a structural diagnostic with zero observations; it cannot claim Fixture identity, Attribute identity, raw DMX, decimal16, or physical values.

Real MA2 sample acquired: NO. The onPC process and local settings exist, but no user-specified Fixture/Preset pair was supplied and the verifier deliberately refuses to choose one.

Preset XML contains fixture identity: NO (not yet evidenced).

Preset XML contains attribute identity: NO (not yet evidenced).

Preset XML contains stored value: NO (not yet evidenced).

Raw DMX available: NO (not yet evidenced).

16-bit/fine information available: NO (not yet evidenced).

Physical value available: NO (not yet evidenced).

Position Preset Pan/Tilt: BLOCKED_PENDING_REAL_EXPORT_SAMPLE.

Fixture observation capture: PARTIAL. The draft normalizer is ready for `VERIFIED_PRESET` observations, but automatic MA2 capture is blocked pending the sample/parser proof.

Local onPC status: LOCAL_ONPC_SUPPORTED by design when the active onPC importexport directory resolves; final runtime proof awaits the verifier.

Remote console status: REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM. No shared-filesystem claim is made.

Files added/changed: `zen_ma2_agent/state/providers/preset_export.py`, `zen_ma2_agent/runtime.py`, `zen_ma2_agent/state/providers/__init__.py`, `scripts/verify_real_preset_export.py`, `tests/test_preset_export_discovery.py`, and this report.

Exact next blocker: acquire exactly one real export using `scripts/verify_real_preset_export.py --real-machine --fixture <id> --preset <type.id> --keep-export`, then inspect its retained agent-cache XML to prove the three required identity/value fields before writing a parser.

Recommended next step: run that one guarded verifier on a controlled Position Preset; do not start any Writer or Extract diagnostic.

PRESET_VALUE_SCANNER_HANDOFF_END

## 20 Real-Machine Preset Value Scanner Follow-up

This section supersedes the earlier Preset-value readiness statements.  It was
run against the local grandMA2 onPC 3.9.60.65 Show on 2026-09-08 with an
authenticated MM Telnet session.  It created only Agent-owned test Presets and
used a Fixture that was both unpatched and absent from Groups 1--7.

### Controlled test and preservation record

- Selected Fixture: `9999`, `461 G BSW 1`, Fixture Type `2 ZEN BAW 20R Mode 2`.
  It was selected because `List Fixture` showed Patch `(-)`, it was outside all
  verified production Group memberships, and `List Fixture 9999 Attribute
  Pan/Tilt` showed both attributes.
- Agent-owned Presets: `Preset 2.900 "ZEN_SCAN_TEST_POS_A"` (Pan 15 only),
  `Preset 2.901 "ZEN_SCAN_TEST_POS_B"` (Tilt 25 only), and
  `Preset 2.902 "ZEN_SCAN_TEST_POS_C"` (Pan 15 plus Tilt 25).  Every slot was
  verified empty before Store and verified absent after Delete.
- No production Preset, Fixture Type, Patch, Cue, Sequence, Effect, Group, or
  fixture in Groups 1--7 was changed.
- Existing Programmer and Selection values could not be fingerprinted by the
  available read APIs.  `Extract Preset` was therefore kept inside the isolated
  Fixture-9999 test and followed by `Off Fixture 9999` and `Clear`; the original
  state cannot be positively reconstructed from current MA2 feedback.

### Backend evidence

| Backend | Real result | Capability conclusion |
| --- | --- | --- |
| `Export Preset` XML | Both exports are 3.9.60 `<MA>` documents with only `<Info>` and an empty `<Preset index name SpecialUse />`. POS_A and POS_B differ only in timestamp/index/name. | `METADATA_ONLY_REAL_MA2_3_9_60`; no Fixture, Subfixture, Attribute, stored value, raw DMX, Decimal16, or physical value is present. |
| bounded Lua `preset_probe` | `Preset 2.900` is `CMD_PRESET`, has zero children, and six metadata properties (`No.`, `Name`, `Symbol`, `Included Preset Types`, `Special`, `Info`). | Object-tree probe does not expose Preset content. |
| controlled `Extract Preset` | MA2 accepted Extract, but current `List Programmer` exposes only `Programmer 21`; Fixture Attribute list still exposes Fixture-Type defaults, not active hard values. | No safe value-reader backend is currently established. |

The real XML schema is now represented by sanitized fixtures under
`tests/fixtures/ma2_preset_exports/`.  `PresetExportProvider` explicitly
returns an empty observation set and `NOT_PRESENT_IN_EXPORT` for every value
field; it will reject an index that cannot prove the requested Preset identity.

### Updated Scanner and Fixture Profiler status

| Capability | Updated status | Evidence |
| --- | --- | --- |
| Preset Export transport, local onPC | SUPPORTED | unique Agent filename, stable XML gate, cleanup, two real exports |
| Preset identity/name from Export | SUPPORTED_METADATA_ONLY | requested numeric reference, XML index (`number - 1`), and label agree |
| Fixture/Subfixture/Attribute/value from Export | BLOCKED_BY_REAL_SCHEMA | neither real export contained those fields |
| Position Preset Pan/Tilt scanner | BLOCKED | Export, Lua, and controlled Extract all lacked an identity/value readback path |
| Automatic Fixture Observation Capture | BLOCKED | no trustworthy `Fixture + Attribute + stored value` record exists |
| Fixture Profiler end-to-end | BLOCKED | draft normalizer exists, but cannot receive verified MA2 observations |
| Normal ShowScanner integration | BLOCKED | no value provider was connected, to avoid fabricated data |

Multi-fixture mapping was deliberately **not tested**: Fixture 9999 was the
only Fixture that could be proven non-production without modifying a production
fixture or Group.  A second safe Fixture must be established before a future
mapping test.

### Exact next blocker

Find a documented, read-only grandMA2 3.9 source that exposes stored Preset
values per Fixture and Attribute, or build an isolated clean-show Extract
reader that can prove and restore Programmer state.  Do not infer values from
the metadata-only Export XML.

## 21 Controlled Showfile Differential Follow-up

With explicit real-machine authorization, a second research pass used only
Fixture `9999` (unpatched and re-verified outside Groups 1--7) and the
Agent-owned Position Preset `2.900`.

- A baseline copy of `zen templ show.show.gz` was made read-only in
  `cache/preset_showfile_differential/20260908/` before test writes.
- The first pair stored Pan/Tilt `(15, 25)` and `(35, 45)`.  A second,
  orthogonal set then stored the same Preset as E `(15, 25)`, F `(35, 25)`,
  G `(15, 45)`, and H `(35, 45)`.  Each state was saved to a unique
  Agent-owned Show copy and immediately copied into the research cache.
- All live-session test output was removed with `Off Fixture 9999`, `Clear`,
  and `Delete Preset 2.900 /nc`; a subsequent `List Preset 2.900` returned
  `NO OBJECTS FOUND`.

The gzip streams and decompressed payloads differ, but their lengths increase
on every save and the string label moves by 91 bytes per save.  Label-anchored
comparison found the same 21 bookkeeping changes for Pan-only, Tilt-only, and
both-axis pairs.  No binary Fixture-9999 reference occurs near the Preset
label, and no candidate record simultaneously binds Fixture identity,
Attribute identity, and a value delta.  The experiment therefore does **not**
meet the evidence threshold for a showfile parser or normal Scanner provider.

The six Agent-owned `ZEN_AGENT_PRESET_DIFF_*.show.gz` copies remain in the
MA2 Shows directory because the host safety guard declined their filesystem
deletion after creation; identical research copies are retained under the
Agent cache.  They contain only the controlled Fixture-9999 test Preset and
may be removed later as an exact-name cleanup operation.

## 22 Isolated Preset Runtime Research Conclusion

The real-machine follow-up was performed only while the Agent-owned isolated
Show `zen_agent_preset_diff_h` was loaded.  The original production Show
`zen templ show` was copied read-only before the work and was restored with
`LoadShow "zen templ show" /nc` afterward.  A post-restore Group-1 export
identifies `showfile="zen templ show"`; the production Show file SHA-256
remains `55592397CA6ED372A719D72748FCD752ECBACB0ECA9B08BF3A2E3E8496720FA2`.

The final bounded Lua probe, `preset_context_probe`, examined a known
Agent-owned Position Preset and up to three ancestors.  It found:

- root: `CMD_PRESET`, zero children, only No./Name/Symbol/Included Preset
  Types/Special/Info metadata;
- ancestor 1: `CMD_PRESET_POOL` (`Position 2`), 902 children, only a pool
  name property;
- ancestor 2: `CMD_PRESET_POOL_COLLECT` (`Global`), only a collection name;
- ancestor 3: `CMD_PRESET_POOL_COLLECT_COLLECT` (`Presets`), no properties.

No Fixture, Subfixture, Attribute, or stored-value node was exposed.  This
matches the earlier metadata-only Preset XML, metadata-only List CSV, and the
controlled Extract result whose available Programmer readers exposed no hard
value.  The runtime Lua/object-tree route is therefore `BLOCKED` for a normal
read-only Preset Value Scanner; binary Showfile parsing remains
`RESEARCH_ONLY` and is not a Scanner backend.

The isolated Show cleanup sent `Clear`, `Off Fixture 9999`, and deleted only
`Preset 2.900`, `2.901`, and `2.902`; `List Preset 2` afterward listed only
the pre-existing `Position 2.2 CENTER`.  No production Show object was
written after returning to `zen templ show`.

The local importexport file `ZEN_AGENT_RESTORE_VERIFY.xml` is the sole
residual artifact from the restore check.  It is Agent-owned and contains only
the Group-1 read-only verification export; host safety policy rejected its
exact-file removal, so it is retained rather than bypassing that policy.

## 23 Fixture Geometry Scanner Real-Machine PoC

This follow-up supersedes the earlier Stage-XYZ blocker.  It does **not** use
Layout Export or a Showfile binary parser.  On grandMA2 onPC 3.9.60, `List
Fixture <id>` exposes root inventory metadata, while `List Fixture <id>.1`
exposes the actual Subfixture properties: FixID, Fixture Type, Patch, Pan/Tilt
DMX and encoder inversion, Pan/Tilt offsets, PosX/PosY/PosZ, and
RotX/RotY/RotZ.

- Production read-only discovery: Fixture `101.1` is `CMD_SUBFIXTURE`, FixID
  `101`, Patch `10.001`; Fixture `701.1` and `701.2` both exist while
  `701.3` does not.  The root inventory count `(2)` was thus verified against
  this two-instance Fixture rather than assumed.
- Isolated Show: `zen_agent_preset_diff_h` was loaded only for the controlled
  readback test. `Move3D At -2 1 4` plus `Rotate3D At 0 0 90` for Fixture 101
  read back from `101.1` as exactly `(-2, 1, 4)` and `RotZ 90`. Fixture 301
  independently read back `(4, 2, 5)` and `RotZ -45`; static Fixture 601.1
  read back `(1, -3, 2)`. Root Fixture rows remained zero, proving that the
  geometry must be scanned from Subfixture rows.
- A bounded, read-only Lua `fixture_property_probe` corroborated the same
  Subfixture properties. The normal provider uses the more portable Telnet
  List path and does not require a Plugin slot.
- After the test, production `zen templ show` was reloaded and verified:
  Fixtures 101.1, 301.1, 601.1 and 9999.1 all read zero; no test Preset or
  production Patch, Cue, Effect, Sequence, or Fixture Type was changed.

`FixtureGeometryProvider` now stores per-Subfixture records under
`fixture_geometry`, source `MA2_FIXTURE_OBJECT_PROPERTY`, backend
`MA2_TELNET_LIST_SUBFIXTURE`, confidence `REAL_MACHINE_VERIFIED`. A full
read-only production scan returned 65 records with no missing Subfixture path.
`ZEN_SHOW_PROFILE.json` now contains a Fixture-level `stage_geometry` record
and its explicit Subfixture list when this resource is fresh.

The coordinate-axis semantic convention is still unverified. Numeric geometry
is supported; left/right, upstage/downstage labels and normalized geometry are
therefore intentionally not emitted.

`semantic_presets/ZEN_SEMANTIC_PRESET_REGISTRY.json` adds strict exact-label
POSITION roles (`POS_HOME`, `POS_STAGE_L/C/R/U/D`) with TEMPLATE/ACTIVE/
PROTECTED/IGNORE permissions. It makes no fuzzy label guesses. The current
production Position inventory has no resolvable entry, so runtime semantic
Position resolution remains pending user-created exact labels.

## 24 Stage Axis and Deterministic Geometry Derivation

The numeric coordinate backend was verified again on the isolated Show
`zen_agent_preset_diff_h`, using only Agent Fixture `9999.1`. Six absolute
`Move3D At` cases read back exactly from the verified Subfixture provider:
`X +4/-4`, `Y +4/-4`, and `Z 8/2` (with the other axes held at the test
baseline). The production Show was then reloaded; Fixture `101.1` returned
zero geometry and the production file SHA-256 remained
`55592397CA6ED372A719D72748FCD752ECBACB0ECA9B08BF3A2E3E8496720FA2`.

The host's Windows Stage View capture interface failed before it could provide
an independent visual axis indicator. Therefore `ZEN_STAGE_AXIS_PROFILE.json`
records numeric readback as `REAL_MACHINE_VERIFIED`, but deliberately uses
neutral `X/Y/Z ... SIDE_A/SIDE_B` names and `PARTIAL` confidence. It does not
claim which sign is Stage Left, Upstage, or Above.

`zen_ma2_agent.geometry.GeometryNormalizer` now produces read-only derived
data per relevant geometry-bearing Fixture/Subfixture set: zero-safe
normalization; deterministic numeric X/Y/Z ordering; center detection;
tolerance-based rows/layers; mirror-pair candidates scored from X reflection,
Y/Z proximity and Fixture Type compatibility; and inner/outer rank. This is
labelled `GEOMETRY_INFERRED` and keeps raw Subfixture geometry authoritative.
`ZEN_SHOW_PROFILE.json` now includes `geometry_analysis`, `stage_axis_profile`,
and normalized/relationship data for each primary and Subfixture geometry row.
Raw Patch text is retained; only the verified `Universe.Address` shape such as
`10.001` is additionally parsed as Universe `10`, Address `1`.

## 25 First Song Builder PoC

The first executable Builder path is deliberately narrow and uses a manual
portable song-structure input (`examples/FIRST_SONG_INPUT.json`), a fresh
`ZEN_SHOW_PROFILE.json`, typed `ZEN_SHOW_PLAN.json` actions, and the shared
MODIFY preview/approval lifecycle. It dynamically resolves only Group and
Preset references returned by the current scan, uses the explicit input
Sequence allocation range, and creates only a new `ZEN_AI_TEST_*` Sequence.
No existing Preset, Effect, Cue, Sequence, Patch, or Fixture Type is modified.
If an exact semantic Position Preset is absent, it records a warning and skips
that action rather than inventing a resource. Effect calls remain skipped until
their production call grammar is independently verified.

The verification contract is intentionally PARTIAL: it reads back the exact
Sequence label, Cue count, Cue labels, and Cue fades. Preset/Effect content
inside a Cue has no verified read-only provider. Narrow rollback is a proposal
only: `Delete Sequence <n> /nc` is available solely after exact read-back of
the same number plus an `ZEN_AI_TEST_*` label, and still requires a separate
explicit approval.

Real MA2 3.9 verification on `zen templ show` created two Agent-owned test
Sequences only: `201 ZEN_AI_TEST_ZEN_FIRST_SONG_TEST` and
`202 ZEN_AI_TEST_ZEN_FIRST_SONG_TEST_R2`.  The current Builder proof executed
through the shared ActionRecord approval route for Sequence 202 and read back
all seven Part-0 Cue rows through the verified read-only form
`List Cue <cue> Part 0 Sequence <sequence>`.  Exact labels `INTRO`, `VERSE_1`,
`PRE`, `CHORUS_1`, `VERSE_2`, `CHORUS_2`, `OUTRO` and Fades
`2, 1.2, 1.2, 0.5, 1.2, 0.5, 2` matched the approved plan.  MA2 returned no
command error; existing Presets, Effects, production Sequences, Patch, and
Fixture Types were not modified.  The two named test Sequences are retained
for operator inspection.

## 26 Song Analysis v0.1

`zen_ma2_agent/song_analysis/` provides a portable, command-free input
boundary for the verified First Song Builder. The `zen.song_analysis.v0.1`
schema supports a title, optional duration/BPM, typed sections, optional
accent events, live-performance flags, stage-role metadata, and an explicit
Sequence allocation range. Every normalized section retains provenance;
unknown timing, BPM, and energy remain `null` rather than being invented.

JSON is the highest-fidelity input. `ScriptSongParser` deterministically
parses simple time-stamped TXT/Markdown structure notes and recognizes only
the fixed typed role vocabulary. `manual_overrides` have priority over parsed
values. The document rejects overlapping known time ranges, duplicate IDs,
out-of-range energy values, and all MA2 transport-field names.

`SongAnalysisAdapter` is the sole bridge to the existing FirstSongDesigner.
The Designer remains typed-intent-only, dynamically resolves live Groups and
Presets, and still routes through the unchanged Builder, Preview, approval,
and verification boundary. Repeated roles receive bounded deterministic
intensity variation; explicit section-bound accents can add a bounded extra
cue. Effects remain inventory-only and semantic-position absence remains a
safe warning/fallback. `examples/REALISTIC_SONG_ANALYSIS.json` provides a
nine-section fixture for the next guarded real-MA2 build; it is distinct from
`FIRST_SONG_INPUT.json`.

Real grandMA2 3.9 validation then used that distinct `ZEN_SONG_ANALYSIS`
fixture through `AgentCore.preview_song_analysis()` and the same shared
ActionRecord approval boundary. It created only Sequence `203`, labelled
`ZEN_AI_TEST_ZEN_REAL_SONG_ANALYSIS_TEST`. The approved plan used freshly
scanned Group `1` and Focus Preset `6.2`, created 11 cues, and ended with
`ClearAll`. Read-only verification confirmed the exact Sequence label plus all
11 Cue labels and fades: INTRO (2), VERSE_1 (1.2), PRE_CHORUS (0.5),
CHORUS_1 (0.5), CHORUS_1_ACCENT_1 (0.2), VERSE_2 (1.2), SAX_SOLO (0.5),
CHORUS_2 (0.5), FINAL_CHORUS (0.5), FINAL_CHORUS_ACCENT_1 (0.2), OUTRO (2).
Preset/effect content readback remains explicitly PARTIAL. Existing production
objects were reference-only; the three `ZEN_AI_TEST_*` Sequences are retained
for inspection.

## 27 Industry Reference Pack 001

`ZEN_INDUSTRY_REFERENCE_PACK_001` is a local, read-only evidence pack built
from six traceable professional sources: two large-concert references, two
band/live references, and two theatre/narrative references. The source model
is `zen.industry_reference_source.v0.1`; observations are short,
copyright-safe derived notes with source URL, context, limitations, evidence
type, confidence, and a default `HUMAN_REVIEW_REQUIRED` status.

The pack records repeated cross-domain signals such as focus hierarchy,
resource awareness, color development, spatial depth, and movement usage. It
also preserves context dependence (for example, an early signature effect can
be intentional in one show) rather than turning one practice into a global
rule. Internal principles and anti-patterns are reported in separate
validation documents; no global promotion occurred.

This round does not wire external evidence into Designer, does not create a
`ZEN_STYLE_PROFILE`, and performs zero MA2 writes. Industry ingestion status
is `LOCAL_PACK_READY / HUMAN_REVIEW_REQUIRED`; runtime use remains
`NOT_IMPLEMENTED` until explicit review and a future context adapter.

## 28 Industry Reference Pack 002 — Contemporary Mainstream Pop / K-pop

`INDUSTRY_REFERENCE_PACK_002` is a second, independent, local and read-only
evidence pack covering nine named contemporary large-stage productions from
2022–2025. It adds explicit visual-language tags, visual-reference metadata,
source-selection bias, and bounded transient-impact, buildup/restraint,
camera-readability and controlled-maximalism observations. Pack 001 remains
the broader cross-domain baseline; Pack 002 is a narrower contemporary
mainstream prior and does not replace it.

The prior uses `zen.contemporary_mainstream_prior.v0.1` with its domain, time
window, evidence count, visual-language set, confidence and source diversity.
`DIRECT_SOURCE_STATEMENT`, `VISUAL_INFERENCE` and `MODEL_INTERPRETATION` remain
separate; no fake cue timing, DMX value or universal K-pop grammar is inferred.
The YG hypothesis review records partial or mixed evidence only and does not
create or promote `ZEN_STYLE_PROFILE`.

`ZEN_INDUSTRY_REFERENCE_PACK_002_VISUAL_REVIEW.md` is visual-first and requires
human inspection of each linked production/source page before any lesson can
be considered for future knowledge. Runtime wiring is `NOT_RUN`, Designer
behavior is unchanged, and MA2 writes are `ZERO`.

## 29 Human-reviewed User Style Evidence

`zen.user_style_evidence.v0.1` stores Zen's direct visual-review reactions as
a separate, reversible layer. Raw reactions remain distinct from normalized
traits; provenance is always `HUMAN_VISUAL_REVIEW`. Positive references include
BABYMONSTER, Subtronics, Drake and Billie Eilish; Karol G is mixed/lower
positive, while Billy Strings is retained as case-local negative evidence.

The synthesis records controlled high impact, clean hierarchy, palette
coherence, musical-form following, rhythmic/dynamic alignment, multi-level
energy design, intentional restraint and controlled maximalism as candidates.
`HIGH_IMPACT_ALWAYS` is explicitly rejected by the evidence. `KPOP_YG_LEANING`
is a direction label only, not a global rule. Industry Pack 001/002 remain
independent and immutable; alignment is reported for review only.

`ZEN_STYLE_PROFILE` remains `DEFERRED`. No Designer runtime wiring, Scanner
connection or MA2 write is part of this layer. Permanent promotion would
require repeated cross-artist, cross-style and cross-scale evidence plus
explicit human confirmation.

## 30 Human Style Review Decisions

`zen.user_style_review.v0.1` stores human decisions separately from immutable
User Style Evidence and Style Candidate records. Review-ready records include
candidate and evidence references, scope, rationale, limitations, reviewer and
version metadata. Every generated template has human decision `UNSET`.

AI recommendations are explicitly labelled `AI_RECOMMENDATION`; they are not
acceptance decisions. Even a later human `ACCEPT` only makes a candidate
eligible for future knowledge/style consideration. It cannot become a global
Designer rule, hard constraint, or permanent `ZEN_STYLE_PROFILE` trait.

The revised synthesis treats clean hierarchy, palette coherence, musical
alignment, multi-level energy design, negative-space acceptance and intentional
restraint as supported candidates. Controlled maximalism, dominant-theme color,
transient impact, section delta and between-peak restraint remain partial or
moderate. Complete-look, musically-justified-impact and geometry/global claims
remain weak or uncertain. `HIGH_IMPACT_ALWAYS` is rejected by evidence.

This layer remains review-only: Designer runtime wiring is `NOT_RUN`,
`ZEN_STYLE_PROFILE` is `DEFERRED`, Industry evidence is unchanged, and MA2
writes are `ZERO`.

## 32 Second Human Style Decision Batch

The second explicit review batch is stored in
`tests/fixtures/user_style_review_decisions_002.json` using
`zen.user_style_review.v0.1`. `PROGRESSIVE_ENERGY_ARC` and
`EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK` are `ACCEPT`; the latter carries
`priority: HIGH`. Six properties are explicitly context-dependent and remain
`NEEDS_MORE_EVIDENCE`: dominant theme color, strong transient impact, section
delta, restraint between peaks, controlled buildup and geometric composition.

The synthesis now records the emerging observation that Zen style is not a
large collection of fixed look rules. The stronger transferable preference is
design coherence and context-aware energy design. This is a synthesis
observation only, not a runtime rule. All previous decisions and the three
rejected interpretations remain preserved.

Designer runtime wiring is `NOT_RUN`, `ZEN_STYLE_PROFILE` is `DEFERRED`,
Industry evidence is unchanged, and MA2 writes remain `ZERO`.

## 31 Explicit Human Style Decisions

The first explicit decisions are stored separately using
`zen.user_style_review.v0.1`. `CLEAN_VISUAL_HIERARCHY`, `PALETTE_COHERENCE`,
`MUSIC_STRUCTURE_ALIGNMENT`, `RHYTHMIC_ACCENT_SYNC`,
`DYNAMIC_CONTOUR_TRACKING`, `MULTI_LEVEL_ENERGY_DESIGN` and
`INTENTIONAL_RESTRAINT` are `ACCEPT`. `CONTROLLED_HIGH_IMPACT` and
`CONTROLLED_MAXIMALISM` are `ACCEPT_WITH_LIMITATION` with their documented
context boundaries.

`HIGH_IMPACT_ALWAYS`, `MAXIMALISM_EQUALS_CLUTTER` and
`MULTICOLOR_EQUALS_BAD` are explicitly `REJECT`. Other candidates remain
`UNSET` / `NEEDS_MORE_EVIDENCE`; previous AI recommendations were not used as
human decisions. Acceptance only makes a candidate eligible for future
knowledge/style consideration and never creates a global Designer rule or
permanent `ZEN_STYLE_PROFILE` trait.

Designer runtime wiring remains `NOT_RUN`, `ZEN_STYLE_PROFILE` remains
`DEFERRED`, Industry evidence is unchanged, and MA2 writes remain `ZERO`.

## 33 Shadow-Mode Design Guidance Integration

`zen.design_guidance_context.v0.1` and `zen.design_advisory.v0.1` now provide a
typed, command-free shadow layer around the deterministic Designer. It retains
separate song signals (`SECTION_STRUCTURE`, `RHYTHMIC_ACCENT`,
`DYNAMIC_CONTOUR`, `BUILDUP_RELEASE`, and repeated-section development), bounded
Training Case context, evidence-provenanced Industry Pack observations, and only
explicitly human-reviewed User Style decisions.

The active human signals are accepted preferences plus bounded
`ACCEPT_WITH_LIMITATION` preferences. Context-dependent candidates remain
non-fixed, while rejected/non-global interpretations remain explicit. Advisory
conflicts are structured rather than reduced to a global weighted score; case
resource limits and professionally-valid/user-style divergence remain visible.

The existing `FirstSongDesigner` is run unchanged in the shadow-preservation
test. Baseline and shadow `ZEN_SHOW_PLAN` outputs are structurally identical;
only a separate advisory envelope is added. Designer production guidance
activation is `NOT_RUN`, `ZEN_STYLE_PROFILE` is `DEFERRED`, and this local test
work produced no MA2/Telnet/plugin execution or MA2 writes.

## 34 Shadow Advisory Evaluation 001

Five explicitly `SYNTHETIC_EVALUATION_ONLY` song-structure cases now evaluate
the shadow guidance across high-energy pop, medium verse/chorus, restrained
minimal, buildup/drop, and irregular non-linear forms. The existing realistic
song-analysis fixture is retained as a baseline-preservation control. Every
baseline and shadow `ZEN_SHOW_PLAN` remains structurally identical.

The evaluation keeps section/form, rhythmic accent, dynamic contour,
buildup/release, and repeated-section development distinct. It confirms that
complete low/medium/high energy states can be advised without emitting a dimmer
or other MA2 decision. Rejected interpretations and context-dependent style
candidates remain inactive. The outcome is `NEEDS_MORE_SHADOW_WORK`: advisory
reasoning is traceable and non-formulaic, but still broad and only evaluated
against the Training Case 001 context.

## 35 Shadow Advisory Evaluation 002 — Cross-Rig Robustness

The same synthetic buildup/drop Song Analysis is now evaluated against four
bounded contexts: Training Case 001 resource-rich control, medium live,
LED-only, and imperfect/asymmetric. These are `SHADOW_EVALUATION_ONLY` semantic
contexts, not live MA2 rigs. The new resource advisory records per-section
`KEEP`, `REDUCE`, `OMIT`, `SUBSTITUTE`, and `REASON` choices with explicit
resource adaptation versus limitation.

All baseline and shadow `ZEN_SHOW_PLAN` values remain identical. LED-only
guidance substitutes declared color/density/timing/left-right relationships
instead of mover/beam language; asymmetric guidance uses declared imbalance
intentionally rather than forcing a mirror. The restrained/minimal re-evaluation
now records both selected and intentionally inactive roles. This is ready for
human cross-rig review only; production guidance activation, `ZEN_STYLE_PROFILE`,
and MA2 writes remain `NOT_RUN`/`DEFERRED`/`ZERO`.

## 36 Single-Entry Rig Intake / Router

`zen.show_intake.v0.1`, `zen.rig_context.v0.1`, and
`zen.rig_proposal.v0.1` now establish a command-free single-entry boundary in
front of the existing shadow guidance path. One user-facing ZEN MA2 Agent can
route a request to `USER_CONFIRMED_LAYOUT`, optional
`ASSISTED_RIG_PLANNING`, or `EXISTING_SHOW`; users do not need to select
separate venue, rig, designer, or builder agents.

Confirmed placement bypasses the planner and remains authoritative. Existing
scanned-show placement is reused rather than redesigned. Sparse information can
produce a bounded floor-only semantic proposal if `FLOOR_ONLY` and a usable
floor-zone observation are available; otherwise the router asks only the
material `CONFIRM_SAFE_FLOOR_ZONE` question. Facts retain
`CONFIRMED`/`INFERRED`/`UNKNOWN` certainty and source. Visual observations can
state an inferred visible truss or usable floor zone but never certify hanging,
load, electrical capacity, or rigging points.

Normalized Rig Context exposes inferred capability roles and advisory-only
`KEEP`/`REDUCE`/`OMIT`/`SUBSTITUTE` affordances to shadow guidance. Baseline and
shadow plans remain identical. The production Designer, Resolver, Builder,
MA2/Telnet/plugin paths, Guidance-Assisted Designer A/B, and `ZEN_STYLE_PROFILE`
remain `NOT_RUN`/`DEFERRED`; MA2 writes are `ZERO`.

## 37 Guidance-Assisted Designer A/B Experiment 001

`GuidanceAssistedExperimentalDesigner` is an explicit
`GUIDANCE_ASSISTED_AB_ONLY` adapter, not a modification of the production
`FirstSongDesigner`. It first obtains the ordinary typed show plan and may
change only existing typed actions when a normalized Rig Context supplies a
`CONFIRMED` role-to-Group binding that matches a scanned Group in the supplied
profile. Absent a binding, it returns a clearly marked no-action-change
candidate rather than treating an abstract role as an MA2 resource.

Four deterministic synthetic comparisons cover resource-rich buildup/drop,
restrained/minimal medium rig, LED-only, and user-confirmed asymmetric rig
contexts. B creates role-aware typed Group/preset/dimmer action composition and
intentional omissions where justified. LED-only selects only color, density,
and timing roles; asymmetric mode never moves/rebalances or forces a mirror.
The asymmetric result is honestly `MIXED`, because its physical/aesthetic value
cannot be assessed without a real venue/lighting-designer review.

The production default is regression-tested unchanged; A and B both validate as
canonical typed plans and no live build path is invoked. Context-dependent and
rejected style candidates remain inactive. This is
`READY_FOR_HUMAN_AB_REVIEW` only; `ZEN_STYLE_PROFILE`, production
guidance-assisted activation, and real venue validation remain
`DEFERRED`/`NOT_RUN`/`WAIT_FOR_REAL_CASE`, and MA2 writes remain `ZERO`.

## 38 Guidance-Assisted Designer A/B Experiment 002 — Human Review Refinement

Human A/B Review 001 is now preserved independently as
`zen.guidance_ab_human_review.v0.1`; it does not mutate the original A/B
fixture, its baseline, or the prior experimental output. The reviewed direction
accepted bounded headroom/buildup design but required a musically justified
second-Drop delta, rejected the LED energy/layer ladder as formulaic, and kept
restrained/minimal and asymmetric aesthetic treatment explicitly context
dependent.

The explicit experimental adapter now selects role composition from section
structure, measured density, explicit rhythmic events, occurrence comparison,
and confirmed role-to-scanned-Group bindings. It no longer maps energy alone to
an LED role count: low energy can use timing when an accent warrants it, high
energy can omit timing when it does not, and medium energy need not include
density. Repeated sections are marked `MUSICALLY_JUSTIFIED_DELTA` only when
their comparative song evidence warrants it; otherwise they retain
`INTENTIONAL_SIMILARITY`. Complete-look composition is tracked as independent
from energy and layer count.

The experimental plan records an explicit deny-list for repeat-always-bigger,
LED energy-ladder, forced-asymmetry, and fixed Verse/Refrain interpretations.
Production `FirstSongDesigner` regression tests remain unchanged. This work
does not route experimental output to production, create `ZEN_STYLE_PROFILE`,
or touch MA2/Telnet/plugins; MA2 writes remain `ZERO` and real venue validation
remains `WAIT_FOR_REAL_CASE`. A/B 002 needs a new human cue-level review before
any future production decision.

## 39 Guidance-Assisted Designer A/B Experiment 003 — Design Intent First

The experimental path now has `zen.design_intent.v0.1`, a bounded command-free
record that sits between known Song/Rig context and B3 resource choice. For each
experimental cue it records the audience goal, continuity/change relation,
previous visual roles, measured upcoming context/headroom, visual-dimension
intent, intentional omissions, provenance and explicit unavailable signals.
The production Designer remains unmodified.

Repeated-section reasoning now compares available event, density, accent,
section-note, transition and known-future-peak evidence. It can produce a
meaningful delta with unchanged energy, or an explicit `INTENTIONAL_SIMILARITY`
when continuity is the supported design decision. Texture is no longer gated on
a hit or dynamic rise: supplied atmospheric/sustained section context can
justify it in a quiet section, while a high section can omit it. Likewise,
low-energy timing and high-energy timing omission are verified experimental
possibilities rather than recipes.

The B3 trace exposes known song context, previous visual state, upcoming
context, Design Intent, keep/change/omit/substitute choices, unknown data,
typed-action boundary and `HUMAN_REVIEW: UNSET`. It rejects expanded formulaic
interpretations including more-rhythm/more-lighting, texture-requires-accent,
every-repeat-different, final-always-biggest, high-always-complex,
low-always-simple and available-role-must-be-used. Tests cover eight
deterministic synthetic cases and retain B2 as an explicit comparison-only
reference. This is `READY_FOR_HUMAN_REVIEW`, never production activation:
`ZEN_STYLE_PROFILE` remains `DEFERRED`, real venue validation is
`WAIT_FOR_REAL_CASE`, and MA2 writes remain `ZERO`.

## 40 Human Design Review 001 — Ready for Human Input

`ZEN_HUMAN_DESIGN_REVIEW_001.md` is a presentation-only extraction of the
existing deterministic A/B-003 outputs. It preserves the actual B3 Design
Intent, previous/upcoming context, typed actions, provenance and all eight
bounded review cases (A–H); it does not alter the production Designer or the
experimental B3 algorithm. Duplicate cue occurrences are retained rather than
collapsed, and unavailable Song Analysis signals are labelled explicitly.

Every review card leaves `HUMAN REVIEW: UNSET`. Audience-perception language is
classified as supported by supplied input or bounded inference, not presented
as an artistic verdict. The package is ready for a real lighting designer to
judge intent, continuity, repeat logic, resource choices and human-like
reasoning. Human approval has not been recorded. Production activation,
`ZEN_STYLE_PROFILE`, live Builder/MA2 work and venue validation remain
`NOT_RUN`/`DEFERRED`/`WAIT_FOR_REAL_CASE`; MA2 writes remain `ZERO`.

`HUMAN_DESIGN_REVIEW_001 = READY_FOR_HUMAN_INPUT`

## 41 Repository Context and Design Pipeline Integrity 001

The durable startup/navigation contract is recorded in `AGENTS.md` and the
living documents under `docs/`: Product Constitution, Workflow Contract, MA2
Programming Intelligence, Continuous Learning Policy, Console Platform
Architecture, and Repository Policy. Future sessions should read the concise
navigation plus current state and only the reports relevant to their task.

The current integrity work preserves the production Designer and the
GUIDANCE_ASSISTED_AB_ONLY boundary while making repeated cue identity explicit:
each cue now carries deterministic `section_instance_id`, `section_role`,
`occurrence_index`, and `cue_occurrence_index`; review traces carry the cue id
and resolve the exact occurrence. Experimental designs also expose canonical
`zen.role_state.v0.1` entries; legacy `selected_roles` remains a documented
active-role projection, while role states are authoritative.

Design Intent is separate from realization. Experimental output records whether
a requested repeat delta is `REALIZED`, `PARTIALLY_REALIZED`,
`NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES`, or
`INTENTIONAL_SIMILARITY`, with the actual typed action delta and reason. No
artistic rule was added or activated; Case C's unsupported composition delta is
reported honestly. Production behavior, B3 reasoning, ZEN_STYLE_PROFILE and
real venue validation remain unchanged/deferred, and MA2 writes remain ZERO.

`HUMAN_DESIGN_REVIEW_001` remains ready for human input. Before a Real Song +
Existing Show A/B, the remaining integrity requirement is to carry the new
occurrence and realization metadata through any future review/plan consumers
without introducing a second schema or changing artistic behavior.

## 42 Current continuation state

The committed repository on `main` is the source of truth for exact HEAD and
test state. Production Designer artistic behavior is `UNCHANGED`; the
experimental path remains `GUIDANCE_ASSISTED_AB_ONLY`. Fixture geometry, typed
plans, resolvers, Builder and prior real-machine capabilities remain as
previously verified. The current integrity report is
`ZEN_DESIGN_PIPELINE_INTEGRITY_001.md`.

Before the next real-song/existing-show A/B, consume occurrence identity,
realizability and canonical role states in review-facing consumers. Do not
activate experimental guidance, create `ZEN_STYLE_PROFILE`, infer unavailable
song/venue facts, or perform MA2 writes. `REAL_VENUE_VALIDATION` remains
`WAIT_FOR_REAL_CASE`; MA2 write audit remains `ZERO_WRITES`.

## 43 Real Song + Existing Show A/B 001

`ZEN_REAL_SONG_EXISTING_SHOW_AB_001.md` evaluates the existing manual real-song
analysis against a sanitized read-only snapshot of the resource-rich Existing
Show. The route is `EXISTING_SHOW` and planner bypass is verified. The snapshot
contains the exact scanned Groups HYBRID, SPOT, BEAM, WASH, B-EYE, LED PAR and
STROBE plus Focus presets 6.1–6.5; geometry is uninitialized and semantic
positions are absent.

The experimental B3 path now exposes current Design Intent even when an
Existing Show has no confirmed role-to-Group binding, but it makes no action
change and marks each intent `NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES`.
Training Case role suggestions remain inferred and are not silently promoted.
This is a human-review-ready negative A/B result, not a production activation.
Production behavior is unchanged, `ZEN_STYLE_PROFILE` remains deferred, real
venue validation remains `WAIT_FOR_REAL_CASE`, and MA2 write audit is ZERO.

## 44 Existing Show Resource Mapping Review 001

`ZEN_EXISTING_SHOW_RESOURCE_MAPPING_REVIEW_001.md` is a concise, read-only,
human-reviewable capability/candidate-role proposal for the exact scanned
Existing Show Groups. It explicitly separates `resource_capabilities`,
non-ranked `candidate_roles`, and a song/case-specific `case_role_assignment`.
Fixture labels and past case judgments do not create a fixed ZEN role habit,
fixture priority, or permanent Group identity.

There are zero confirmed resource-to-role mappings: HYBRID, SPOT, WASH, B-EYE,
LED PAR, and STROBE have six inferred candidate proposals, while BEAM
deliberately has no safe current B3 candidate translation. Geometry remains uninitialized,
semantic positions remain absent, and Effect inventory/labels remain unsafe
for action-level mapping. Training Case 001 has not been promoted. Every human
review field is `UNSET`; no role binding or action authorization exists.

Production Designer behavior remains unchanged, B3 remains
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains deferred, real venue
validation remains `WAIT_FOR_REAL_CASE`, and the MA2 write audit remains ZERO.
The next bounded step is explicit human review of these candidates before a
new Existing Show experimental A/B can express a song/case-specific selection.

## 45 Existing Show Resource Capability Verification 001

`ZEN_EXISTING_SHOW_RESOURCE_CAPABILITY_VERIFICATION_001.md` separates the
current Show's verified resource identity from channel-capability evidence. A
read-only local MA2 library inspection found closely matching XML/XMLP profile
candidates and parsed their channel definitions, but the current scanner has
no Show-bound Fixture Type-to-library-profile binding. Consequently all
requested attributes remain `UNKNOWN_FOR_EXISTING_SHOW`, and no B3 role is
eligible from verified current-Show capability.

The local profiles are retained as `LOCAL_PROFILE_CANDIDATE_UNBOUND` evidence
only. The practical human decision is to confirm/reject an exact profile
binding or preserve the unknown state; it is not a request to establish a
fixture priority, permanent role, or artistic preference. Existing mapping
hypotheses are now capability-eligibility pending. BEAM is not collapsed into
`MOVER_TEXTURE_LAYER`; B3 vocabulary/capability gaps remain explicit.

`REAL_SONG_EXISTING_SHOW_AB_002` is not ready for an expressive action-delta
run: proceeding now would either repeat the no-action result or guess. The
smallest blocker is a Show-bound read-only channel/profile binding source (or
reviewed exact binding). Production Designer behavior remains unchanged, B3
remains `GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains deferred,
real venue validation remains `WAIT_FOR_REAL_CASE`, and MA2 writes remain ZERO.

## 46 Show-Bound Fixture Type / Channel Profile Binding 001

`FixtureTypeExportProvider` implements the narrow native read-only path:
current `List Fixture` label -> exact `Export FixtureType <id>` -> strict XML
identity check -> ChannelType/ChannelFunction inventory -> provenance-bearing
technical capability profile. It is loopback-onPC only, creates and removes
only an Agent-owned external XML file, and rejects ambiguous XML, mismatched
ID/label, empty channel inventory, remote filesystem access and structurally
different local candidates. Scanner support for optional
`fixture_type_profiles` is additive and does not alter fixture inventory
contracts.

No grandMA2 onPC process was running for this implementation round, so no
current-Show XML was exported and every Existing Show type remains
`UNKNOWN_FOR_EXISTING_SHOW`. Local candidates remain unbound. The exact next
technical step is real-console execution of the provider with the Existing
Show loaded, followed by review of identity/export hash/channel evidence. No
B3 role eligibility, artistic role assignment, action grammar or A/B 002 run
is authorized yet. Production Designer behavior remains unchanged, B3 remains
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains deferred, real venue
validation remains `WAIT_FOR_REAL_CASE`, and MA2 writes remain ZERO.

## 47 Show-Bound Fixture Type Real-Console Attempt

The bounded `scripts/verify_show_bound_fixture_type_binding.py
--real-machine` verifier now proves the expected Existing Show fingerprint
before any FixtureType export and preserves a success/failure record for every
unique FixtureType if one export fails. It allows only Login, List Group, List
Fixture, List Preset All and native external `Export FixtureType`; Fixture
`9999` is never selected or addressed. A current Show profile reports the
aggregate binding state from the per-type capability metadata rather than
mistaking a mixed result for supported structure.

The initial endpoint probe was briefly refused, but the onPC process was then
verified listening on `0.0.0.0:30000` and `0.0.0.0:30001`; the configured
loopback `127.0.0.1:30000` reached `READY` as `MM`. Fresh Group/Fixture/Preset
identity exactly matched the intended Existing Show fingerprint. The verifier
exported each of the six unique FixtureTypes once; every native Export returned
without MA2 error, but every exported XML failed the strict
`FixtureType@index == List-derived pool ID` requirement. No channel inventory,
fingerprint, capability, or local candidate comparison was promoted; all
temporary Agent-owned XML files were removed.

This is a real-console export-schema/binding blocker, not a name-match or
fixture-capability conclusion. `REAL_SONG_EXISTING_SHOW_AB_002` remains blocked
from expressive action deltas until a separately verified Show-bound identity
rule can explain the export index without weakening fail-closed provenance.
Production Designer behavior, B3 boundary, ZEN_STYLE_PROFILE, venue validation
and MA2 object state remain unchanged (`UNCHANGED`/
`GUIDANCE_ASSISTED_AB_ONLY`/`DEFERRED`/`WAIT_FOR_REAL_CASE`/`ZERO_WRITES`).

## 48 Fixture Type Export Schema / Identity Research 001

`ZEN_FIXTURE_TYPE_EXPORT_SCHEMA_RESEARCH_001.md` records a second controlled,
read-only current-Show export batch with bounded diagnostics retained before
temporary-file cleanup. The expected Existing Show fingerprint again matched;
all six exact `Export FixtureType` requests were accepted, every XML had one
FixtureType/channel inventory, and the observed serialization was consistently
`FixtureType@index = requested current-Show pool ID - 1` for IDs 2 through 7.

The strict single-export equality validator remains unchanged. A separate
compound batch identity validator now requires the Show match, exact requested
ID/unique filename/accepted command, one XML FixtureType, the observed offset,
exact List-label reconstruction from requested ID plus XML name/mode, nonempty
channels, and unique IDs/indices. It has established all six current
FixtureTypes as `SHOW_BOUND_VERIFIED`, without name-only fallback. Technical
channel capability is available for future **case-specific** eligibility; it
does not assign permanent roles. Local profile candidates were compared only
after that proof and are mixed (three structurally bound, one structural
mismatch, two local XMLP parsing limits).

No MA2 object write occurred and Fixture 9999 was not addressed. Production
Designer stays `UNCHANGED`, B3 stays `GUIDANCE_ASSISTED_AB_ONLY`,
`ZEN_STYLE_PROFILE` stays `DEFERRED`, and venue validation stays
`WAIT_FOR_REAL_CASE`. The next blocker before a real-song Existing Show A/B is
an updated human-reviewable capability-to-candidate-role eligibility decision;
no artistic assignment or action delta is authorized by this evidence alone.

## 49 Existing Show Capability → Candidate Role Eligibility Review 001

`ZEN_EXISTING_SHOW_CAPABILITY_CANDIDATE_ROLE_ELIGIBILITY_REVIEW_001.md`
supersedes the historical identity-origin mapping hypotheses for current
eligibility review. It applies the six real-console `SHOW_BOUND_VERIFIED`
FixtureType channel profiles to the exact scanned Groups while preserving the
essential separation: technical capability is not candidate-role eligibility,
case role assignment, a fixture priority, or permanent artistic identity.

Every current Group is technically eligible to be considered for
`DENSITY_LAYER` because DIMMER is Show-bound verified and B3 already has a
typed `SET_DIMMER` route. Every Group can be considered for `COLOR_FIELD` at a
technical level because COLOR is verified, but the current B3 Color action
resource is not verified. Pan/Tilt/Focus Groups remain blocked from
performer/area `PRIMARY_FOCUS` by missing semantic targets/geometry/Position
meaning and preset applicability; movable texture and all timing candidates
remain blocked by current safe action grammar. BEAM aerial/impact and possible
B-EYE pixel/shape use are explicit role-vocabulary gaps, not forced mappings.

All `case_role_assignment` values and Human Review fields remain `NONE`/
`UNSET`. The repository is `READY_FOR_HUMAN_ELIGIBILITY_APPROVAL`, not yet
authorized to run `REAL_SONG_EXISTING_SHOW_AB_002`. Production Designer stays
`UNCHANGED`, B3 stays `GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` stays
`DEFERRED`, venue validation stays `WAIT_FOR_REAL_CASE`, Fixture 9999 remains
untouched, and MA2 writes remain `ZERO_WRITES`.

## 50 Real Song + Existing Show A/B 002

`ZEN_REAL_SONG_EXISTING_SHOW_AB_002.md` records the first real Existing Show
action-delta experiment. Zen explicitly approved Groups 1–7 as
`DENSITY_LAYER` candidates for this case only. The approval is represented as
a provenance-bearing, case-scoped multi-Group density cohort; it creates no
permanent Group mapping, priority, role identity, or production behavior.

B3 uses the existing Design Intent density/headroom/repeat trace to select and
omit members of that cohort, then emits only typed `SET_DIMMER` actions. It
preserves cue/section occurrence identity, canonical aggregate role states,
per-resource KEEP/REDUCE/OMIT state, desired-versus-realized status, and the
exact human approval source. No focus, color, texture, timing, effect,
movement, beam, pixel, or position behavior is inferred.

The experiment produces real target-composition deltas: `verse_2` and later
choruses change only where B3 has recorded contextual basis, while earlier
high material can reduce for a measured later peak. It is intentionally not a
production recommendation: the current final cue saturates the equal density
cohort and all selected Groups use equal dimmer values because no verified
spatial/coverage hierarchy exists. These are reported as
`FINAL_COHORT_SATURATION_RISK` and `GROUP_LEVEL_HOMOGENEITY_UNRESOLVED`;
the case recommendation is `NEEDS_REVISION` and human review remains unset.

Production Designer remains `UNCHANGED`, B3 remains
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains `DEFERRED`, real
venue validation remains `WAIT_FOR_REAL_CASE`, Fixture 9999 is untouched, and
MA2 writes remain `ZERO_WRITES`.

## 51 External Lighting Knowledge Ingestion 001

`EXTERNAL_LIGHTING_KNOWLEDGE_PACK_001` provides 25 compact,
provenance-bearing `DESCRIPTIVE` records from seven diverse official,
educational, structured-fixture, professional-practice, and scoped case
sources. It is stored as a compact source registry plus normalized pack, never
as scraped pages or a bulk research archive. The ingestion validator rejects
commands, copied-text fields, unregistered sources, overly long extracts, and
production promotion. No Git LFS, CI, cache, or external media was added.

The optional `zen.external_lighting_knowledge_context.v0.1` is
`SHADOW_ONLY`. It is not connected to the Production Designer or B3. Its one
demonstration attaches source-linked review questions to the existing A/B 002
`FINAL_COHORT_SATURATION_RISK` and
`GROUP_LEVEL_HOMOGENEITY_UNRESOLVED` findings, returns zero action changes, and
explicitly requires Current Show visual/spatial evidence rather than inventing
a Group hierarchy.

The next high-leverage task is a bounded Current Show visual/spatial
relationship survey or user-confirmed rig layout, followed by shadow critique
of the real A/B 002 density cohort. Do not treat external general knowledge as
a substitute for location, coverage, audience viewpoint, action grammar, or
case-specific human design judgment. Production stays `UNCHANGED`, B3 stays
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` stays `DEFERRED`, and MA2
writes stay `ZERO_WRITES`.

## 52 Current Show Visual Relationship Intake 001

`CURRENT_SHOW_VISUAL_RELATIONSHIP_INTAKE_001` is a compact, Show-fingerprint
bound, human-reviewable data layer for the actual Existing Show Groups 1–7.
All five visual descriptors (presence, coverage, visual weight, symmetry, and
visual domain) deliberately begin `UNKNOWN`; Group labels, FixtureTypes,
numeric IDs, raw origin-overlap XYZ, external knowledge, and Training Case
material cannot fill them. Optional pairwise visual relationships require
explicit `HUMAN_CONFIRMED` provenance; no relationship is inferred.

Current Group inventory, uninitialized geometry, absent semantic positions,
and unapplied virtual auto-geometry proposals are retained separately as
`PREEXISTING_EVIDENCE`, never human confirmation. The intake is role-free and
unwired: it cannot select B3 roles, change A/B 002, write geometry, or modify
MA2. It is `READY_FOR_HUMAN_INPUT`; the next action is a one-pass Zen review of
only known visual facts. Production remains `UNCHANGED`, B3 remains
`GUIDANCE_ASSISTED_AB_ONLY`, `ZEN_STYLE_PROFILE` remains `DEFERRED`, and MA2
writes remain `ZERO_WRITES`.
