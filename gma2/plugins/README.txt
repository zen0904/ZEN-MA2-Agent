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
  ZEN_DEBUG|CHILD|0|<class>|<number>|<name>

The plugin clears `ZEN_AGENT_REQUEST` after safely copying it, so a stale
request cannot run a second time. It rejects malformed, duplicate, and unknown
requests. Until a Group child class is verified as a fixture member, the plugin
returns `ZEN_STATE|abc123|ERROR|UNSUPPORTED_SAFE_ACCESS` instead of silently
reporting an empty Group. It does not Store, Update, Delete, Clone, Patch,
Clear, or modify selection/programmer.
