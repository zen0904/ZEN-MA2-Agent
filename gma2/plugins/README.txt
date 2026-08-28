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

RUN / CHECK
-----------
Run the imported Plugin Pool object normally, or use:

  Plugin "ZEN_AGENT" "group_membership 1"

The adapter emits a System Monitor line beginning with:

  ZEN_STATE|group_membership|

For a layout request, use:

  Plugin "ZEN_AGENT" "layouts 1"

The ZEN MA2 Agent sends these read-only requests automatically. The plugin does
not Store, Update, Delete, Clone, Patch, Clear, or select fixtures.
