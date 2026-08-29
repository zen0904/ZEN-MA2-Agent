from __future__ import annotations

import re
import secrets
import time
from typing import Any
from xml.etree import ElementTree as ET

from .group_membership import GroupMembershipProviderError, GroupMembershipProviderUnavailable, ImportExportPathResolver, _configured_path, _is_loopback_host, _timeout_seconds
from .layout_cobject_registry import validated_mapping


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


class LayoutInventoryProvider:
    command = "List Layout"
    _line = re.compile(r"^\s*(?:layout\s+)?(\d+)\s+['\"]?(.+?)['\"]?\s*$", re.I)

    def parse(self, output: str) -> list[dict]:
        return [{"layout": int(match.group(1)), "name": match.group(2).strip().strip("'\""), "items": []} for line in output.splitlines() if (match := self._line.match(line.strip()))]


class LayoutObjectResolver:
    """Resolve explicit XML references and console-validated CObject tuples only."""

    _reference_attributes = (
        ("fixture", ("fix_id", "fixture_id")), ("subfixture", ("subfixture_id", "subfix_id")),
        ("group", ("group_no", "group_id")), ("macro", ("macro_no", "macro_id")),
        ("executor", ("executor_no", "executor_id")), ("sequence", ("sequence_no", "sequence_id")),
        ("page", ("page_no", "page_id")), ("screen", ("screen_no", "screen_id")),
    )

    @classmethod
    def resolve(cls, element: ET.Element, *, parent_path: str) -> dict[str, Any]:
        cobject = next((child for child in element if _local_name(child) == "CObject"), None)
        attributes, cobject_attributes = dict(element.attrib), dict(cobject.attrib) if cobject is not None else {}
        tokens = [child.text.strip() for child in (list(cobject) if cobject is not None else []) if child.text and child.text.strip()]
        object_class = next((attributes.get(name) or cobject_attributes.get(name) for name in ("object_class", "class", "type", "object_type") if attributes.get(name) or cobject_attributes.get(name)), None)
        token_mapping = validated_mapping(tokens)
        name = attributes.get("name") or cobject_attributes.get("name") or ""
        base = {"name": name, "object_class": object_class, "raw_xml_tag": _local_name(element), "raw_attributes": attributes, "cobject_attributes": cobject_attributes, "parent_path": parent_path, "reference_tokens": tokens}
        for object_type, names in cls._reference_attributes:
            value = next((attributes.get(name) or cobject_attributes.get(name) for name in names if attributes.get(name) or cobject_attributes.get(name)), None)
            if value is not None:
                return {"type": object_type, "reference": int(value) if value.isdigit() else value, "resolved": True, **base}
        if token_mapping:
            reference: int | str
            if token_mapping["object_type"] == "preset":
                reference = f"{int(tokens[2])}.{int(tokens[3])}"
            else:
                reference = int(tokens[2])
            return {"type": token_mapping["object_type"], "reference": reference, "resolved": True, "ma2_class": token_mapping["ma2_class"], "provenance": token_mapping["source"], **base}
        return {"type": "unknown", "reference": tokens, "resolved": False, "validated_token_class": None, **base}

    @staticmethod
    def lighting_items(layout: dict[str, Any]) -> list[dict[str, Any]]:
        """A Group button is not an individual fixture item in a Layout."""
        return [item for item in layout["items"] if item["type"] in {"fixture", "subfixture"}]


class LayoutFixtureProvider:
    """Future read-only source for Fixture/Subfixture XY, separate from XML CObjects."""

    source = "ma2_layout_fixture_probe"
    capability = "UNSUPPORTED"
    reason = "Fixture layout data is not available from the current MA2 Layout Export provider."

    def state(self) -> dict[str, str]:
        return {"status": self.capability, "source": self.source, "reason": self.reason}


