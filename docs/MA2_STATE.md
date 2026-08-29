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
| `group_membership` | `ZEN_AGENT` adapter | Group number/name and sparse Fixture IDs |
| `sequences` | `List Sequence` | Number and name |
| `cues` | `List Cue <sequence>` | Number, name, and parsed trigger/fade/delay when present |
| `selection` | `ZEN_AGENT` adapter | `UNSUPPORTED` unless a verified non-mutating fixture-ID accessor is available |
| `programmer` | `ZEN_AGENT` adapter | `UNSUPPORTED` unless a verified non-mutating active-value summary is available |

## Read-only boundary

The runtime accepts only these state commands:

- `List Group`, `List Fixture`, `List Layout`, `List Sequence`, `List Cue <n>`
- `SetUserVar $ZEN_AGENT_REQUEST="<request_id> <allow-listed request> <argument>"`
  followed by `Plugin <configured numeric Plugin Pool slot>`

No State provider can send `Store`, `Update`, `Delete`, `Clone`, `Patch`,
`Clear`, or a fixture/group selection command. An unknown adapter response is
not parsed optimistically; it becomes `UNSUPPORTED` or `ERROR` in the cache.

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
with a generated request id and allow-listed request. The bundled Lua file only
traverses objects and uses `gma.feedback()` to emit framed responses:

```text
ZEN_STATE|abc123|BEGIN|group_membership|1
ZEN_STATE|abc123|MEMBER|101
ZEN_STATE|abc123|END|group_membership|1
```

It currently returns a request-id-scoped `ZEN_STATE|<id>|ERROR|UNKNOWN_COMMAND`
for Selection and Programmer until a real console test proves a non-mutating
accessor. Do not replace this with a Group-selection, Clear, Store, or
Programmer probe.

## Chat dependencies

`HYBRID 裡有哪些燈？` first refreshes Groups if needed, resolves the Group name,
then requests `group_membership`. `Layout 1 裡有哪些燈？`, `我現在選了哪些
Fixture？`, `現在 Programmer 有東西嗎？`, `有哪些 Sequence？`, and `Sequence 5
有哪些 Cue？` similarly refresh their required state automatically.
