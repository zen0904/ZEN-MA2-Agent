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
            table_row = re.match(r"^Timecode\s+(\d+)\s+(.+?)\s+(Intern|Link\s+Selected|\d+)\s+(\d+:\d{2})\s+(\d+:\d{2})\b", line, re.I)
            if table_row:
                number, name, _slot, _length, offset_raw = table_row.groups()
                rows.append({
                    "timecode_number": int(number),
                    "name": name.strip(),
                    "tracks": [],
                    "events": [],
                    "offset_raw": offset_raw,
                    "offset_ms": self._list_frames_to_ms(offset_raw),
                    "offset_timebase": "30 FPS List Timecode readout (validated controlled differential)",
                    "event_capability": "UNSUPPORTED",
                    "source": "ma2_telnet_list",
                })
                continue
            match = self._row.match(line)
            if not match:
                continue
            number = int(match.group(1))
            name = match.group(2).strip().strip("'\"")
            rest = (match.group(3) or "").strip()
            offset_raw = None
            offset_ms = None
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
            if offset and offset_raw is None:
                offset_raw = offset.group(1)
            rows.append({
                "timecode_number": number,
                "name": name,
                "tracks": [],
                "events": [],
                "offset_raw": offset_raw,
                "offset_ms": offset_ms,
                "event_capability": "UNSUPPORTED",
                "source": "ma2_telnet_list",
            })
        return rows

    @staticmethod
    def _list_frames_to_ms(value: str) -> int | None:
        match = re.fullmatch(r"(\d+):(\d{2})", value)
        if not match:
            return None
        # On the verified MA2 3.9.60 onPC session, List Timecode renders
        # ``0.25s`` as ``0:08`` and ``0.50s`` as ``0:15``.  Its colon form is
        # consequently a 30 FPS seconds:frames readout, even when the object
        # TimeUnit column says 1/100 Seconds (that setting is graphical only).
        seconds, frames = map(int, match.groups())
        return round((seconds + frames / 30) * 1_000)

    @staticmethod
    def capability() -> dict[str, str]:
        return {
            "inventory": "supported",
            "tracks": "UNSUPPORTED",
            "events": "UNSUPPORTED",
            "event_time_readback": "UNSUPPORTED",
        }
