#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path("/opt/zen/ZEN-MA2-Agent")
ALLOWED_SERVICES = {
    "zen-show-controller",
    "zen-controller-readonly-facade",
    "zen-lighting-operator-proxy",
    "zen-glances",
    "zen-antseed-buyer",
}
MCP_SERVERS = {
    "zen-native-stdio",
    "glances",
    "markitdown",
    "docling",
    "crawl4ai",
    "codebase-memory",
    "basic-memory",
    "reaper-live",
    "reaper-readonly",
}


def run(argv: list[str], *, timeout: int = 120) -> int:
    proc = subprocess.run(
        argv,
        cwd=REPO,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    print("$", " ".join(argv))
    print(proc.stdout.rstrip())
    return proc.returncode


def parse_body(body: str) -> tuple[str, str]:
    action = ""
    arg = ""
    for raw in body.splitlines():
        line = raw.strip()
        if line.lower().startswith("action:"):
            action = line.split(":", 1)[1].strip().lower()
        elif line.lower().startswith("arg:"):
            arg = line.split(":", 1)[1].strip()
    if not action:
        raise SystemExit("Missing required 'action:' line.")
    return action, arg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", required=True)
    ns = ap.parse_args()
    action, arg = parse_body(ns.body)

    if action == "status":
        rc = 0
        for service in sorted(ALLOWED_SERVICES):
            rc |= run(["systemctl", "is-active", service], timeout=20)
        rc |= run(["free", "-h"], timeout=20)
        rc |= run(["df", "-h", "/"], timeout=20)
        return rc

    if action == "antseed-status":
        rc = run(["systemctl", "is-active", "zen-antseed-buyer"], timeout=20)
        rc |= run(["systemctl", "is-enabled", "zen-antseed-buyer"], timeout=20)
        rc |= run(["ss", "-ltn"], timeout=20)
        rc |= run(
            [
                "python3", "-c",
                "import json,urllib.request; p=json.load(urllib.request.urlopen('http://127.0.0.1:8377/v1/models', timeout=5)); ids=[str(x.get('id')) for x in p.get('data',[]) if isinstance(x,dict) and x.get('id')]; print('MODELS_COUNT='+str(len(ids))); print('MODELS_SAMPLE='+','.join(ids[:30]))",
            ],
            timeout=20,
        )
        return rc

    if action == "tests":
        return run(
            ["/opt/zen/venv/bin/python", "-m", "pytest", "-q"],
            timeout=1800,
        )

    if action == "mcp-probe":
        targets = [arg] if arg else sorted(MCP_SERVERS)
        bad = [x for x in targets if x not in MCP_SERVERS]
        if bad:
            raise SystemExit(f"MCP server not allowlisted: {bad[0]}")
        rc = 0
        for target in targets:
            rc |= run(["openclaw", "mcp", "probe", target, "--json"], timeout=90)
        return rc

    if action == "logs":
        if arg not in ALLOWED_SERVICES:
            raise SystemExit("Service is not allowlisted.")
        return run(
            ["journalctl", "-u", arg, "-n", "200", "--no-pager"],
            timeout=30,
        )

    if action == "restart":
        if arg not in ALLOWED_SERVICES:
            raise SystemExit("Service is not allowlisted.")
        return run(["sudo", "/usr/local/sbin/zen-root-ops", "restart", arg], timeout=60)

    if action == "git-sync":
        rc = run(["git", "fetch", "origin", "main"], timeout=120)
        if rc:
            return rc
        return run(["git", "merge", "--ff-only", "origin/main"], timeout=120)

    if action == "tool-inventory":
        commands = [
            ["restic", "version"],
            ["docker", "--version"],
            ["midimonster", "-v"],
            ["rtpmidid-cli", "--help"],
            ["ltcgen", "--help"],
            ["bd", "--version"],
            ["supergateway", "--version"],
            ["codex-acp", "--version"],
            ["gemini", "--version"],
            ["docker", "mcp", "version"],
        ]
        rc = 0
        for cmd in commands:
            rc |= run(cmd, timeout=30)
        return rc

    if action == "recovery-verify":
        return run(
            ["/bin/bash", "deploy/ops_tasks/verify_zen_ops_recovery.sh"],
            timeout=300,
        )

    raise SystemExit(f"Unsupported action: {action}")


if __name__ == "__main__":
    sys.exit(main())
