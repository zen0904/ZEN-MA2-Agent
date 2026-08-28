"""Build the USB-portable Windows bundle from a project virtual environment."""

from __future__ import annotations

import subprocess
import sys
from shutil import copytree
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    data = lambda source, destination: f"{ROOT / source};{destination}"
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--noupx", "--onedir",
        "--name", "ZEN_MA2_Agent", "--add-data", data("web", "web"),
        "--add-data", data("config", "config"), "--add-data", data("gma2", "gma2"),
        "--add-data", data("lua", "lua"), "--add-data", data("skills", "skills"),
        "--runtime-hook", str(ROOT / "scripts" / "pyside6_runtime_hook.py"),
        # PyInstaller's official PySide6 hooks preserve Qt's required layout.
        # Only shiboken6 needs explicit collection for its native runtime files.
        "--collect-all", "shiboken6", "--collect-all", "qrcode", "main.py",
    ]
    result = subprocess.call(command, cwd=ROOT)
    if result:
        return result
    bundle = ROOT / "dist" / "ZEN_MA2_Agent"
    internal = bundle / "_internal"
    # PyInstaller stores --add-data under _internal by default. Copy mutable and
    # user-facing resources alongside the EXE so USB-relative lookup is stable.
    for name in ("web", "lua", "config", "gma2", "skills"):
        copytree(internal / name, bundle / name, dirs_exist_ok=True)
    for name in ("logs", "cache"):
        (bundle / name).mkdir(exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
