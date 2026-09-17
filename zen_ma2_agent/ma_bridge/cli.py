from __future__ import annotations

import argparse
import threading

from .server import BridgeServer, DEFAULT_BRIDGE_HOST, DEFAULT_BRIDGE_PORT


def main() -> int:
    parser = argparse.ArgumentParser(description="ZEN MA-Initiated Bridge PoC server")
    parser.add_argument("--host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()

    server = BridgeServer(host=args.host, port=args.port, allow_remote=args.allow_remote)
    server.start()
    stop = threading.Event()
    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
