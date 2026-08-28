from __future__ import annotations

import re

from ..models import Fixture


class FixtureProvider:
    """Generic Telnet list provider; it parses only inventory metadata."""

    command = "List Fixture"
    _line = re.compile(r"^\s*(?:fixture\s+)?(\d+)\s+['\"]?(.+?)['\"]?(?:\s+\(([^)]+)\))?\s*$", re.I)

    def parse(self, output: str) -> list[Fixture]:
        fixtures: list[Fixture] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if match:
                fixtures.append(Fixture(int(match.group(1)), match.group(2).strip().strip("'\""), match.group(3)))
        return fixtures
