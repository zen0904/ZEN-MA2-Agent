"""Rebuild normal MA2 Group selection order from live fixture geometry.

This is a bounded Test Show operation.  It never changes membership, fixture
geometry, or any object other than the seven existing normal Groups.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.group_order_builder import GroupOrderBuildError, GroupOrderSpec
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.fixture_geometry import FixtureGeometryProvider
from zen_ma2_agent.telnet_client import ConnectionState


TARGET_GROUPS = {1: "HYBRID", 2: "SPOT", 3: "BEAM", 4: "WASH", 5: "B-EYE", 6: "LED PAR", 7: "STROBE"}


def _ready(core: AgentCore) -> None:
    deadline = time.monotonic() + 8
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.05)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 did not reach READY: {core.runtime.status_text()}")


def _refresh_group(core: AgentCore, group_no: int) -> dict:
    result = core.refresh_state("group_membership", group_no=group_no)
    if result.get("status") != "available":
        raise RuntimeError(f"Group {group_no} readback unavailable: {result.get('error') or result.get('status')}")
    value = next((item for item in result["values"] if item.get("group_no") == group_no), None)
    if not value:
        raise RuntimeError(f"Group {group_no} readback did not contain its own membership.")
    return value


def run(real_machine: bool) -> dict:
    if not real_machine:
        raise RuntimeError("Refusing Group writes without --real-machine.")
    core = AgentCore(AgentRuntime(ROOT))
    result: dict = {
        "schema": "zen.normal_group_order_write.v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "CURRENT_LIVE_MA2_GEOMETRY",
        "target_groups": TARGET_GROUPS,
        "group_rows": [],
        "fixture_9999_touched": False,
        "ma2_group_writes": 0,
        "ai_provider_calls": 0,
        "codex_artistic_intervention": "NONE",
    }
    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _ready(core)
        groups_read = core.refresh_state("groups")
        groups = {int(item["number"]): item for item in groups_read["values"]}
        if 9999 not in {int(item.get("number")) for item in core.refresh_state("fixtures")["values"]}:
            raise RuntimeError("Protected Fixture 9999 sentinel is absent; refusing unknown Show.")
        geometry_read = core.refresh_state("fixture_geometry")
        geometry = {}
        geometry_instances: dict[int, list[int]] = {}
        for item in geometry_read["values"]:
            geometry.setdefault(int(item["fixture_id"]), item)
            geometry_instances.setdefault(int(item["fixture_id"]), []).append(int(item["subfixture_id"]))
        if 9999 not in geometry:
            raise RuntimeError("Protected Fixture 9999 geometry is absent; refusing unknown Show.")

        # Read all memberships before any write and bind exact identities.
        specs: list[GroupOrderSpec] = []
        for group_no, expected_name in TARGET_GROUPS.items():
            group = groups.get(group_no)
            if not group or group.get("name") != expected_name:
                raise RuntimeError(f"Normal Group identity mismatch for {group_no}: expected {expected_name!r}.")
            membership = _refresh_group(core, group_no)
            members = [int(item) for item in membership.get("fixtures", [])]
            exact_members = [str(item) for item in membership.get("fixture_refs", [])]
            if len(exact_members) != len(members):
                raise RuntimeError(
                    f"Group {group_no} exact subfixture membership is unavailable; "
                    "refusing an order write that could change multi-instance identity."
                )
            if 9999 in members:
                result["fixture_9999_touched"] = True
                raise RuntimeError(f"Protected Fixture 9999 appears in normal Group {group_no}.")

            def root_fixture(reference: str) -> int:
                root = reference.split(".", 1)[0]
                if not root.isdigit() or int(root) not in geometry:
                    raise RuntimeError(
                        f"Group {group_no} exact member {reference!r} has no verified root geometry."
                    )
                return int(root)

            # Sort by root-fixture geometry while preserving the exact serialized
            # Group member identity (e.g. 701.1 vs 701.2).  Never synthesize a
            # subfixture from the geometry inventory.
            desired_exact = sorted(
                exact_members,
                key=lambda ref: (
                    float(geometry[root_fixture(ref)]["position"]["y"]),
                    float(geometry[root_fixture(ref)]["position"]["x"]),
                    root_fixture(ref),
                    ref,
                ),
            )
            spec = GroupOrderSpec.create(group_no, expected_name, exact_members, desired_exact)
            specs.append(spec)
            result["group_rows"].append({
                "group_id": group_no,
                "group_name": expected_name,
                "member_count_before": len(exact_members),
                "member_count_after": len(desired_exact),
                "members_before": members,
                "exact_members_before": exact_members,
                "expected_selection_order": [root_fixture(ref) for ref in desired_exact],
                "expected_exact_selection_order": desired_exact,
                "membership_changed": False,
                "order_changed": tuple(exact_members) != tuple(desired_exact),
                "status": "PENDING",
            })

        for spec, row in zip(specs, result["group_rows"]):
            if spec.members_before == spec.desired_order:
                row["status"] = "ALREADY_CANONICAL"
                row["readback_selection_order"] = [int(ref.split(".", 1)[0]) for ref in spec.members_before]
                row["readback_exact_selection_order"] = list(spec.members_before)
                row["readback_match"] = True
                continue
            original = spec.members_before
            try:
                responses = core.runtime.execute_approved_commands(spec.commands())
                if any("error" in response.lower() or "illegal" in response.lower() for response in responses):
                    raise GroupOrderBuildError(f"MA2 rejected Group {spec.group_id} overwrite: {responses}")
                readback = _refresh_group(core, spec.group_id)
                actual_exact = tuple(str(item) for item in readback.get("fixture_refs", []))
                spec.verify(actual_exact)
                row["status"] = "REORDERED"
                row["readback_selection_order"] = [int(ref.split(".", 1)[0]) for ref in actual_exact]
                row["readback_exact_selection_order"] = list(actual_exact)
                row["readback_match"] = True
                result["ma2_group_writes"] += 1
            except Exception as exc:
                # Restore the exact prior ordered membership before surfacing
                # the failure. A failed rollback is explicit and fatal.
                rollback_spec = GroupOrderSpec.create(spec.group_id, spec.group_name, original, original)
                rollback_responses = core.runtime.execute_approved_commands(rollback_spec.commands())
                rollback = _refresh_group(core, spec.group_id)
                rollback_actual = tuple(str(item) for item in rollback.get("fixture_refs", []))
                rollback_ok = rollback_actual == original
                row["status"] = "FAILED_ROLLED_BACK" if rollback_ok else "FAILED_ROLLBACK_MISMATCH"
                row["error"] = f"{type(exc).__name__}: {exc}"
                row["rollback_verified"] = rollback_ok
                row["rollback_responses_contained_error"] = any("error" in response.lower() or "illegal" in response.lower() for response in rollback_responses)
                raise RuntimeError(f"Group {spec.group_id} reorder failed; rollback_verified={rollback_ok}: {exc}") from exc
        result["group_readback_mismatch_count"] = sum(not row.get("readback_match", False) for row in result["group_rows"])
        result["status"] = "SUCCESS" if result["group_readback_mismatch_count"] == 0 else "FAILED"
        return result
    finally:
        try:
            if core.runtime.ready:
                core.runtime.execute_approved_commands(("ClearAll",))
        finally:
            core.disconnect()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-machine", action="store_true")
    parser.add_argument("--result", type=Path, default=None)
    args = parser.parse_args()
    try:
        result = run(args.real_machine)
        if args.result:
            args.result.parent.mkdir(parents=True, exist_ok=True)
            args.result.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "ma2_group_writes": 0, "fixture_9999_touched": False}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
