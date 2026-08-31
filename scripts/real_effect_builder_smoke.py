"""Explicit controlled grandMA2 Effect Builder test via packaged Desktop UI."""
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
QUERY = "幫 Group 1 建立 Effect 2500 Dimmer Chase"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _request(port: int, action: str, *, timeout: float = 45, **payload: object) -> dict:
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
        raise SystemExit("Refusing real MA2 modification without --real-machine.")
    verify_existing = "--verify-existing" in sys.argv
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
    report: dict[str, object] = {"query": QUERY, "effect_number": 2500, "mode": "verify_existing" if verify_existing else "create"}
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
        if verify_existing:
            # This is deliberately a Desktop Chat, read-only validation path for
            # an already-created controlled Effect.  It avoids overwriting a
            # real console object while proving the packaged parser/formatter.
            report["lookup_submit"] = _request(port, "submit", text="Effect 2500 是什麼？")
            transcript = _request(port, "chat_text")["chat_text"]
            records = _new_records(log_path, offset)
            writes = [item.get("data", {}).get("commands", []) for item in records if item.get("event") == "workflow_execute"]
            if "Effect 2500: HYBRID Dimmer Chase" not in transcript or writes:
                raise RuntimeError(f"Existing Effect read-back was not a clean Desktop read-only verification: {transcript}; writes={writes}")
            report["chat"] = transcript
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        report["preview_submit"] = _request(port, "submit", text=QUERY)
        preview = _request(port, "chat_text")["chat_text"]
        if "Effect Builder Preview" not in preview or "Approval required." not in preview:
            raise RuntimeError(f"Effect Builder preview missing: {preview}")
        preview_records = _new_records(log_path, offset)
        premature = [item.get("data", {}).get("commands", []) for item in preview_records if item.get("event") == "workflow_execute"]
        if premature:
            raise RuntimeError(f"Preview executed MA2 commands before approval: {premature}")
        report["preview"] = preview
        report["execute"] = _request(port, "execute_pending", timeout=90)
        transcript = _request(port, "chat_text")["chat_text"]
        if "Verification: PARTIAL" not in transcript:
            raise RuntimeError(f"Effect Builder verification was not reported: {transcript}")
        records = _new_records(log_path, offset)
        workflow = [item.get("data", {}) for item in records if item.get("event") == "workflow_execute"]
        verification = [item.get("data", {}) for item in records if item.get("event") == "effect_builder_verification"]
        if len(workflow) != 1 or workflow[0].get("commands", [None])[0] != "Store Effect 2500 /nc":
            raise RuntimeError(f"Unexpected approved Effect workflow audit: {workflow}")
        if not verification or not verification[-1].get("exists") or not verification[-1].get("label_verified"):
            raise RuntimeError(f"Effect 2500 was not verified after execution: {verification}")
        report["chat"] = transcript
        report["workflow"] = workflow
        report["verification"] = verification
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
