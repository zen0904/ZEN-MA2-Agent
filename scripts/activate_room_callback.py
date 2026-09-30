#!/usr/bin/env python3
from __future__ import annotations

import glob
import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

WINDOWS_HOST = "100.67.178.35"
WINDOWS_PORT = 18082
SESSION = "zenmon"
REPO = Path(__file__).resolve().parents[1]
ROOM = REPO / "deploy" / "ubuntu" / "zen-control-room"


def run(argv: list[str], timeout: int = 8) -> dict:
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout, check=False)
        return {"rc": p.returncode, "out": p.stdout[-5000:]}
    except Exception as exc:
        return {"rc": 999, "out": f"{type(exc).__name__}: {exc}"}


def send(payload: dict) -> None:
    raw=(json.dumps(payload,ensure_ascii=False)+"\n").encode()
    try:
        with socket.create_connection((WINDOWS_HOST, WINDOWS_PORT), timeout=5) as s:
            s.sendall(raw)
    except Exception:
        pass


def main() -> int:
    result={
        "schema":"zen.room.callback.v0.1",
        "time":datetime.now(timezone.utc).isoformat(),
        "euid":os.geteuid() if hasattr(os,"geteuid") else None,
        "repo":str(REPO),
        "room_exists":ROOM.is_file(),
        "branch":run(["git","-C",str(REPO),"rev-parse","--abbrev-ref","HEAD"]),
        "head":run(["git","-C",str(REPO),"rev-parse","--short","HEAD"]),
        "sockets":[],
        "activation":"failed",
        "ma2_writes":0,
        "ma3_writes":0,
    }
    for sock in sorted(glob.glob("/tmp/tmux-*/default")):
        row={"socket":sock}
        row["sessions"]=run(["tmux","-S",sock,"list-sessions"])
        if row["sessions"]["rc"]==0 and SESSION in row["sessions"]["out"] and ROOM.is_file():
            before=run(["tmux","-S",sock,"list-windows","-t",SESSION,"-F","#{window_name}"])
            row["before"]=before
            names=before["out"].splitlines()
            if "ROOM" in names:
                action=run(["tmux","-S",sock,"respawn-pane","-k","-t","zenmon:ROOM.0",
                            "python3","-u",str(ROOM)])
            else:
                action=run(["tmux","-S",sock,"new-window","-d","-t",SESSION,"-n","ROOM",
                            "python3","-u",str(ROOM)])
            row["action"]=action
            if action["rc"]==0:
                cmds=[
                    ["tmux","-S",sock,"bind-key","-n","F10","select-window","-t","zenmon:ROOM"],
                    ["tmux","-S",sock,"bind-key","-n","F11","select-window","-t","zenmon:MONITOR"],
                    ["tmux","-S",sock,"bind-key","-n","F12","select-window","-t","zenmon:MA_AGENT"],
                    ["tmux","-S",sock,"set-option","-t",SESSION,"-g","status-left"," ZEN | F10 ROOM F11 MON F12 MA "],
                    ["tmux","-S",sock,"select-window","-t","zenmon:ROOM"],
                ]
                row["commands"]=[run(x) for x in cmds]
                row["after"]=run(["tmux","-S",sock,"list-windows","-t",SESSION,
                                  "-F","#{window_name}:#{window_active}"])
                result["activation"]="completed"
                result["socket"]=sock
        result["sockets"].append(row)
    send(result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["activation"]=="completed" else 3


if __name__=="__main__":
    raise SystemExit(main())
