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
    match = re.fullmatch(r"(?:群組|group)\s*(\d+)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("state_group_membership", {"group_no": int(match.group(1))}, source)
    match = re.fullmatch(r"(?:layout|佈局|布局)\s*(\d+)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("state_layout", {"layout_no": int(match.group(1))}, source)
    match = re.fullmatch(r"(.+?)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("state_group_membership_name", {"group_name": match.group(1).strip().strip("'\"")}, source)
    if re.fullmatch(r"(?:我\s*)?(?:現在\s*)?(?:選了|選取了|selected)\s*(?:哪些)?\s*(?:燈具|fixture|fixtures)", state_source, flags=re.I):
        return Intent("state_selection", {}, source)
    if re.fullmatch(r"(?:現在\s*)?(?:programmer|programmer\s*有東西嗎|編程器|程式器)(?:\s*(?:有東西嗎|summary))?", state_source, flags=re.I):
        return Intent("state_programmer", {}, source)
    match = re.fullmatch(r"(?:序列|sequence)\s*(\d+)\s*(?:有)?\s*(?:哪些)?\s*(?:cue|cues|提示)", state_source, flags=re.I)
    if match:
        return Intent("state_cues", {"sequence": int(match.group(1))}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:layout|layouts?|佈局|布局)", state_source, flags=re.I):
        return Intent("state_layouts", {}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:序列|sequences?)", state_source, flags=re.I):
        return Intent("state_sequences", {}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:群組|groups?)", state_source, flags=re.I):
        return Intent("state_groups", {}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:燈具|fixtures?)", state_source, flags=re.I):
        return Intent("state_fixtures", {}, source)

    match = re.fullmatch(r"(?:選|選擇|选择|select)\s+(?:燈具|fixture)\s+(\d+)\s*(?:到|to|thru)\s*(\d+)", source, flags=re.I)
    if match:
        first, last = int(match.group(1)), int(match.group(2))
        if first > last:
            raise ParseError("Fixture range must start before it ends.")
        return Intent("select_fixture_range", {"first": first, "last": last}, source)

    match = re.fullmatch(r"(?:選|選擇|选择|select)\s+(?:(?:群組|group)\s+)?(.+)", source, flags=re.I)
    if match:
        return Intent("select_group", {"group": _quoted_group(match.group(1))}, source)

    match = re.fullmatch(r"(?:beam\s*)?(?:亮|亮度|at)\s*(\d{1,3})\s*%?", source, flags=re.I)
    if match:
        level = int(match.group(1))
        if not 0 <= level <= 100:
            raise ParseError("Intensity must be between 0 and 100.")
        return Intent("beam_intensity", {"group": "BEAM", "level": level}, source)

    match = re.fullmatch(r"(?:go\s+sequence|(?:前往|執行)?\s*(?:序列|sequence))\s+(\d+)", source, flags=re.I)
    if match:
        return Intent("go_sequence", {"sequence": int(match.group(1))}, source)

    if source.lower() in {"blackout", "bo", "全黑"}:
        return Intent("blackout", {}, source)
    raise ParseError("No deterministic intent matched.")
