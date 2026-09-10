# General MA2 State

ZEN's State layer is a read-only, shared cache for Desktop, Phone, and future
workflow Skills. Every cached resource includes `updated_at`, `source`,
`stale`, and `error`. Disconnect marks records stale; an explicit or Chat-driven
refresh replaces them.

| Resource | Source | Current result |
| --- | --- | --- |
| `groups` | `List Group` | Pool number and name |
| `fixtures` | `List Fixture` | Fixture number, name, type |
| `layouts` | `List Layout` + adapter for an individual layout | Pool metadata; item type/reference/XY and optional width/height/rotation |
| `layout_items` | Partial LayoutState: native Export XML CObjects + Fixture geometry capability | Exported CObject references/geometry; Fixture/Subfixture XY currently `UNSUPPORTED` pending a separate safe provider |
| `group_membership` | Local native Export XML provider | Group number/name, ordered `Subfixture@fix_id` members, when the Agent can read onPC `importexport` |
| `sequences` | `List Sequence` | Number and name |
| `cues` | `List Cue <sequence>` | Number, name, and parsed trigger/fade/delay when present |
| `presets` | `List Preset <type>` | Type, number and label only; no content/value inspection |
| `effects` | `List Effect` | Number, label and only explicitly returned basic metadata |
| `pages` | `List Page` | Page number and label |
| `executors` | `List Executor` | Page/location and explicitly returned assignment metadata |
| `timecodes` | `List Timecode` | Pool number/name only; tracks/events/event times are explicitly `UNSUPPORTED` |
| `selection` | Verified MA2 3.9 API capability boundary | `UNSUPPORTED`: no verified non-mutating accessor exposes current fixture members |
| `programmer` | Verified MA2 3.9 API capability boundary | `UNSUPPORTED`: no verified non-mutating accessor exposes presence, members, attributes, or values |

## Read-only boundary

The runtime accepts only these state commands:

- `List Group`, `List Fixture`, `List Layout`, `List Sequence`, `List Cue <n>`
- `List Timecode`
- `Export Group <n> "ZEN_AGENT_G<n>_<request-id>.xml" /nc` for temporary local
  Group membership state only
- `SetUserVar $ZEN_AGENT_REQUEST="<request_id> <allow-listed request> <argument>"`
  followed by `Plugin <configured numeric Plugin Pool slot>`

No State provider can send `Store`, `Update`, `Delete`, `Clone`, `Patch`,
`Clear`, or a fixture/group selection command. Export writes only an
Agent-owned temporary XML file; it does not modify Show content. An unknown
adapter response is not parsed optimistically; it becomes `UNSUPPORTED` or
`ERROR` in the cache.

## FixtureType channel-profile export

`fixture_type_profiles` is an explicit, loopback-onPC-only read-only resource.
It uses native `Export FixtureType <id> "ZEN_AGENT_FT_<id>_<request-id>.xml"
/nc`, which exports the current Show's FixtureType object to the selected
drive's library and never changes the loaded Show. The provider accepts an XML
profile only when its numeric FixtureType index and reconstructed `id name
mode` label exactly match the current `List Fixture` label. It then exposes
the actual `ChannelType` inventory and derived technical capabilities with
source, hash and identity provenance.

Installed library profiles are not a substitute for this export. They may be
classified `LOCAL_PROFILE_CANDIDATE_BOUND` only after exact structural
comparison with a `SHOW_BOUND_VERIFIED` current-Show export. Pixel/shape
topology, Effect behavior, preset applicability and artistic role are outside
this provider's boundary.

## Timecode boundary

`List Timecode` is allow-listed as a read-only inventory source. The grandMA2
3.9 documentation verifies the positive whole-show `Timecode/Offset` property,
but it does not provide a verified non-mutating event/track readback contract
for this Agent. Therefore Timecode Offset v1 can only set a positive whole-show
offset after Preview and Approval. The verified 3.9.60 `List Timecode` read-back
uses a 30 FPS seconds:frames display (`0.50s` -> `0:15`); v1 therefore accepts
only exact 30 FPS whole-show offsets. Event count, per-event diffs, range offsets,
negative offsets, non-frame-aligned offsets, and exact event-time verification are reported as
`UNSUPPORTED`, never inferred from an empty event list.

## Group membership: local Export XML backend

For a same-machine grandMA2 onPC connection (`127.0.0.1` or `localhost`), the
Group membership provider generates a unique filename, sends the allow-listed
native command, waits for a fresh file, validates Group number and XML, then
updates the shared state cache. It only removes successful files named
`ZEN_AGENT_G<n>_<request-id>.xml`; malformed/failed exports remain for local
diagnostics. Files are rejected unless their name matches the request and their
mtime is newer than the export request.

`state_adapter.importexport_path` defaults to `"auto"`. Auto discovery prefers
the currently running `gma2onpc.exe` version's
`C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_*\\importexport`
directory, falling back to the newest available version. Set an absolute path
when the installation needs an explicit override:

