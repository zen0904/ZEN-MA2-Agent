#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/opt/zen/zen-ops-runtime") if Path("/opt/zen/zen-ops-runtime/.git").is_dir() else Path("/opt/zen/ZEN-MA2-Agent")
ROOM = REPO / "deploy" / "ubuntu" / "zen-control-room"
PUBLIC_RESULT = Path("/var/lib/zen-ops/public/control-room-activate.json")
TMP_RESULT = Path("/tmp/zen-control-room-activate.json")
SESSION = "zenmon"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def publish(status: str, **extra: object) -> None:
    payload = {
        "schema": "zen.control_room.activate.v0.2",
        "status": status,
        "time": datetime.now(timezone.utc).isoformat(),
        "euid": os.geteuid(),
        **extra,
    }
    text = json.dumps(payload, indent=2) + "\n"
    for path in (TMP_RESULT, PUBLIC_RESULT):
        try:
            path.write_text(text)
        except Exception:
            pass


def tmux_prefix() -> list[str] | None:
    direct = run("tmux", "has-session", "-t", SESSION)
    if direct.returncode == 0:
        return ["tmux"]
    for sock in sorted(Path("/tmp").glob("tmux-*/*")):
        try:
            if not sock.is_socket():
                continue
        except OSError:
            continue
        probe = run("tmux", "-S", str(sock), "has-session", "-t", SESSION)
        if probe.returncode == 0:
            return ["tmux", "-S", str(sock)]
    return None


def main() -> int:
    publish("starting", repo=str(REPO), room=str(ROOM))
    if not ROOM.is_file():
        publish("failed", error="ROOM_SOURCE_MISSING")
        return 2

    check = run("python3", "-m", "py_compile", str(ROOM))
    if check.returncode != 0:
        publish("failed", error="ROOM_COMPILE_FAILED", output=check.stdout[-1200:])
        return check.returncode

    prefix = tmux_prefix()
    if prefix is None:
        publish("failed", error="TMUX_SESSION_MISSING")
        return 3

    names = run(*prefix, "list-windows", "-t", SESSION, "-F", "#{window_name}").stdout.splitlines()
    if "ROOM" in names:
        proc = run(*prefix, "respawn-pane", "-k", "-t", f"{SESSION}:ROOM.0", "python3", "-u", str(ROOM))
    else:
        proc = run(*prefix, "new-window", "-d", "-t", SESSION, "-n", "ROOM", "python3", "-u", str(ROOM))
    if proc.returncode != 0:
        publish("failed", error="ROOM_WINDOW_FAILED", output=proc.stdout[-1200:])
        return proc.returncode

    commands = [
        ("bind-key", "-n", "F10", "select-window", "-t", "zenmon:ROOM"),
        ("bind-key", "-n", "F11", "select-window", "-t", "zenmon:MONITOR"),
        ("bind-key", "-n", "F12", "select-window", "-t", "zenmon:MA_AGENT"),
        ("set-option", "-t", SESSION, "-g", "status-left", " ZEN | F10 ROOM F11 MON F12 MA "),
        ("select-window", "-t", f"{SESSION}:ROOM"),
    ]
    for args in commands:
        proc = run(*prefix, *args)
        if proc.returncode != 0:
            publish("failed", error="TMUX_CONFIG_FAILED", args=list(args), output=proc.stdout[-1200:])
            return proc.returncode

    current = run(*prefix, "display-message", "-p", "-t", SESSION, "#{window_name}").stdout.strip()
    publish(
        "completed",
        repo=str(REPO),
        room_source=str(ROOM),
        tmux_prefix=prefix,
        room_selected=(current == "ROOM"),
        current_window=current,
        ma2_writes=0,
        ma3_writes=0,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
