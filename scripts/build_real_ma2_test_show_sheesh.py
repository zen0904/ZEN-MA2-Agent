"""Build the explicitly-authorized, editable MA2 SHEESH test Show.

This is deliberately *not* a production builder.  It may run only with the
``--real-machine`` acknowledgement while the fingerprinted Existing Show is
the user-designated test show.  All writes are constrained to documented
``ZEN_*`` objects, fixture IDs 101-708, and a new Sequence/Executor.  It never
patches, addresses, touches Fixture 9999, or changes an existing Sequence.

The source plan is typed intent.  Console commands are generated here, at the
explicit test-show Builder boundary, and recorded with every response for
read-back and human review.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.allocation import AllocationError, first_free_executor, first_free_from_front
from zen_ma2_agent.designer.schema import validate_show_plan
from zen_ma2_agent.protected_objects import PROTECTED_SEQUENCES
from zen_ma2_agent.runtime import AgentRuntime
from zen_ma2_agent.state.providers.fixture_geometry import FixtureGeometryProvider
from zen_ma2_agent.state.providers.show_pools import EffectProvider
from zen_ma2_agent.state.providers.sequences import SequenceProvider
from zen_ma2_agent.test_show_resources import (
    reconcile_template_effect_specs,
    template_effect_commands,
    template_effect_labels,
    verify_template_effect_rows,
)
from zen_ma2_agent.telnet_client import ConnectionState


PLAN_PATH = ROOT / "data" / "zen_real_ma2_test_show_sheesh_001_plan.json"
RESULT_PATH = ROOT / "data" / "zen_real_ma2_test_show_sheesh_001_result.json"
RESOURCE_RESULT_PATH = ROOT / "data" / "zen_sheesh_artistic_resources_001_result.json"
EXPECTED_GROUPS = {
    1: "HYBRID", 2: "SPOT", 3: "BEAM", 4: "WASH", 5: "B-EYE", 6: "LED PAR", 7: "STROBE"
}
FIXTURE_IDS = tuple(list(range(101, 109)) + list(range(201, 209)) + list(range(301, 309)) + list(range(401, 409)) + list(range(501, 509)) + list(range(601, 609)) + list(range(701, 709)))
SEQUENCE = 901
# MA2's assignment grammar uses the local executor number.  The verified
# read-back prints that allocation as Page 1 Executor 1.201.
EXECUTOR = "201"
EXECUTOR_DISPLAY = "1.201"
# In this MA2 show a Label Executor action updates the attached Sequence's
# visible name.  Use the single clean shared operator label instead of
# pretending Sequence and Executor labels are independent objects.
SEQUENCE_LABEL = "ZEN_SHEESH_TEST"
LAYOUT_NAME = "TEST_STAGE_LAYOUT_SHEESH_001"


def _await_ready(core: AgentCore) -> None:
    deadline = time.monotonic() + 10
    while core.runtime.state is ConnectionState.AUTHENTICATING and time.monotonic() < deadline:
        core.tick()
        time.sleep(0.1)
    if core.runtime.state is not ConnectionState.READY:
        raise RuntimeError(f"MA2 did not reach READY: {core.runtime.status_text()}")


def _response_failed(response: str) -> bool:
    return "Error #" in response or "Syntax Error" in response or "Illegal" in response


def _run(core: AgentCore, command: str, audit: list[dict[str, str]]) -> str:
    if not core.runtime.client:
        raise RuntimeError("MA2 client unavailable")
    response = core.runtime.client.execute(command)
    audit.append({"command": command, "response": response})
    if _response_failed(response):
        raise RuntimeError(f"MA2 command failed: {command}\n{response}")
    return response


def _read(core: AgentCore, command: str, reads: dict[str, str]) -> str:
    value = core.runtime.read_state(command)
    reads[command] = value
    return value


def _read_preset_reference(core: AgentCore, reference: str, reads: dict[str, str]) -> str:
    """Read a numeric preset reference MA2's generic state allow-list cannot yet express.

    It is constrained to a positive Color-pool reference and sends only a
    native ``List`` command; callers still own the exact authorized refs.
    """
    if not re.fullmatch(r"4\.[1-9]\d*", reference):
        raise ValueError("Unexpected SHEESH owned Color preset reference.")
    if not core.runtime.client:
        raise RuntimeError("MA2 client unavailable")
    command = f"List Preset {reference}"
    value = core.runtime.client.execute(command)
    reads[command] = value
    return value


def _load_plan(path: Path, *, require_legacy_identity: bool = False) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    validate_show_plan(plan)
    if require_legacy_identity and (
        plan.get("sequence") != SEQUENCE or plan.get("sequence_label") != SEQUENCE_LABEL
    ):
        raise ValueError("Legacy SHEESH restore requires the historical owned Sequence identity.")
    return plan


def _assert_preflight(
    core: AgentCore,
    reads: dict[str, str],
    *,
    resume_existing_build: bool,
    require_owned_executor: bool = True,
) -> None:
    groups = _read(core, "List Group", reads)
    for number, label in EXPECTED_GROUPS.items():
        if f"Group {number}" not in groups or label not in groups:
            raise RuntimeError(f"Current loaded Show did not prove expected Group {number} {label}.")
    fixtures = _read(core, "List Fixture", reads)
    if "Fixture 9999" not in fixtures:
        raise RuntimeError("Expected protected Fixture 9999 sentinel is absent; refusing a different Show.")
    for fixture_id in (101, 201, 301, 401, 501, 601, 701):
        if not re.search(rf"^\s*Fixture\s+{fixture_id}\s", fixtures, re.MULTILINE):
            raise RuntimeError(f"Current loaded Show is missing expected Fixture {fixture_id}.")
    sequences = _read(core, "List Sequence", reads)
    owned_existing_sequence = f"Sequ {SEQUENCE}" in sequences and SEQUENCE_LABEL in sequences
    if owned_existing_sequence != resume_existing_build:
        state = "missing" if resume_existing_build else "already occupied"
        raise RuntimeError(f"Sequence {SEQUENCE} / {SEQUENCE_LABEL} is {state}; refusing this build mode.")
    for protected in PROTECTED_SEQUENCES:
        if f"Sequ {protected}" not in sequences:
            raise RuntimeError(f"Protected existing Sequence {protected} is missing; refusing an unexpected Show.")
    executors = _read(core, "List Executor", reads)
    owned_existing_executor = "Sequence=Seq 901" in executors and "ZEN_SHEESH_TEST" in executors
    if require_owned_executor:
        if resume_existing_build:
            if executors and not owned_existing_executor:
                raise RuntimeError(f"Executor {EXECUTOR_DISPLAY} is not the exact owned SHEESH assignment.")
        elif EXECUTOR_DISPLAY in executors or "ZEN_TEST_SHEESH" in executors:
            raise RuntimeError(f"Executor {EXECUTOR_DISPLAY} is occupied; refusing to overwrite.")
    palette_labels = {entry["preset"]: entry["label"] for entry in _palette(_load_plan(PLAN_PATH))}
    for reference in range(101, 114):
        # Individual lookup is required because this MA2 List All display omits
        # newly-created Color pool rows.  4.101 may exist only as the initial
        # approved smoke write, and must have the exact owned label.
        output = _read_preset_reference(core, f"4.{reference}", reads)
        expected_label = palette_labels[reference]
        absent = "OBJECT DOES NOT EXIST" in output or "NO OBJECTS FOUND" in output.upper()
        if not absent and expected_label not in output:
            raise RuntimeError(f"Color Preset 4.{reference} is occupied by a non-owned object; refusing to overwrite.")


def _palette(plan: dict[str, Any], *, require_legacy_ids: bool = False) -> list[dict[str, Any]]:
    palette = plan.get("test_palette")
    if not isinstance(palette, list) or len(palette) != 13:
        raise ValueError("SHEESH test palette requires exactly 13 entries.")
    numbers = [entry.get("preset") for entry in palette]
    if any(
        not isinstance(number, int) or isinstance(number, bool) or number < 1
        for number in numbers
    ) or len(set(numbers)) != 13:
        raise ValueError("SHEESH palette requires thirteen distinct positive Color-pool IDs.")
    if require_legacy_ids and numbers != list(range(101, 114)):
        raise ValueError("Legacy SHEESH palette restore requires Color IDs 4.101 through 4.113.")
    return palette


def _write_palette(core: AgentCore, plan: dict[str, Any], audit: list[dict[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entry in _palette(plan):
        reference = f"4.{entry['preset']}"
        label = str(entry["label"])
        existing = core.runtime.client.execute(f"List Preset {reference}") if core.runtime.client else ""
        if label in existing:
            results.append({"reference": reference, "label": label, "status": "EXISTING_OWNED_TEST_VALUE_VERIFIED"})
            continue
        _run(core, "ClearAll", audit)
        _run(core, "Group 1 Thru 7", audit)
        for attribute, value in (("ColorRGB1", entry["rgb"][0]), ("ColorRGB2", entry["rgb"][1]), ("ColorRGB3", entry["rgb"][2])):
            _run(core, f'Attribute "{attribute}" At {value}', audit)
        _run(core, f'Store Preset {reference} "{label}" /nc', audit)
        _run(core, "ClearAll", audit)
        results.append({"reference": reference, "label": label, "status": "CREATED_TEST_VALUE", "rgb": entry["rgb"]})
    return results


def _read_effect_line_detail(core: AgentCore, effect_id: int, reads: dict[str, str]) -> str:
    if isinstance(effect_id, bool) or not isinstance(effect_id, int) or effect_id < 1:
        raise ValueError("Effect detail read requires a positive integer ID.")
    if not core.runtime.client:
        raise RuntimeError("MA2 client unavailable")
    command = f"List Effect 1.{effect_id}.*"
    value = core.runtime.client.execute(command)
    reads[command] = value
    return value


def _effect_rows(core: AgentCore, reads: dict[str, str]) -> list[dict[str, Any]]:
    output = _read(core, "List Effect", reads)
    provider = EffectProvider()
    rows = provider.parse(output)
    reserved = {label.upper() for label in template_effect_labels()}
    for row in rows:
        label = str(row.get("name") or "").strip().upper()
        if label not in reserved:
            continue
        detail = provider.parse_template_detail(
            _read_effect_line_detail(core, int(row["number"]), reads)
        )
        row["template_detail"] = detail
        if detail.get("status") == "VERIFIED":
            row["kind"] = detail.get("kind")
    return rows


def _write_template_effects(
    core: AgentCore,
    audit: list[dict[str, str]],
    reads: dict[str, str],
) -> dict[str, Any]:
    before = _effect_rows(core, reads)
    specs, existing_ids = reconcile_template_effect_specs(before)
    created: list[dict[str, Any]] = []
    reused: list[dict[str, Any]] = []
    for spec in specs:
        if spec.effect_id in existing_ids:
            reused.append(spec.summary())
            continue
        for command in template_effect_commands(spec):
            _run(core, command, audit)
        one = verify_template_effect_rows(_effect_rows(core, reads), (spec,))[spec.effect_id]
        if not one["verified"]:
            detail = reads.get(f"List Effect 1.{spec.effect_id}.*", "")
            raise RuntimeError(
                f"Effect {spec.effect_id} read-back did not prove exact label + TEMPLATE kind; "
                f"detail_evidence={detail!r}; stopping before creating additional Effects."
            )
        created.append(spec.summary())

    after = _effect_rows(core, reads)
    verification = verify_template_effect_rows(after, specs)
    if not all(item["verified"] for item in verification.values()):
        raise RuntimeError(
            "Template Effect read-back did not prove exact label + TEMPLATE kind; "
            "resources remain unavailable."
        )
    return {
        "created": created,
        "reused": reused,
        "verification": verification,
    }


def _verify_artistic_resources(
    core: AgentCore,
    plan: dict[str, Any],
    reads: dict[str, str],
    effect_verification: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    verification: dict[str, Any] = {"presets": {}, "template_effects": effect_verification}
    for entry in _palette(plan):
        reference = f"4.{entry['preset']}"
        output = _read_preset_reference(core, reference, reads)
        verification["presets"][reference] = {
            "label": entry["label"],
            "verified": entry["label"] in output,
        }
    return verification


def _test_geometry(plan: dict[str, Any]) -> dict[int, tuple[float, float, float]]:
    layout = plan.get("test_stage_layout")
    if not isinstance(layout, dict) or layout.get("id") != LAYOUT_NAME:
        raise ValueError("Missing fixed provisional test-stage layout.")
    group_rows = layout.get("group_rows")
    if not isinstance(group_rows, dict) or {int(key) for key in group_rows} != set(EXPECTED_GROUPS):
        raise ValueError("Test-stage layout must place every approved Group exactly once.")
    x_positions = tuple(float(value) for value in layout.get("x_positions", []))
    if len(x_positions) != 8 or x_positions != tuple(sorted(x_positions)) or x_positions[0] != -x_positions[-1]:
        raise ValueError("Test-stage layout must expose a balanced eight-fixture x row.")
    result: dict[int, tuple[float, float, float]] = {}
    for group, row in group_rows.items():
        group_id = int(group)
        y, z = float(row["y"]), float(row["z"])
        base = {1: 101, 2: 301, 3: 201, 4: 501, 5: 401, 6: 601, 7: 701}[group_id]
        for offset, x in enumerate(x_positions):
            result[base + offset] = (x, y, z)
    if set(result) != set(FIXTURE_IDS):
        raise ValueError("Test-stage layout target set is not exactly Fixtures 101-708.")
    return result


def _write_geometry(core: AgentCore, plan: dict[str, Any], audit: list[dict[str, str]]) -> dict[str, Any]:
    coordinates = _test_geometry(plan)
    for fixture_id in FIXTURE_IDS:
        x, y, z = coordinates[fixture_id]
        # Atomic has two geometry-bearing Subfixtures.  Its parent selection
        # is not executable for Move3D on this actual Show, so address its
        # explicitly listed child instances instead of guessing a parent rule.
        targets = (f"{fixture_id}.1", f"{fixture_id}.2") if 701 <= fixture_id <= 708 else (str(fixture_id),)
        for target in targets:
            _run(core, "ClearAll", audit)
            _run(core, f"Fixture {target}", audit)
            _run(core, f"Move3D At {x:g} {y:g} {z:g}", audit)
    _run(core, "ClearAll", audit)
    return {str(fixture_id): {"x": x, "y": y, "z": z} for fixture_id, (x, y, z) in coordinates.items()}


def _cue_commands(plan: dict[str, Any]) -> list[tuple[str, str]]:
    generated: list[tuple[str, str]] = [("ClearAll", "boundary")]
    for cue in plan["cues"]:
        for action in cue["actions"]:
            group = action["target"]["ref"]
            generated.append((f"Group {group}", f"cue-{cue['cue_number']}-select-{group}"))
            if action["operation"] == "CALL_PRESET":
                generated.append((f"At Preset {action['preset_ref']}", f"cue-{cue['cue_number']}-preset-{group}"))
            elif action["operation"] == "SET_DIMMER":
                generated.append((f"At {action['level']}", f"cue-{cue['cue_number']}-dimmer-{group}"))
            else:
                raise ValueError(f"Unsupported SHEESH test action {action['operation']}")
        fade = float(cue["fade"])
        generated.append((f'Store Cue {cue["cue_number"]} Sequence {SEQUENCE} "{cue["label"]}" Fade {fade:g} /nc', f"cue-{cue['cue_number']}-store"))
    generated.extend([
        (f'Label Sequence {SEQUENCE} "{SEQUENCE_LABEL}" /nc', "label-sequence"),
        (f'Assign Sequence {SEQUENCE} At Executor {EXECUTOR} /nc', "assign-executor"),
        (f'Label Executor {EXECUTOR} "ZEN_SHEESH_TEST" /nc', "label-executor"),
        ("ClearAll", "boundary"),
    ])
    return generated


def _write_sequence(core: AgentCore, plan: dict[str, Any], audit: list[dict[str, str]]) -> None:
    for command, _step in _cue_commands(plan):
        _run(core, command, audit)


def _verify(core: AgentCore, plan: dict[str, Any], reads: dict[str, str]) -> dict[str, Any]:
    verification: dict[str, Any] = {"presets": {}, "geometry": {}, "sequence": {}, "executor": {}}
    for entry in _palette(plan):
        reference = f"4.{entry['preset']}"
        output = _read_preset_reference(core, reference, reads)
        verification["presets"][reference] = {"label": entry["label"], "verified": entry["label"] in output}
    geometry_provider = FixtureGeometryProvider()
    for fixture_id in FIXTURE_IDS:
        expected = _test_geometry(plan)[fixture_id]
        instances = (1, 2) if 701 <= fixture_id <= 708 else (1,)
        listed = {}
        for instance in instances:
            output = _read(core, f"List Fixture {fixture_id}.{instance}", reads)
            parsed = geometry_provider.parse_subfixture(output, fixture_id=fixture_id, instance=instance)
            listed[str(instance)] = bool(parsed and parsed.get("position") == {"x": expected[0], "y": expected[1], "z": expected[2]})
        verification["geometry"][str(fixture_id)] = {"expected": expected, "listed": listed, "fixture_9999": fixture_id == 9999}
    sequence = _read(core, "List Sequence", reads)
    verification["sequence"] = {"id": SEQUENCE, "label": SEQUENCE_LABEL, "verified": f"Sequ {SEQUENCE}" in sequence and SEQUENCE_LABEL in sequence}
    cue_metadata = {}
    for cue in plan["cues"]:
        output = _read(core, f"List Cue {cue['cue_number']} Part 0 Sequence {SEQUENCE}", reads)
        cue_metadata[str(cue["cue_number"])] = cue["label"] in output
    verification["sequence"]["cue_metadata"] = cue_metadata
    executors = _read(core, "List Executor", reads)
    verification["executor"] = {"id": EXECUTOR_DISPLAY, "label": "ZEN_SHEESH_TEST", "verified": EXECUTOR_DISPLAY in executors and "ZEN_SHEESH_TEST" in executors and "Sequence=Seq 901" in executors}
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the user-authorized SHEESH MA2 test Show.")
    parser.add_argument("--real-machine", action="store_true", help="Required before test-show MA2 writes.")
    parser.add_argument("--plan", type=Path, default=PLAN_PATH)
    parser.add_argument("--result", type=Path, default=None)
    parser.add_argument(
        "--resources-only",
        action="store_true",
        help="Restore only owned Color presets and verified template Effects; do not touch geometry, cues, Sequence, or Executor.",
    )
    parser.add_argument("--resume-existing-build", action="store_true", help="Only finish an exact, read-back Agent-owned sequence after a bounded command failure.")
    args = parser.parse_args()
    if not args.real_machine:
        raise SystemExit("Refusing MA2 writes without --real-machine.")
    result_path = args.result or (RESOURCE_RESULT_PATH if args.resources_only else RESULT_PATH)
    if result_path.exists():
        raise SystemExit(f"Refusing to overwrite prior build evidence: {result_path}")
    plan = _load_plan(args.plan)
    core = AgentCore(AgentRuntime(ROOT))
    audit: list[dict[str, str]] = []
    reads: dict[str, str] = {}
    result: dict[str, Any] = {
        "schema": "zen.real_ma2_test_show_sheesh_build.v0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test_show_mode": "WRITE_ALLOWED",
        "production_show_mode": "PREVIEW_APPROVAL_REQUIRED",
        "song": plan.get("song"),
        "plan_schema": plan.get("schema"),
        "sequence": {"id": SEQUENCE, "label": SEQUENCE_LABEL},
        "executor": EXECUTOR,
        "fixture_9999_targeted": False,
        "write_audit": audit,
        "readbacks": reads,
    }
    try:
        ma2 = core.runtime.preferences["ma2"]
        core.connect(ma2["host"], ma2["port"], ma2["username"], "")
        _await_ready(core)
        result["connection"] = {"host": ma2["host"], "port": ma2["port"], "user": core.runtime.client.authenticated_user if core.runtime.client else None, "ready": core.runtime.ready}
        _assert_preflight(
            core,
            reads,
            resume_existing_build=args.resume_existing_build or args.resources_only,
            require_owned_executor=not args.resources_only,
        )
        result["preflight"] = "PASS"
        if args.resources_only:
            result["resource_mode"] = "ARTISTIC_RESOURCES_ONLY"
            result["created_presets"] = _write_palette(core, plan, audit)
            result["template_effects"] = _write_template_effects(core, audit, reads)
        elif args.resume_existing_build:
            result["resume"] = "EXACT_AGENT_OWNED_SEQUENCE_VERIFIED"
            if "ZEN_SHEESH_TEST" not in reads.get("List Executor", ""):
                _run(core, f'Assign Sequence {SEQUENCE} At Executor {EXECUTOR} /nc', audit)
                _run(core, f'Label Executor {EXECUTOR} "ZEN_SHEESH_TEST" /nc', audit)
        else:
            result["created_presets"] = _write_palette(core, plan, audit)
            result["test_stage_layout"] = {"id": LAYOUT_NAME, "coordinates": _write_geometry(core, plan, audit)}
            _write_sequence(core, plan, audit)
        if args.resources_only:
            result["verification"] = _verify_artistic_resources(
                core,
                plan,
                reads,
                result["template_effects"]["verification"],
            )
            preset_ok = all(value["verified"] for value in result["verification"]["presets"].values())
            effect_ok = all(value["verified"] for value in result["verification"]["template_effects"].values())
            result["build_status"] = "COMPLETE" if preset_ok and effect_ok else "PARTIAL_READBACK"
        else:
            result["verification"] = _verify(core, plan, reads)
            result["build_status"] = "COMPLETE" if all(value["verified"] for value in result["verification"]["presets"].values()) and result["verification"]["sequence"]["verified"] and result["verification"]["executor"]["verified"] else "PARTIAL_READBACK"
        return_code = 0
    except Exception as exc:
        result["build_status"] = "FAILED_OR_PARTIAL"
        result["failure"] = f"{type(exc).__name__}: {exc}"
        return_code = 1
    finally:
        try:
            if core.runtime.ready and audit:
                _run(core, "ClearAll", audit)
        except Exception as exc:
            result["clear_after_failure"] = f"{type(exc).__name__}: {exc}"
        core.disconnect()
        result["ma2_write_count"] = len(audit)
        result["fixture_9999_targeted"] = any("9999" in item["command"] for item in audit)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["build_status"], "result": str(result_path), "writes": len(audit), "fixture_9999_targeted": result["fixture_9999_targeted"]}, ensure_ascii=False))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
