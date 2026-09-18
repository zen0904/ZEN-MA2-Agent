from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import shutil
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import psutil


@dataclass(frozen=True)
class ProbeTarget:
    name: str
    host: str
    port: int


def _service_manager() -> str:
    system = platform.system().lower()
    if system == "linux":
        if Path("/run/systemd/system").exists() or shutil.which("systemctl"):
            return "systemd"
        return "UNKNOWN"
    if system == "darwin":
        return "launchd" if shutil.which("launchctl") else "UNKNOWN"
    if system == "windows":
        return "windows_scm" if shutil.which("sc.exe") or shutil.which("sc") else "UNKNOWN"
    return "UNKNOWN"


def _package_version(name: str) -> Optional[str]:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _ipv4_interfaces() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    stats = psutil.net_if_stats()
    for name, addresses in psutil.net_if_addrs().items():
        ipv4 = [
            item.address
            for item in addresses
            if item.family == socket.AF_INET and not item.address.startswith("127.")
        ]
        if not ipv4:
            continue
        state = stats.get(name)
        result.append(
            {
                "name": name,
                "ipv4": sorted(ipv4),
                "up": bool(state and state.isup),
                "speed_mbps": int(state.speed) if state and state.speed >= 0 else None,
            }
        )
    return sorted(result, key=lambda item: str(item["name"]).lower())


def _probe(target: ProbeTarget, timeout: float) -> dict[str, object]:
    try:
        with socket.create_connection((target.host, target.port), timeout=timeout):
            reachable = True
            error = None
    except OSError as exc:
        reachable = False
        error = f"{type(exc).__name__}: {str(exc)[:240]}"
    return {
        "name": target.name,
        "host": target.host,
        "port": target.port,
        "reachable": reachable,
        "error": error,
    }


def _parse_target(value: str) -> ProbeTarget:
    name, sep, endpoint = value.partition("=")
    if not sep or not name or not endpoint:
        raise argparse.ArgumentTypeError("target must use NAME=HOST:PORT")
    host, sep, raw_port = endpoint.rpartition(":")
    if not sep or not host:
        raise argparse.ArgumentTypeError("target must use NAME=HOST:PORT")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("target port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("target port must be in range 1..65535")
    return ProbeTarget(name=name, host=host, port=port)


def collect(targets: tuple[ProbeTarget, ...], timeout: float) -> dict[str, object]:
    memory = psutil.virtual_memory()
    root = Path(__file__).resolve().anchor or os.path.abspath(os.sep)
    disk = psutil.disk_usage(root)
    return {
        "schema": "zen.host_preflight.v0.1",
        "hostname": socket.gethostname(),
        "os": platform.system() or "UNKNOWN",
        "os_release": platform.release() or "UNKNOWN",
        "os_version": platform.version() or "UNKNOWN",
        "architecture": platform.machine() or "UNKNOWN",
        "cpu": platform.processor() or "UNKNOWN",
        "cpu_logical_threads": psutil.cpu_count(logical=True),
        "cpu_physical_cores": psutil.cpu_count(logical=False),
        "ram_total_mb": int(memory.total) // (1024 * 1024),
        "disk_root": root,
        "disk_total_mb": int(disk.total) // (1024 * 1024),
        "disk_free_mb": int(disk.free) // (1024 * 1024),
        "python": platform.python_version(),
        "packages": {
            "fastapi": _package_version("fastapi"),
            "httpx": _package_version("httpx"),
            "psutil": _package_version("psutil"),
            "uvicorn": _package_version("uvicorn"),
        },
        "service_manager": _service_manager(),
        "interfaces": _ipv4_interfaces(),
        "remote_admin_hints": {
            "ssh": shutil.which("ssh") is not None,
            "sshd": shutil.which("sshd") is not None,
        },
        "targets": [_probe(target, timeout) for target in targets],
        "ma2_writes": 0,
        "notes": [
            "Read-only preflight. No installation or configuration changes are performed.",
            "A reachable TCP port proves transport reachability only, not application readiness or authorization.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only ZEN Gateway/Worker host preflight"
    )
    parser.add_argument(
        "--target",
        action="append",
        type=_parse_target,
        default=[],
        metavar="NAME=HOST:PORT",
        help="Optional TCP reachability probe, repeatable.",
    )
    parser.add_argument("--timeout", type=float, default=1.0)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    payload = collect(tuple(args.target), float(args.timeout))
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
