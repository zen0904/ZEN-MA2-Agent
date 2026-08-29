"""Verify that the built one-folder EXE stays alive before distribution."""

from __future__ import annotations

import subprocess
import os
import time
import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"


def _chat_routing_smoke() -> int:
    """Exercise the actual frozen Desktop Send path, not AgentCore directly."""
    from portable_resources import assert_portable_resources

    bundle = EXE.parent
    assert_portable_resources(bundle)
    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    identity_run = subprocess.run([str(EXE), "--build-identity"], cwd=bundle, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if identity_run.returncode:
        raise SystemExit(identity_run.stdout + identity_run.stderr)
    identity = json.loads(identity_run.stdout.strip())
    if identity.get("head") != expected_head:
        raise SystemExit(f"Portable build identity mismatch: {identity.get('head')} != {expected_head}")

    log_path = bundle / "logs" / "agent.jsonl"
    log_path.unlink(missing_ok=True)
    checks = (
        ("Layout 1 裡有哪些燈？", "layout_items_query", "LayoutExportProvider", "configure state_adapter.plugin_slot"),
        ("有哪些 Position Preset？", "preset_list", "PresetProvider", "I understand this needs an MA2 workflow"),
        ("有哪些 Effect？", "effect_list", "EffectProvider", "I understand this needs an MA2 workflow"),
    )
    for query, intent, provider, forbidden in checks:
        run = subprocess.run([str(EXE), "--ui-smoke-request", query], cwd=bundle, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        output = run.stdout + run.stderr
        if run.returncode or forbidden in output:
            raise SystemExit(f"Portable chat smoke failed for {query}:\n{output}")
        events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        route = next((event["data"] for event in reversed(events) if event.get("event") == "chat_routing" and event["data"].get("CHAT_INPUT") == query), None)
        if not route or route.get("ROUTER_INTENT") != intent or route.get("PROVIDER") != provider or route.get("ROUTER_HANDLER") != "state_answer":
            raise SystemExit(f"Portable chat routing mismatch for {query}: {route}")
        response = next((event["data"] for event in reversed(events) if event.get("event") == "chat_response"), None)
        if not response or response.get("RESPONSE_TYPE") != "ANSWER":
            raise SystemExit(f"Portable chat response mismatch for {query}: {response}")
        print(f"PACKAGED_CHAT|{intent}|{provider}|{response['message']}")
    print(f"PACKAGED_BUILD|HEAD|{identity['head']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui-request", help="Run a request through the packaged PySide6 chat widget.")
    parser.add_argument("--chat-routing", action="store_true", help="Run the three routing checks through the packaged desktop widget.")
    args = parser.parse_args()
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
    if args.chat_routing:
        return _chat_routing_smoke()
    if args.ui_request:
        environment = dict(os.environ)
        environment["QT_QPA_PLATFORM"] = "offscreen"
        process = subprocess.Popen([str(EXE), "--ui-smoke-request", args.ui_request], cwd=EXE.parent, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            process.terminate()
            stdout, stderr = process.communicate(timeout=10)
            raise SystemExit("Portable UI smoke timed out.\n" + stdout + stderr)
        output = stdout + stderr
        if process.returncode or "Unsupported MVP request" in output or "NOT IMPLEMENTED" not in output:
            raise SystemExit(output or f"UI smoke failed with code {process.returncode}")
        print(output.strip())
        return 0
    process = subprocess.Popen([str(EXE)], cwd=EXE.parent)
    try:
        time.sleep(5)
        if process.poll() is not None:
            raise SystemExit(f"Portable EXE exited early with code {process.returncode}")
        print("Portable EXE smoke passed: process stayed alive for 5 seconds.")
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
