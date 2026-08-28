from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .portable import app_root, ensure_runtime_dirs


DEFAULTS: dict[str, Any] = {
    "host": "127.0.0.1", "port": 30000, "login_command": "",
    "read_timeout_seconds": 0.35, "blackout_command_template": None,
}


def load_preferences(root: Path | None = None) -> dict[str, Any]:
    root = root or app_root()
    data, _ = ensure_runtime_dirs(root)
    path = data / "user_preferences.json"
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        return {**DEFAULTS, **(stored if isinstance(stored, dict) else {})}
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)


def save_preferences(preferences: dict[str, Any], root: Path | None = None) -> Path:
    root = root or app_root()
    data, _ = ensure_runtime_dirs(root)
    path = data / "user_preferences.json"
    path.write_text(json.dumps(preferences, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
