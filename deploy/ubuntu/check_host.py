from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path


def _nvidia() -> dict[str, object]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"nvidia_smi": False, "gpu_name": None, "vram_total_mb": None}
    try:
        completed = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"nvidia_smi": True, "gpu_name": None, "vram_total_mb": None}
    if completed.returncode != 0:
        return {"nvidia_smi": True, "gpu_name": None, "vram_total_mb": None}
    line = next((item.strip() for item in completed.stdout.splitlines() if item.strip()), "")
    parts = [part.strip() for part in line.split(",", 1)] if line else []
    name = parts[0] if parts else None
    try:
        vram = int(parts[1]) if len(parts) > 1 else None
    except ValueError:
        vram = None
    return {"nvidia_smi": True, "gpu_name": name, "vram_total_mb": vram}


def _ram_mb() -> int | None:
    try:
        return int(os.sysconf("SC_PHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE")) // (1024 * 1024)
    except (OSError, ValueError, AttributeError):
        return None


def main() -> int:
    root = Path.cwd()
    disk = shutil.disk_usage(root)
    report = {
        "schema": "zen.ubuntu_host_check.v0.1",
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "cpu_logical_threads": os.cpu_count(),
        "ram_total_mb": _ram_mb(),
        "disk_free_mb": disk.free // (1024 * 1024),
        "git_available": shutil.which("git") is not None,
        "node_available": shutil.which("node") is not None,
        "npm_available": shutil.which("npm") is not None,
        **_nvidia(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
