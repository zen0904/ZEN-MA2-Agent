import importlib.util
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "portable_resources", ROOT / "scripts" / "portable_resources.py"
)
portable_resources = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(portable_resources)


class PortableResourceTests(unittest.TestCase):
    def _bundle(self, temporary: str) -> Path:
        bundle = Path(temporary)
        for name in (
            "lua",
            "skills",
            "config",
            "gma2",
            "semantic_presets",
            "geometry",
            "examples",
        ):
            copytree(ROOT / name, bundle / name)
        for name in ("logs", "cache", "data"):
            (bundle / name).mkdir()
        return bundle

    def test_plugin_files_are_required_nonempty_and_reference_exact_lua_name(self):
        with tempfile.TemporaryDirectory(prefix="zen-portable-") as temporary:
            bundle = self._bundle(temporary)
            files = portable_resources.assert_portable_resources(bundle)
            self.assertEqual(
                files,
                ["gma2/plugins/ZEN_AGENT.xml", "gma2/plugins/ZEN_AGENT.lua"],
            )
            self.assertTrue((bundle / "geometry" / "ZEN_STAGE_AXIS_PROFILE.json").is_file())
            (bundle / "gma2" / "plugins" / "ZEN_AGENT.lua").unlink()
            with self.assertRaisesRegex(RuntimeError, "ZEN_AGENT.lua"):
                portable_resources.assert_portable_resources(bundle)

    def test_song_inputs_are_required_portable_resources(self):
        with tempfile.TemporaryDirectory(prefix="zen-portable-") as temporary:
            bundle = self._bundle(temporary)
            for filename in (
                "FIRST_SONG_INPUT.json",
                "REALISTIC_SONG_ANALYSIS.json",
                "REALISTIC_SONG_SCRIPT.md",
            ):
                with self.subTest(filename=filename):
                    copied = bundle / "examples" / filename
                    backup = copied.read_bytes()
                    copied.unlink()
                    with self.assertRaisesRegex(RuntimeError, filename):
                        portable_resources.assert_portable_resources(bundle)
                    copied.write_bytes(backup)

    def test_legacy_frontend_is_not_a_portable_resource(self):
        self.assertNotIn("web", portable_resources.RESOURCE_DIRECTORIES)


if __name__ == "__main__":
    unittest.main()
