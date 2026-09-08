from __future__ import annotations

import re

from ..models import Fixture
from .fixture_geometry import FixtureGeometryProvider


class FixtureProvider:
    """Generic Telnet list provider; it parses only inventory metadata."""

    command = "List Fixture"
    _line = re.compile(r"^\s*(?:fixture\s+)?(\d+)\s+['\"]?(.+?)['\"]?(?:\s+\(([^)]+)\))?\s*$", re.I)

    def parse(self, output: str) -> list[Fixture]:
        # grandMA2 3.9's real List Fixture table has no quoted columns.  Its
        # verified fixed-tail layout is parsed by the geometry inventory reader;
        # retain the original compact-list parser for simulators and old output.
        table_rows = FixtureGeometryProvider().parse_inventory(output)
        if table_rows:
            return [Fixture(item.fixture_id, item.name, item.fixture_type) for item in table_rows]
        fixtures: list[Fixture] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if match:
                fixtures.append(Fixture(int(match.group(1)), match.group(2).strip().strip("'\""), match.group(3)))
        return fixtures