class LayoutExportProvider:
    """Partial LayoutState provider: exported CObjects plus fixture-geometry capability."""

    source = "ma2_export_xml"
    requires_local_filesystem = True
    _name = re.compile(r"^ZEN_AGENT_LAYOUT_[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml$")

    def __init__(self, resolver: ImportExportPathResolver | None = None, fixture_provider: LayoutFixtureProvider | None = None) -> None:
        self.resolver = resolver or ImportExportPathResolver()
        self.fixture_provider = fixture_provider or LayoutFixtureProvider()

    def capabilities(self, runtime: Any, settings: object) -> dict[str, object]:
        try:
            path = self.resolver.resolve(_configured_path(settings)) if _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")) else None
        except GroupMembershipProviderUnavailable:
            path = None
        return {
            "requires_local_filesystem": True,
            "local_export_access": bool(path),
            "importexport_path": str(path) if path else None,
            "layout_cobjects": "supported",
            "layout_fixture_geometry": self.fixture_provider.capability,
            "layout_fixture_geometry_source": self.fixture_provider.source,
        }

    def get_layout(self, runtime: Any, layout_no: int, settings: object) -> dict:
        if not isinstance(layout_no, int) or isinstance(layout_no, bool) or layout_no < 1:
            raise ValueError("Layout requires a positive number.")
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_EXPORT_ACCESS_UNAVAILABLE")
        directory = self.resolver.resolve(_configured_path(settings)); request_id = secrets.token_hex(8); filename = f"ZEN_AGENT_LAYOUT_{layout_no}_{request_id}.xml"; path = directory / filename; started = time.time_ns()
        try:
            runtime.export_layout_file(layout_no, filename)
            deadline = time.monotonic() + _timeout_seconds(settings)
            while time.monotonic() <= deadline:
                if path.is_file() and path.stat().st_mtime_ns >= started: break
                time.sleep(.05)
            else: raise GroupMembershipProviderError("EXPORT_FILE_TIMEOUT")
            result = self.parse(path.read_text(encoding="utf-8"), layout_no)
        except (OSError, ET.ParseError, ValueError) as exc:
            raise GroupMembershipProviderError("EXPORT_LAYOUT_XML_INVALID") from exc
        if path.parent.resolve() == directory.resolve() and self._name.fullmatch(path.name): path.unlink(missing_ok=True)
        for item in result["items"]:
            runtime.log("layout_object_diagnostic", {"layout": layout_no, **{key: item.get(key) for key in ("type", "reference", "resolved", "provenance", "raw_xml_tag", "raw_attributes", "cobject_attributes", "parent_path", "reference_tokens", "object_class", "name", "x", "y")}})
        # Export Layout 99 on grandMA2 3.9.60 can omit visible Fixture items.
        # Preserve XML CObjects while explicitly surfacing the unavailable part.
        result["fixture_geometry"] = self.fixture_provider.state()
        result["layout_cobjects"] = {"status": "supported", "source": self.source}
        return result

    @staticmethod
    def parse(xml: str, layout_no: int) -> dict:
        root = ET.fromstring(xml); group = next((element for element in root.iter() if _local_name(element) == "Group" and element.get("index") == str(layout_no - 1)), None)
        if group is None: raise ValueError("EXPORT_LAYOUT_NUMBER_MISMATCH")
        data = next((element for element in group if _local_name(element) == "LayoutData"), None)
        if data is None: raise ValueError("EXPORT_LAYOUT_NO_DATA")
        parent = {child: node for node in root.iter() for child in node}
        def parent_path(element: ET.Element) -> str:
            nodes = [element]
            while nodes[-1] in parent: nodes.append(parent[nodes[-1]])
            return "/".join(_local_name(node) for node in reversed(nodes))
        items: list[dict[str, Any]] = []
        for element in data.iter():
            if _local_name(element) != "LayoutCObject": continue
            item = LayoutObjectResolver.resolve(element, parent_path=parent_path(element))
            item.update({"x": float(element.get("center_x", "0")), "y": float(element.get("center_y", "0")), "w": float(element.get("size_w", "0")), "h": float(element.get("size_h", "0")), "rotation": float(element.get("rotation")) if element.get("rotation") is not None else None, "export_order": len(items)})
            items.append(item)
        return {"layout": layout_no, "name": group.get("name", ""), "items": items, "source": "ma2_export_xml"}
