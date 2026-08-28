from __future__ import annotations

import re

from ..models import Group


class GroupProvider:
    """Generic Telnet list provider; MA2 access is injected by AgentCore."""

    command = "List Group"
    _line = re.compile(r"^\s*(?:group\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)

    def parse(self, output: str) -> list[Group]:
        groups: list[Group] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if match:
                groups.append(Group(int(match.group(1)), match.group(2).strip().strip("'\"")))
        return groups
