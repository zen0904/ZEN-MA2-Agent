"""Opt-in, read-only grandMA2 Preset XML acquisition verifier.

It requires a user-supplied Fixture and Preset reference.  It never invokes
Extract, Store, Clear, selection, or Programmer commands.  The only MA2
commands it may issue are ``List Fixture`` and ``Export Preset <type.id>``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.fixtures import FixtureProvider
from zen_ma2_agent.state.providers.preset_export import PresetExportProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire one real MA2 Preset export without changing Show or Programmer state.")
    parser.add_argument("--real-machine", action="store_true", help="Required before any MA2 connection is permitted.")
    parser.add_argument("--fixture", type=int, help="Expected Fixture ID; must exist in List Fixture before Export.")
    parser.add_argument("--preset", help="Numeric Preset reference, for example 2.21.")
    parser.add_argument("--keep-export", action="store_true", help="Copy the acquired XML to cache/preset_export_diagnostics before temporary-file cleanup.")
    parser.add_argument("--output", type=Path, help="Optional local JSON output path. Refuses to overwrite an existing file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 validation without --real-machine.")
    if not isinstance(args.fixture, int) or args.fixture < 1:
        raise SystemExit("--fixture requires a positive user-specified Fixture ID.")
    if not args.preset:
        raise SystemExit("--preset requires a user-specified numeric type.id reference.")
    if args.output and args.output.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {args.output}")

    runtime = AgentRuntime(ROOT)
    provider = PresetExportProvider()
    password = os.environ.get("ZEN_MA2_PASSWORD", "")
    report: dict[str, object] = {
        "schema": "zen.real_preset_export_verification.v0.1",
        "read_only_contract": ["List Fixture", f"Export Preset {args.preset}"],
        "fixture_id_requested": args.fixture,
        "preset_requested": args.preset,
        "programmer_mutation": False,
    }
    try:
        ma2 = runtime.preferences["ma2"]
        report["connect"] = runtime.connect(ma2["host"], ma2["port"], ma2["username"], password)
        if not runtime.ready:
            raise RuntimeError(f"MA2 did not reach READY: {runtime.status_text()}")
        fixtures = FixtureProvider().parse(runtime.read_state("List Fixture"))
        matching = [item for item in fixtures if item.get("number") == args.fixture]
        if not matching:
            raise RuntimeError(f"Requested Fixture {args.fixture} was not found by read-only List Fixture; Export was not attempted.")
        report["fixture_inventory_proof"] = matching[0]
        report["capabilities"] = provider.capabilities(runtime, runtime.preferences.get("state_adapter"))
        result = provider.export_and_discover(runtime, args.preset, runtime.preferences.get("state_adapter"), retain_export=args.keep_export)
        report["preset_export"] = result
        report["fixture_identity_proven"] = "NO"
        report["attribute_identity_proven"] = "NO"
        report["stored_value_proven"] = "NO"
        report["next_action"] = "Review retained real XML structure and add a parser only after proving Fixture, Attribute, and value fields."
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    finally:
        runtime.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
