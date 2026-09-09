"""Run the one opt-in real-song build through the packaged Desktop bridge.

The bridge exposes no MA command channel.  This verifier can only connect with
the saved Desktop settings, preview the fixed bundled typed analysis fixture,
and press the Desktop's normal Execute button.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"
PROTECTED_SEQUENCES = {201, 202, 204}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _request(port: int, action: str, *, timeout: float = 180) -> dict[str, Any]:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
        client.settimeout(timeout)
        client.sendall(json.dumps({"action": action}, ensure_ascii=False).encode("utf-8"))
        data = b""
        while not data.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk:
                break
            data += chunk
    response = json.loads(data.decode("utf-8"))
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "Desktop automation request failed"))
    return response


def _wait(port: int, action: str, timeout: float = 10) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _request(port, action, timeout=3)
        except (OSError, ValueError, RuntimeError) as exc:
            error = exc
            time.sleep(0.1)
    raise RuntimeError(f"Desktop automation bridge did not become available: {error}")


def _new_records(path: Path, offset: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("rb") as handle:
        handle.seek(offset)
        return [json.loads(line) for line in handle.read().decode("utf-8", errors="replace").splitlines() if line.strip()]


def _pending_action(snapshot: dict[str, Any]) -> dict[str, Any]:
    pending = [item for item in snapshot.get("actions", []) if item.get("status") == "PENDING_APPROVAL"]
    if len(pending) != 1:
        raise RuntimeError(f"Expected one pending real-song ActionPlan, got {pending!r}")
    return pending[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Opt-in packaged Desktop real-song verification.")
    parser.add_argument("--real-machine", action="store_true", help="Required acknowledgement before any approved MA2 write.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing to run against MA2 without --real-machine.")
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
    report: dict[str, Any] = {"automation_port": port, "protected_sequences": sorted(PROTECTED_SEQUENCES)}
    try:
        status = _wait(port, "status")
        if status.get("build_head") != expected_head or not status.get("desktop_alive"):
            raise RuntimeError(f"Packaged build identity mismatch: {status}")
        report["status"] = status
        report["connect"] = _request(port, "connect", timeout=15)
        deadline = time.monotonic() + 10
        connection: dict[str, Any] = {}
        while time.monotonic() < deadline:
            connection = _request(port, "connection_state", timeout=3)
            if connection.get("connection_state") == "READY":
                break
            time.sleep(0.1)
        if connection.get("connection_state") != "READY":
            raise RuntimeError(f"Desktop did not reach READY: {connection}")
        report["connection"] = connection

        report["preview"] = _request(port, "preview_real_song", timeout=180)
        pending = _pending_action(_request(port, "state_snapshot"))
        intent = ((pending.get("task") or {}).get("intent") or {})
        parameters = intent.get("parameters") or {}
        sequence = parameters.get("sequence")
        if not isinstance(sequence, int) or sequence in PROTECTED_SEQUENCES:
            raise RuntimeError(f"Unsafe Sequence allocation: {sequence!r}")
        if parameters.get("cue_count", 0) < 8:
            raise RuntimeError("Real-song plan did not create at least eight Cues.")
        if not parameters.get("referenced_effects"):
            raise RuntimeError("Real-song plan has no typed CALL_EFFECT reference.")
        report["plan"] = {"sequence": sequence, "label": parameters.get("sequence_label"), "cue_count": parameters.get("cue_count"), "referenced_groups": parameters.get("referenced_groups"), "referenced_presets": parameters.get("referenced_presets"), "referenced_effects": parameters.get("referenced_effects")}
        transcript = _request(port, "chat_text")["chat_text"]
        if "ZEN AI REAL SONG BUILD PREVIEW" not in transcript or "Approval required." not in transcript:
            raise RuntimeError("Packaged Desktop did not render the required real-song Preview.")
        report["preview_text"] = transcript

        report["execute"] = _request(port, "execute_pending", timeout=180)
        completed = next((item for item in _request(port, "state_snapshot").get("actions", []) if item.get("id") == pending.get("id")), None)
        if not completed or completed.get("status") != "EXECUTED":
            raise RuntimeError(f"Real-song ActionPlan did not execute: {completed}")
        report["result"] = completed.get("result")
        if "Verification: PARTIAL" not in str(completed.get("result")):
            raise RuntimeError("Real-song metadata verification was not reported.")
        if "Effect references verified:" not in str(completed.get("result")):
            raise RuntimeError("Fresh Effect reference verification was not reported.")

        records = _new_records(log_path, offset)
        workflow_records = [record for record in records if record.get("event") == "workflow_execute"]
        if len(workflow_records) != 1:
            raise RuntimeError(f"Expected one approved workflow execution, got {len(workflow_records)}")
        commands = workflow_records[0].get("data", {}).get("commands", [])
        expected_prefix = ("ClearAll",)
        if not commands or tuple(commands[:1]) != expected_prefix or commands[-1] != "ClearAll":
            raise RuntimeError("Programmer ClearAll boundaries are missing from the approved build.")
        if not any(command.startswith("Effect ") for command in commands):
            raise RuntimeError("No verified Effect call was sent by the approved build.")
        if any(command.startswith("Store Cue ") and f" Sequence {sequence} " not in command for command in commands):
            raise RuntimeError("Build attempted to store a Cue in a non-owned Sequence.")
        if any(any(token in command for token in ("Delete", "Assign", "Move", "Go", "Off", "Patch")) for command in commands):
            raise RuntimeError("Unexpected destructive/playback command in approved real-song build.")
        report["approved_commands"] = commands
        report["audit_events"] = [record.get("event") for record in records]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        try:
            _request(port, "shutdown", timeout=3)
        except Exception:
            pass
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=8)


if __name__ == "__main__":
    raise SystemExit(main())
