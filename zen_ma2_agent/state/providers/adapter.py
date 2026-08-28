from __future__ import annotations

import json
import re
from typing import Any


class AdapterResponseError(ValueError):
    pass


class AdapterUnsupported(AdapterResponseError):
    pass


class ZenStateAdapter:
    """Strict parser/compiler for the bundled read-only ZEN_AGENT Lua protocol."""

    source = "ma2_lua_adapter"
    _request = re.compile(r"^[a-z_]+(?:\s+\d+)?$")

    def command(self, template: str, request: str) -> str:
        if not self._request.fullmatch(request):
            raise ValueError("Invalid read-only adapter request.")
        if "{request}" not in template:
            raise ValueError("State adapter command template must contain {request}.")
        command = template.replace("{request}", request)
        if not re.fullmatch(r'Plugin\s+(?:"ZEN_AGENT"|\d+)\s+"[a-z_]+(?:\s+\d+)?"', command, re.I):
            raise ValueError("State adapter command template is not a safe ZEN_AGENT Plugin invocation.")
        return command

    def payload(self, output: str, resource: str) -> Any:
        error_marker = f"ZEN_STATE_ERROR|{resource}|"
        if error_marker in output:
            detail = output.split(error_marker, 1)[1].splitlines()[0].strip()
            raise AdapterUnsupported(f"UNSUPPORTED {resource}: {detail or 'adapter reported no safe accessor'}")
        marker = f"ZEN_STATE|{resource}|"
        if marker not in output:
            raise AdapterUnsupported(f"UNSUPPORTED {resource}: read-only ZEN_AGENT adapter is missing or returned no compatible data.")
        encoded = output.split(marker, 1)[1].lstrip()
        try:
            value, _ = json.JSONDecoder().raw_decode(encoded)
        except json.JSONDecodeError as exc:
            raise AdapterResponseError(f"Malformed ZEN_AGENT {resource} response.") from exc
        return value

    def group_membership(self, output: str, group_no: int) -> dict[str, Any]:
        value = self.payload(output, "group_membership")
        if not isinstance(value, dict) or value.get("group_no") != group_no or not isinstance(value.get("name"), str) or not isinstance(value.get("fixtures"), list):
            raise AdapterResponseError("Malformed group membership response.")
        fixtures = value["fixtures"]
        if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in fixtures):
            raise AdapterResponseError("Malformed group membership fixture IDs.")
        return {"group_no": group_no, "name": value["name"], "fixtures": fixtures}

    def layout(self, output: str, layout_no: int) -> dict[str, Any]:
        value = self.payload(output, "layouts")
        if not isinstance(value, dict) or value.get("layout") != layout_no or not isinstance(value.get("items"), list):
            raise AdapterResponseError("Malformed layout response.")
        items: list[dict[str, Any]] = []
        for item in value["items"]:
            if not isinstance(item, dict) or item.get("type") not in {"fixture", "group"}:
                raise AdapterResponseError("Malformed layout item type.")
            reference = item.get(item["type"])
            if isinstance(reference, bool) or not isinstance(reference, int) or reference < 1:
                raise AdapterResponseError("Malformed layout object reference.")
            normalized = {"type": item["type"], item["type"]: reference}
            for key in ("x", "y", "width", "height", "rotation"):
                if key in item:
                    if isinstance(item[key], bool) or not isinstance(item[key], (int, float)):
                        raise AdapterResponseError(f"Malformed layout {key}.")
                    normalized[key] = float(item[key])
            if "x" not in normalized or "y" not in normalized:
                raise AdapterResponseError("Layout item lacks XY coordinates.")
            items.append(normalized)
        result = {"layout": layout_no, "items": items}
        if isinstance(value.get("name"), str):
            result["name"] = value["name"]
        return result

    def selection(self, output: str) -> dict[str, Any]:
        value = self.payload(output, "selection")
        if not isinstance(value, dict) or not isinstance(value.get("fixtures"), list):
            raise AdapterResponseError("Malformed selection response.")
        fixtures = value["fixtures"]
        if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in fixtures):
            raise AdapterResponseError("Malformed selection fixture IDs.")
        return {"fixtures": fixtures}

    def programmer(self, output: str) -> dict[str, Any]:
        value = self.payload(output, "programmer")
        if not isinstance(value, dict) or not isinstance(value.get("has_active_values"), bool):
            raise AdapterResponseError("Malformed programmer response.")
        result = {"has_active_values": value["has_active_values"]}
        if "active_attributes" in value:
            if not isinstance(value["active_attributes"], (dict, list)):
                raise AdapterResponseError("Malformed active attribute summary.")
            result["active_attributes"] = value["active_attributes"]
        return result
