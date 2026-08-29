import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = ROOT / "gma2" / "plugins"
MA_NAMESPACE = "http://schemas.malighting.de/grandma2/xml/MA"


class GrandMA2PluginPackageTests(unittest.TestCase):
    def test_ma2_39_plugin_descriptor_references_paired_lua_with_exact_case(self):
        xml_path = PLUGIN_DIR / "ZEN_AGENT.xml"
        lua_path = PLUGIN_DIR / "ZEN_AGENT.lua"
        root = ET.parse(xml_path).getroot()
        self.assertEqual(root.tag, f"{{{MA_NAMESPACE}}}MA")
        self.assertEqual((root.attrib["major_vers"], root.attrib["minor_vers"], root.attrib["stream_vers"]), ("3", "9", "60"))
        self.assertIn("/3.9.60/MA.xsd", root.attrib["{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"])
        plugin = root.find(f"{{{MA_NAMESPACE}}}Plugin")
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.attrib, {"index": "0", "execute_on_load": "0", "name": "ZEN_AGENT", "luafile": "ZEN_AGENT.lua"})
        self.assertTrue(lua_path.is_file())
        self.assertEqual(lua_path.name, plugin.attrib["luafile"])

    def test_ma2_lua_entrypoint_uses_the_read_only_mailbox_protocol(self):
        lua = (PLUGIN_DIR / "ZEN_AGENT.lua").read_text(encoding="utf-8")
        portable_lua = (ROOT / "lua" / "ZEN_AGENT.lua").read_text(encoding="utf-8")
        self.assertEqual(lua, portable_lua)
        self.assertIn("local function main()", lua)
        self.assertIn("return main", lua)
        self.assertIn('gma.user.getvar("ZEN_AGENT_REQUEST")', lua)
        self.assertIn('gma.feedback("ZEN_DEBUG|REQUEST|" .. tostring(request))', lua)
        self.assertIn('gma.user.setvar("ZEN_AGENT_REQUEST", "")', lua)
        self.assertIn('tostring(request):match("^%s*(.-)%s*$")', lua)
        self.assertIn('normalized:match("^([A-Za-z0-9_-]+)%s+([a-z_]+)%s*(.-)%s*$")', lua)
        self.assertIn('feedback(visible_request_id, "ERROR", "MALFORMED_REQUEST")', lua)
        self.assertIn('argument == ""', lua)
        self.assertNotIn(')|([a-z_]+)|', lua)
        self.assertIn('"ZEN_STATE|" .. request_id', lua)
        self.assertIn('"DUPLICATE_REQUEST"', lua)
        self.assertIn('"MALFORMED_REQUEST"', lua)
        self.assertIn('"UNKNOWN_COMMAND"', lua)
        self.assertIn('command == "group_membership"', lua)
        for forbidden in ("gma.cmd", "Store", "Update", "Delete", "Clone", "Patch", "ClearSelection"):
            self.assertNotIn(forbidden, lua)
        self.assertNotIn("main(display_handle, argument)", lua)
        readme = (PLUGIN_DIR / "README.txt").read_text(encoding="utf-8")
        self.assertIn("ZEN_AGENT.xml", readme)
        self.assertIn("ZEN_AGENT.lua", readme)
        self.assertIn('SetUserVar $ZEN_AGENT_REQUEST="abc123 group_membership 1"', readme)
        self.assertIn("Plugin 3", readme)
        self.assertIn("ZEN_STATE|abc123|BEGIN|group_membership|1", readme)
        self.assertIn("import `ZEN_AGENT.xml` again", readme)


if __name__ == "__main__":
    unittest.main()
