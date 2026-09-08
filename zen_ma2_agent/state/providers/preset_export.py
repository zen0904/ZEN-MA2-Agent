"""Guarded local-onPC Preset export discovery.

This module deliberately does *not* claim a grandMA2 Preset XML schema.  It
acquires one real export safely and describes the XML structure.  Observations
remain empty until a real grandMA2 3.9 sample proves Fixture, Attribute, and
value semantics.
"""

from __future__ import annotations

import hashlib
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


class PresetExportError(GroupMembershipProviderError):
    """A Preset export could not be safely acquired or diagnosed."""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def preset_export_discovery(xml: str | bytes, preset_ref: str) -> dict[str, Any]:
    """Describe actual XML without guessing MA2 data semantics.

    A well-formed, unknown document always returns zero observations.  It must
    not equate XML indices with Fixture IDs or any numeric value with DMX.
    """
    reference = str(preset_ref).strip()
    if not re.fullmatch(r"[1-9]\d*\.[1-9]\d*", reference):
        raise ValueError("Preset reference must be numeric type.id.")
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise PresetExportError("EXPORT_PRESET_XML_MALFORMED") from exc
    paths: set[str] = set()
    attributes: dict[str, set[str]] = {}

    def walk(node: ET.Element, prefix: str) -> None:
        name = _local_name(node.tag)
        path = f"{prefix}/{name}" if prefix else name
        paths.add(path)
        attributes.setdefault(name, set()).update(node.attrib)
        for child in node:
            walk(child, path)

    walk(root, "")
    preset_type_id, preset_number = (int(part) for part in reference.split("."))
    presets = [node for node in root if _local_name(node.tag) == "Preset"]
    ma2_3960 = (
        _local_name(root.tag) == "MA"
        and root.get("major_vers") == "3"
        and root.get("minor_vers") == "9"
        and root.get("stream_vers") == "60"
    )
    if ma2_3960 and len(presets) == 1:
        preset = presets[0]
        raw_index = preset.get("index")
        if raw_index is None or not raw_index.isdecimal() or int(raw_index) != preset_number - 1:
            raise PresetExportError("EXPORT_PRESET_NUMBER_MISMATCH")
        # This exact real-MA2 sample contains no Fixture, Attribute, or value
        # children.  Treat that as a positive capability result, not an empty
        # preset or an invitation to infer content from an internal index.
        if list(preset):
            schema_status = "PRESET_CONTENT_SCHEMA_UNVERIFIED"
            content_status = "UNPARSED_CHILDREN_PRESENT"
        else:
            schema_status = "METADATA_ONLY_REAL_MA2_3_9_60"
            content_status = "NOT_PRESENT_IN_EXPORT"
        return {
            "schema": "zen.preset_observations.v0.1",
            "read_only": True,
            "preset": {
                "id": reference,
                "name": preset.get("name") or None,
                "preset_type": None,
                "preset_type_id": preset_type_id,
                "xml_index": int(raw_index),
                "source": "MA2_EXPORT_PRESET_XML",
                "confidence": "VERIFIED_SOURCE",
            },
            "observations": [],
            "source": "MA2_EXPORT_PRESET_XML",
            "status": schema_status,
            "content_status": content_status,
            "capabilities": {
                "fixture_identity": "NOT_PRESENT_IN_EXPORT",
                "subfixture_identity": "NOT_PRESENT_IN_EXPORT",
                "attribute_identity": "NOT_PRESENT_IN_EXPORT",
                "stored_value": "NOT_PRESENT_IN_EXPORT",
                "raw_dmx": "NOT_PRESENT_IN_EXPORT",
                "decimal16": "NOT_PRESENT_IN_EXPORT",
                "physical_value": "NOT_PRESENT_IN_EXPORT",
            },
            "xml_discovery": {
                "sha256": hashlib.sha256(raw).hexdigest(),
                "root": _local_name(root.tag),
                "element_paths": sorted(paths),
                "attributes_by_element": {name: sorted(names) for name, names in sorted(attributes.items())},
                "byte_length": len(raw),
            },
        }
    return {
        "schema": "zen.preset_observations.v0.1",
        "read_only": True,
        "preset": {"id": reference, "name": None, "preset_type": None},
        "observations": [],
        "source": "MA2_EXPORT_PRESET_XML",
        "status": "SCHEMA_UNVERIFIED",
        "reason": "A real grandMA2 3.9 Preset XML sample is required before Fixture, Attribute, or value fields can be decoded.",
        "xml_discovery": {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "root": _local_name(root.tag),
            "element_paths": sorted(paths),
            "attributes_by_element": {name: sorted(names) for name, names in sorted(attributes.items())},
            "byte_length": len(raw),
        },
    }


