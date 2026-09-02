"""Deterministic, Group-order based grandMA2 Geometry Clone v1.

Despite its product name, v1 deliberately does *not* infer physical geometry.
It maps the verified fixture order in one Group export to the verified fixture
order in another Group export, then delegates data cloning to MA2's native
``Clone Fixture <source> At Fixture <destination>`` command.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from .models import Intent
from .workflow import ActionStep, SkillGraphNode, Subtask, Task, WorkflowPlan


class GeometryCloneError(ValueError):
    pass


class GeometryCloneAmbiguous(GeometryCloneError):
    pass


@dataclass(frozen=True)
class GeometryClonePair:
    source_fixture: int
    destination_fixture: int
    order: int


@dataclass(frozen=True)
class GeometryCloneSpec:
    source_group_number: int
    source_group_name: str
    source_members: tuple[int, ...]
    destination_group_number: int
    destination_group_name: str
    destination_members: tuple[int, ...]
    mapping_mode: str
    pairs: tuple[GeometryClonePair, ...]
    source_count: int
    destination_count: int
    source_membership_fingerprint: str
    destination_membership_fingerprint: str
    source_request: str

    def summary(self) -> dict[str, Any]:
        result = asdict(self)
        result["source_members"] = list(self.source_members)
        result["destination_members"] = list(self.destination_members)
        return result

    @classmethod
    def from_summary(cls, raw: dict[str, Any]) -> "GeometryCloneSpec":
        pairs = tuple(GeometryClonePair(**item) for item in raw.get("pairs", []))
        return cls(
            source_group_number=int(raw["source_group_number"]),
            source_group_name=str(raw["source_group_name"]),
            source_members=tuple(int(item) for item in raw["source_members"]),
            destination_group_number=int(raw["destination_group_number"]),
            destination_group_name=str(raw["destination_group_name"]),
            destination_members=tuple(int(item) for item in raw["destination_members"]),
            mapping_mode=str(raw["mapping_mode"]),
            pairs=pairs,
            source_count=int(raw["source_count"]),
            destination_count=int(raw["destination_count"]),
            source_membership_fingerprint=str(raw["source_membership_fingerprint"]),
            destination_membership_fingerprint=str(raw["destination_membership_fingerprint"]),
            source_request=str(raw["source_request"]),
        )


def membership_fingerprint(group: dict[str, Any]) -> str:
    """Fingerprint only state that identifies ordered Group membership."""
    stable = {
        "group_no": group.get("group_no"),
        "name": group.get("name") or group.get("group_name"),
        "fixtures": list(group.get("fixtures") or []),
        "source": group.get("source"),
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def _resolve_group(groups: list[dict[str, Any]], *, number: object = None, name: object = None, role: str) -> dict[str, Any]:
    if isinstance(number, int) and not isinstance(number, bool):
        matches = [item for item in groups if item.get("number") == number]
    elif isinstance(name, str) and name.strip():
        wanted = name.strip().casefold()
        matches = [item for item in groups if str(item.get("name") or "").casefold() == wanted]
    else:
        raise GeometryCloneError(f"Geometry Clone requires a {role} Group.")
    if not matches:
        label = f"Group {number}" if isinstance(number, int) else repr(name)
        raise GeometryCloneError(f"{role.title()} {label} was not found in the current Group inventory.")
    if len(matches) > 1:
        raise GeometryCloneAmbiguous(f"Multiple Groups named {name!r} are available; use Group <number> for the {role}.")
    return matches[0]


def resolve_geometry_clone_spec(intent: Intent, *, groups: list[dict[str, Any]], memberships: dict[int, dict[str, Any]]) -> GeometryCloneSpec:
    if intent.kind not in {"geometry_clone", "geometry_clone_mapping"}:
        raise GeometryCloneError("Geometry Clone received an unsupported intent.")
    parameters = intent.parameters
    source = _resolve_group(groups, number=parameters.get("source_group_number"), name=parameters.get("source_group_name"), role="source")
    destination = _resolve_group(groups, number=parameters.get("destination_group_number"), name=parameters.get("destination_group_name"), role="destination")
    source_number, destination_number = int(source["number"]), int(destination["number"])
    if source_number == destination_number:
        raise GeometryCloneError("Source and destination Groups must be different.")
    source_membership = memberships.get(source_number)
    destination_membership = memberships.get(destination_number)
    if not source_membership or not destination_membership:
        raise GeometryCloneError("Cannot build Geometry Clone because Group Membership state is not fresh.")
    source_members = tuple(int(item) for item in source_membership.get("fixtures", []))
    destination_members = tuple(int(item) for item in destination_membership.get("fixtures", []))
    if not source_members:
        raise GeometryCloneError(f'Source Group {source_number} "{source.get("name", "")}" is empty.')
    if not destination_members:
        raise GeometryCloneError(f'Destination Group {destination_number} "{destination.get("name", "")}" is empty.')
    equal_count = len(source_members) == len(destination_members)
    pairs = tuple(
        GeometryClonePair(source_fixture, destination_fixture, index)
        for index, (source_fixture, destination_fixture) in enumerate(zip(source_members, destination_members))
    ) if equal_count else ()
    return GeometryCloneSpec(
        source_group_number=source_number,
        source_group_name=str(source.get("name") or source_number),
        source_members=source_members,
        destination_group_number=destination_number,
        destination_group_name=str(destination.get("name") or destination_number),
        destination_members=destination_members,
        mapping_mode="ORDERED_1_TO_1" if equal_count else "COUNT_MISMATCH",
        pairs=pairs,
        source_count=len(source_members),
        destination_count=len(destination_members),
        source_membership_fingerprint=membership_fingerprint(source_membership),
        destination_membership_fingerprint=membership_fingerprint(destination_membership),
        source_request=intent.source_text,
    )


def format_mapping(spec: GeometryCloneSpec, *, preview: bool) -> str:
    title = "Geometry Clone Preview" if preview else "Geometry Clone Mapping (SAFE)"
    lines = [
        title,
        "",
        "Source:",
        f'Group {spec.source_group_number} "{spec.source_group_name}"',
        f"Fixtures: {spec.source_count}",
        "",
        "Destination:",
        f'Group {spec.destination_group_number} "{spec.destination_group_name}"',
        f"Fixtures: {spec.destination_count}",
        "",
    ]
    if spec.mapping_mode == "COUNT_MISMATCH":
        lines.extend((
            "Status: COUNT_MISMATCH",
            "v1 supports Ordered 1:1 mapping only; no MA2 Clone commands will be generated.",
        ))
        return "\n".join(lines)
    lines.extend(("Mapping:", *(f"{pair.source_fixture} → {pair.destination_fixture}" for pair in spec.pairs[:10])))
    if len(spec.pairs) > 10:
        lines.append(f"Showing first 10 of {len(spec.pairs)}")
    lines.extend(("", "Mode:", "Ordered 1:1"))
    if preview:
        lines.extend((
            "",
            "Clone scope:",
            "MA2 native Fixture Clone semantics (default low-priority selective data; no unverified scope filter).",
            f"Destination fixtures affected: {spec.destination_count}",
            "",
            "Safety:",
            "MODIFY",
            "Approval required.",
        ))
    return "\n".join(lines)


class GeometryCloneSkill:
    """Build native Clone steps from a verified, ordered fixture mapping."""

    def __init__(self, manifest: Any):
        self.manifest = manifest

    def can_handle(self, intent: Intent, state: Any) -> bool:
        # A disabled manifest still permits a non-executable Preview.  This
        # keeps real state inspection useful while preventing approval/write.
        return intent.kind == "geometry_clone" and state.has(("groups", "group_membership"))

    def create_task(self, intent: Intent) -> Task:
        return Task("geometry-clone", "Geometry Clone", intent, self.manifest.id, ("groups", "group_membership"))

    def plan(self, task: Task, state: Any, preferences: dict[str, Any]) -> WorkflowPlan:
        raw = task.intent.parameters.get("geometry_clone_spec")
        if not isinstance(raw, dict):
            raise GeometryCloneError("Geometry Clone received an unresolved mapping specification.")
        spec = GeometryCloneSpec.from_summary(raw)
        commands = tuple(
            ActionStep(
                f"clone-{pair.order + 1}",
                f"Clone Fixture {pair.source_fixture} to Fixture {pair.destination_fixture}",
                "command",
                f"Clone Fixture {pair.source_fixture} At Fixture {pair.destination_fixture} /nc",
                "MODIFY",
                verification="Re-read Group membership and Fixture inventory",
            )
            for pair in spec.pairs
        )
        executable = bool(self.manifest.enabled and spec.mapping_mode == "ORDERED_1_TO_1" and commands)
        return WorkflowPlan(
            task,
            (
                Subtask("resolve", "Resolve source and destination Groups", "Planning"),
                Subtask("membership", "Read fresh ordered Group membership", "Planning"),
                Subtask("mapping", "Calculate ordered 1:1 fixture pairs", "Planning"),
                Subtask("clone", "Run approved native MA2 Fixture Clone steps", "Execution"),
                Subtask("verify", "Re-read membership and destination Fixture inventory", "Verification"),
            ),
            (SkillGraphNode("root", self.manifest.id, "Geometry Clone"),),
            commands,
            "MODIFY",
            format_mapping(spec, preview=True),
            ("PREVIEW", "APPROVAL"),
            "Re-read source/destination Group membership and Fixture inventory. Internal cloned data is not exposed by a verified read-only provider.",
            "Rollback: Not automatically available. Use MA2 Undo or a saved show backup if required.",
            executable,
        )

    def validate(self, plan: WorkflowPlan, state: Any) -> None:
        if plan.task.skill_id != self.manifest.id or plan.safety != "MODIFY":
            raise GeometryCloneError("Invalid Geometry Clone workflow.")
        if any(not command.startswith("Clone Fixture ") or " At Fixture " not in command for command in plan.commands):
            raise GeometryCloneError("Geometry Clone may only execute deterministic Fixture-to-Fixture MA2 Clone commands.")

    def execute(self, approved_plan: WorkflowPlan) -> tuple[str, ...]:
        if approved_plan.task.skill_id != self.manifest.id:
            raise GeometryCloneError("Geometry Clone cannot execute another workflow.")
        return approved_plan.commands
