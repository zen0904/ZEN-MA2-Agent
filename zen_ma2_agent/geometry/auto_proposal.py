"""Read-only virtual geometry proposals for an uninitialized MA2 show.

The proposal is intentionally separate from the MA2 geometry writer.  It uses
fresh Group membership and Fixture identity, preserves each Group's verified
selection order, and emits typed target coordinates only.  No MA2 command
string is generated here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .normalizer import GeometryNormalizer


AUTO_GEOMETRY_SCHEMA = "zen.auto_geometry_proposal.v0.1"
WRITE_PLAN_SCHEMA = "zen.auto_geometry_write_plan.v0.1"
PROPOSAL_ALGORITHM_VERSION = "zen.auto_geometry.v0.1"


@dataclass(frozen=True)
class GeometryWriteOperation:
    fixture_id: int
    subfixture_ids: tuple[int, ...]
    target_xyz: tuple[float, float, float]
    target_rotation: tuple[float, float, float]
    source: str
    candidate_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_ref": {"fixture_id": self.fixture_id, "subfixture_ids": list(self.subfixture_ids)},
            "target_xyz": {"x": self.target_xyz[0], "y": self.target_xyz[1], "z": self.target_xyz[2]},
            "target_rotation": {"x": self.target_rotation[0], "y": self.target_rotation[1], "z": self.target_rotation[2]},
            "source": self.source,
            "candidate_id": self.candidate_id,
        }


def validate_write_plan(plan: dict[str, Any]) -> None:
    """Reject an untyped or command-bearing geometry plan."""
    if plan.get("schema") != WRITE_PLAN_SCHEMA:
        raise ValueError("Invalid Auto Geometry write-plan schema.")
    if plan.get("mode") != "PREVIEW_ONLY":
        raise ValueError("Auto Geometry proposal plans are preview-only.")
    if plan.get("safety") != "MODIFY" or plan.get("approval_required") is not True:
        raise ValueError("Auto Geometry write plan must retain MODIFY approval metadata.")
    if plan.get("commands") or plan.get("raw_commands"):
        raise ValueError("Auto Geometry write plan cannot contain raw MA2 commands.")
    for operation in plan.get("operations", []):
        if not isinstance(operation, dict) or not isinstance(operation.get("fixture_ref"), dict):
            raise ValueError("Auto Geometry write plan operation is not typed.")
        if "command" in operation or "raw_command" in operation:
            raise ValueError("Auto Geometry write plan cannot contain command fields.")


def state_change_guard(*, current_status: str, baseline_identity: str, current_identity: str) -> dict[str, Any]:
    """Return a conservative precondition for any future writer."""
    if current_status != "GEOMETRY_UNINITIALIZED":
        return {"status": "STATE_CHANGED_SINCE_PREVIEW", "allowed": False, "reason": "Current geometry is no longer uninitialized."}
    if baseline_identity != current_identity:
        return {"status": "STATE_CHANGED_SINCE_PREVIEW", "allowed": False, "reason": "Show identity changed since proposal."}
    return {"status": "READY_IF_REAPPROVED", "allowed": False, "reason": "A future writer still requires explicit user approval."}


class AutoGeometryProposer:
    """Build deterministic candidates from a sanitized Show profile."""

    def __init__(self, *, spacing: float = 1.0, row_spacing: float = 2.0, tolerance: float = 0.05) -> None:
        if spacing <= 0 or row_spacing <= 0:
            raise ValueError("Geometry spacing must be positive.")
        self.spacing = float(spacing)
        self.row_spacing = float(row_spacing)
        self.normalizer = GeometryNormalizer(tolerance=tolerance)

    def build(self, profile: dict[str, Any], discovery: dict[str, Any] | None = None) -> dict[str, Any]:
        fixture_by_id = {int(item["fixture_id"]): item for item in profile.get("fixtures", []) if isinstance(item, dict) and str(item.get("fixture_id", "")).isdigit()}
        groups = [item for item in profile.get("groups", []) if isinstance(item, dict) and item.get("fixture_ids_in_selection_order")]
        group_specs = []
        memberships: dict[int, list[int]] = {}
        for group in groups:
            group_id = int(group.get("group_id"))
            fixture_ids = [int(value) for value in group.get("fixture_ids_in_selection_order", [])]
            for fixture_id in fixture_ids:
                memberships.setdefault(fixture_id, []).append(group_id)
            group_specs.append({"id": group_id, "name": group.get("name") or "", "fixture_ids": fixture_ids})
        overlap = [{"fixture_id": fixture_id, "groups": sorted(group_ids)} for fixture_id, group_ids in sorted(memberships.items()) if len(group_ids) > 1]
        ungrouped = []
        for fixture_id, fixture in sorted(fixture_by_id.items()):
            if fixture_id not in memberships:
                geometry = fixture.get("stage_geometry") or {}
                ungrouped.append({"fixture_id": fixture_id, "name": fixture.get("name"), "fixture_type": fixture.get("fixture_type"), "patch": geometry.get("patch"), "excluded": True, "reason": "UNGROUPED_FIXTURE"})

        candidate_defs = (
            ("A_LAYERED_ROWS", "Layered Rows", self._layered_rows(group_specs)),
            ("B_FIXTURE_FAMILY_STAGING", "Fixture-family staging", self._family_staging(group_specs, fixture_by_id)),
            ("C_COMPACT_SYMMETRIC", "Compact Symmetric", self._compact_symmetric(group_specs)),
        )
        candidates = [self._candidate(candidate_id, name, placements, fixture_by_id, group_specs, overlap) for candidate_id, name, placements in candidate_defs]
        recommended = "A_LAYERED_ROWS"
        write_plan = self._write_plan(recommended, candidates, profile.get("show_identity"))
        validate_write_plan(write_plan)
        return {
            "schema": AUTO_GEOMETRY_SCHEMA,
            "algorithm_version": PROPOSAL_ALGORITHM_VERSION,
            "read_only": True,
            "show_identity": profile.get("show_identity"),
            "current_geometry_state": (discovery or {}).get("geometry", {}).get("status", "UNKNOWN"),
            "root_fixture_count": len(fixture_by_id),
            "grouped_fixture_count": len(memberships),
            "group_membership_overlap": overlap,
            "ungrouped_fixtures": ungrouped,
            "subfixture_policy": "ROOT_GEOMETRY_WITH_SUBFIXTURE_INHERITANCE_UNLESS_VERIFIED_INDEPENDENT_OFFSET",
            "candidates": candidates,
            "recommended_candidate": recommended,
            "typed_write_plan": write_plan,
            "state_change_protection": state_change_guard(
                current_status=(discovery or {}).get("geometry", {}).get("status", "UNKNOWN"),
                baseline_identity=str(profile.get("show_identity") or ""),
                current_identity=str(profile.get("show_identity") or ""),
            ),
            "ma2_write_audit": "ZERO_WRITES",
        }

    def _x_positions(self, count: int, spacing: float) -> list[float]:
        center = (count - 1) / 2.0
        return [round((index - center) * spacing, 6) for index in range(count)]

    def _layered_rows(self, groups: list[dict[str, Any]]) -> dict[int, tuple[float, float]]:
        center = (len(groups) - 1) / 2.0
        return {int(group["id"]): (0.0, round((index - center) * self.row_spacing, 6)) for index, group in enumerate(groups)}

    def _family_staging(self, groups: list[dict[str, Any]], fixture_by_id: dict[int, dict[str, Any]]) -> dict[int, tuple[float, float]]:
        families: dict[str, int] = {}
        for group in groups:
            types = sorted({str((fixture_by_id.get(fixture_id) or {}).get("fixture_type") or "UNAVAILABLE") for fixture_id in group["fixture_ids"]})
            key = "|".join(types)
            families.setdefault(key, len(families))
        return {int(group["id"]): (round(((families["|".join(sorted({str((fixture_by_id.get(fid) or {}).get('fixture_type') or 'UNAVAILABLE') for fid in group['fixture_ids']}))] % 3) - 1) * self.row_spacing, 6), round((families["|".join(sorted({str((fixture_by_id.get(fid) or {}).get('fixture_type') or 'UNAVAILABLE') for fid in group['fixture_ids']}))] // 3) * self.row_spacing, 6)) for group in groups}

    def _compact_symmetric(self, groups: list[dict[str, Any]]) -> dict[int, tuple[float, float]]:
        center = (len(groups) - 1) / 2.0
        return {int(group["id"]): (round((index - center) * 0.75, 6), 0.0) for index, group in enumerate(groups)}

    def _candidate(self, candidate_id: str, name: str, placements: dict[int, tuple[float, float]], fixture_by_id: dict[int, dict[str, Any]], groups: list[dict[str, Any]], overlap: list[dict[str, Any]]) -> dict[str, Any]:
        group_results = []
        all_operations: dict[int, GeometryWriteOperation] = {}
        for row_index, group in enumerate(groups, start=1):
            fixture_ids = group["fixture_ids"]
            x_values = self._x_positions(len(fixture_ids), self.spacing if candidate_id != "C_COMPACT_SYMMETRIC" else 0.75)
            y, z = placements[int(group["id"])]
            records = []
            for fixture_id, x in zip(fixture_ids, x_values):
                fixture = fixture_by_id.get(fixture_id) or {}
                geometry = fixture.get("stage_geometry") or {}
                subfixtures = tuple(sorted(int(item.get("subfixture_id")) for item in geometry.get("subfixtures", []) if isinstance(item, dict) and str(item.get("subfixture_id", "")).isdigit())) or (1,)
                record = {"fixture_id": fixture_id, "subfixture_id": subfixtures[0], "fixture_type": fixture.get("fixture_type"), "position": {"x": x, "y": y, "z": z}}
                records.append(record)
                operation = GeometryWriteOperation(fixture_id, subfixtures, (x, y, z), (0.0, 0.0, 0.0), "VIRTUAL_LAYOUT_ASSUMPTION", candidate_id)
                if fixture_id not in all_operations:
                    all_operations[fixture_id] = operation
                elif all_operations[fixture_id].target_xyz != operation.target_xyz:
                    # Overlapping Groups cannot receive two physical positions.
                    all_operations.pop(fixture_id, None)
            analysis = self.normalizer.analyze(records)
            group_results.append({"group_id": group["id"], "name": group["name"], "fixture_ids_in_selection_order": fixture_ids, "x_positions": x_values, "y": y, "z": z, "row_id": f"ROW_{row_index}", "normalizer": analysis, "mirror_pairs": self._pairs(analysis), "inner": self._ranked(analysis, "inner"), "outer": self._ranked(analysis, "outer"), "center": analysis.get("nearest_to_x_center"), "assumption": "VIRTUAL_LAYOUT_ASSUMPTION"})
        return {"id": candidate_id, "name": name, "spacing": self.spacing if candidate_id != "C_COMPACT_SYMMETRIC" else 0.75, "groups": group_results, "operations": [operation.to_dict() for _, operation in sorted(all_operations.items())], "excluded_overlap_fixtures": [item["fixture_id"] for item in overlap], "advantages": self._advantages(candidate_id), "disadvantages": self._disadvantages(candidate_id), "creative_usefulness": self._usefulness(candidate_id)}

    @staticmethod
    def _pairs(analysis: dict[str, Any]) -> list[dict[str, Any]]:
        seen: set[tuple[int, int | None]] = set()
        pairs = []
        for record in analysis.get("records", []):
            key = (record.get("fixture_id"), record.get("subfixture_id"))
            partner = ((record.get("relationships") or {}).get("symmetry_pair") or {})
            partner_key = (partner.get("fixture_id"), partner.get("subfixture_id"))
            if partner and key not in seen and partner_key not in seen:
                pairs.append({"fixture_a": key[0], "fixture_b": partner_key[0], "score": partner.get("score"), "confidence": "GEOMETRY_INFERRED"})
                seen.update((key, partner_key))
        return pairs

    @staticmethod
    def _ranked(analysis: dict[str, Any], kind: str) -> list[int]:
        records = sorted(analysis.get("records", []), key=lambda item: ((item.get("relationships") or {}).get("inner_outer_rank", 0), item.get("fixture_id", 0)))
        if kind == "outer":
            records = list(reversed(records))
        return [int(item["fixture_id"]) for item in records[:2]]

    @staticmethod
    def _advantages(candidate_id: str) -> list[str]:
        return {"A_LAYERED_ROWS": ["Preserves ordered Group membership on a clear symmetric row.", "Separates Group rows without assigning real venue semantics."], "B_FIXTURE_FAMILY_STAGING": ["Makes fixture-family layers visually distinguishable in virtual geometry.", "Keeps deterministic symmetry inside each Group."], "C_COMPACT_SYMMETRIC": ["Small coordinate footprint for compact virtual inspection.", "Maintains an even center gap and mirror pairs."]}[candidate_id]

    @staticmethod
    def _disadvantages(candidate_id: str) -> list[str]:
        return {"A_LAYERED_ROWS": ["Row spacing is a virtual scale, not a measured rig distance."], "B_FIXTURE_FAMILY_STAGING": ["Family placement is an assumption based on Group/Fixture Type identity only."], "C_COMPACT_SYMMETRIC": ["Groups are vertically compressed and less separated for large-show browsing."]}[candidate_id]

    @staticmethod
    def _usefulness(candidate_id: str) -> str:
        return {"A_LAYERED_ROWS": "BEST_GENERAL_DESIGN_INPUT", "B_FIXTURE_FAMILY_STAGING": "GOOD_FAMILY_LAYER_EXPLORATION", "C_COMPACT_SYMMETRIC": "GOOD_COMPACT_PREVIEW"}[candidate_id]

    @staticmethod
    def _write_plan(candidate_id: str, candidates: list[dict[str, Any]], show_identity: Any) -> dict[str, Any]:
        candidate = next(item for item in candidates if item["id"] == candidate_id)
        return {
            "schema": WRITE_PLAN_SCHEMA,
            "mode": "PREVIEW_ONLY",
            "candidate_id": candidate_id,
            "show_identity": show_identity,
            "safety": "MODIFY",
            "approval_required": True,
            "source": "ZEN_AUTO_GEOMETRY_PROPOSAL",
            "operations": candidate["operations"],
            "will_modify": "Fixture Stage Geometry only",
            "will_not_modify": ["Patch", "Fixture Type", "Groups", "Presets", "Effects", "Sequences", "Cues"],
        }
