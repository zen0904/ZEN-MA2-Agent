"""Real-MA2 Geometry Clone verification through the packaged Desktop only.

This explicit test runner is intentionally narrow.  It can only drive the
Desktop's fixed automation actions and the allow-listed isolated-show workflow
implemented by AgentCore.  It never sends MA2 commands itself.
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
TEST_SHOW = "MA2_EFFECT_PROBE_WORK"
PRODUCTION_SHOW = "zen templ show"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _request(port: int, action: str, *, timeout: float = 180, **payload: object) -> dict[str, Any]:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
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
        raise RuntimeError(response.get("error", "Desktop automation request failed"))
    return response


def _wait_for_bridge(port: int) -> dict[str, Any]:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            return _request(port, "status", timeout=3)
        except (OSError, ConnectionError, RuntimeError, ValueError):
            time.sleep(0.2)
    raise RuntimeError("Packaged Desktop automation bridge did not become available.")


def _wait_ready(port: int) -> dict[str, Any]:
    deadline = time.monotonic() + 20
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _request(port, "connection_state", timeout=5)
        if last.get("connection_state") == "READY":
            return last
        time.sleep(0.25)
    raise RuntimeError(f"Desktop did not reach READY: {last}")


def _submit(port: int, text: str) -> str:
    _request(port, "submit", text=text)
    return str(_request(port, "chat_text")["chat_text"])


def _state(port: int) -> dict[str, Any]:
    return _request(port, "state_snapshot")


def _action(port: int) -> dict[str, Any]:
    actions = _state(port)["actions"]
    if not actions:
        raise RuntimeError("Desktop did not create an ActionPlan.")
    return actions[-1]


def _execute_pending(port: int) -> dict[str, Any]:
    _request(port, "execute_pending", timeout=180)
    action = _action(port)
    if action.get("status") != "EXECUTED":
        raise RuntimeError(f"Approved Desktop action did not execute: {action}")
    return action


def _refresh(port: int, *queries: str) -> dict[str, Any]:
    for query in queries:
        _submit(port, query)
    return _state(port)["state_browser"]


def _groups(browser: dict[str, Any]) -> list[dict[str, Any]]:
    return list(browser["groups"].get("values") or [])


def _fixtures(browser: dict[str, Any]) -> list[dict[str, Any]]:
    return list(browser["fixtures"].get("values") or [])


def _membership(browser: dict[str, Any], number: int) -> list[int]:
    value = next((item for item in browser["group_membership"].get("values", []) if item.get("group_no") == number), None)
    if not value:
        raise RuntimeError(f"Group {number} membership was not returned.")
    return list(value.get("fixtures") or [])


def _new_records(path: Path, offset: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open("rb") as handle:
        handle.seek(offset)
        return [json.loads(line) for line in handle.read().decode("utf-8", errors="replace").splitlines() if line.strip()]


def _write_events(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if record.get("event") == "workflow_execute"]


def _production_fingerprint(port: int) -> tuple[dict[str, Any], dict[int, list[int]]]:
    browser = _refresh(port, "有哪些 Group", "有哪些 Fixture", *(f"Group {number} 裡有哪些燈？" for number in range(1, 8)))
    memberships = {number: _membership(browser, number) for number in range(1, 8)}
    return {"groups": _groups(browser), "fixtures": _fixtures(browser)}, memberships


def _restore(port: int, report: dict[str, Any]) -> None:
    transcript = _submit(port, "ZEN TEST restore production show")
    if "Production Show Restore Preview" not in transcript:
        raise RuntimeError("Production restore did not render the expected Desktop Preview.")
    action = _execute_pending(port)
    report["restore"] = {"preview": "Production Show Restore Preview", "result": action.get("result")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-machine", action="store_true", help="Required acknowledgement before using a real MA2 session.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 verification without --real-machine.")
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")

    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    bundle, log_path = EXE.parent, EXE.parent / "logs" / "agent.jsonl"
    offset = log_path.stat().st_size if log_path.exists() else 0
    subprocess.run(["taskkill", "/F", "/IM", "ZEN_MA2_Agent.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    port = _free_port()
    environment = dict(os.environ, ZEN_MA2_AUTOMATION="1", ZEN_MA2_AUTOMATION_PORT=str(port), ZEN_MA2_GEOMETRY_TEST_MODE="1")
    process = subprocess.Popen([str(EXE), "--automation-test"], cwd=bundle, env=environment)
    report: dict[str, Any] = {"test_show": TEST_SHOW, "production_show": PRODUCTION_SHOW}
    loaded_test = False
    try:
        status = _wait_for_bridge(port)
        if status.get("build_head") != expected_head or not status.get("desktop_alive"):
            raise RuntimeError(f"Packaged build identity mismatch: {status}")
        report["build"] = status
        _request(port, "connect", timeout=20)
        report["connection"] = _wait_ready(port)

        production_before, memberships_before = _production_fingerprint(port)
        report["production_before"] = {"group_count": len(production_before["groups"]), "fixture_count": len(production_before["fixtures"]), "memberships": memberships_before}

        load_preview = _submit(port, "ZEN TEST load geometry show")
        if "Geometry Clone Test Show Preview" not in load_preview:
            raise RuntimeError("Test Show load did not render the expected Desktop Preview.")
        load_action = _execute_pending(port)
        loaded_test = True
        report["test_load"] = {"preview": "Geometry Clone Test Show Preview", "result": load_action.get("result")}

        test_browser = _refresh(port, "有哪些 Group", "有哪些 Fixture")
        test_fixtures = _fixtures(test_browser)
        if len(test_fixtures) < 2:
            raise RuntimeError("The isolated candidate Show does not contain two Fixtures; no production state was modified.")
        source, destination = int(test_fixtures[0]["number"]), int(test_fixtures[1]["number"])
        if any(item.get("number") in {90, 91} for item in _groups(test_browser)):
            raise RuntimeError("The isolated candidate already contains Group 90 or 91; refusing to overwrite it.")
        report["test_fixtures"] = [{"number": item.get("number"), "name": item.get("name")} for item in test_fixtures]
        report["selected_pair"] = [source, destination]

        setup_preview = _submit(port, f"ZEN TEST setup geometry groups {source} {destination}")
        if "Geometry Clone Test Groups Preview" not in setup_preview:
            raise RuntimeError("Test Group setup did not render the expected Desktop Preview.")
        setup_action = _execute_pending(port)
        report["group_setup"] = {"preview": "Geometry Clone Test Groups Preview", "result": setup_action.get("result")}

        test_browser = _refresh(port, "有哪些 Group", "Group 90 裡有哪些燈？", "Group 91 裡有哪些燈？", "有哪些 Fixture")
        memberships = {90: _membership(test_browser, 90), 91: _membership(test_browser, 91)}
        if memberships != {90: [source], 91: [destination]}:
            raise RuntimeError(f"Test Group membership mismatch: {memberships}")
        report["test_memberships"] = memberships

        clone_preview = _submit(port, "預覽 Group 90 → Group 91 Clone")
        if not all(marker in clone_preview for marker in ("Geometry Clone Preview", "Safety: MODIFY", f"{source} → {destination}")):
            raise RuntimeError("Clone preview did not contain the expected deterministic mapping.")
        pending = _action(port)
        if pending.get("status") != "PENDING_APPROVAL":
            raise RuntimeError(f"Clone was not held for approval: {pending}")
        report["clone_preview"] = {"safety": pending.get("safety"), "mapping": f"{source} -> {destination}"}

        clone_action = _execute_pending(port)
        clone_result = str(clone_action.get("result"))
        if "Verification: PARTIAL" not in clone_result:
            raise RuntimeError(f"Clone verification did not reach PARTIAL: {clone_result}")
        report["clone"] = {"commands": [step.get("command") for step in clone_action.get("steps", [])], "result": clone_result}

        _restore(port, report)
        loaded_test = False
        production_after, memberships_after = _production_fingerprint(port)
        unchanged = production_before == production_after and memberships_before == memberships_after
        report["production_after"] = {"group_count": len(production_after["groups"]), "fixture_count": len(production_after["fixtures"]), "memberships": memberships_after}
        report["production_unchanged"] = unchanged
        if not unchanged:
            raise RuntimeError("Production Show state fingerprint differs after the isolated verification.")

        records = _new_records(log_path, offset)
        writes = _write_events(records)
        clone_writes = [record for record in writes if any("Clone Fixture" in str(command) for command in record.get("data", {}).get("commands", []))]
        report["audit"] = {"workflow_writes": writes, "clone_writes": clone_writes}
        if len(clone_writes) != 1 or clone_writes[0].get("data", {}).get("commands") != [f"Clone Fixture {source} At Fixture {destination} /nc"]:
            raise RuntimeError(f"Unexpected approved Clone audit trail: {clone_writes}")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    finally:
        if loaded_test:
            try:
                _restore(port, report)
            except Exception as exc:
                report["restore_failure"] = str(exc)
        try:
            _request(port, "shutdown", timeout=5)
        except Exception:
            pass
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
