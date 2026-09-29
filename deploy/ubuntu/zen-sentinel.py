#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

RUN = Path("/run/zen-sentinel")
STATE = RUN / "state.json"
MODE = RUN / "mode"
PORTS = {
    "controller": 8876,
    "ma_bridge": 8877,
    "lighting_proxy": 18878,
    "openclaw": 18789,
    "glances": 61208,
}

def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.15):
            return True
    except OSError:
        return False

def meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            out[key] = int(value.strip().split()[0])
    except Exception:
        pass
    return out

def thermal_c():
    vals = []
    for p in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            v = int(p.read_text().strip())
            if 0 < v < 200000:
                vals.append(v / 1000.0)
        except Exception:
            pass
    return max(vals) if vals else None

def operstate(name: str) -> str:
    p = Path("/sys/class/net") / name / "operstate"
    try:
        return p.read_text().strip()
    except Exception:
        return "missing"

def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    if not MODE.exists():
        MODE.write_text("auto\n")

    while True:
        try:
            mode = MODE.read_text().strip() if MODE.exists() else "auto"
            ports = {name: port_open(port) for name, port in PORTS.items()}
            mem = meminfo()
            disk = shutil.disk_usage("/")
            state = {
                "schema": "zen.sentinel.v0.1",
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "mode": mode,
                "ports": ports,
                "ma_ports_ok": ports["controller"] and ports["ma_bridge"] and ports["lighting_proxy"],
                "network": {
                    "ethernet": operstate("enp1s0f0"),
                    "wifi": operstate("wlp2s0b1"),
                    "tailscale": operstate("tailscale0"),
                },
                "memory": {
                    "total_kib": mem.get("MemTotal"),
                    "available_kib": mem.get("MemAvailable"),
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                },
                "temperature_c": thermal_c(),
                "avb": {
                    "interface": "enp1s0f0",
                    "phc_present": any(Path("/dev").glob("ptp*")),
                },
            }
            tmp = STATE.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
            os.replace(tmp, STATE)
        except Exception as exc:
            err = {"schema": "zen.sentinel.error.v0.1", "error": repr(exc)}
            STATE.write_text(json.dumps(err) + "\n")
        time.sleep(2)

if __name__ == "__main__":
    main()
