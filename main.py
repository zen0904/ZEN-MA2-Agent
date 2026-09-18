from __future__ import annotations

import argparse
import json

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.field_host import FieldHost, FieldHostConfig


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ZEN Field Core headless runtime (OpenClaw-first UI architecture)"
    )
    parser.add_argument("--build-identity", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--operator-host", default="127.0.0.1")
    parser.add_argument("--operator-port", type=int, default=8876)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=8877)
    parser.add_argument("--allow-remote-operator", action="store_true")
    parser.add_argument("--allow-remote-bridge", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()

    if args.build_identity:
        core = AgentCore()
        print(json.dumps(core.build_identity, ensure_ascii=False, sort_keys=True), flush=True)
        return 0

    host = FieldHost(
        FieldHostConfig(
            operator_host=args.operator_host,
            operator_port=args.operator_port,
            bridge_host=args.bridge_host,
            bridge_port=args.bridge_port,
            allow_remote_operator=args.allow_remote_operator,
            allow_remote_bridge=args.allow_remote_bridge,
        )
    )

    if args.self_check:
        print(
            json.dumps(
                {
                    "schema": "zen.field_host_self_check.v0.1",
                    "ui_strategy": "OPENCLAW_FIRST",
                    "field_core_available": host.status()["field_core"]["available"],
                    "remote_ai_available": host.status()["remote_ai_available"],
                    "ma_bridge_state": host.status()["ma"]["bridge_state"],
                    "operator_bind": f"{host.operator.host}:{host.operator.port}",
                    "bridge_bind": f"{host.bridge.host}:{host.bridge.port}",
                    "ma2_writes": 0,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        return 0

    print(
        json.dumps(
            {
                "schema": "zen.field_host_start.v0.1",
                "ui_strategy": "OPENCLAW_FIRST",
                "operator_api": f"http://{host.operator.host}:{host.operator.port}",
                "bridge": f"{host.bridge.host}:{host.bridge.port}",
                "ma2_writes": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    host.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
