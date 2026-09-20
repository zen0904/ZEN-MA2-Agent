# SHEESH Live Snapshot Upstream Spatial Runtime 001

**Status:** STRUCTURAL CONTRACT HARDENED; CONTROLLED RERUN BLOCKED AT `RESEARCHER`
**Run:** `SHEESH_CURRENT_SHOW_REDESIGN_001`
**Read-only boundary:** `MA2_WRITES=0`
**Artistic provenance:** `CODEX_ARTISTIC_INTERVENTION=NONE`

## Result

The conditional live-Show runtime path is implemented. The saved Phase A
snapshot normalized successfully, entered the context hash, and was recorded in
run metadata. The existing no-snapshot four-role pipeline remains intact.

The first real run stopped at `RIG_DESIGNER`. Three bounded role attempts received
transport-successful JSON from a provider, but all three responses omitted the
required `schema` field/value for `zen.multi_agent_rig_design.v0.1`. Runtime
validation rejected them and did not create a Rig checkpoint. Position Designer
and all later roles were not called. No artistic/spatial proposal was accepted,
so this run provides no basis to judge a proposed rig's quality.

The structural contract is now hardened without changing spatial/artistic
content. Both spatial system prompts require an exact first `schema` key. A
bounded deterministic normalizer may add only the known Rig or Position schema
identity when the provider JSON is an object, the schema key is absent, every
other required top-level field is already present, and
`codex_artistic_intervention` is exactly `NONE`. Wrong/blank schemas, missing
fields, invalid references, Fixture 9999, mutation/command content and every
other validation failure remain rejected. Raw provider text and the accepted
normalized artifact remain separate, secret-safe audit evidence.

The controlled rerun from commit `e3a81ba82747660aac02725ca0e2cbac2bbea7d5`
used the same request, run id and Phase A snapshot through the formal restart
archive path. It stopped at a new upstream blocker: `RESEARCHER` exhausted three
bounded attempts because transport-successful OpenRouter artifacts used
non-canonical shapes in `sources`. Rig Designer and all downstream roles were
therefore not called. This is not evidence for or against a spatial proposal.

## Exact input and provenance

- Request: `Artist: BABYMONSTER. Song: SHEESH. Produce the requested case-specific design proposal from the supplied current Show snapshot and role instructions. This run is read-only.`
- Snapshot: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001\current_show_snapshot\snapshot.json`
- Profile: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001\current_show_snapshot\show_profile.json`
- Run artifact root: `E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001`
- Fingerprint: `b41d801b915cddfdd5017df787ad66b55941fbce415ab02ee8ec63acaa027bd5` (scan-derived, confidence `PARTIAL`)
- First-run `GIT_HEAD`: `20da57fd89e88516b67369222c43547f06962eed`
- First-run `CONTEXT_HASH`: `495d96c77febb72942bacc1de260b0e1b1334c2ef476d161cfcce7033309b731`
- `REQUEST_HASH`: `e4fcdf2050900ba3bf8f8a458ba4c682c31fd5a3135a70f5b2415df0f774770c`
- First-run interval: `2026-09-20 20:02:48` to `20:13:33` local time (about 645 seconds)
- Controlled-rerun `GIT_HEAD`: `e3a81ba82747660aac02725ca0e2cbac2bbea7d5`
- Controlled-rerun `CONTEXT_HASH`: `33bcc9367308874ed3bcb41c9271e84d13586a16731f4a2509e95906811312e2`
- Controlled-rerun interval: `2026-09-20 20:33:50` to `20:35:04` local time (about 75 seconds)
- Three prior run-state archives are retained under the USB run's `restart_archive/`; the Phase A snapshot directory remains in place.

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

## Structural repair verification

- Rig and Position prompts now use the established exact-first-schema contract.
- Metadata-only normalization is limited to `RIG_DESIGNER` and
  `POSITION_DESIGNER`; it can add only one `schema` field.
- Diagnostics record whether normalization occurred. When it does, the exact
  original response SHA256/character count and secret-safe raw response are
  retained separately from the normalized checkpoint.
- Already-valid outputs are unchanged. Missing artistic/spatial fields are
  never added by code.

## Test and self-check

- `python -m unittest discover -s tests -v`: **559 passed**.
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

## First real provider run (before structural repair)

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

## Controlled rerun after structural repair

