#!/usr/bin/env python3
from __future__ import annotations

import getpass
import glob
import http.server
import json
import os
import socketserver
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PORT = 18081
SESSION = "zenmon"
HERE = Path(__file__).resolve()
REPO = HERE.parents[1]
ROOM = REPO / "deploy" / "ubuntu" / "zen-control-room"


def run(argv: list[str], timeout: int = 8) -> dict:
    try:
        p = subprocess.run(
            argv,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {"rc": p.returncode, "out": p.stdout[-8000:]}
    except Exception as exc:
        return {"rc": 999, "out": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    diag: dict = {
        "schema": "zen.room.remote_diag.v0.1",
        "time": datetime.now(timezone.utc).isoformat(),
        "euid": os.geteuid() if hasattr(os, "geteuid") else None,
        "user": getpass.getuser(),
        "repo": str(REPO),
        "room_source_exists": ROOM.is_file(),
        "git_branch": run(["git", "-C", str(REPO), "rev-parse", "--abbrev-ref", "HEAD"]),
        "git_head": run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"]),
        "tmux_sockets": [],
        "activation": {"status": "not_attempted"},
    }

    for sock in sorted(glob.glob("/tmp/tmux-*/default")):
        row = {"socket": sock}
        row["sessions"] = run(["tmux", "-S", sock, "list-sessions"])
        if row["sessions"]["rc"] == 0 and SESSION in row["sessions"]["out"]:
            row["windows_before"] = run(
                ["tmux", "-S", sock, "list-windows", "-t", SESSION, "-F", "#{window_index}:#{window_name}"]
            )
            if ROOM.is_file():
                check = run(["python3", "-m", "py_compile", str(ROOM)])
                row["room_compile"] = check
                if check["rc"] == 0:
                    names = row["windows_before"]["out"].splitlines()
                    has_room = any(line.endswith(":ROOM") for line in names)
                    if has_room:
                        action = run(
                            ["tmux", "-S", sock, "respawn-pane", "-k", "-t", f"{SESSION}:ROOM.0",
                             "python3", "-u", str(ROOM)]
                        )
                    else:
                        action = run(
                            ["tmux", "-S", sock, "new-window", "-d", "-t", SESSION, "-n", "ROOM",
                             "python3", "-u", str(ROOM)]
                        )
                    row["room_create"] = action
                    if action["rc"] == 0:
                        for cmd in (
                            ["tmux", "-S", sock, "bind-key", "-n", "F10", "select-window", "-t", "zenmon:ROOM"],
                            ["tmux", "-S", sock, "bind-key", "-n", "F11", "select-window", "-t", "zenmon:MONITOR"],
                            ["tmux", "-S", sock, "bind-key", "-n", "F12", "select-window", "-t", "zenmon:MA_AGENT"],
                            ["tmux", "-S", sock, "set-option", "-t", SESSION, "-g", "status-left",
                             " ZEN | F10 ROOM F11 MON F12 MA "],
                            ["tmux", "-S", sock, "select-window", "-t", "zenmon:ROOM"],
                        ):
                            run(cmd)
                        row["windows_after"] = run(
                            ["tmux", "-S", sock, "list-windows", "-t", SESSION,
                             "-F", "#{window_index}:#{window_name}:active=#{window_active}"]
                        )
                        diag["activation"] = {
                            "status": "completed",
                            "socket": sock,
                            "ma2_writes": 0,
                            "ma3_writes": 0,
                        }
        diag["tmux_sockets"].append(row)

    payload = json.dumps(diag, ensure_ascii=False, indent=2).encode("utf-8")

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def log_message(self, fmt, *args):
            return

    class Server(socketserver.TCPServer):
        allow_reuse_address = True

    print(json.dumps(diag, ensure_ascii=False, indent=2))
    print(f"ROOM_DIAG_LISTEN=0.0.0.0:{PORT}", flush=True)
    with Server(("0.0.0.0", PORT), Handler) as server:
        deadline = time.monotonic() + 120
        server.timeout = 1
        while time.monotonic() < deadline:
            server.handle_request()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