```json
{
  "state_adapter": {
    "importexport_path": "C:\\ProgramData\\MA Lighting Technologies\\grandma\\gma2_V_3.9.60\\importexport"
  }
}
```

This backend has `local_export_access: true` only when MA2 is a loopback onPC
connection and the selected directory is readable. A LAN/remote MA2 endpoint
does not imply filesystem access and returns
`REMOTE_EXPORT_ACCESS_UNAVAILABLE`; ZEN does not pretend that a local path is
the console filesystem. Future remote backends remain separate providers.

## Layout geometry: local Export XML backend

`LayoutExportProvider` follows the same unique-name, fresh-mtime and
Agent-owned-cleanup boundary as Group membership, using `Export Layout <n>
"ZEN_AGENT_LAYOUT_<n>_<request-id>.xml" /nc`. It preserves `center_x`,
`center_y`, `size_w`, `size_h`, and `rotation` for exported CObjects. A direct
exported fixture/group reference is typed; otherwise the `CObject` reference is
retained as `unknown` rather than guessed. It requires `local_export_access`;
remote use returns `REMOTE_EXPORT_ACCESS_UNAVAILABLE`.

This is explicitly a partial LayoutState. A grandMA2 3.9.60 Layout 99 export
was observed to contain its Group CObject while omitting a visible Fixture 101.
Consequently `layout_cobjects` is `supported`, while
`layout_fixture_geometry` is `UNSUPPORTED` until a separate verified read-only
provider supplies Fixture/Subfixture XY. A Layout fixture query must report the
unavailable capability instead of interpreting an empty exported fixture list
as “no fixtures”.

Sequence/Cue, Preset, Effect, Page and Executor inventories use Telnet `List`
commands and therefore do not require local filesystem access. All StateStore
records expose `source`, `updated_at`, `stale`, `error`, and `capability`.

The exported Group schema is documented in
[MA2 Group Export research](MA2_GROUP_EXPORT.md). `Subfixture@fix_id` is the
only verified membership reference. Its XML appearance order is kept as
`export_order`, not asserted as separate MA selection-order metadata.

## Lua adapter install

Copy [ZEN_AGENT.xml](../gma2/plugins/ZEN_AGENT.xml) and its paired
[ZEN_AGENT.lua](../gma2/plugins/ZEN_AGENT.lua) to `gma2/importexport` on the
USB drive. In **System → Plugin**, edit an empty Plugin Pool object, press
**Import**, select `ZEN_AGENT.xml`, then save/reload the plugin. The imported
object is named `ZEN_AGENT`. The default portable setting invokes:

```text
SetUserVar $ZEN_AGENT_REQUEST="abc123 group_membership 1"
Plugin 12
```

If the console uses a numeric Plugin Pool slot, set only this portable,
non-secret value in `config/settings.json`:

```json
{
  "state_adapter": {
    "plugin_slot": 12,
    "timeout_seconds": 3.0
  }
}
```

The command compiler permits only the exact `ZEN_AGENT` label or a numeric slot,
with a generated request id and allow-listed request. The bundled Lua file is
kept for object diagnostics and future verified adapter resources; Group
membership no longer depends on its child/property probe. It only traverses
objects and uses `gma.feedback()` to emit framed responses:

```text
ZEN_STATE|abc123|BEGIN|group_membership|1
ZEN_STATE|abc123|MEMBER|101
ZEN_STATE|abc123|END|group_membership|1
```

It currently returns a request-id-scoped `ZEN_STATE|<id>|ERROR|UNKNOWN_COMMAND`
for Selection and Programmer until a real console test proves a non-mutating
accessor. Do not replace this with a Group-selection, Clear, Store, or
Programmer probe.

## Programmer and Selection inspect boundary

The installed grandMA2 3.9.60 API Test documents `gma.show.getobj.*`,
`gma.show.property.*`, `gma.user.getvar`, `gma.user.getcmddest`, and
`gma.user.getselectedexec`. It does not document a read-only accessor for the
current selected Fixture/Subfixture list or for Programmer presence, active
Fixture members, attributes, or values. The normal Agent therefore records a
typed `UNSUPPORTED` cache record and does not contact the MA2 adapter for these
Chat queries.

The paired plugin includes `selection_probe` and `programmer_probe` as bounded
diagnostics only. They emit API/object metadata through `ZEN_INSPECT_PROBE` and
never call `gma.cmd`; they are not a state provider. A future provider may only
be enabled after repeatable real-console evidence ties one of those read-only
API values to Selection or Programmer state. Until then, `programmer.inspect`
remains a disabled SAFE Skill and Show Diagnostics does not depend on it.

## Chat dependencies

`HYBRID 裡有哪些燈？` first refreshes Groups if needed, resolves the Group name,
then requests `group_membership`. `Layout 1 裡有哪些燈？`, `我現在選了哪些
Fixture？`, `現在 Programmer 有東西嗎？`, `有哪些 Sequence？`, and `Sequence 5
有哪些 Cue？` similarly refresh their required state automatically.
