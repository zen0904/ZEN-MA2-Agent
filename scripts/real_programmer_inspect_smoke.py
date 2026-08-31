"""Verify Programmer Inspect through the frozen Desktop's local test bridge.

This opt-in verifier deliberately sends no MA2 command itself.  The packaged
Desktop receives two natural-language requests through ZenDesktop.submit().
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"
QUERIES = (
    ("Programmer 有沒有東西？", "UNSUPPORTED programmer"),
    ("現在選了哪些燈？", "UNSUPPORTED selection"),
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _request(port: int, action: str, *, timeout: float = 30, **payload: object) -> dict:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
        client.settimeout(timeout)
        client.sendall(json.dumps({"action": action, **payload}, ensure_ascii=False).encode("utf-8"))
        data = b""
        while not data.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    response = json.loads(data.decode("utf-8"))
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "automation request failed"))
    return response


def _wait_for(port: int) -> dict:
    deadline = time.monotonic() + 10
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _request(port, "status", timeout=3)
        except (ConnectionError, OSError, ValueError, RuntimeError) as exc:
            last_error = exc
            time.sleep(0.1)
    raise RuntimeError(f"automation bridge unavailable: {last_error}")


def _new_records(path: Path, offset: int) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("rb") as handle:
        handle.seek(offset)
        return [json.loads(line) for line in handle.read().decode("utf-8", errors="replace").splitlines() if line.strip()]


def main() -> int:
    if "--real-machine" not in sys.argv:
        raise SystemExit("Refusing real MA2 validation without --real-machine.")
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    bundle = EXE.parent
    log_path = bundle / "logs" / "agent.jsonl"
    offset = log_path.stat().st_size if log_path.exists() else 0
    subprocess.run(["taskkill", "/F", "/IM", "ZEN_MA2_Agent.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    port = _free_port()
    environment = dict(os.environ, ZEN_MA2_AUTOMATION="1", ZEN_MA2_AUTOMATION_PORT=str(port))
    process = subprocess.Popen([str(EXE), "--automation-test"], cwd=bundle, env=environment)
    report: dict[str, object] = {"queries": []}
    try:
        status = _wait_for(port)
        if status.get("build_head") != expected_head:
            raise RuntimeError(f"packaged identity mismatch: {status}")
        report["status"] = status
        report["connect"] = _request(port, "connect", timeout=15)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            connection = _request(port, "connection_state")
            if connection.get("connection_state") == "READY":
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Desktop did not reach READY: {connection}")
        report["connection"] = connection
        for query, expected in QUERIES:
            submitted = _request(port, "submit", text=query)
            transcript = _request(port, "chat_text")["chat_text"]
            if expected not in transcript or "I understand this needs an MA2 workflow" in transcript:
                raise RuntimeError(f"unexpected Desktop Chat output for {query}: {transcript}")
            report["queries"].append({"text": query, "submitted": submitted, "chat_text": transcript})
        records = _new_records(log_path, offset)
        state_commands = [item.get("data", {}).get("command", "") for item in records if item.get("event") in {"state_read", "state_export"}]
        report["audit_events"] = [item.get("event") for item in records]
        report["state_commands"] = state_commands
        report["write_command_detected"] = bool(state_commands)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if state_commands else 0
    finally:
        try:
            _request(port, "shutdown", timeout=3)
        except Exception:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
