"""Explicit controlled grandMA2 Timecode Offset v1 test via packaged Desktop."""
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
TEST_TIMECODE = 9000
SETUP_QUERY = f"ZEN TEST create Timecode {TEST_TIMECODE}"
OFFSET_QUERY = f"Timecode {TEST_TIMECODE} 往後 500ms"


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
    result = json.loads(data.decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "automation request failed"))
    return result


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
    reuse_existing = "--reuse-existing" in sys.argv
    calibration = "--calibrate-250ms" in sys.argv
    requested_offset_ms = 250 if calibration else 500
    expected_literal = f"{requested_offset_ms // 1000}.{(requested_offset_ms % 1000) // 10:02d}s"
    offset_query = f"Timecode {TEST_TIMECODE} 往後 {requested_offset_ms}ms"
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    bundle, log_path = EXE.parent, EXE.parent / "logs" / "agent.jsonl"
    log_offset = log_path.stat().st_size if log_path.exists() else 0
    subprocess.run(["taskkill", "/F", "/IM", "ZEN_MA2_Agent.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    port = _free_port()
    environment = dict(os.environ, ZEN_MA2_AUTOMATION="1", ZEN_MA2_AUTOMATION_PORT=str(port), ZEN_MA2_TIMECODE_TEST_MODE="1")
    process = subprocess.Popen([str(EXE), "--automation-test"], cwd=bundle, env=environment)
    report: dict[str, object] = {
        "timecode": TEST_TIMECODE,
        "setup_query": SETUP_QUERY,
        "offset_query": offset_query,
        "reuse_existing": reuse_existing,
    }
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

        if reuse_existing:
            report["setup"] = f"Reused controlled Timecode {TEST_TIMECODE}; no setup write issued."
        else:
            # Test data itself has the ordinary UI preview/approval lifecycle.
            report["setup_submit"] = _request(port, "submit", text=SETUP_QUERY)
            setup_preview = _request(port, "chat_text")["chat_text"]
            if "TEST-ONLY Timecode Setup Preview" not in setup_preview:
                raise RuntimeError(f"Test Timecode setup preview missing: {setup_preview}")
            if any(item.get("event") == "workflow_execute" for item in _new_records(log_path, log_offset)):
                raise RuntimeError("Test Timecode setup wrote before the Desktop approval handler.")
            report["setup_preview"] = setup_preview
            report["setup_execute"] = _request(port, "execute_pending", timeout=60)

        # The actual product workflow is a separate, fresh Preview and approval.
        report["offset_submit"] = _request(port, "submit", text=offset_query)
        offset_preview = _request(port, "chat_text")["chat_text"]
        expected_preview_offset = f"Offset: +{requested_offset_ms / 1000:.3f} s"
        if "Timecode Offset Preview" not in offset_preview or expected_preview_offset not in offset_preview or "Approval required." not in offset_preview:
            raise RuntimeError(f"Timecode Offset preview missing: {offset_preview}")
        records_before_approval = _new_records(log_path, log_offset)
        workflows_before = [item for item in records_before_approval if item.get("event") == "workflow_execute"]
        expected_prior_workflows = 0 if reuse_existing else 1
        if len(workflows_before) != expected_prior_workflows:
            raise RuntimeError(f"Offset Preview wrote before approval: {workflows_before}")
        if not reuse_existing and workflows_before[0].get("data", {}).get("commands") != [f"Store Timecode {TEST_TIMECODE} /nc"]:
            raise RuntimeError(f"Test setup was not isolated: {workflows_before}")
        report["offset_preview"] = offset_preview
        report["offset_execute"] = _request(port, "execute_pending", timeout=60)
        transcript = _request(port, "chat_text")["chat_text"]
        if not calibration and "Verification: VERIFIED" not in transcript:
            raise RuntimeError(f"Timecode Offset verification was not reported: {transcript}")
        records = _new_records(log_path, log_offset)
        workflows = [item.get("data", {}) for item in records if item.get("event") == "workflow_execute"]
        verification = [item.get("data", {}) for item in records if item.get("event") == "timecode_offset_verification"]
        expected = f"Assign Timecode {TEST_TIMECODE}/Offset = {expected_literal}"
        expected_workflow_count = 1 if reuse_existing else 2
        if len(workflows) != expected_workflow_count or workflows[-1].get("commands") != [expected]:
            raise RuntimeError(f"Unexpected approved Timecode workflow audit: {workflows}")
        if not verification or not verification[-1].get("exists"):
            raise RuntimeError(f"Timecode was not read back after approved offset: {verification}")
        if not calibration and verification[-1].get("status") != "VERIFIED":
            raise RuntimeError(f"Timecode Offset was not verified: {verification}")
        report.update({"chat": transcript, "workflows": workflows, "verification": verification})
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
