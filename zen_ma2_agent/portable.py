from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Resolve the USB/app folder for source and future frozen executable runs."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def ensure_runtime_dirs(root: Path | None = None) -> tuple[Path, Path]:
    root = root or app_root()
    data, logs, cache = root / "data", root / "logs", root / "cache"
    data.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    return data, logs
