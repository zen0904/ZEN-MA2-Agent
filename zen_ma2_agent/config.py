from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .portable import app_root, ensure_runtime_dirs


DEFAULTS: dict[str, Any] = {
    "ma2": {"host": "127.0.0.1", "port": 30000, "username": ""},
    "read_timeout_seconds": 0.35,
    "blackout_command_template": None,
    "mobile": {"enabled": True, "port": 8765},
    "internet_access": "AUTO",
    # The imported Plugin Pool slot is deliberately opt-in: no show has a
    # universal Plugin slot. The Lua request itself travels through a UserVar.
    "state_adapter": {"plugin_slot": None, "timeout_seconds": 3.0},
}

HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")


class SettingsError(ValueError):
    pass


def settings_path(root: Path | None = None) -> Path:
    return (root or app_root()) / "config" / "settings.json"


def validate_ma2_settings(host: str, port: object, username: str, *, require_username: bool = False) -> dict[str, Any]:
    host = str(host).strip()
    username = str(username)
    if not host or not HOST_RE.fullmatch(host):
        raise SettingsError("Host must be a hostname or IPv4 address.")
    try:
        port = int(str(port).strip())
    except ValueError as exc:
        raise SettingsError("Port must be an integer from 1 to 65535.") from exc
    if not 1 <= port <= 65535:
        raise SettingsError("Port must be from 1 to 65535.")
    if require_username and not username:
        raise SettingsError("USERNAME REQUIRED")
    return {"host": host, "port": port, "username": username}


def validate_state_adapter_settings(settings: object) -> dict[str, Any]:
    settings = settings if isinstance(settings, dict) else {}
    raw_slot = settings.get("plugin_slot")
    if raw_slot in (None, ""):
        plugin_slot = None
    else:
        if isinstance(raw_slot, bool):
            raise SettingsError("ZEN_AGENT Plugin slot must be a number.")
        try:
            plugin_slot = int(str(raw_slot).strip())
        except ValueError as exc:
            raise SettingsError("ZEN_AGENT Plugin slot must be a number.") from exc
        if not 2 <= plugin_slot <= 9999:
            raise SettingsError("ZEN_AGENT Plugin slot must be from 2 to 9999.")
    try:
        timeout_seconds = float(settings.get("timeout_seconds", DEFAULTS["state_adapter"]["timeout_seconds"]))
    except (TypeError, ValueError) as exc:
        raise SettingsError("ZEN_AGENT timeout must be a number.") from exc
    if not 0.1 <= timeout_seconds <= 30:
        raise SettingsError("ZEN_AGENT timeout must be from 0.1 to 30 seconds.")
    return {"plugin_slot": plugin_slot, "timeout_seconds": timeout_seconds}


def load_preferences(root: Path | None = None) -> dict[str, Any]:
    root = root or app_root()
    ensure_runtime_dirs(root)
    path = settings_path(root)
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(stored, dict):
            raise ValueError("settings root is not an object")
        ma2 = {**DEFAULTS["ma2"], **(stored.get("ma2") if isinstance(stored.get("ma2"), dict) else {})}
        adapter = stored.get("state_adapter")
        return {**DEFAULTS, **stored, "ma2": validate_ma2_settings(ma2["host"], ma2["port"], ma2["username"]), "state_adapter": validate_state_adapter_settings(adapter)}
    except (OSError, json.JSONDecodeError):
        defaults = {**DEFAULTS, "ma2": dict(DEFAULTS["ma2"])}
        save_preferences(defaults, root)
        return defaults


def save_preferences(preferences: dict[str, Any], root: Path | None = None) -> Path:
    root = root or app_root()
    ensure_runtime_dirs(root)
    path = settings_path(root)
    path.parent.mkdir(exist_ok=True)
    ma2 = preferences.get("ma2") if isinstance(preferences.get("ma2"), dict) else {}
    saved = {
        "ma2": validate_ma2_settings(ma2.get("host", ""), ma2.get("port", ""), ma2.get("username", "")),
        "read_timeout_seconds": float(preferences.get("read_timeout_seconds", DEFAULTS["read_timeout_seconds"])),
        "blackout_command_template": preferences.get("blackout_command_template"),
        "mobile": {"enabled": bool((preferences.get("mobile") or {}).get("enabled", True)), "port": int((preferences.get("mobile") or {}).get("port", 8765))},
        "internet_access": str(preferences.get("internet_access", "AUTO")),
        "state_adapter": validate_state_adapter_settings(preferences.get("state_adapter")),
    }
    # Password is intentionally absent from this portable file.
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