class PresetExportProvider:
    """Local onPC: Export Preset -> stable XML -> discovery -> cleanup."""

    source = "ma2_export_preset_xml"
    _temporary_name = re.compile(r"^ZEN_AGENT_PRESET_[1-9]\d*_[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml$")

    def __init__(
        self,
        resolver: ImportExportPathResolver | None = None,
        *,
        request_id_factory: Callable[[], str] | None = None,
        wall_clock_ns: Callable[[], int] = time.time_ns,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        poll_seconds: float = 0.05,
    ) -> None:
        self.resolver = resolver or ImportExportPathResolver()
        self.request_id_factory = request_id_factory or (lambda: secrets.token_hex(8))
        self.wall_clock_ns = wall_clock_ns
        self.monotonic_clock = monotonic_clock
        self.sleep = sleep
        self.poll_seconds = poll_seconds

    def capabilities(self, runtime: Any, settings: object) -> dict[str, object]:
        local = _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", ""))
        try:
            path = self.resolver.resolve(_configured_path(settings)) if local else None
        except GroupMembershipProviderUnavailable:
            path = None
        return {
            "backend": "local_export_file",
            "local_onpc_status": "LOCAL_ONPC_SUPPORTED" if path else "LOCAL_ONPC_UNAVAILABLE",
            "remote_console_status": "REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM",
            "local_export_access": bool(path),
            "importexport_path": str(path) if path else None,
            "preset_xml_schema": "UNVERIFIED",
        }

    def export_and_discover(self, runtime: Any, preset_ref: str, settings: object, *, retain_export: bool = False) -> dict[str, Any]:
        reference = self._reference(preset_ref)
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM")
        directory = self.resolver.resolve(_configured_path(settings))
        filename = self._filename(reference, self.request_id_factory())
        path = directory / filename
        started_at_ns = self.wall_clock_ns()
        feedback: str | None = None
        retained_path: Path | None = None
        try:
            with _export_transaction(runtime):
                self._remove_owned_stale(path, directory)
                started_at_ns = self.wall_clock_ns()
                feedback = runtime.export_preset_file(reference, filename)
                raw = self._wait_for_fresh_stable_xml(path, started_at_ns, _timeout_seconds(settings))
                result = preset_export_discovery(raw, reference)
                if retain_export:
                    retained_path = self._retain_copy(runtime, path, filename)
        except PresetExportError as exc:
            self._record_diagnostic(runtime, path, reference, filename, started_at_ns, feedback, str(exc))
            raise
        except (OSError, GroupMembershipProviderError) as exc:
            error = str(exc) if isinstance(exc, GroupMembershipProviderError) else "EXPORT_FILE_ACCESS_ERROR"
            self._record_diagnostic(runtime, path, reference, filename, started_at_ns, feedback, error)
            raise PresetExportError(error) from exc
        finally:
            self._cleanup(path, directory)
        result["export"] = {
            "filename": filename,
            "ma2_feedback": feedback,
            "retained_copy_path": str(retained_path) if retained_path else None,
            "cleanup": "AGENT_OWNED_TEMPORARY_FILE_REMOVED",
        }
        runtime.log("preset_export_discovery", {"preset_ref": reference, "filename": filename, "retain_export": retain_export, "status": result["status"], "observation_count": 0})
        return result

    @staticmethod
    def _reference(value: object) -> str:
        reference = str(value).strip()
        if not re.fullmatch(r"[1-9]\d*\.[1-9]\d*", reference):
            raise ValueError("Preset export requires a numeric type.id reference.")
        return reference

    def _filename(self, preset_ref: str, request_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", request_id):
            raise PresetExportError("INVALID_EXPORT_REQUEST_ID")
        preset_type, number = preset_ref.split(".")
        return f"ZEN_AGENT_PRESET_{preset_type}_{number}_{request_id}.xml"

    def _wait_for_fresh_stable_xml(self, path: Path, started_at_ns: int, timeout_seconds: float) -> bytes:
        deadline = self.monotonic_clock() + timeout_seconds
        previous: tuple[int, int] | None = None
        stable_polls = 0
        malformed = False
        while self.monotonic_clock() <= deadline:
            try:
                stat = path.stat()
                if path.is_file() and stat.st_mtime_ns >= started_at_ns and stat.st_size > 0:
                    signature = (stat.st_mtime_ns, stat.st_size)
                    stable_polls = stable_polls + 1 if signature == previous else 1
                    previous = signature
                    if stable_polls >= 2:
                        raw = path.read_bytes()
                        after = path.stat()
                        if (after.st_mtime_ns, after.st_size) != signature:
                            previous, stable_polls = None, 0
                        else:
                            try:
                                ET.fromstring(raw)
                            except ET.ParseError:
                                malformed = True
                            else:
                                return raw
            except OSError:
                pass
            self.sleep(self.poll_seconds)
        raise PresetExportError("EXPORT_PRESET_XML_MALFORMED" if malformed else "EXPORT_FILE_TIMEOUT")

    def _retain_copy(self, runtime: Any, source: Path, filename: str) -> Path:
        root = getattr(runtime, "root", None)
        if not isinstance(root, Path):
            raise PresetExportError("DIAGNOSTIC_COPY_UNAVAILABLE")
        target = root / "cache" / "preset_export_diagnostics" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        copy2(source, target)
        return target

    def _cleanup(self, path: Path, directory: Path) -> None:
        try:
            if path.parent.resolve() == directory.resolve() and self._temporary_name.fullmatch(path.name):
                path.unlink(missing_ok=True)
        except OSError:
            pass

    def _remove_owned_stale(self, path: Path, directory: Path) -> None:
        if path.exists() and path.parent.resolve() == directory.resolve() and self._temporary_name.fullmatch(path.name):
            path.unlink()

    def _record_diagnostic(self, runtime: Any, path: Path, preset_ref: str, filename: str, started_at_ns: int, feedback: str | None, error: str) -> None:
        details: dict[str, Any] = {"preset_ref": preset_ref, "filename": filename, "actual_file_path": str(path), "request_started_at_ns": started_at_ns, "ma2_feedback": feedback, "error": error}
        if path.is_file():
            try:
                raw = path.read_bytes()
                details.update({"byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "xml_well_formed": True})
                ET.fromstring(raw)
            except (OSError, ET.ParseError):
                details["xml_well_formed"] = False
        log = getattr(runtime, "log", None)
        if callable(log):
            log("preset_export_diagnostic", details)
