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
    if re.fullmatch(r"(?:檢查(?:這個|目前)?\s*show|show\s*diagnostics|這個\s*show\s*有沒有問題|幫我檢查(?:目前)?\s*show)", state_source, flags=re.I):
        return Intent("diagnose_show", {}, source)
    if re.fullmatch(r"(?:顯示)?詳細診斷", state_source, flags=re.I):
        return Intent("diagnose_show_details", {}, source)
    match = re.fullmatch(r"只看\s*(warning|warnings|警告|error|errors|錯誤)", state_source, flags=re.I)
    if match:
        return Intent("diagnose_show_filter", {"severity": "WARNING" if match.group(1).casefold() in {"warning", "warnings", "警告"} else "ERROR"}, source)
    match = re.fullmatch(r"(layout|佈局|布局|group|群組|sequence|序列)\s*有什麼問題", state_source, flags=re.I)
    if match:
        aliases = {"佈局": "layout", "布局": "layout", "群組": "group", "序列": "sequence"}
        return Intent("diagnose_show_filter", {"category": aliases.get(match.group(1).casefold(), match.group(1).casefold())}, source)
    match = re.fullmatch(r"(?:群組|group)\s*(\d+)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("state_group_membership", {"group_no": int(match.group(1))}, source)
    match = re.fullmatch(r"(?:layout|佈局|布局)\s*(\d+)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("layout_items_query", {"layout_no": int(match.group(1))}, source)
    match = re.fullmatch(r"(?:layout|佈局|布局)\s*(\d+)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:物件|物件|objects?)", state_source, flags=re.I)
    if match:
        return Intent("layout_all_objects_query", {"layout_no": int(match.group(1))}, source)
    match = re.fullmatch(r"(.+?)\s*(?:在|於)\s*(?:layout|佈局|布局)\s*(\d+)\s*(?:怎麼排|如何排|怎麼排列)", state_source, flags=re.I)
    if match:
        return Intent("layout_items_query", {"layout_no": int(match.group(2)), "object_name": match.group(1).strip()}, source)
    match = re.fullmatch(r"(?:sequence|序列)\s*(\d+)\s*(?:掛在(?:哪個)?|在哪個)\s*(?:executor|exec|執行器)", state_source, flags=re.I)
    if match: return Intent("sequence_executor_lookup", {"sequence":int(match.group(1))}, source)
    match = re.fullmatch(r"(?:page|頁面)\s*(\d+)\s*(?:有)?\s*(?:哪些)?\s*(?:executor|exec|執行器)", state_source, flags=re.I)
    if match: return Intent("page_executor_list", {"page":int(match.group(1))}, source)
    if re.fullmatch(r"(?:我\s*)?(?:(?:現在|目前)\s*)?(?:選了|選取了|selected)\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)|(?:selection|選擇)\s*(?:裡|里|中)?\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I):
        return Intent("state_selection", {}, source)
    if re.fullmatch(r"(?:(?:現在|目前)\s*)?(?:programmer|編程器|程式器)(?:\s*(?:裡|里|中))?(?:\s*(?:有什麼|有東西嗎|有沒有東西|summary))?|(?:哪些燈\s*有\s*active\s*value|現在\s*有什麼\s*attribute\s*在\s*programmer)", state_source, flags=re.I):
        return Intent("state_programmer", {}, source)
    match = re.fullmatch(r"(.+?)\s*(?:裡|里|中)\s*(?:有)?\s*(?:哪些)?\s*(?:燈|燈具|fixture|fixtures)", state_source, flags=re.I)
    if match:
        return Intent("state_group_membership_name", {"group_name": match.group(1).strip().strip("'\"")}, source)
    match = re.fullmatch(r"(?:序列|sequence)\s*(\d+)\s*(?:有)?\s*(?:哪些)?\s*(?:cue|cues|提示)", state_source, flags=re.I)
    if match:
        return Intent("state_cues", {"sequence": int(match.group(1))}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:layout|layouts?|佈局|布局)", state_source, flags=re.I):
        return Intent("state_layouts", {}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:序列|sequences?)", state_source, flags=re.I):
        return Intent("state_sequences", {}, source)
    match=re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(dimmer|position|gobo|color|beam|focus|control|all|調光|位置|圖案|顏色|光束)\s*(?:preset|presets?|預設)", state_source, flags=re.I)
    if match:
        aliases={"調光":"DIMMER","位置":"POSITION","圖案":"GOBO","顏色":"COLOR","光束":"BEAM"}; return Intent("preset_list", {"preset_type":aliases.get(match.group(1).casefold(),match.group(1).upper())}, source)
    if re.fullmatch(r"(?:現在\s*(?:show\s*)?[裡里]?\s*有\s*哪些|(?:show\s*)?有哪些|列出|list|show)\s*(?:effect|effects?|效果)", state_source, flags=re.I): return Intent("effect_list", {}, source)
    if re.fullmatch(r"(?:下一頁|next\s+page)", state_source, flags=re.I): return Intent("effect_next_page", {}, source)
    match=re.fullmatch(r"(?:effect|效果)\s*(\d+)\s*(?:是什麼|是甚麼|what(?:\s+is)?|info)?", state_source, flags=re.I)
    if match: return Intent("effect_lookup", {"effect":int(match.group(1))}, source)
    build = _parse_dimmer_chase(source)
    if build:
        return build
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


def _parse_dimmer_chase(source: str) -> Intent | None:
    """Parse only the deterministic Effect Builder v1 vocabulary.

    Other effect families deliberately remain unmatched until their MA2 command
    grammar is verified on the real console.
    """
    normalized = source.rstrip("?？").strip()
    if not re.search(r"(?:dimmer|調光|亮度)\s*(?:chase|effect|效果)|(?:chase|追逐)|(?:做|建立|create|build|make)\s*(?:一個\s*)?(?:effect|效果)\s*\d+", normalized, re.I):
        return None
    if not re.search(r"(?:做|建立|幫|create|build|make)", normalized, re.I):
        return None
    parameters: dict[str, object] = {}
    number = re.search(r"(?:effect|效果)\s*(\d+)", normalized, re.I)
    if number:
        parameters["effect_number"] = int(number.group(1))
    bpm = re.search(r"(\d{1,3})\s*bpm", normalized, re.I)
    if bpm:
        parameters["speed_bpm"] = int(bpm.group(1))
    if re.search(r"(?:反方向|reverse|backward)", normalized, re.I):
        parameters["direction"] = "reverse"
    elif re.search(r"(?:從左到右|left\s*to\s*right|forward)", normalized, re.I):
        parameters["direction"] = "forward"
    group_no = re.search(r"(?:group|群組)\s*(\d+)", normalized, re.I)
    fixture_no = re.search(r"(?:fixture|燈具)\s*(\d+)", normalized, re.I)
    if group_no:
        parameters.update({"target_type": "group_number", "target": int(group_no.group(1))})
    elif fixture_no:
        parameters.update({"target_type": "fixture_number", "target": int(fixture_no.group(1))})
    else:
        target = re.search(r"(?:幫|給|for)\s*([A-Za-z][A-Za-z0-9 _-]*)\s*(?:做|建立|create|build|make|一個|a)?", normalized, re.I)
        if target:
            name = target.group(1).strip()
            # Stop at effect-description words if the natural phrase did not
            # use a Chinese target separator.
            name = re.split(r"\s+(?:dimmer|chase|effect|效果)", name, maxsplit=1, flags=re.I)[0].strip()
            if name:
                parameters.update({"target_type": "group_name", "target": name})
    return Intent("build_dimmer_chase", parameters, source)
