"""Normalize verified fixture geometry without inventing stage semantics.

The MA2 provider gives numeric X/Y/Z on geometry-bearing *Subfixture* rows.
This module derives order, proximity and mirror candidates from those values.
It intentionally calls the axes ``x/y/z`` rather than Stage Left/Right or
Upstage/Downstage until an MA2 Stage View sign convention has visual evidence.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from typing import Any, Iterable


GEOMETRY_ALGORITHM_VERSION = "zen.geometry.v0.1"


@dataclass(frozen=True)
class _Point:
    fixture_id: int
    subfixture_id: int | None
    x: float
    y: float
    z: float
    fixture_type: str | None
    original: dict[str, Any]

    @property
    def key(self) -> tuple[int, int | None]:
        return self.fixture_id, self.subfixture_id


class GeometryNormalizer:
    """Pure deterministic geometry analysis for one relevant fixture set."""

    def __init__(self, *, tolerance: float = 0.01) -> None:
        if tolerance < 0:
            raise ValueError("Geometry tolerance must be non-negative.")
        self.tolerance = float(tolerance)

    def analyze(self, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """Return one derived record per geometry-bearing Fixture/Subfixture.

        Normalization uses *only* this call's relevant set, not the full Show.
        Records missing an explicit finite numeric X/Y/Z are omitted rather
        than replaced with a misleading zero position.
        """
        points = self._points(records)
        if not points:
            return self._empty()
        axes = {axis: [getattr(point, axis) for point in points] for axis in ("x", "y", "z")}
        ranges = {axis: {"min": min(values), "max": max(values), "span": max(values) - min(values)} for axis, values in axes.items()}
        center = {axis: (item["min"] + item["max"]) / 2.0 for axis, item in ranges.items()}
        normal = {point.key: self._normal(point, ranges) for point in points}
        horizontal = self._axis_indices(points, "x")
        depth = self._axis_indices(points, "y")
        height = self._axis_indices(points, "z")
        rows = self._clusters(points, axes=("y", "z"), prefix="row")
        layers = self._clusters(points, axes=("z",), prefix="layer")
        pairings = self._mirror_pairs(points, center["x"], ranges)
        radial_rank = self._distance_ranks(points, center["x"])
        nearest = self._nearest_to_center(points, center["x"])

        derived: list[dict[str, Any]] = []
        for point in sorted(points, key=lambda item: (item.fixture_id, item.subfixture_id or 0)):
            partner = pairings.get(point.key)
            derived.append({
                "fixture_id": point.fixture_id,
                "subfixture_id": point.subfixture_id,
                "normalized": normal[point.key],
                "relationships": {
                    "horizontal_index": horizontal[point.key],
                    "depth_index": depth[point.key],
                    "height_index": height[point.key],
                    "x_side": self._x_side(point.x, center["x"], ranges["x"]["span"]),
                    "distance_from_x_center": abs(point.x - center["x"]),
                    "inner_outer_rank": radial_rank[point.key],
                    "row_id": rows[point.key],
                    "layer_id": layers[point.key],
                    "symmetry_pair": self._partner_payload(partner),
                },
                "derived_source": "GEOMETRY_INFERRED",
                "algorithm_version": GEOMETRY_ALGORITHM_VERSION,
                "confidence": "GEOMETRY_INFERRED",
            })
        return {
            "status": "SUPPORTED",
            "algorithm_version": GEOMETRY_ALGORITHM_VERSION,
            "tolerance": self.tolerance,
            "axis_ranges": ranges,
            "rig_center": center,
            "nearest_to_x_center": nearest,
            "records": derived,
        }

    def _points(self, records: Iterable[dict[str, Any]]) -> list[_Point]:
        points: list[_Point] = []
        for record in records:
            position = record.get("position") or record.get("stage_geometry") or {}
            try:
                x, y, z = float(position["x"]), float(position["y"]), float(position["z"])
                fixture_id = int(record["fixture_id"])
            except (KeyError, TypeError, ValueError):
                continue
            subfixture = record.get("subfixture_id")
            if subfixture is not None:
                try:
                    subfixture = int(subfixture)
                except (TypeError, ValueError):
                    continue
            points.append(_Point(fixture_id, subfixture, x, y, z, record.get("fixture_type"), record))
        return points

    def _normal(self, point: _Point, ranges: dict[str, dict[str, float]]) -> dict[str, float]:
        result: dict[str, float] = {}
        for axis in ("x", "y", "z"):
            span = ranges[axis]["span"]
            result[{"x": "horizontal", "y": "depth", "z": "height"}[axis]] = 0.0 if span <= self.tolerance else round(((getattr(point, axis) - ranges[axis]["min"]) / span) * 2.0 - 1.0, 8)
        return result

    def _axis_indices(self, points: list[_Point], axis: str) -> dict[tuple[int, int | None], int]:
        ordered = sorted(points, key=lambda item: (getattr(item, axis), item.fixture_id, item.subfixture_id or 0))
        return {point.key: index for index, point in enumerate(ordered)}

    def _clusters(self, points: list[_Point], *, axes: tuple[str, ...], prefix: str) -> dict[tuple[int, int | None], str]:
        groups: list[list[_Point]] = []
        for point in sorted(points, key=lambda item: tuple(getattr(item, axis) for axis in axes) + (item.fixture_id, item.subfixture_id or 0)):
            for group in groups:
                representative = group[0]
                if all(abs(getattr(point, axis) - getattr(representative, axis)) <= self.tolerance for axis in axes):
                    group.append(point)
                    break
            else:
                groups.append([point])
        return {point.key: f"{prefix}_{index + 1}" for index, group in enumerate(groups) for point in group}

    def _mirror_pairs(self, points: list[_Point], x_center: float, ranges: dict[str, dict[str, float]]) -> dict[tuple[int, int | None], dict[str, Any]]:
        scale = max(ranges["x"]["span"], ranges["y"]["span"], ranges["z"]["span"], 1.0)
        candidates: list[tuple[float, _Point, _Point, bool]] = []
        for offset, left in enumerate(points):
            for right in points[offset + 1:]:
                if (left.x - x_center) * (right.x - x_center) >= -self.tolerance ** 2:
                    continue
                mirrored_x = abs((left.x - x_center) + (right.x - x_center))
                y_delta, z_delta = abs(left.y - right.y), abs(left.z - right.z)
                type_match = bool(left.fixture_type and left.fixture_type == right.fixture_type)
                penalty = 0.0 if type_match else 0.15 * scale
                score = (mirrored_x + y_delta + z_delta + penalty) / scale
                if score <= 0.35:
                    candidates.append((score, left, right, type_match))
        used: set[tuple[int, int | None]] = set()
        pairs: dict[tuple[int, int | None], dict[str, Any]] = {}
        for score, first, second, type_match in sorted(candidates, key=lambda value: (value[0], value[1].key, value[2].key)):
            if first.key in used or second.key in used:
                continue
            used.update((first.key, second.key))
            confidence = round(max(0.0, 1.0 - score), 3)
            if not type_match:
                confidence = round(confidence * 0.75, 3)
            pairs[first.key] = {"fixture_id": second.fixture_id, "subfixture_id": second.subfixture_id, "relationship": "MIRROR_PAIR", "score": confidence, "fixture_type_compatible": type_match}
            pairs[second.key] = {"fixture_id": first.fixture_id, "subfixture_id": first.subfixture_id, "relationship": "MIRROR_PAIR", "score": confidence, "fixture_type_compatible": type_match}
        return pairs

    @staticmethod
    def _partner_payload(partner: dict[str, Any] | None) -> dict[str, Any] | None:
        return dict(partner) if partner else None

    @staticmethod
    def _distance_ranks(points: list[_Point], center: float) -> dict[tuple[int, int | None], int]:
        ordered = sorted(points, key=lambda item: (abs(item.x - center), item.fixture_id, item.subfixture_id or 0))
        return {point.key: index for index, point in enumerate(ordered)}

    def _nearest_to_center(self, points: list[_Point], center: float) -> dict[str, Any]:
        distances = {point.key: abs(point.x - center) for point in points}
        minimum = min(distances.values())
        nearest = [point for point in points if abs(distances[point.key] - minimum) <= self.tolerance]
        return {"x": center, "fixture_subfixtures": [{"fixture_id": point.fixture_id, "subfixture_id": point.subfixture_id} for point in nearest], "between_fixtures": len(nearest) == 2 and minimum > self.tolerance}

    def _x_side(self, value: float, center: float, span: float) -> str:
        if span <= self.tolerance or abs(value - center) <= self.tolerance:
            return "X_CENTER"
        return "X_NEGATIVE_SIDE" if value < center else "X_POSITIVE_SIDE"

    def _empty(self) -> dict[str, Any]:
        return {"status": "UNAVAILABLE", "reason": "No explicit geometry-bearing Subfixture records.", "algorithm_version": GEOMETRY_ALGORITHM_VERSION, "records": []}
