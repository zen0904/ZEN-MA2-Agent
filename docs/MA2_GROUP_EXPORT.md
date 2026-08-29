# grandMA2 3.9 Group export research

This is a diagnostic-format record and offline parser prototype. It is **not**
a live ZEN state provider and does not change the mailbox, Lua adapter,
AgentCore, UI, or Skills.

## Verified export command

The grandMA2 3.9.60/3.9.61 bundled system tests use this form:

```text
Export Group 1 "ZEN_GROUP_1_EXPORT.xml" /nc
```

`/nc` suppresses the command-line confirmation. The command writes an XML
file to the onPC installation's active `importexport` directory; it does not
alter Group data, the active selection, or the programmer. On the verified
3.9.60 onPC installation the resulting file was:

```text
C:\ProgramData\MA Lighting Technologies\grandma\gma2_V_3.9.60\importexport\ZEN_GROUP_1_EXPORT.xml
```

The active version/path is installation-dependent. The portable Agent must not
assume this path, and this research round does not automate the command.

## Verified Group 1 structure

The live Group 1 export contained this structure (fixture list abbreviated):

```xml
<MA xmlns="http://schemas.malighting.de/grandma2/xml/MA"
    major_vers="3" minor_vers="9" stream_vers="60">
  <Info datetime="..." showfile="22222" />
  <Group index="0" name="HYBRID">
    <Subfixtures>
      <Subfixture fix_id="101" />
      <Subfixture fix_id="102" />
      <!-- more Subfixture elements -->
    </Subfixtures>
  </Group>
</MA>
```

The user-facing Group number is one-based, while the exported `Group@index` is
zero-based: Group 1 exported as `index="0"`. Membership is the ordered
`Subfixture/@fix_id` list. The observed file contains fixture/subfixture IDs,
not Channel IDs. It has no `Channel`, `Fixture`, `Selection`, `MATricks`,
`Block`, `Wing`, or explicit selection-order attribute. Element order is
preserved by the parser, but it is not asserted to be an independently
documented MA2 selection-order field.

## Offline prototype

`zen_ma2_agent.state.providers.group_export.group_membership_from_export()`
accepts XML text/bytes or a local `Path`, validates the MA2 Group shape, maps
the requested one-based Group number, and returns:

```python
{
    "group_no": 1,
    "name": "HYBRID",
    "fixtures": [101, 102],
    "source": "ma2_group_export_xml",
}
```

It distinguishes an empty `<Subfixtures>` list from missing membership XML and
rejects malformed or invalid `fix_id` data. It is intentionally not imported
by `AgentCore` and does not execute MA2 commands. A future runtime integration
would need a separate portable-path, file-transfer, freshness, and safety
design review.
