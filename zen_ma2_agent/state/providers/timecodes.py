"""Read-only grandMA2 Timecode pool inventory.

grandMA2 3.9 exposes the Timecode pool through ``List Timecode``.  Its event
editor is graphical and no per-event CLI/XML schema has been verified for this
Agent yet, so this provider deliberately reports an inventory only.
"""
from __future__ import annotations

import re


class TimecodeProvider:
    command = "List Timecode"
    _row = re.compile(r"^\s*(?:timecode\s+)?(\d+)\s+['\"]?(.+?)['\"]?(?:\s+(.*))?$", re.I)

    def parse(self, output: str) -> list[dict]:
        rows: list[dict] = []
        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line or line.casefold().startswith(("executing", "no.", "warning")):
                continue
            match = self._row.match(line)
            if not match:
                continue
            number = int(match.group(1))
            name = match.group(2).strip().strip("'\"")
            rest = (match.group(3) or "").strip()
            # MA2's table format repeats the object No. before the visible name.
            if name == str(number) and rest:
                visible = re.sub(r"\s+\([^)]*\)\s*$", "", rest).strip()
                if visible:
                    property_start = re.search(r"\boffset\s*[:=]", visible, re.I)
                    if property_start:
                        name, rest = visible[:property_start.start()].strip(), visible[property_start.start():].strip()
                    else:
                        name, rest = visible, ""
            offset = re.search(r"\boffset\s*[:=]\s*([^\s]+)", rest, re.I)
            rows.append({
                "timecode_number": number,
                "name": name,
                "tracks": [],
                "events": [],
                "offset_raw": offset.group(1) if offset else None,
                "event_capability": "UNSUPPORTED",
                "source": "ma2_telnet_list",
            })
        return rows

    @staticmethod
    def capability() -> dict[str, str]:
        return {
            "inventory": "supported",
            "tracks": "UNSUPPORTED",
            "events": "UNSUPPORTED",
            "event_time_readback": "UNSUPPORTED",
        }
