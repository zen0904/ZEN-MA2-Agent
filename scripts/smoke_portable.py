"""Verify that the built one-folder EXE stays alive before distribution."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "ZEN_MA2_Agent" / "ZEN_MA2_Agent.exe"


def main() -> int:
    if not EXE.is_file():
        raise SystemExit(f"Portable EXE not found: {EXE}")
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
