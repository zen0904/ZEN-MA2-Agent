"""Read-only real-MA2 Geometry Clone v1 Preview verification via frozen Desktop."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _request(port: int, action: str, *, timeout: float = 90, **payload: object) -> dict:
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
    while time.monotonic() < deadline:
        try:
            return _request(port, "status", timeout=3)
        except (OSError, ConnectionError, RuntimeError, ValueError):
            time.sleep(0.1)
    raise RuntimeError("Geometry Clone Desktop automation bridge was not available.")


def _new_records(path: Path, offset: int) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("rb") as handle:
        handle.seek(offset)
        return [json.loads(line) for line in handle.read().decode("utf-8", errors="replace").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-machine", action="store_true", help="Required acknowledgement before connecting to real MA2.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 verification without --real-machine.")
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")

    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    bundle = EXE.parent
    log_path = bundle / "logs" / "agent.jsonl"
    log_offset = log_path.stat().st_size if log_path.exists() else 0
    subprocess.run(["taskkill", "/F", "/IM", "ZEN_MA2_Agent.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    port = _free_port()
    environment = dict(os.environ, ZEN_MA2_AUTOMATION="1", ZEN_MA2_AUTOMATION_PORT=str(port))
    process = subprocess.Popen([str(EXE), "--automation-test"], cwd=bundle, env=environment)
    report: dict[str, object] = {"queries": []}
    try:
        status = _wait_for(port)
        if status.get("build_head") != expected_head or not status.get("desktop_alive"):
            raise RuntimeError(f"Invalid frozen Desktop identity: {status}")
        report["status"] = status
        report["connect"] = _request(port, "connect", timeout=15)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            connection = _request(port, "connection_state", timeout=3)
            if connection.get("connection_state") == "READY":
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Desktop did not reach READY: {connection}")
        report["connection"] = connection

        for text in ("HYBRID 跟 SPOT 數量一樣嗎？", "預覽 HYBRID → SPOT Clone"):
            submitted = _request(port, "submit", timeout=120, text=text)
            transcript = _request(port, "chat_text", timeout=3)["chat_text"]
            report["queries"].append({"text": text, "submitted": submitted, "chat_text": transcript})

        mapping, preview = report["queries"]
        if "Geometry Clone Mapping (SAFE)" not in mapping["chat_text"]:
            raise RuntimeError(f"SAFE mapping response was missing: {mapping['chat_text']}")
        expected_preview = ("Geometry Clone Preview", "Safety:", "MODIFY", "Approval required.", "Disabled pending safe real-machine Clone write validation")
        if not all(marker in preview["chat_text"] for marker in expected_preview):
            raise RuntimeError(f"Disabled Clone Preview was incomplete: {preview['chat_text']}")
        records = _new_records(log_path, log_offset)
        workflow_writes = [record for record in records if record.get("event") == "workflow_execute"]
        clone_commands = [record for record in records if "Clone Fixture" in json.dumps(record.get("data", {}), ensure_ascii=False)]
        if workflow_writes or clone_commands:
            raise RuntimeError(f"Preview unexpectedly executed MA2 writes: {workflow_writes or clone_commands}")
        report["audit_events"] = [record.get("event") for record in records]
        report["state_exports"] = [record.get("data", {}).get("command") for record in records if record.get("event") == "state_export"]
        report["workflow_writes"] = workflow_writes
        report["clone_commands"] = clone_commands
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
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
