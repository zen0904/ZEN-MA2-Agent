"""Smoke-test the packaged headless ZEN Field Core."""

from __future__ import annotations

import json
import socket
import subprocess
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_http(url: str, timeout: float = 8.0) -> dict:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Operator API did not become ready: {last_error}")


def _bridge_ping(port: int) -> str:
    with socket.create_connection(("127.0.0.1", port), timeout=2.0) as client:
        client.sendall(b"ZEN/1 REQ smoke-1 PING\n")
        return client.recv(1024).decode("utf-8").strip()


def main() -> int:
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")

    check = subprocess.run(
        [str(EXE), "--self-check"],
        cwd=EXE.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    if check.returncode:
        raise SystemExit(check.stdout + check.stderr)
    payload = json.loads(check.stdout.strip())
    if payload.get("ui_strategy") != "OPENCLAW_FIRST" or payload.get("ma2_writes") != 0:
        raise SystemExit(f"Unexpected Field Core self-check: {payload}")

    operator_port = _free_port()
    bridge_port = _free_port()
    process = subprocess.Popen(
        [
            str(EXE),
            "--operator-port",
            str(operator_port),
            "--bridge-port",
            str(bridge_port),
        ],
        cwd=EXE.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        health = _wait_http(f"http://127.0.0.1:{operator_port}/healthz")
        if health.get("status") != "OK":
            raise RuntimeError(f"Operator health failed: {health}")
        status = _wait_http(f"http://127.0.0.1:{operator_port}/zen/v0.1/status")
        if not status.get("field_core", {}).get("available"):
            raise RuntimeError(f"Field Core status failed: {status}")
        ping = _bridge_ping(bridge_port)
        if ping != "ZEN/1 READY smoke-1 PONG":
            raise RuntimeError(f"Bridge PING failed: {ping}")
        print(
            json.dumps(
                {
                    "PORTABLE_HEADLESS_SMOKE": "PASS",
                    "operator_port": operator_port,
                    "bridge_port": bridge_port,
                    "ui_strategy": "OPENCLAW_FIRST",
                    "ma2_writes": 0,
                },
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
