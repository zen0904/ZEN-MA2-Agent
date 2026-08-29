ZEN MA2 Agent - grandMA2 3.9 Plugin import package
=====================================================

FILES THAT MUST STAY TOGETHER
-----------------------------
ZEN_AGENT.xml
ZEN_AGENT.lua

USB / onPC FILE LOCATION
------------------------
Copy both files, without renaming either one, to:

  USB drive:\gma2\importexport\

On grandMA2 onPC, the Import dialog can also browse the same pair from the
portable folder. Do not import the .lua file directly: import ZEN_AGENT.xml.

IMPORT
------
1. Open System > Plugin to open the Plugin Pool.
2. Press Edit and select an empty Plugin Pool object.
3. Press Import.
4. Browse to gma2\importexport on the USB drive and select ZEN_AGENT.xml.
5. Confirm Import, then Save. The Plugin Pool object is named ZEN_AGENT.
6. Press Reload in the Plugin editor and confirm, if the console asks to reload
   the plugin engine.

USERVAR MAILBOX TRANSPORT
-------------------------
After changing the Lua file, import `ZEN_AGENT.xml` again into the intended
Plugin Pool slot, then Save and Reload the Plugin. grandMA2 stores the imported
Plugin object in the show; replacing a USB file alone does not update an
already-imported object.

Set the one-shot request variable, then run the imported Plugin Pool object
using its actual slot. For example:

  SetUserVar $ZEN_AGENT_REQUEST="abc123 group_membership 1"
  Plugin 3

Use the actual imported Plugin Pool slot in place of `3`. The adapter emits
read-only Group object diagnostics before any membership result:

  ZEN_DEBUG|REQUEST|abc123|group_membership|1
  ZEN_DEBUG|GROUP_HANDLE|...
  ZEN_DEBUG|CLASS|...
  ZEN_DEBUG|AMOUNT|...
  ZEN_DEBUG|PROP_AMOUNT|...
  ZEN_DEBUG|PROP|<index>|<name>|<value>

The plugin clears `ZEN_AGENT_REQUEST` after safely copying it, so a stale
request cannot run a second time. It rejects malformed, duplicate, and unknown
requests. Until a Group child class is verified as a fixture member, the plugin
returns `ZEN_STATE|abc123|ERROR|UNSUPPORTED_SAFE_ACCESS` instead of silently
reporting an empty Group. It does not Store, Update, Delete, Clone, Patch,
Clear, or modify selection/programmer.

LAYOUT COBJECT VALIDATION (READ-ONLY)
--------------------------------------
Run these mailbox probes with a fresh request id each time. Replace `375` with
the actual imported Plugin Pool slot:

  SetUserVar $ZEN_AGENT_REQUEST="p11 object_probe Preset 1.1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="p42 object_probe Preset 4.2"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="p515 object_probe Preset 5.15"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="g1 object_probe Group 1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="g2 object_probe Group 2"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="g7 object_probe Group 7"
  Plugin 375

Each emits only read-only feedback: `ZEN_LAYOUT_PROBE|<id>|PATH|...`, then
`HANDLE`, `CLASS`, `NUMBER`, `NAME`, and `LABEL`. The documented `getobj.name`
value is used for both Name and Label; no unverified label accessor is called.
To validate a disposable Layout 99, first create it in MA2's Layout View with
one known object of each supported type, then use fresh IDs below. Replace the
placeholder object numbers and Plugin slot `375` with objects that actually
exist in the current show:

  SetUserVar $ZEN_AGENT_REQUEST="fx1 object_probe Fixture 1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="sf1 object_probe Subfixture 1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="m1 object_probe Macro 1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="ex11 object_probe Executor 1.1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="s1 object_probe Sequence 1"
  Plugin 375
  SetUserVar $ZEN_AGENT_REQUEST="ef1 object_probe Effect 1"
  Plugin 375

Then ask the Agent `Layout 99 裡有哪些物件？`. Its Logs page writes one
`layout_object_diagnostic` record for every exported item, including raw XML
tag/attributes, parent path, CObject tokens, label/name, and XY. Compare each
record to its matching `ZEN_LAYOUT_PROBE` output. Do not add a resolver mapping
until both observations match and no conflicting sample exists. A nil handle or
an object that MA2 cannot put in a Layout remains unsupported, not unknown type
inference.

LAYOUT FIXTURE GEOMETRY PROBE (READ-ONLY)
------------------------------------------
`Export Layout` is a partial CObject source: on grandMA2 3.9.60 it can omit a
visible Fixture item. To investigate the separate Fixture/Subfixture geometry
source without changing the Show, run:

  SetUserVar $ZEN_AGENT_REQUEST="lf99 layout_fixture_probe 99"
  Plugin 375

The bounded diagnostic emits `ZEN_LAYOUT_FIXTURE_PROBE` feedback for `Layout
99`: root/child handles, class, number, name, parent handle, child count, and
at most 16 properties. Traversal is limited to depth 2 and 12 children per
node. It only calls `gma.show.getobj.*` and `gma.show.property.*`; it does not
select, Store, Assign, Move, Delete, or modify the Layout.
