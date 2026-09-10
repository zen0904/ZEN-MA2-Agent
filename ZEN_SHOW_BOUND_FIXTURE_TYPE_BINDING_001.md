# Show-Bound Fixture Type / Channel Profile Binding 001

**Status:** `PARTIAL`

Machine-readable real-console evidence is preserved in
`data/ZEN_SHOW_BOUND_FIXTURE_TYPE_BINDING_001.json`.

## Real-console preflight

- Telnet loopback READY: `True` as `MM`.
- Expected Existing Show fingerprint: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.
- Fresh loaded-Show fingerprint: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.
- Existing Show identity/profile match: `MATCH`.
- Fixture `9999` was not selected, exported, or addressed: `YES`.
- Native Export feedback: all six `Export FixtureType <id>` commands returned
  `Executing` without an MA2 error; each external temporary XML was removed
  after its strict validation failure.

## Binding method and provenance

`List Fixture` exact type label -> native `Export FixtureType <id>` -> exact XML index/name/mode identity -> parsed ChannelType/ChannelFunction inventory -> technical-definition SHA-256.
No name-only local profile match can establish a Show binding. Local candidates are compared only after `SHOW_BOUND_VERIFIED`.

## Results by current Show FixtureType

### `2 ZEN BAW 20R Mode 2`

- FixtureType numeric ID: `2`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

### `3 ZEN DMH-160 St_Preset`

- FixtureType numeric ID: `3`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

### `4 ZEN K10 Shapes`

- FixtureType numeric ID: `4`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

### `5 ZEN MAC AU XB Standard`

- FixtureType numeric ID: `5`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

### `6 ZEN LEDPar 9c 9Ch Mode A`

- FixtureType numeric ID: `6`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

### `7 Atomic 3000 LED Extended`

- FixtureType numeric ID: `7`.
- Export / provenance state: `PARTIAL` via `ma2_export_fixture_type_xml`.
- Exact identity verification: `FAIL / NOT_AVAILABLE`.
- Failure reason: `EXPORT_FIXTURE_TYPE_ID_MISMATCH`.
- Technical-definition SHA-256: `UNAVAILABLE`.
- XML SHA-256: `UNAVAILABLE`.
- Capability classification: UNKNOWN.
- Local profile candidate comparison: `NOT_ATTEMPTED_NO_SHOW_BOUND_EXPORT`.

#### Parsed ChannelType / ChannelFunction inventory

- `NOT_AVAILABLE` — no verified exported channel inventory.

## B3 eligibility and A/B readiness

Show-bound technical capability can support only future case-specific resource eligibility. It does not create a permanent fixture role, case assignment, geometry/position semantics, Effect behavior, or action grammar.
- `REAL_SONG_EXISTING_SHOW_AB_002`: `NOT_READY_FOR_EXPRESSIVE_ACTION_DELTA`.
- Reason: One or more current FixtureTypes did not establish a Show-bound technical definition.

## Exact current blocker

The loaded Existing Show is confirmed by the fresh scanned fingerprint, and
native export accepted every requested FixtureType numeric ID. However, all six
temporary XML exports presented a `FixtureType@index` that did not equal the
List-derived current-Show pool ID, so the implementation correctly returned
`EXPORT_FIXTURE_TYPE_ID_MISMATCH` before channel inventory/capabilities could
be used. The temporary XML is deliberately removed even on failure; therefore
no raw channel content, technical fingerprint, or local-profile comparison was
retained for this run.

This is a real-console schema/binding limitation, not a fixture capability
claim. Do not weaken the ID rule or substitute a similar local profile. A
future bounded research task must establish whether the export XML index is a
library-local serialization index and, if so, what additional Show-bound
identity evidence can safely bind it to the requested current-Show FixtureType
without treating labels alone as proof.

## Safety audit

- MA2 objects modified: `NONE`.
- MA2 object write audit: `ZERO_WRITES`.
- Allowed console transport was Login, List Group, List Fixture, List Preset All and native external `Export FixtureType` only.
- Unexpected commands: `none`.
- Production Designer: `UNCHANGED`; B3: `GUIDANCE_ASSISTED_AB_ONLY`; `ZEN_STYLE_PROFILE`: `DEFERRED`.
