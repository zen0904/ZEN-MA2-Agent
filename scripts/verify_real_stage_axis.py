"""Opt-in numeric Stage-axis verifier for the isolated grandMA2 research Show.

It proves only that MA2 stores and returns the requested signed coordinates on
the actual geometry-bearing Subfixture.  It does *not* infer Stage Left/Right
or Upstage/Downstage: those labels require an independent Stage View visual
observation.  The script always reloads the recorded production Show.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.fixture_geometry import FixtureGeometryProvider


TEST_SHOW = "zen_agent_preset_diff_h"
PRODUCTION_SHOW = "zen templ show"
TEST_FIXTURE = 9999
TEST_SUBFIXTURE = 1
CASES = {
    "x_positive": (4.0, 0.0, 5.0),
    "x_negative": (-4.0, 0.0, 5.0),
    "y_positive": (0.0, 4.0, 5.0),
    "y_negative": (0.0, -4.0, 5.0),
    "z_positive": (0.0, 0.0, 8.0),
    "z_negative": (0.0, 0.0, 2.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify MA2 signed Stage coordinate read-back in an isolated Show.")
    parser.add_argument("--real-machine", action="store_true", help="Required before any MA2 connection is made.")
    parser.add_argument("--output", type=Path, help="Write the JSON evidence to a new local path.")
    return parser.parse_args()


def _execute(runtime: AgentRuntime, command: str) -> str:
    if not runtime.client:
        raise RuntimeError("MA2 client is unavailable.")
    return runtime.client.execute(command)


def _read_current(provider: FixtureGeometryProvider, runtime: AgentRuntime) -> dict[str, object]:
    output = runtime.read_state(provider.command_for(TEST_FIXTURE, TEST_SUBFIXTURE))
    value = provider.parse_subfixture(output, fixture_id=TEST_FIXTURE, instance=TEST_SUBFIXTURE)
    if value is None:
        raise RuntimeError(f"Fixture {TEST_FIXTURE}.{TEST_SUBFIXTURE} did not return a geometry-bearing Subfixture row.")
    return value


def main() -> int:
    args = parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing real MA2 verification without --real-machine.")
    if args.output and args.output.exists():
        raise SystemExit(f"Refusing to overwrite existing output: {args.output}")

    runtime = AgentRuntime(ROOT)
    provider = FixtureGeometryProvider()
    report: dict[str, object] = {
        "schema": "zen.ma2.stage_axis_numeric_verification.v0.1",
        "test_show": TEST_SHOW,
        "production_restore_show": PRODUCTION_SHOW,
        "fixture": f"{TEST_FIXTURE}.{TEST_SUBFIXTURE}",
        "semantic_labels": "UNVERIFIED_NO_STAGE_VIEW_EVIDENCE",
        "cases": {},
    }
    try:
        ma2 = runtime.preferences["ma2"]
        report["connect"] = runtime.connect(ma2["host"], ma2["port"], ma2["username"], os.environ.get("ZEN_MA2_PASSWORD", ""))
        deadline = time.monotonic() + 5.0
        while not runtime.ready and time.monotonic() < deadline:
            runtime.poll_connection()
            time.sleep(0.1)
        if not runtime.ready:
            raise RuntimeError(f"MA2 did not reach READY: {runtime.status_text()}")
        report["load_test_show"] = _execute(runtime, f'LoadShow "{TEST_SHOW}" /nc')
        for name, expected in CASES.items():
            _execute(runtime, "Clear")
            _execute(runtime, f"Fixture {TEST_FIXTURE}")
            command = f"Move3D At {expected[0]:g} {expected[1]:g} {expected[2]:g}"
            feedback = _execute(runtime, command)
            actual = _read_current(provider, runtime)
            position = actual["position"]
            report["cases"][name] = {
                "command": command,
                "expected": {"x": expected[0], "y": expected[1], "z": expected[2]},
                "actual": position,
                "match": position == {"x": expected[0], "y": expected[1], "z": expected[2]},
                "feedback": feedback,
            }
        _execute(runtime, "Clear")
        if not all(value["match"] for value in report["cases"].values()):
            raise RuntimeError("At least one signed Stage coordinate did not read back exactly.")
        report["numeric_readback"] = "REAL_MACHINE_VERIFIED"
    finally:
        try:
            if runtime.ready:
                _execute(runtime, "Clear")
                report["restore_production_show"] = _execute(runtime, f'LoadShow "{PRODUCTION_SHOW}" /nc')
        finally:
            runtime.disconnect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
