from __future__ import annotations

import argparse
import ipaddress

import uvicorn

from .server import WorkerConfig, create_worker_app

DEFAULT_WORKER_HOST = "127.0.0.1"
DEFAULT_WORKER_PORT = 8878


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="ZEN remote AI worker control-plane service")
    parser.add_argument("--worker-id", required=True)
    parser.add_argument("--host", default=DEFAULT_WORKER_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_WORKER_PORT)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()

    if not args.allow_remote and not _is_loopback(args.host):
        parser.error("non-loopback worker bind requires --allow-remote and separate network security review")
    if not 1 <= args.port <= 65535:
        parser.error("port must be in range 1..65535")

    uvicorn.run(
        create_worker_app(WorkerConfig(args.worker_id)),
        host=args.host,
        port=args.port,
        log_level="warning",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
