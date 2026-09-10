# Show-Bound Fixture Type / Channel Profile Binding 001

Status: `REAL_CONSOLE_VERIFICATION_REQUIRED` — the read-only binding provider
is implemented and locally tested, but no grandMA2 onPC process was running for
this task. No current-Show Fixture Type capability has been promoted yet.

## Objective and evidence rule

This work establishes the only acceptable path from a scanned current-Show
Fixture Type to attribute capability:

```text
List Fixture exact type label
  -> Export FixtureType exact numeric id (current Show)
  -> exported XML exact identity check
  -> parsed ChannelType / ChannelFunction inventory
  -> SHOW_BOUND_VERIFIED capability record
```

It does not select an artistic role, create a `case_role_assignment`, infer
placement/geometry, prove Effect behavior, or activate Designer behavior.
HYBRID and BEAM sharing a technical type remains unrelated to their possible
song/case use.

## Methods investigated

| Method | Result | Evidence boundary |
| --- | --- | --- |
| Existing `List Fixture` / Scanner | `PARTIAL` | Confirms a current Fixture's exact displayed type label, but has no channel inventory. |
| Existing Group/Layout/Preset exports | `UNSUPPORTED_FOR_BINDING` | These do not expose a current Show FixtureType definition. Preset export is deliberately not reopened. |
| Existing Lua `gma.show.getobj.*` / property probes | `UNSUPPORTED_FOR_BINDING` | The bundled read-only probes do not have real-console evidence for safe FixtureType/channel tree traversal. They were not broadened by guesswork. |
| Native `Export FixtureType` | `IMPLEMENTED_LOCAL_TESTED` | Local MA2 3.9.60 help identifies FixtureType as a Show-file object and Export as a Show-to-library operation. The provider exports only an Agent-owned external XML file, then parses and removes it. Real current-Show execution remains required. |
| Installed library XML/XMLP candidates | `LOCAL_PROFILE_CANDIDATE_UNBOUND` | They remain useful comparison inputs only after a Show export exists; name/model similarity never binds one. |

## Implemented read-only provider

`FixtureTypeExportProvider` is loopback-onPC only. It accepts the exact type
label already returned by `List Fixture`, extracts only its explicit leading
FixtureType ID, and requests:

```text
Export FixtureType <exact-id> "ZEN_AGENT_FT_<id>_<request-id>.xml" /nc
```

MA2 documents `Export` as a transfer from the Show to its library; this command
does not Store, Update, Delete, Patch, Import, Assign, select fixtures, or
modify any Show object. The only external write is an owned temporary XML file
in the selected drive's FixtureType library. The provider waits for a fresh,
stable, well-formed file, validates it, then deletes only that exact
Agent-owned filename.

The parser requires all of the following before it emits a capability:

1. exactly one `FixtureType` XML element;
2. exported `FixtureType@index` equals the current List-derived numeric ID;
3. reconstructed `"<id> <name> <mode>"` equals the complete current `List Fixture`
   type label exactly; and
4. at least one parsed `ChannelType` record.

Failure gives an explicit error such as
`EXPORT_FIXTURE_TYPE_ID_MISMATCH`, `EXPORT_FIXTURE_TYPE_LABEL_MISMATCH`,
`EXPORT_FIXTURE_TYPE_COUNT_MISMATCH`, or
`EXPORT_FIXTURE_TYPE_CHANNELS_NOT_PRESENT`; it never returns a partial
capability claim.

## Current-Show result

The actual onPC application was not running during this task, so no native
export was sent. Every current Show type remains `UNKNOWN_FOR_EXISTING_SHOW`:

| Current scanned type | Current binding state | Channel / attribute result | Failure reason |
| --- | --- | --- | --- |
| `2 ZEN BAW 20R Mode 2` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |
| `3 ZEN DMH-160 St_Preset` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |
| `5 ZEN MAC AU XB Standard` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |
| `4 ZEN K10 Shapes` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |
| `6 ZEN LEDPar 9c 9Ch Mode A` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |
| `7 Atomic 3000 LED Extended` | `REAL_CONSOLE_VERIFICATION_REQUIRED` | `UNKNOWN` | no current-Show export captured |