The rerun retained all earlier evidence in a third `restart_archive/` entry and
recorded `GIT_HEAD=e3a81ba82747660aac02725ca0e2cbac2bbea7d5`.

| Researcher attempt | Provider transport | Artifact result |
|---|---|---|
| 1 | Groq slot 2 HTTP 403; Mistral slot 4 HTTP 429; OpenRouter slot 5 success | Schema-valid Research artifact, but its nine `sources` items used `{evidence_ref, summary}` instead of canonical `{source_id, record_id}` identities; canonical source resolution rejected `unknown source_id`. |
| 2 | Groq slot 2 HTTP 403; Mistral slot 4 HTTP 429; OpenRouter slot 5 success | Invalid JSON; rejected before evidence validation. |
| 3 | Groq slot 2 HTTP 403; Mistral slot 4 HTTP 429; OpenRouter slot 5 success | Schema-valid envelope, but `sources` contained ten strings rather than canonical identity objects; canonical source resolution again rejected `unknown source_id`. |

All attempt responses passed the secret-echo check. A scan of current run JSON
artifacts against configured provider keys found `SECRETS_LEAKED=NO`. The
current run contains no completed role checkpoint because Researcher never
passed canonical source validation. `MA2_WRITES=0`.

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
RESEARCHER_PROVIDER=OpenRouter slot 5 (transport-successful; canonical source validation failed in attempts 1 and 3; attempt 2 invalid JSON)
RIG_DESIGNER_ATTEMPTED_SLOTS=NOT_RUN_IN_CONTROLLED_RERUN
RIG_DESIGNER_PROVIDER=NOT_RUN_IN_CONTROLLED_RERUN
RIG_RAW_SCHEMA_PRESENT=NOT_RUN
RIG_STRUCTURAL_NORMALIZATION_APPLIED=NOT_RUN
RIG_ARTIFACT_VALID=NOT_RUN
RIG_REFERENCES_VALID=NOT_RUN
POSITION_DESIGNER_ATTEMPTED_SLOTS=NOT_RUN
POSITION_DESIGNER_PROVIDER=NOT_RUN
POSITION_RAW_SCHEMA_PRESENT=NOT_RUN
POSITION_STRUCTURAL_NORMALIZATION_APPLIED=NOT_RUN
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
SPATIAL_CONSISTENCY_VALID=NOT_REACHED
EVIDENCE_VALID=NO (Researcher canonical source validation failed); final evidence validation NOT_REACHED
SECRETS_LEAKED=NO
MA2_WRITES=0
MA2_WRITE_SUMMARY=NONE
CAPABILITY_GAPS=Researcher provider output did not use canonical source identity shape after bounded retries; spatial roles/downstream not reached; current-fingerprint fixture capabilities and coordinate-axis semantics remain UNKNOWN
CODEX_ARTISTIC_INTERVENTION=NONE
```

## Traditional Chinese handoff

這次 controlled rerun 仍沒有產生可接受的 ZEN 空間提案。schema 結構修復
本身已由 559 個測試驗證，但新的真實 run 在 Researcher 就停止：OpenRouter
回傳的 `sources` 使用了 `{evidence_ref, summary}` 或字串清單，而不是 runtime
要求的 canonical source identity，因此 provenance validator 正確 fail closed。
RIG_DESIGNER、POSITION_DESIGNER 與後續角色都沒有執行。故目前不能描述
「ZEN 如何重新排列燈具」、不能評論其空間概念，也不能判斷藝術品質。

已保存的 Phase A 快照顯示數值幾何可讀，但沒有經校準的舞台軸語意，也
沒有 Stage/3D 畫面；能力資料對這個 fingerprint 仍是 UNKNOWN。這些限制
不能靠 Group 或 FixtureType 名稱補猜。沒有執行任何 MA2 命令或寫入，
Fixture 9999、Patch、Address、Fixture ID/Type、Preset、Sequence、Executor
與 Stage geometry 均未觸碰。

## Remaining blocker

`RESEARCHER_PROVIDER_OUTPUT_NON_CANONICAL_SOURCE_IDENTITY_AFTER_BOUNDED_RETRIES`

需要 Researcher 先輸出 canonical source identity，或在沒有可引用 source 時
保留空 `sources`，並通過現有 provenance validator；之後才可進入已修復的
Rig/Position 結構契約。此報告不授權 Codex 修補 Researcher 內容、調整模型、
provider config，或開始 Move3D writeback。
