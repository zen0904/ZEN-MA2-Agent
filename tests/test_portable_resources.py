import importlib.util
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("portable_resources", ROOT / "scripts" / "portable_resources.py")
portable_resources = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(portable_resources)


class PortableResourceTests(unittest.TestCase):
    def test_plugin_files_are_required_nonempty_and_reference_exact_lua_name(self):
        with tempfile.TemporaryDirectory(prefix="zen-portable-") as temporary:
            bundle = Path(temporary)
            for name in ("web", "lua", "skills", "config", "gma2"):
                copytree(ROOT / name, bundle / name)
            for name in ("logs", "cache"):
                (bundle / name).mkdir()
            files = portable_resources.assert_portable_resources(bundle)
            self.assertEqual(files, ["gma2\\plugins\\ZEN_AGENT.xml", "gma2\\plugins\\ZEN_AGENT.lua"])
            (bundle / "gma2" / "plugins" / "ZEN_AGENT.lua").unlink()
            with self.assertRaisesRegex(RuntimeError, "ZEN_AGENT.lua"):
                portable_resources.assert_portable_resources(bundle)
