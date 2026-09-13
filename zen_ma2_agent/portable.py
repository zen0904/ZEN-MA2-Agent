from __future__ import annotations

import os
import sys
from pathlib import Path


def zen_home() -> Path | None:
    """Return the portable installation root when the launcher supplied it.

    ``ZEN_HOME`` is intentionally set by launchers relative to themselves.  It
    is never a machine-specific path and is the only supported location for
    mutable portable state.
    """
    raw = os.environ.get("ZEN_HOME", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def app_root() -> Path:
    """Resolve source/bundle root while preserving the historic bundle layout."""
    home = zen_home()
    if home:
        repo = home / "repo" / "ZEN-MA2-Agent"
        if repo.is_dir():
            return repo
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def ensure_runtime_dirs(root: Path | None = None) -> tuple[Path, Path]:
    root = root or app_root()
    # Source/bundle compatibility remains unchanged when ZEN_HOME is absent.
    # With the portable launcher, runtime data must travel with the USB and
    # never leak into a host profile or the versioned repository.
    home = zen_home()
    persistent = home if home else root
    data, logs, cache = persistent / "show_context", persistent / "logs", persistent / "cache"
    if not home:
        data = root / "data"
    data.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    return data, logs


def portable_state_path(name: str) -> Path:
    """Return an Agent-owned mutable directory; never a host-global path."""
    allowed = {"config", "providers", "knowledge", "show_context", "projects", "runtime", "logs", "cache", "temp", "secrets"}
    if name not in allowed:
        raise ValueError(f"Unsupported portable state directory: {name}")
    base = zen_home() or app_root()
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path
