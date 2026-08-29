from __future__ import annotations

import re

from ..models import Group


class GroupProvider:
    """Generic Telnet list provider; MA2 access is injected by AgentCore."""

    command = "List Group"
    # grandMA2 3.9 table output includes object number and the `No.` column:
    # `Group  1 1    HYBRID`. Use the latter as the user-facing Group number.
    _table_row = re.compile(r"^\s*group\s+\d+\s+(\d+)\s+(.+?)\s*$", re.I)
    _line = re.compile(r"^\s*(?:group\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)

    def parse(self, output: str) -> list[Group]:
        groups: list[Group] = []
        for line in output.splitlines():
            match = self._table_row.match(line.strip()) or self._line.match(line.strip())
            if match:
                groups.append(Group(int(match.group(1)), match.group(2).strip().strip("'\"")))
        return groups
