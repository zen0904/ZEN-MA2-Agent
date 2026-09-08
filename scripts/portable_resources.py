"""Assertions for files that must be present in every USB portable bundle."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


RESOURCE_DIRECTORIES = ("web", "lua", "skills", "config", "logs", "cache", "gma2", "semantic_presets", "geometry", "examples")
PLUGIN_FILES = ("ZEN_AGENT.xml", "ZEN_AGENT.lua")
AXIS_PROFILE_FILE = "geometry\\ZEN_STAGE_AXIS_PROFILE.json"


def assert_portable_resources(bundle: Path) -> list[str]:
    """Fail fast when a one-folder bundle is missing a user-facing resource."""
    missing = [name for name in RESOURCE_DIRECTORIES if not (bundle / name).is_dir()]
    axis_profile = bundle / "geometry" / "ZEN_STAGE_AXIS_PROFILE.json"
    if not axis_profile.is_file() or axis_profile.stat().st_size <= 0:
        missing.append(AXIS_PROFILE_FILE)
    plugin_dir = bundle / "gma2" / "plugins"
    plugin_paths = [plugin_dir / name for name in PLUGIN_FILES]
    missing.extend(str(path.relative_to(bundle)) for path in plugin_paths if not path.is_file() or path.stat().st_size <= 0)
    if missing:
        raise RuntimeError("Portable resource check failed: " + ", ".join(missing))

    xml_path, lua_path = plugin_paths
    try:
        root = ET.fromstring(xml_path.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        raise RuntimeError(f"Portable plugin XML is invalid: {xml_path}") from exc
    plugin = next((element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "Plugin"), None)
    if plugin is None or plugin.get("luafile") != lua_path.name:
        raise RuntimeError("Portable plugin XML must reference ZEN_AGENT.lua with exact case.")
    song_input = bundle / "examples" / "FIRST_SONG_INPUT.json"
    if not song_input.is_file() or song_input.stat().st_size <= 0:
        raise RuntimeError("Portable resource check failed: examples/FIRST_SONG_INPUT.json")
    return [str(path.relative_to(bundle)) for path in plugin_paths]
