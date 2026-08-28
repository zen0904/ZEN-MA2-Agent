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

    def test_ma2_lua_entrypoint_preserves_zen_state_bridge_protocol(self):
        lua = (PLUGIN_DIR / "ZEN_AGENT.lua").read_text(encoding="utf-8")
        self.assertIn("local function main(argument)", lua)
        self.assertIn("return main", lua)
        self.assertIn('gma.feedback("ZEN_DEBUG|ARG|" .. tostring(debug_argument))', lua)
        self.assertIn('if debug_argument == nil or tostring(debug_argument) == "" then debug_argument = "nil" end', lua)
        self.assertIn('gma.echo("ZEN_STATE|"', lua)
        self.assertIn('gma.echo("ZEN_STATE_ERROR|"', lua)
        self.assertNotIn("main(display_handle, argument)", lua)
        readme = (PLUGIN_DIR / "README.txt").read_text(encoding="utf-8")
        self.assertIn("ZEN_AGENT.xml", readme)
        self.assertIn("ZEN_AGENT.lua", readme)
        self.assertIn('Plugin 3 "group_membership 1"', readme)
        self.assertIn('ZEN_DEBUG|ARG|group_membership 1', readme)


if __name__ == "__main__":
    unittest.main()
