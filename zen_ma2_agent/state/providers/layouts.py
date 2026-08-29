from __future__ import annotations

import re
import secrets
import time
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .group_membership import GroupMembershipProviderError, GroupMembershipProviderUnavailable, ImportExportPathResolver, _configured_path, _is_loopback_host, _timeout_seconds


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


class LayoutExportProvider:
    """Local onPC Export Layout backend; does not use selection or Lua probes."""
    source = "ma2_export_xml"
    requires_local_filesystem = True
    _name = re.compile(r"^ZEN_AGENT_LAYOUT_[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml$")

    def __init__(self, resolver: ImportExportPathResolver | None = None) -> None:
        self.resolver = resolver or ImportExportPathResolver()

    def capabilities(self, runtime: Any, settings: object) -> dict[str, object]:
        try:
            path = self.resolver.resolve(_configured_path(settings)) if _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")) else None
        except GroupMembershipProviderUnavailable:
            path = None
        return {"requires_local_filesystem": True, "local_export_access": bool(path), "importexport_path": str(path) if path else None}

    def get_layout(self, runtime: Any, layout_no: int, settings: object) -> dict:
        if not isinstance(layout_no, int) or isinstance(layout_no, bool) or layout_no < 1: raise ValueError("Layout requires a positive number.")
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_EXPORT_ACCESS_UNAVAILABLE")
        directory=self.resolver.resolve(_configured_path(settings)); request_id=secrets.token_hex(8); filename=f"ZEN_AGENT_LAYOUT_{layout_no}_{request_id}.xml"; path=directory/filename
        started=time.time_ns()
        try:
            runtime.export_layout_file(layout_no, filename)
            deadline=time.monotonic()+_timeout_seconds(settings)
            while time.monotonic() <= deadline:
                if path.is_file() and path.stat().st_mtime_ns >= started: break
                time.sleep(.05)
            else: raise GroupMembershipProviderError("EXPORT_FILE_TIMEOUT")
            result=self.parse(path.read_text(encoding="utf-8"), layout_no)
        except (OSError, ET.ParseError, ValueError) as exc:
            raise GroupMembershipProviderError("EXPORT_LAYOUT_XML_INVALID") from exc
        if path.parent.resolve()==directory.resolve() and self._name.fullmatch(path.name): path.unlink(missing_ok=True)
        return result

    @staticmethod
    def parse(xml: str, layout_no: int) -> dict:
        root=ET.fromstring(xml); group=next((e for e in root.iter() if e.tag.rsplit("}",1)[-1]=="Group" and e.get("index")==str(layout_no-1)),None)
        if group is None: raise ValueError("EXPORT_LAYOUT_NUMBER_MISMATCH")
        data=next((e for e in group if e.tag.rsplit("}",1)[-1]=="LayoutData"),None)
        if data is None: raise ValueError("EXPORT_LAYOUT_NO_DATA")
        items=[]
        for element in data.iter():
            if element.tag.rsplit("}",1)[-1] != "LayoutCObject": continue
            obj=next((e for e in element if e.tag.rsplit("}",1)[-1]=="CObject"),None); nos=[n.text for n in obj] if obj is not None else []
            explicit_fix=element.get("fix_id") or element.get("fixture_id"); explicit_group=element.get("group_no")
            item_type="fixture" if explicit_fix else "group" if explicit_group else "unknown"
            reference=int(explicit_fix or explicit_group) if (explicit_fix or explicit_group or "").isdigit() else nos
            items.append({"type":item_type,"reference":reference,"name":obj.get("name","") if obj is not None else "","x":float(element.get("center_x","0")),"y":float(element.get("center_y","0")),"w":float(element.get("size_w","0")),"h":float(element.get("size_h","0")),"rotation":float(element.get("rotation")) if element.get("rotation") is not None else None,"export_order":len(items)})
        return {"layout":layout_no,"name":group.get("name", ""),"items":items,"source":"ma2_export_xml"}
