"""Offline parser prototype for a grandMA2 3.9 Group export XML file.

This module deliberately has no transport or AgentCore dependency. It parses
an XML file that the operator exported through MA2's native ``Export Group``
command; wiring that export into live state refresh requires a separate safety
review.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET


class GroupExportParseError(ValueError):
    """The input is not a supported, single-object grandMA2 Group export."""


def group_membership_from_export(source: str | bytes | Path, group_no: int) -> dict[str, object]:
    """Parse one MA2 Group export without changing the show or console state.

    grandMA2 3.9 exports Group 1 as ``<Group index=\"0\">``; its XML index is
    therefore zero-based while the user-facing Group number is one-based.
    Fixture membership is the ordered list of ``Subfixture/@fix_id`` values.
    """
    if not isinstance(group_no, int) or isinstance(group_no, bool) or group_no < 1:
        raise GroupExportParseError("Group number must be a positive integer.")
    root = _root(source)
    groups = [element for element in root.iter() if _local_name(element.tag) == "Group"]
    if not groups:
        raise GroupExportParseError("EXPORT_XML_NO_GROUP")

    expected_index = group_no - 1
    group = next((item for item in groups if item.get("index") == str(expected_index)), None)
    if group is None:
        raise GroupExportParseError("EXPORT_XML_GROUP_NUMBER_MISMATCH")

    subfixtures = next((item for item in group if _local_name(item.tag) == "Subfixtures"), None)
    if subfixtures is None:
        # Native grandMA2 3.9 exports a genuinely empty Group as a self-closing
        # Group node.  That is a supported empty membership, not a missing
        # schema.  Unknown child nodes still remain a schema error: never guess
        # that they are fixture membership.
        if not list(group):
            return {
                "group_no": group_no,
                "name": group.get("name", ""),
                "fixtures": [],
                "source": "ma2_group_export_xml",
            }
        raise GroupExportParseError("EXPORT_XML_NO_MEMBERSHIP")

    fixtures: list[int] = []
    for item in subfixtures:
        if _local_name(item.tag) != "Subfixture":
            continue
        value = item.get("fix_id")
        if value is None or not value.isdecimal() or int(value) < 1:
            raise GroupExportParseError("EXPORT_XML_INVALID_FIX_ID")
        fixtures.append(int(value))

    return {
        "group_no": group_no,
        "name": group.get("name", ""),
        "fixtures": fixtures,
        "source": "ma2_group_export_xml",
    }


def _root(source: str | bytes | Path) -> ET.Element:
    try:
        if isinstance(source, Path):
            return ET.parse(source).getroot()
        if isinstance(source, bytes):
            return ET.fromstring(source)
        if isinstance(source, str):
            return ET.fromstring(source)
    except (OSError, ET.ParseError) as exc:
        raise GroupExportParseError("EXPORT_XML_MALFORMED") from exc
    raise TypeError("source must be XML text, XML bytes, or a Path")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
