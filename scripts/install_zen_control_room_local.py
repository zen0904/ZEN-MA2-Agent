#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path("/opt/zen/ZEN-MA2-Agent")
DEST = Path("/usr/local/bin")
PUBLIC = Path("/var/lib/zen-ops/public")
SESSION = "zenmon"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def main() -> int:
    result = {
        "schema": "zen.control_room.install.v0.1",
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "euid": os.geteuid(),
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    out = PUBLIC / "control-room-local-install.json"
    out.write_text(json.dumps(result, indent=2) + "\n")

    try:
        for name in ("zen-control-room", "zenmon", "zen-console-mode"):
            src = REPO / "deploy" / "ubuntu" / name
            dst = DEST / name
            if not src.is_file():
                raise RuntimeError(f"missing source: {src}")
            shutil.copy2(src, dst)
            dst.chmod(0o755)

        proc = run("python3", "-m", "py_compile", str(DEST / "zen-control-room"))
        if proc.returncode != 0:
            raise RuntimeError("py_compile failed: " + proc.stdout[-2000:])

        live = run("tmux", "has-session", "-t", SESSION).returncode == 0
        if live:
            names = run("tmux", "list-windows", "-t", SESSION, "-F", "#{window_name}").stdout.splitlines()
            if "ROOM" in names:
                run("tmux", "respawn-pane", "-k", "-t", f"{SESSION}:ROOM.0", str(DEST / "zen-control-room"))
            else:
                run("tmux", "new-window", "-d", "-t", SESSION, "-n", "ROOM", str(DEST / "zen-control-room"))
            run("tmux", "bind-key", "-n", "F10", "select-window", "-t", "zenmon:ROOM")
            run("tmux", "bind-key", "-n", "F11", "select-window", "-t", "zenmon:MONITOR")
            run("tmux", "bind-key", "-n", "F12", "select-window", "-t", "zenmon:MA_AGENT")
            run("tmux", "set-option", "-t", SESSION, "-g", "status-left", " ZEN | F10 ROOM F11 MON F12 MA ")
            run("tmux", "select-window", "-t", f"{SESSION}:ROOM")

        result.update({
            "status": "completed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "tmux_room_live": live,
            "control_room_path": str(DEST / "zen-control-room"),
            "ma2_writes": 0,
            "ma3_writes": 0,
        })
        out.write_text(json.dumps(result, indent=2) + "\n")
        return 0
    except Exception as exc:
        result.update({
            "status": "failed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "error": f"{type(exc).__name__}: {exc}",
            "ma2_writes": 0,
            "ma3_writes": 0,
        })
        out.write_text(json.dumps(result, indent=2) + "\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
