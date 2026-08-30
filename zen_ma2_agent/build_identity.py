"""Runtime identity for a portable build.

The build script writes ``build_identity.json`` beside the executable.  Keeping
the metadata outside the Python archive makes it possible to prove exactly what
was packaged without relying on the source checkout present on the build PC.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .portable import app_root


IDENTITY_FILE = "build_identity.json"
DEVELOPMENT_IDENTITY = {
    "head": "development",
    "build_timestamp": "development",
    "source_root": "source checkout",
    "router_build_id": "intent-router-v3-diagnostics",
}


def load_build_identity(root: Path | None = None) -> dict[str, Any]:
    """Load build-time metadata, with a harmless source-development fallback."""
    path = (root or app_root()) / IDENTITY_FILE
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return dict(DEVELOPMENT_IDENTITY)
    if not isinstance(loaded, dict):
        return dict(DEVELOPMENT_IDENTITY)
    return {**DEVELOPMENT_IDENTITY, **loaded}


def display_build_identity(identity: dict[str, Any]) -> str:
    identity = {**DEVELOPMENT_IDENTITY, **identity}
    return (
        f"HEAD: {identity['head']}\n"
        f"Build: {identity['build_timestamp']}\n"
        f"Source: {identity['source_root']}\n"
        f"Router: {identity['router_build_id']}"
    )
