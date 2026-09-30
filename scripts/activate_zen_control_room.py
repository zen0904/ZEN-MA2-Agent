#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/opt/zen/zen-ops-runtime") if Path("/opt/zen/zen-ops-runtime/.git").is_dir() else Path("/opt/zen/ZEN-MA2-Agent")
ROOM = REPO / "deploy" / "ubuntu" / "zen-control-room"
SESSION = "zenmon"
PUBLIC_RESULT = Path("/var/lib/zen-ops/public/control-room-activate.json")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def publish(status: str, **extra: object) -> None:
    payload = {
        "schema": "zen.control_room.activate.v0.1",
        "status": status,
        "time": datetime.now(timezone.utc).isoformat(),
        "euid": os.geteuid(),
        **extra,
    }
    try:
        PUBLIC_RESULT.write_text(json.dumps(payload, indent=2) + "\n")
    except Exception:
        pass


def main() -> int:
    publish("starting")
    if not ROOM.is_file():
        print(f"ROOM_SOURCE_MISSING={ROOM}")
        publish("failed", error="ROOM_SOURCE_MISSING")
        return 2

    check = run("python3", "-m", "py_compile", str(ROOM))
    if check.returncode != 0:
        print(check.stdout)
        return check.returncode

    if run("tmux", "has-session", "-t", SESSION).returncode != 0:
        print("TMUX_SESSION_MISSING=zenmon")
        publish("failed", error="TMUX_SESSION_MISSING")
        return 3

    names = run("tmux", "list-windows", "-t", SESSION, "-F", "#{window_name}").stdout.splitlines()
    if "ROOM" in names:
        proc = run("tmux", "respawn-pane", "-k", "-t", f"{SESSION}:ROOM.0", "python3", "-u", str(ROOM))
    else:
        proc = run("tmux", "new-window", "-d", "-t", SESSION, "-n", "ROOM", "python3", "-u", str(ROOM))
    if proc.returncode != 0:
        print(proc.stdout)
        return proc.returncode

    commands = [
        ("bind-key", "-n", "F10", "select-window", "-t", "zenmon:ROOM"),
        ("bind-key", "-n", "F11", "select-window", "-t", "zenmon:MONITOR"),
        ("bind-key", "-n", "F12", "select-window", "-t", "zenmon:MA_AGENT"),
        ("set-option", "-t", SESSION, "-g", "status-left", " ZEN | F10 ROOM F11 MON F12 MA "),
        ("select-window", "-t", f"{SESSION}:ROOM"),
    ]
    for args in commands:
        proc = run("tmux", *args)
        if proc.returncode != 0:
            print(proc.stdout)
            return proc.returncode

    publish("completed", room_source=str(ROOM), room_window="LIVE", room_selected=True, ma2_writes=0, ma3_writes=0)
    print("ROOM_SOURCE=" + str(ROOM))
    print("ROOM_WINDOW=LIVE")
    print("ROOM_SELECTED=YES")
    print("ROOT_REQUIRED=NO")
    print("MA2_WRITES=0")
    print("MA3_WRITES=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
