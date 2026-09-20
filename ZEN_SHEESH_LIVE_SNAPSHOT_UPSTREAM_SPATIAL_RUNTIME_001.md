# SHEESH Live Snapshot Upstream Spatial Runtime 001

**Status:** IMPLEMENTED; REAL RUN BLOCKED AT `RIG_DESIGNER`  
**Run:** `SHEESH_CURRENT_SHOW_REDESIGN_001`  
**Read-only boundary:** `MA2_WRITES=0`  
**Artistic provenance:** `CODEX_ARTISTIC_INTERVENTION=NONE`

## Result

The conditional live-Show runtime path is implemented. The saved Phase A
snapshot normalized successfully, entered the context hash, and was recorded in
run metadata. The existing no-snapshot four-role pipeline remains intact.

The real run stopped at `RIG_DESIGNER`. Three bounded role attempts received
transport-successful JSON from a provider, but all three responses omitted the
required `schema` field/value for `zen.multi_agent_rig_design.v0.1`. Runtime
validation rejected them and did not create a Rig checkpoint. Position Designer
and all later roles were not called. No artistic/spatial proposal was accepted,
so this run provides no basis to judge a proposed rig's quality.

## Exact input and provenance

- Request: `Artist: BABYMONSTER. Song: SHEESH. Produce the requested case-specific design proposal from the supplied current Show snapshot and role instructions. This run is read-only.`
- Snapshot: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001\current_show_snapshot\snapshot.json`
- Profile: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001\current_show_snapshot\show_profile.json`
- Run artifact root: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001`
- Fingerprint: `b41d801b915cddfdd5017df787ad66b55941fbce415ab02ee8ec63acaa027bd5` (scan-derived, confidence `PARTIAL`)
- `GIT_HEAD` recorded in run: `20da57fd89e88516b67369222c43547f06962eed`
- `CONTEXT_HASH`: `495d96c77febb72942bacc1de260b0e1b1334c2ef476d161cfcce7033309b731`
- `REQUEST_HASH`: `e4fcdf2050900ba3bf8f8a458ba4c682c31fd5a3135a70f5b2415df0f774770c`
- Run interval: `2026-09-20 20:02:48` to `20:13:33` local time (about 645 seconds)
- Two prior run-state archives are retained under the USB run's `restart_archive/`; the Phase A snapshot directory remains in place.

The normalized input contains 57 fixtures, 6 fixture types, 7 Groups and 65
fixture/subfixture geometry records. Numeric coordinates and rotations were
available; no Stage/3D screenshot or calibrated axis semantics were available.
Cached capability records with a different Show fingerprint were not supplied
as current truth. `CURRENT_SHOW_CAPABILITY_STATUS=UNKNOWN_FOR_CURRENT_FINGERPRINT`;
coordinate axis semantics remain `UNKNOWN`. Fixture 9999 remains visible only
as protected, unavailable inventory evidence.

## Runtime and validation implemented

- Explicit `current_show_snapshot` input; no hard-coded machine-local scan path
  and no second MA2 scanner.
- Snapshot/profile schema and freshness checks, fingerprint retained in
  normalized context, `CONTEXT_HASH`, `run.json`, and each completed step.
- Resume rejection for a different Show fingerprint, request/context hash, or
  role order.
- Conditional role order:

  ```text
  RESEARCHER -> RIG_DESIGNER -> POSITION_DESIGNER
  -> LIGHTING_DESIGNER -> CRITIC -> FINALIZER
  ```

- No live snapshot continues to use the existing four-role order.
- Rig and Position semantic roles route through the existing
  `LIGHTING_DESIGNER` provider eligibility pool without changing private config.
- RIG/POS validators enforce live fixture/subfixture identity, matching Show
  fingerprint, Fixture 9999 exclusion, finite coordinates, no duplicate
  placement references, and no command/identity/Patch/Address/FixtureType
  mutation fields.
- Lighting Designer, Critic and Finalizer payloads include the validated
  upstream spatial artifacts when those checkpoints exist. Finalizer must
  reference the canonical Position artifact and may not contradict explicit
  fixture/subfixture coordinates.
- No MA2 transport, Resolver, Builder, or writeback was added or invoked.

## Test and self-check

- `python -m unittest discover -s tests -v`: **549 passed**.
- `python main.py --self-check`: **PASS**, `ma2_writes=0`; Field Core available,
  MA Bridge OFFLINE, no Workers configured.
- Focused live-spatial tests cover the no-snapshot compatibility path, six-role
  activation, snapshot hash/resume binding, unknown/protected fixture rejection,
  duplicate/non-finite placement rejection, exact artifact handoff, Finalizer
  consistency, and absence of MA/Builder/Resolver imports.
- A real-run-discovered evidence-validation boundary was tightened: canonical
  evidence/source checks now participate in the existing bounded role retry;
  failed response diagnostics check for API-key echo before persisting raw text.
  Regression coverage confirms the retry and secret guard.

## Real provider run

| Role | Result | Provider / evidence |
|---|---|---|
| Researcher | PASS | OpenRouter slot 5, one attempt; returned `OFFLINE_CACHED_CONTEXT`, empty source refs and empty resolved sources. Its artifact passed runtime validation. |
| Rig Designer | FAIL | Three bounded attempts; no accepted artifact. |
| Position Designer | NOT RUN | Blocked by missing validated Rig artifact. |
| Lighting Designer | NOT RUN | Did not receive Rig or Position artifacts. |
| Critic | NOT RUN | Not reached. |
| Finalizer | NOT RUN | Not reached; no final design artifact. |

Rig attempt evidence:

| Attempt | Eligible calls attempted | Transport result | Output result |
|---|---|---|---|
| 1 | slots 1, 3, 5 | Gemini slot 1: HTTP 503; NVIDIA slot 3: timeout at ~120 s; OpenRouter slot 5: response received | Missing required `schema` identity; `Role output schema must be zen.multi_agent_rig_design.v0.1.` |
| 2 | slots 1, 3, 5 | Gemini slot 1: HTTP 503; NVIDIA slot 3: timeout at ~120 s; OpenRouter slot 5: response received | Same missing schema identity; rejected |
| 3 | slots 1, 3 | Gemini slot 1: HTTP 503; NVIDIA slot 3: response received at 113 s | Same missing schema identity; rejected |

The failed responses contained the other required Rig fields but no `schema`
field. They were not normalized or repaired by Codex. `secret_check=PASS` was
recorded for each, and a scan comparing configured keys against run artifacts
found `SECRETS_LEAKED=NO`. The failed responses and bounded diagnostics remain
on the USB run directory; runtime state/cache is not committed.

## Required outcome fields

```text
CURRENT_SHOW_IDENTIFIED=YES (from saved Phase A snapshot)
CURRENT_SHOW_FINGERPRINT=b41d801b915cddfdd5017df787ad66b55941fbce415ab02ee8ec63acaa027bd5
FIXTURE_COUNT=57
FIXTURE_TYPES=6
GROUP_COUNT=7
CURRENT_STAGE_GEOMETRY_READABLE=YES (numeric geometry only; no Stage/3D image or axis semantics)
LIVE_SNAPSHOT_VALID=YES
LIVE_SNAPSHOT_IN_CONTEXT=YES
ROLE_EXECUTION_ORDER=RESEARCHER,RIG_DESIGNER,POSITION_DESIGNER,LIGHTING_DESIGNER,CRITIC,FINALIZER
RIG_DESIGNER_PROVIDER=OpenRouter slot 5 (attempts 1-2); NVIDIA NIM slot 3 (attempt 3)
RIG_ARTIFACT_VALID=NO
RIG_REFERENCES_VALID=NOT_EVALUATED
POSITION_DESIGNER_PROVIDER=NOT_RUN
POSITION_ARTIFACT_VALID=NOT_RUN
POSITION_REFERENCES_VALID=NOT_RUN
PROPOSED_FIXTURE_COUNT=0 (no accepted Position artifact)
SPATIAL_PROPOSAL_CREATED=NO
SPATIAL_WRITEBACK_PERFORMED=NO
LIGHTING_DESIGNER_RECEIVED_RIG_ARTIFACT=NO
LIGHTING_DESIGNER_RECEIVED_POSITION_ARTIFACT=NO
DESIGNER_ATTEMPTED_SLOTS=NOT_RUN
DESIGNER_ACCEPTED_SLOTS=NOT_RUN
DESIGNER_CANDIDATE_COUNT=0
CRITIC_ATTEMPTED_SLOTS=NOT_RUN
CRITIC_ACCEPTED_SLOTS=NOT_RUN
CRITIC_CANDIDATE_COUNT=0
FINALIZER_PROVIDER=NOT_RUN
FINAL_SCHEMA_VALID=NOT_REACHED
EVIDENCE_VALID=Researcher PASS; final evidence validation NOT_REACHED
SECRETS_LEAKED=NO
MA2_WRITES=0
MA2_WRITE_SUMMARY=NONE
CAPABILITY_GAPS=RIG provider output omitted required schema after three attempts; Position/downstream not reached; current-fingerprint fixture capabilities and coordinate-axis semantics remain UNKNOWN
CODEX_ARTISTIC_INTERVENTION=NONE
```

## Traditional Chinese handoff

這次沒有產生可接受的 ZEN 空間提案：RIG_DESIGNER 三次收到模型回應，
但都缺少必要的 `schema` 身分欄位，因此沒有建立 Rig checkpoint；Position
Designer 與後續角色沒有執行。故目前不能描述「ZEN 如何重新排列燈具」、
不能評論其空間概念，也不能判斷藝術品質。這不是空間設計失敗的判定，
而是 provider 輸出未符合角色 artifact 契約的執行阻塞。

已保存的 Phase A 快照顯示數值幾何可讀，但沒有經校準的舞台軸語意，也
沒有 Stage/3D 畫面；能力資料對這個 fingerprint 仍是 UNKNOWN。這些限制
不能靠 Group 或 FixtureType 名稱補猜。沒有執行任何 MA2 命令或寫入，
Fixture 9999、Patch、Address、Fixture ID/Type、Preset、Sequence、Executor
與 Stage geometry 均未觸碰。

## Remaining blocker

`RIG_DESIGNER_PROVIDER_OUTPUT_MISSING_REQUIRED_SCHEMA_AFTER_THREE_ATTEMPTS`

需要一個既有合格 provider 在不改寫空間內容的前提下輸出通過
`zen.multi_agent_rig_design.v0.1` 驗證的 artifact，之後才可繼續 Position、
Lighting Designer、Critic 與 Finalizer。此報告不授權調整角色提示、模型、
provider config 或開始 Move3D writeback。