Consequently DIMMER, COLOR, PAN, TILT, POSITION, GOBO, PRISM, ZOOM, FOCUS,
FROST, SHUTTER/STROBE and PIXEL/SHAPE are still unknown for each current Show
type. Fixture `9999` is not selected, exported, or otherwise touched.

## What a verified result contains

After a successful exact current-Show export, the record schema is
`zen.fixture_type_channel_profile.v0.1` with:

- exact List label, FixtureType ID, XML index, name, mode and MA version;
- every parsed `ChannelType` and its `ChannelFunction` fields;
- a SHA-256 fingerprint of the parsed technical channel definition;
- typed capability outcomes for DIMMER, COLOR, PAN, TILT, POSITION, GOBO,
  PRISM, ZOOM, FOCUS, FROST and SHUTTER/STROBE; and
- explicit `PIXEL_SHAPE: UNCLASSIFIED_FROM_CHANNEL_INVENTORY` until a separate
  FixtureType topology interpretation is safely verified.

Absence of a deterministically classified channel becomes
`NOT_PRESENT_IN_EXPORTED_PROFILE`; it is not confused with an unavailable
export. Raw channel/function inventory remains available for later, bounded
capability work without inventing artistic semantics.

## Local profile candidate binding

Only after a `SHOW_BOUND_VERIFIED` export exists may a local XML/XMLP candidate
be compared. The comparison fingerprints the complete parsed ChannelType and
ChannelFunction definition, excluding labels, dates and library pool indices.
An exact structural match is `LOCAL_PROFILE_CANDIDATE_BOUND`; any difference
remains `LOCAL_PROFILE_CANDIDATE_UNBOUND`. Candidate filename/name similarity
alone is never a binding.

No installed local candidate is marked bound in this task because the required
current-Show export is absent.

## Focused test evidence

Local deterministic tests verify:

- exact current label/id/channel identity yields `SHOW_BOUND_VERIFIED`;
- mismatched ID, mismatched label, multiple FixtureTypes and missing channel
  inventory fail closed;
- a local profile binds only with an exact structural channel-definition hash;
- exports use a unique Agent-owned filename and clean it up;
- remote consoles are blocked before an export; and
- Scanner retains optional verified profiles without changing existing Fixture
  inventory contracts.

## Exact real-console verification step

With the Existing Show loaded in grandMA2 onPC, Telnet READY on loopback, and
the selected MA2 drive corresponding to the provider-resolved `library`
directory, explicitly refresh `fixture_type_profiles`. The provider will first
refresh fixture inventory if necessary, then export each unique current Show
type once. For every XML it must pass the four identity/channel checks above.

If MA2 writes a file to another selected drive, times out, changes the label,
or returns a different index, preserve that exact failure state and do not use
the local candidate. A successful export is a read-only Show inspection, but
its output must still be retained as provenance (identity, export feedback,
hash and timestamp) before capability-to-role eligibility is considered.

## B3 and A/B readiness

No B3 role eligibility is derived in this task. Even a later technical
capability record only makes a Group eligible for a future case-specific
Design Intent; it does not establish fixture priority, permanent role, Effect
behavior, position semantics or an action grammar.

`REAL_SONG_EXISTING_SHOW_AB_002` remains `NOT_READY_FOR_EXPRESSIVE_ACTION_DELTA`.
The blocker has narrowed from “no safe method” to one real-console execution
of the implemented current-Show export path plus evidence review.

## Safety

- Production Designer: `UNCHANGED`.
- Experimental B3: `GUIDANCE_ASSISTED_AB_ONLY`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- MA2 objects modified: `NONE`.
- MA2 write audit: `ZERO_WRITES`.
