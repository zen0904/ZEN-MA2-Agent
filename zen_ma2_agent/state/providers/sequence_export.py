"""Read-only discovery of the proven grandMA2 Sequence export XML paths."""

from __future__ import annotations

import hashlib
import ipaddress
import re
import secrets
import time
from pathlib import Path
from shutil import copy2
from typing import Any, Callable
from xml.etree import ElementTree as ET

from .group_membership import (
    GroupMembershipProviderError,
    GroupMembershipProviderUnavailable,
    ImportExportPathResolver,
    _configured_path,
    _export_transaction,
    _is_loopback_host,
    _timeout_seconds,
)


class SequenceExportParseError(GroupMembershipProviderError):
    """A Sequence export is malformed or cannot be interpreted safely."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node if _local_name(child.tag) == name]


def _child_text(node: ET.Element, name: str) -> str | None:
    child = next((item for item in node if _local_name(item.tag) == name), None)
    return None if child is None else (child.text if child.text is not None else "")


def _address(node: ET.Element | None) -> dict[str, Any] | None:
    if node is None:
        return None
    components = [_child.text if _child.text is not None else "" for _child in node if _local_name(_child.tag) == "No"]
    result: dict[str, Any] = {"no_components": components}
    if "name" in node.attrib:
        result["name"] = node.attrib["name"]
    if components or "name" in node.attrib:
        display = ".".join(components)
        if "name" in node.attrib:
            display += f' "{node.attrib["name"]}"'
        result["display"] = display
    return result


def _raw_fields(node: ET.Element, names: tuple[str, ...]) -> dict[str, str | None]:
    return {name: _child_text(node, name) for name in names}


def sequence_export_discovery(xml: str | bytes, sequence_no: int) -> dict[str, Any]:
    """Parse only fields selected by MA2's shipped tracking-sheet XSL.

    Numeric values remain raw exported strings.  No unit, DMX, percentage, or
    normalization claim is made here.
    """
    if isinstance(sequence_no, bool) or not isinstance(sequence_no, int) or sequence_no < 1:
        raise ValueError("Sequence export requires a positive sequence number.")
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SequenceExportParseError("EXPORT_SEQUENCE_XML_MALFORMED") from exc

    sequencers = [node for node in root.iter() if _local_name(node.tag) == "Sequ"]
    if not sequencers:
        return {
            "schema": "zen.sequence_export_discovery.v0.1", "read_only": True,
            "sequence_no": sequence_no, "status": "UNSUPPORTED",
            "reason": "SEQU_STRUCTURE_ABSENT", "cues": [],
            "source": "MA2_EXPORT_SEQUENCE_XML",
            "xml_discovery": {"sha256": hashlib.sha256(raw).hexdigest(), "root": _local_name(root.tag)},
        }

    sequ = sequencers[0]
    cues: list[dict[str, Any]] = []
    partial = False
    for cue in _children(sequ, "Cue"):
        if any(_local_name(key) == "nil" and str(value).lower() in {"true", "1"}
               for key, value in cue.attrib.items()):
            continue
        number = next((child for child in cue if _local_name(child.tag) == "Number"), None)
        number_info = None
        if number is not None:
            number_info = {
                "number": number.get("number"),
                "sub_number": number.get("sub_number"),
            }
            if number.get("number") is None:
                partial = True
        else:
            partial = True
        cue_parts = _children(cue, "CuePart")
        cue_datas = next((child for child in cue if _local_name(child.tag) == "CueDatas"), None)
        if cue_datas is None:
            partial = True
        parts: list[dict[str, Any]] = []
        for part in cue_parts:
            index = part.get("index")
            part_info: dict[str, Any] = {"index": index, "name": part.get("name")}
            if index is None:
                partial = True
            rows: list[dict[str, Any]] = []
            if cue_datas is not None:
                for data in _children(cue_datas, "CueData"):
                    if data.get("value_multipart_index") != index and data.get("effect_multipart_index") != index:
                        continue
                    channel = next((child for child in data if _local_name(child.tag) == "Channel"), None)
                    row: dict[str, Any] = {
                        "multipart_indexes": {
                            "value": data.get("value_multipart_index"),
                            "effect": data.get("effect_multipart_index"),
                        },
                        "channel": None if channel is None else {
                            key: channel.attrib[key]
                            for key in ("fixture_id", "channel_id", "subfixture_id", "attribute_name")
                            if key in channel.attrib
                        },
                        "raw_values": _raw_fields(data, ("Value", "Fade", "Delay", "EffectFlags", "EffectRate", "EffectLow", "EffectHigh", "EffectPhase", "EffectWidth")),
                        "preset": _address(next((child for child in data if _local_name(child.tag) == "Preset"), None)),
                        "effect": _address(next((child for child in data if _local_name(child.tag) == "Effect"), None)),
                        "effect_low_preset": _address(next((child for child in data if _local_name(child.tag) == "EffectLowPreset"), None)),
                        "effect_high_preset": _address(next((child for child in data if _local_name(child.tag) == "EffectHighPreset"), None)),
                    }
                    if channel is None:
                        partial = True
                    rows.append(row)
            part_info["cue_data"] = rows
            parts.append(part_info)
        if not cue_parts:
            partial = True
        cues.append({"number": number_info, "parts": parts})

    status = "PARTIAL" if partial else "VERIFIED"
    return {
        "schema": "zen.sequence_export_discovery.v0.1", "read_only": True,
        "sequence_no": sequence_no, "status": status, "source": "MA2_EXPORT_SEQUENCE_XML",
        "cues": cues,
        "xml_discovery": {"sha256": hashlib.sha256(raw).hexdigest(), "root": _local_name(root.tag)},
    }


class SequenceExportProvider:
    """Loopback onPC Export Sequence -> stable XML -> typed discovery."""

    source = "ma2_export_sequence_xml"
    _temporary_name = re.compile(r"^ZEN_AGENT_SEQUENCE_[1-9]\d*_[A-Za-z0-9_-]{1,64}\.xml$")

    def __init__(self, resolver: ImportExportPathResolver | None = None, *, request_id_factory: Callable[[], str] | None = None, wall_clock_ns: Callable[[], int] = time.time_ns, monotonic_clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep, poll_seconds: float = 0.05) -> None:
        self.resolver = resolver or ImportExportPathResolver()
        self.request_id_factory = request_id_factory or (lambda: secrets.token_hex(8))
        self.wall_clock_ns, self.monotonic_clock, self.sleep, self.poll_seconds = wall_clock_ns, monotonic_clock, sleep, poll_seconds

    def capabilities(self, runtime: Any, settings: object) -> dict[str, object]:
        local = _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", ""))
        try:
            path = self.resolver.resolve(_configured_path(settings)) if local else None
        except GroupMembershipProviderUnavailable:
            path = None
        return {"backend": "local_export_file", "local_onpc_status": "LOCAL_ONPC_SUPPORTED" if path else "LOCAL_ONPC_UNAVAILABLE", "remote_console_status": "REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM", "local_export_access": bool(path), "importexport_path": str(path) if path else None, "sequence_xml_schema": "REAL_MACHINE_PARTIAL_CONTENT_PATH_VERIFIED"}

    def export_and_discover(self, runtime: Any, sequence_no: int, settings: object, *, retain_export: bool = False) -> dict[str, Any]:
        if isinstance(sequence_no, bool) or not isinstance(sequence_no, int) or sequence_no < 1:
            raise ValueError("Sequence export requires a positive sequence number.")
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM")
        directory = self.resolver.resolve(_configured_path(settings))
        request_id = self.request_id_factory()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", request_id):
            raise SequenceExportParseError("INVALID_EXPORT_REQUEST_ID")
        filename = f"ZEN_AGENT_SEQUENCE_{sequence_no}_{request_id}.xml"
        path = directory / filename
        started_at_ns = self.wall_clock_ns()
        feedback: str | None = None
        try:
            with _export_transaction(runtime):
                self._remove_owned_stale(path, directory)
                started_at_ns = self.wall_clock_ns()
                feedback = runtime.export_sequence_file(sequence_no, filename)
                raw = self._wait_for_fresh_stable_xml(path, _timeout_seconds(settings))
                result = sequence_export_discovery(raw, sequence_no)
                if retain_export:
                    self._retain_copy(runtime, path, filename)
        except (SequenceExportParseError, GroupMembershipProviderError, OSError) as exc:
            self._record_diagnostic(runtime, path, sequence_no, filename, started_at_ns, feedback, str(exc))
            raise exc if isinstance(exc, GroupMembershipProviderError) else SequenceExportParseError(str(exc)) from exc
        else:
            self._cleanup(path, directory)
        result["export"] = {"filename": filename, "ma2_feedback": feedback, "cleanup": "AGENT_OWNED_TEMPORARY_FILE_REMOVED"}
        runtime.log("sequence_export_discovery", {"sequence_no": sequence_no, "filename": filename, "retain_export": retain_export, "status": result["status"]})
        return result

    def _wait_for_fresh_stable_xml(self, path: Path, timeout_seconds: float) -> bytes:
        deadline = self.monotonic_clock() + timeout_seconds
        previous: tuple[int, int] | None = None
        stable = 0
        malformed = False
        while self.monotonic_clock() <= deadline:
            try:
                stat = path.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
                if path.is_file() and stat.st_size > 0:
                    stable = stable + 1 if signature == previous else 1
                    previous = signature
                    if stable >= 2:
                        raw = path.read_bytes()
                        if (path.stat().st_mtime_ns, path.stat().st_size) != signature:
                            previous, stable = None, 0
                        else:
                            try: ET.fromstring(raw)
                            except ET.ParseError: malformed = True
                            else: return raw
            except OSError:
                pass
            self.sleep(self.poll_seconds)
        raise SequenceExportParseError("EXPORT_SEQUENCE_XML_MALFORMED" if malformed else "EXPORT_FILE_TIMEOUT")

    def _remove_owned_stale(self, path: Path, directory: Path) -> None:
        if path.parent.resolve() == directory.resolve() and self._temporary_name.fullmatch(path.name) and path.exists():
            path.unlink()

    def _cleanup(self, path: Path, directory: Path) -> None:
        if path.parent.resolve() == directory.resolve() and self._temporary_name.fullmatch(path.name):
            path.unlink(missing_ok=True)

    def _retain_copy(self, runtime: Any, path: Path, filename: str) -> None:
        root = getattr(runtime, "root", None)
        if not isinstance(root, Path):
            return
        target = root / "cache" / "sequence_export_diagnostics" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        copy2(path, target)

    def _record_diagnostic(self, runtime: Any, path: Path, sequence_no: int, filename: str, started_at_ns: int, feedback: str | None, error: str) -> None:
        details: dict[str, Any] = {"sequence_no": sequence_no, "filename": filename, "actual_file_path": str(path), "request_started_at_ns": started_at_ns, "ma2_feedback": feedback, "error": error}
        if path.is_file():
            try:
                raw = path.read_bytes()
                details.update({"byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "xml_well_formed": True})
                ET.fromstring(raw)
            except (OSError, ET.ParseError):
                details["xml_well_formed"] = False
            root = getattr(runtime, "root", None)
            if isinstance(root, Path):
                target = root / "logs" / "sequence_export_diagnostics" / filename
                try:
                    target.parent.mkdir(parents=True, exist_ok=True); copy2(path, target); details["diagnostic_copy_path"] = str(target)
                except OSError as exc:
                    details["diagnostic_capture_error"] = exc.__class__.__name__
        log = getattr(runtime, "log", None)
        if callable(log): log("sequence_export_diagnostic", details)
