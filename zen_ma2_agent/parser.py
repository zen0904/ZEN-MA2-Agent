from __future__ import annotations

import re

from .models import Intent


class ParseError(ValueError):
    pass


def _quoted_group(value: str) -> str:
    return value.strip().strip('"').replace('"', "'")


def parse(text: str) -> Intent:
    source = text.strip()
    if not source:
        raise ParseError("Enter a command request.")

    state_source = source.rstrip("?？").strip()
    if re.fullmatch(r"(?:現在\s*show\s*[裡里]?\s*有\s*哪些|list|show)\s*groups?", state_source, flags=re.I):
        return Intent("state_groups", {}, source)
    if re.fullmatch(r"(?:現在\s*show\s*[裡里]?\s*有\s*哪些|list|show)\s*fixtures?", state_source, flags=re.I):
        return Intent("state_fixtures", {}, source)

    match = re.fullmatch(r"(?:選|选择|select)\s+fixture\s+(\d+)\s*(?:到|to|thru)\s*(\d+)", source, flags=re.I)
    if match:
        first, last = int(match.group(1)), int(match.group(2))
        if first > last:
            raise ParseError("Fixture range must start before it ends.")
        return Intent("select_fixture_range", {"first": first, "last": last}, source)

    match = re.fullmatch(r"(?:選|选择|select)\s+(?:group\s+)?(.+)", source, flags=re.I)
    if match:
        return Intent("select_group", {"group": _quoted_group(match.group(1))}, source)

    match = re.fullmatch(r"(?:beam\s*)?(?:亮|亮度|at)\s*(\d{1,3})\s*%?", source, flags=re.I)
    if match:
        level = int(match.group(1))
        if not 0 <= level <= 100:
            raise ParseError("Intensity must be between 0 and 100.")
        return Intent("beam_intensity", {"group": "BEAM", "level": level}, source)

    match = re.fullmatch(r"go\s+sequence\s+(\d+)", source, flags=re.I)
    if match:
        return Intent("go_sequence", {"sequence": int(match.group(1))}, source)

    if source.lower() in {"blackout", "bo", "全黑"}:
        return Intent("blackout", {}, source)
    raise ParseError("Unsupported MVP request. Try Group, Beam, Go Sequence, Fixture range, or Blackout.")
