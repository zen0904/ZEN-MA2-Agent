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
    if not (bundle / "portable_build_complete.json").is_file():
        raise SystemExit("Portable build is incomplete: completion marker is missing.")
    expected_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    environment = dict(os.environ)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    identity_run = subprocess.run([str(EXE), "--build-identity"], cwd=bundle, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if identity_run.returncode:
        raise SystemExit(identity_run.stdout + identity_run.stderr)
    identity = json.loads(identity_run.stdout.strip())
    if identity.get("head") != expected_head:
        raise SystemExit(f"Portable build identity mismatch: {identity.get('head')} != {expected_head}")

    checks = (
        ("Layout 1 裡有哪些燈？", "layout_items_query", "LayoutExportProvider", "configure state_adapter.plugin_slot"),
        ("有哪些 Position Preset？", "preset_list", "PresetProvider", "I understand this needs an MA2 workflow"),
        ("有哪些 Effect？", "effect_list", "EffectProvider", "I understand this needs an MA2 workflow"),
        ("檢查 Show", "diagnose_show", "ShowDiagnostics", "I understand this needs an MA2 workflow"),
        ("Programmer 有沒有東西？", "state_programmer", "ProgrammerInspectCapability", "I understand this needs an MA2 workflow"),
        ("目前選了哪些燈？", "state_selection", "SelectionInspectCapability", "I understand this needs an MA2 workflow"),
    )
    for query, intent, provider, forbidden in checks:
        run = subprocess.run([str(EXE), "--portable-routing-smoke", query], cwd=bundle, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        output = run.stdout + run.stderr
        if run.returncode or forbidden in output:
            raise SystemExit(f"Portable chat smoke failed for {query}:\n{output}")
        payload = json.loads(next(line for line in reversed(run.stdout.splitlines()) if line.startswith("{")))
        route = payload.get("routing")
        if not route or route.get("ROUTER_INTENT") != intent or route.get("PROVIDER") != provider or route.get("ROUTER_HANDLER") != "state_answer":
            raise SystemExit(f"Portable chat routing mismatch for {query}: {route}")
        response = payload.get("response", {})
        if response.get("kind") != "ANSWER":
            raise SystemExit(f"Portable chat response mismatch for {query}: {response}")
        if intent in {"state_programmer", "state_selection"} and "UNSUPPORTED" not in response.get("text", ""):
            raise SystemExit(f"Portable inspect capability response mismatch for {query}: {response}")
        if query == "檢查 Show" and ("Show Diagnostics" not in response.get("text", "") or "ACTION PLAN" in response.get("text", "")):
            raise SystemExit(f"Portable diagnostics response mismatch:\n{response}")
        # Keep the outer Windows console smoke portable even when its active
        # code page cannot encode a localized response body.
        print(f"PACKAGED_CHAT|{intent}|{provider}|{response['text'].splitlines()[0]}")
    effect = subprocess.run([str(EXE), "--portable-routing-smoke", "幫 Group 1 做 Dimmer Chase"], cwd=bundle, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if effect.returncode:
        raise SystemExit(effect.stdout + effect.stderr)
    payload = json.loads(next(line for line in reversed(effect.stdout.splitlines()) if line.startswith("{")))
    if payload.get("routing", {}).get("ROUTER_INTENT") != "build_dimmer_chase" or payload.get("response", {}).get("kind") != "ACTION_PLAN":
        raise SystemExit(f"Portable Effect Builder preview routing mismatch: {payload}")
    print("PACKAGED_CHAT|build_dimmer_chase|EffectBuilderSkill|Effect Builder Preview")
    print(f"PACKAGED_BUILD|HEAD|{identity['head']}")
    return 0


def _effect_approval_smoke() -> int:
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    run = subprocess.run([str(EXE), "--portable-effect-approval-smoke", "幫 Group 1 做 Dimmer Chase"], cwd=EXE.parent, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25)
    if run.returncode:
        raise SystemExit(run.stdout + run.stderr)
    payload = json.loads(next(line for line in reversed(run.stdout.splitlines()) if line.startswith("{")))
    if payload.get("before") != ["List Group", "List Effect"]:
        raise SystemExit(f"Effect preview sent an unexpected command: {payload}")
    if payload.get("action_status") != "EXECUTED" or "Verification: PARTIAL" not in str(payload.get("result")):
        raise SystemExit(f"Effect approval did not execute/verify: {payload}")
    if not any(command.startswith("Store Effect 2500") for command in payload.get("commands", [])):
        raise SystemExit(f"Effect approval did not use the planned commands: {payload}")
    print("PACKAGED_EFFECT_APPROVAL|PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui-request", help="Run a request through the packaged PySide6 chat widget.")
    parser.add_argument("--chat-routing", action="store_true", help="Run the three routing checks through the packaged desktop widget.")
    parser.add_argument("--effect-approval", action="store_true", help="Run a fake-transport Effect Builder preview and approval smoke through the packaged Desktop.")
    args = parser.parse_args()
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
    if args.chat_routing:
        return _chat_routing_smoke()
    if args.effect_approval:
        return _effect_approval_smoke()
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
