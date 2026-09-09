"""Build the USB-portable Windows bundle from a project virtual environment."""

from __future__ import annotations

import subprocess
import sys
import json
from datetime import datetime, timezone
from shutil import copy2, copytree, rmtree
from pathlib import Path

from portable_resources import assert_portable_resources


ROOT = Path(__file__).resolve().parents[1]


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _clean_previous_artifacts() -> None:
    """Remove only generated project artifacts before every portable build."""
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
        "router_build_id": "intent-router-v4-geometry-test-isolation",
    }
    path = ROOT / "build_identity.json"
    path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    _clean_previous_artifacts()
    identity = _write_build_identity()
    data = lambda source, destination: f"{ROOT / source};{destination}"
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--noupx", "--onedir",
        "--name", "ZEN_MA2_Agent", "--add-data", data("web", "web"),
        "--add-data", data("config", "config"), "--add-data", data("gma2", "gma2"),
        "--add-data", data("lua", "lua"), "--add-data", data("skills", "skills"),
        "--add-data", data("semantic_presets", "semantic_presets"), "--add-data", data("geometry", "geometry"),
        "--add-data", data("examples", "examples"),
        "--add-data", f"{identity};.",
        "--runtime-hook", str(ROOT / "scripts" / "pyside6_runtime_hook.py"),
        # PyInstaller's official PySide6 hooks preserve Qt's required layout.
        # Only shiboken6 needs explicit collection for its native runtime files.
        "--collect-all", "shiboken6", "--collect-all", "qrcode", "main.py",
    ]
    try:
        result = subprocess.call(command, cwd=ROOT)
        if result:
            return result
        bundle = ROOT / "dist" / "ZEN_MA2_Agent"
        # app_root() is the folder beside the EXE.  Copy user-facing resources
        # from the authoritative source tree there, then assert the result.
        for name in ("web", "lua", "config", "gma2", "skills", "semantic_presets", "geometry", "examples"):
            copytree(ROOT / name, bundle / name, dirs_exist_ok=True)
        # Runtime data normally stays beside the portable executable.  Preserve
        # the small Agent-owned Effect catalog across a rebuild so a freshly
        # rebuilt bundle can safely revalidate and reuse its own Effects.  The
        # catalog is still bound to the scanned Show fingerprint and always
        # requires a fresh object/label check before reuse.
        data_directory = bundle / "data"
        data_directory.mkdir(exist_ok=True)
        catalog = ROOT / "data" / "ZEN_EFFECT_CATALOG.json"
        if catalog.is_file():
            copy2(catalog, data_directory / catalog.name)
        (bundle / "build_identity.json").write_text(identity.read_text(encoding="utf-8"), encoding="utf-8")
        for name in ("logs", "cache"):
            (bundle / name).mkdir(exist_ok=True)
        assert_portable_resources(bundle)
        (bundle / "portable_build_complete.json").write_text(json.dumps({"head": _git_head(), "completed_at": datetime.now(timezone.utc).isoformat()}) + "\n", encoding="utf-8")
        return 0
    finally:
        identity.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
