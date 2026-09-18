"""Build the USB-portable headless ZEN core bundle on Windows."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2, copytree, rmtree

from portable_resources import assert_portable_resources


ROOT = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _clean_previous_artifacts() -> None:
    for path in (ROOT / "build", ROOT / "dist"):
        if path.exists():
            rmtree(path)
    for cache in ROOT.rglob("__pycache__"):
        if ".venv" not in cache.parts:
            rmtree(cache)
    (ROOT / "ZEN_MA2_Agent.spec").unlink(missing_ok=True)


def _write_build_identity() -> Path:
    metadata = {
        "head": _git_head(),
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_root": str(ROOT.resolve()),
        "ui_strategy": "OPENCLAW_FIRST",
        "runtime": "HEADLESS_FIELD_CORE",
    }
    path = ROOT / "build_identity.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    _clean_previous_artifacts()
    identity = _write_build_identity()
    data = lambda source, destination: f"{ROOT / source};{destination}"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--noupx",
        "--onedir",
        "--name",
        "ZEN_MA2_Agent",
        "--add-data",
        data("config", "config"),
        "--add-data",
        data("gma2", "gma2"),
        "--add-data",
        data("lua", "lua"),
        "--add-data",
        data("skills", "skills"),
        "--add-data",
        data("semantic_presets", "semantic_presets"),
        "--add-data",
        data("geometry", "geometry"),
        "--add-data",
        data("examples", "examples"),
        "--add-data",
        f"{identity};.",
        "main.py",
    ]
    try:
        result = subprocess.call(command, cwd=ROOT)
        if result:
            return result

        bundle = ROOT / "dist" / "ZEN_MA2_Agent"
        for name in (
            "lua",
            "config",
            "gma2",
            "skills",
            "semantic_presets",
            "geometry",
            "examples",
        ):
            copytree(ROOT / name, bundle / name, dirs_exist_ok=True)

        data_directory = bundle / "data"
        data_directory.mkdir(exist_ok=True)
        for filename in (
            "ZEN_EFFECT_CATALOG.json",
            "ZEN_CUE_EFFECT_APPLICATION_CAPABILITY.json",
        ):
            source = ROOT / "data" / filename
            if source.is_file():
                copy2(source, data_directory / source.name)

        (bundle / "build_identity.json").write_text(
            identity.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        for name in ("logs", "cache"):
            (bundle / name).mkdir(exist_ok=True)

        assert_portable_resources(bundle)
        (bundle / "portable_build_complete.json").write_text(
            json.dumps(
                {
                    "head": _git_head(),
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "ui_strategy": "OPENCLAW_FIRST",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return 0
    finally:
        identity.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
