from __future__ import annotations

import re


class LayoutInventoryProvider:
    """Read-only Layout Pool inventory; item geometry needs the Lua adapter."""

    command = "List Layout"
    _line = re.compile(r"^\s*(?:layout\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)

    def parse(self, output: str) -> list[dict]:
        layouts: list[dict] = []
        for line in output.splitlines():
            match = self._line.match(line.strip())
            if match:
                layouts.append({"layout": int(match.group(1)), "name": match.group(2).strip().strip("'\""), "items": []})
        return layouts
