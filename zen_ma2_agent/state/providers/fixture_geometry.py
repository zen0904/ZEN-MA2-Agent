"""Read-only Fixture/Subfixture stage-geometry provider for grandMA2 3.9.

The verified runtime source is ``List Fixture <fixture>.<instance>``.  Root
Fixture rows are inventory metadata only: in the real 3.9.60 test a Move3D
change was visible on the Subfixture row while the root row remained zero.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


NUMBER = r"[+-]?\d+(?:\.\d+)?"


@dataclass(frozen=True)
class FixtureSeed:
    fixture_id: int
    name: str
    fixture_type: str | None
    patch: str | None
    instance_count: int


class FixtureGeometryProvider:
    """Collect only explicit MA2 Fixture/Subfixture object properties."""

    source = "MA2_FIXTURE_OBJECT_PROPERTY"
    backend = "MA2_TELNET_LIST_SUBFIXTURE"
    inventory_command = "List Fixture"
    _root = re.compile(
        rf"^\s*Fixture\s+(?P<fixture_id>\d+)\s+(?P<body>.+?)\s+"
        rf"(?P<x>{NUMBER})\s+(?P<y>{NUMBER})\s+(?P<z>{NUMBER})\s+"
        rf"(?P<rx>{NUMBER})\s+(?P<ry>{NUMBER})\s+(?P<rz>{NUMBER})\s+"
        r"\((?P<instances>\d+)\)\s*$",
        re.I,
    )
    _subfixture = re.compile(
        rf"^\s*SubFixture\s+(?P<object_ref>\d+(?:\.\d+)?)\s+"
        rf"(?P<fix_id>\d+(?:\.\d+)?)\s+(?P<channel>\S+)\s+(?P<body>.+?)\s+"
        rf"(?P<x>{NUMBER})\s+(?P<y>{NUMBER})\s+(?P<z>{NUMBER})\s+"
        rf"(?P<rx>{NUMBER})\s+(?P<ry>{NUMBER})\s+(?P<rz>{NUMBER})\s+"
        r"\S+\s+\(\d+\)\s*$",
        re.I,
    )
    _prefix = re.compile(r"^(?P<name>.+?)\s{2,}(?P<fix_id>\d+)\s+\S+\s{2,}(?P<fixture_type>.+?)\s+(?P<patch>\d+\.\d+|\(-\))\s+(?P<tail>.*)$")
    _sub_prefix = re.compile(r"^(?P<name>.+?)\s{2,}(?P<fixture_type>.+?)\s+(?P<patch>\d+\.\d+|\(-\))\s+(?P<tail>.*)$")

    @staticmethod
    def command_for(fixture_id: int, instance: int) -> str:
        if isinstance(fixture_id, bool) or isinstance(instance, bool) or fixture_id < 1 or instance < 1:
            raise ValueError("Fixture geometry requires positive numeric Fixture and instance IDs.")
        return f"List Fixture {fixture_id}.{instance}"

    def parse_inventory(self, output: str) -> list[FixtureSeed]:
        seeds: list[FixtureSeed] = []
        for line in output.splitlines():
            match = self._root.match(line.strip())
            if not match:
                continue
            prefix = self._prefix.match(match.group("body"))
            seeds.append(FixtureSeed(
                int(match.group("fixture_id")),
                prefix.group("name").strip() if prefix else f"Fixture {match.group('fixture_id')}",
                prefix.group("fixture_type").strip() if prefix else None,
                prefix.group("patch").strip() if prefix else None,
                int(match.group("instances")),
            ))
        return seeds

    def parse_subfixture(self, output: str, *, fixture_id: int, instance: int) -> dict[str, Any] | None:
        """Parse one real MA2 SubFixture row; unknown/missing rows remain absent."""
        for line in output.splitlines():
            match = self._subfixture.match(line.strip())
            if not match:
                continue
            prefix = self._sub_prefix.match(match.group("body"))
            if not prefix:
                return None
            raw_ref = match.group("fix_id")
            # MA2 reports single-instance Fixtures as ``101`` but multi-instance
            # Fixtures as ``701.2``.  The requested numeric path is the binding.
            expected = {str(fixture_id), f"{fixture_id}.{instance}"}
            if raw_ref not in expected or match.group("object_ref") not in expected:
                continue
            tail = prefix.group("tail").split()
            return {
                "fixture_id": fixture_id,
                "subfixture_id": instance,
                "fixture_ref": f"{fixture_id}.{instance}",
                "name": prefix.group("name").strip(),
                "fixture_type": prefix.group("fixture_type").strip(),
                "patch": prefix.group("patch").strip(),
                "position": {"x": float(match.group("x")), "y": float(match.group("y")), "z": float(match.group("z"))},
                "rotation": {"x": float(match.group("rx")), "y": float(match.group("ry")), "z": float(match.group("rz"))},
                "pan_offset": self._tail_float(tail, 5),
                "tilt_offset": self._tail_float(tail, 6),
                "pan_dmx_invert": tail[1] if len(tail) > 1 else None,
                "tilt_dmx_invert": tail[2] if len(tail) > 2 else None,
                "source": self.source,
                "backend": self.backend,
                "confidence": "REAL_MACHINE_VERIFIED",
            }
        return None

    @staticmethod
    def _tail_float(values: list[str], index: int) -> float | None:
        try:
            return float(values[index])
        except (IndexError, ValueError):
            return None

    def collect(self, runtime: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        seeds = self.parse_inventory(runtime.read_state(self.inventory_command))
        values: list[dict[str, Any]] = []
        missing: list[str] = []
        for seed in seeds:
            # In 3.9.60 the parenthesized inventory count matched exactly the
            # valid Subfixture suffixes for a one-instance moving head and a
            # two-instance Atomic fixture.  This is verified, not inferred.
            for instance in range(1, seed.instance_count + 1):
                record = self.parse_subfixture(runtime.read_state(self.command_for(seed.fixture_id, instance)), fixture_id=seed.fixture_id, instance=instance)
                if record is None:
                    missing.append(f"{seed.fixture_id}.{instance}")
                else:
                    values.append(record)
        capability = {
            "stage_geometry": "supported",
            "fixture_identity": "supported",
            "subfixture_identity": "supported",
            "patch": "supported",
            "pan_tilt_offsets": "supported_when_exposed",
            "missing_subfixtures": missing,
        }
        return values, capability
