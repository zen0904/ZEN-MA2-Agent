"""Verify that the built one-folder EXE stays alive before distribution."""

from __future__ import annotations

import subprocess
import os
import time
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ui-request", help="Run a request through the packaged PySide6 chat widget.")
    args = parser.parse_args()
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
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
