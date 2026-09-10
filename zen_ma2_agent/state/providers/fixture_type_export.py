"""Read-only binding of a current-show FixtureType to its exported channels.

grandMA2's native ``Export FixtureType`` exports the FixtureType object held by
the loaded Show into the local library.  This provider deliberately requires
an exact identity check between the current ``List Fixture`` type label and
that exported object before it exposes any channel-derived capability.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import secrets
import time
from pathlib import Path
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


class FixtureTypeExportError(GroupMembershipProviderError):
    """The read-only FixtureType export did not prove a safe binding."""


_TYPE_LABEL = re.compile(r"^(?P<fixture_type_id>[1-9]\d*)\s+(?P<label>\S(?:.*\S)?)$")
_TEMPORARY_NAME = re.compile(r"^ZEN_AGENT_FT_[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml$")
_VOLATILE_XML_TAGS = frozenset({"Info", "InfoItems"})


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def fixture_type_reference_from_list_label(value: object) -> dict[str, Any]:
    """Extract only the explicitly displayed FixtureType pool number.

    The full label remains authoritative.  The parser never attempts to split
    a human-readable FixtureType name from its mode, because neither boundary
    is reliable in arbitrary names.
    """
    label = str(value or "").strip()
    match = _TYPE_LABEL.fullmatch(label)
    if not match:
        raise FixtureTypeExportError("FIXTURE_TYPE_LIST_ID_UNAVAILABLE")
    return {"fixture_type_id": int(match.group("fixture_type_id")), "list_label": label}


def _display_label(fixture_type_id: int, name: str | None, mode: str | None) -> str:
    values = [str(fixture_type_id), str(name or "").strip(), str(mode or "").strip()]
    return " ".join(value for value in values if value)


def _profile_xml(raw: str | bytes) -> bytes:
    value = raw.encode("utf-8") if isinstance(raw, str) else raw
    if value.startswith(b"\x1f\x8b"):
        try:
            return gzip.decompress(value)
        except OSError as exc:
            raise FixtureTypeExportError("FIXTURE_TYPE_PROFILE_GZIP_MALFORMED") from exc
    return value


def _channel_records(fixture_type: ET.Element) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for node in fixture_type.iter():
        if _local_name(node.tag) != "ChannelType":
            continue
        functions = []
        for child in node:
            if _local_name(child.tag) == "ChannelFunction":
                functions.append({key: child.attrib[key] for key in sorted(child.attrib)})
        records.append({
            "index": node.get("index"),
            "attribute": node.get("attribute"),
            "feature": node.get("feature"),
            "preset": node.get("preset"),
            "channel_fields": {key: node.attrib[key] for key in sorted(node.attrib)},
            "functions": functions,
        })
    return sorted(records, key=lambda item: (str(item["index"]), str(item["attribute"]), str(item["feature"])))


def _technical_definition_fingerprint(channels: list[dict[str, Any]]) -> str:
    """Fingerprint all parsed channel/function definitions, not labels or dates."""
    canonical = json.dumps(channels, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _capability_inventory(channels: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    tokens = {
        "attributes": {str(item.get("attribute") or "").upper() for item in channels},
        "features": {str(item.get("feature") or "").upper() for item in channels},
        "presets": {str(item.get("preset") or "").upper() for item in channels},
    }

    def any_token(*values: str) -> bool:
        return any(value in tokens[where] for where in tokens for value in values)

    def contains(value: str) -> bool:
        return any(value in token for where in tokens for token in tokens[where])

    def state(present: bool) -> dict[str, Any]:
        return {
            "status": "SHOW_BOUND_VERIFIED" if present else "NOT_PRESENT_IN_EXPORTED_PROFILE",
            "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
        }

    pan = any_token("PAN")
    tilt = any_token("TILT")
    return {
        "DIMMER": state(any_token("DIM", "DIMMER") or "DIMMER" in tokens["features"] or "DIMMER" in tokens["presets"]),
        "COLOR": state(any(value.startswith("COLOR") for where in tokens for value in tokens[where]) or "COLOR" in tokens["presets"]),
        "PAN": state(pan),
        "TILT": state(tilt),
        "POSITION": state(pan and tilt),
        "GOBO": state(contains("GOBO") or "GOBO" in tokens["presets"]),
        "PRISM": state(contains("PRISM")),
        "ZOOM": state(any_token("ZOOM")),
        "FOCUS": state(any_token("FOCUS")),
        "FROST": state(any_token("FROST")),
        "SHUTTER_STROBE": state(any_token("SHUTTER", "STROBEMODE", "STROBEDURATION") or contains("STROBE")),
        # A generic ChannelType inventory has no safe universal definition of
        # pixel topology or shape behavior.  Keep that distinction explicit.
        "PIXEL_SHAPE": {
            "status": "UNCLASSIFIED_FROM_CHANNEL_INVENTORY",
            "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
            "reason": "Pixel/shape topology requires a separately verified FixtureType schema interpretation.",
        },
    }


def fixture_type_export_binding(xml: str | bytes, fixture_type_label: object) -> dict[str, Any]:
    """Validate one native FixtureType export against one current-show label."""
    expected = fixture_type_reference_from_list_label(fixture_type_label)
    raw = _profile_xml(xml)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_XML_MALFORMED") from exc
    if _local_name(root.tag) != "MA":
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_ROOT_UNSUPPORTED")
    types = [node for node in root.iter() if _local_name(node.tag) == "FixtureType"]
    if len(types) != 1:
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_COUNT_MISMATCH")
    fixture_type = types[0]
    raw_index = fixture_type.get("index")
    if raw_index is None or not raw_index.isdecimal() or int(raw_index) != expected["fixture_type_id"]:
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_ID_MISMATCH")
    exported_label = _display_label(expected["fixture_type_id"], fixture_type.get("name"), fixture_type.get("mode"))
    if exported_label != expected["list_label"]:
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_LABEL_MISMATCH")
    channels = _channel_records(fixture_type)
    if not channels:
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_CHANNELS_NOT_PRESENT")
    return {
        "schema": "zen.fixture_type_channel_profile.v0.1",
        "read_only": True,
        "status": "SHOW_BOUND_VERIFIED",
        "source": "MA2_EXPORT_FIXTURE_TYPE_XML",
        "fixture_type": {
            **expected,
            "xml_index": int(raw_index),
            "name": fixture_type.get("name"),
            "mode": fixture_type.get("mode"),
            "ma_version": {
                "major": root.get("major_vers"),
                "minor": root.get("minor_vers"),
                "stream": root.get("stream_vers"),
            },
        },
        "channels": channels,
        "capabilities": _capability_inventory(channels),
        "technical_definition_sha256": _technical_definition_fingerprint(channels),
        "xml_sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw),
    }


def bind_local_profile_candidate(show_bound: dict[str, Any], local_profile_xml: str | bytes) -> dict[str, Any]:
    """Bind a local candidate only by exact parsed channel-definition identity."""
    if show_bound.get("status") != "SHOW_BOUND_VERIFIED":
        raise FixtureTypeExportError("SHOW_BOUND_PROFILE_REQUIRED")
    raw = _profile_xml(local_profile_xml)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise FixtureTypeExportError("LOCAL_PROFILE_XML_MALFORMED") from exc
    types = [node for node in root.iter() if _local_name(node.tag) == "FixtureType"]
    if len(types) != 1:
        raise FixtureTypeExportError("LOCAL_PROFILE_FIXTURE_TYPE_COUNT_MISMATCH")
    channels = _channel_records(types[0])
    candidate_hash = _technical_definition_fingerprint(channels)
    return {
        "status": "LOCAL_PROFILE_CANDIDATE_BOUND" if candidate_hash == show_bound["technical_definition_sha256"] else "LOCAL_PROFILE_CANDIDATE_UNBOUND",
        "source": "STRUCTURAL_CHANNEL_DEFINITION_COMPARISON",
        "show_bound_technical_definition_sha256": show_bound["technical_definition_sha256"],
        "local_candidate_technical_definition_sha256": candidate_hash,
        "local_candidate_xml_sha256": hashlib.sha256(raw).hexdigest(),
    }


class FixtureTypeExportProvider:
    """Loopback-only native Export FixtureType -> exact Show-bound XML parser."""

    source = "ma2_export_fixture_type_xml"

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

    def capabilities(self, runtime: Any, settings: object) -> dict[str, Any]:
        local = _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", ""))
        try:
            directory = self.resolver.resolve_library(_configured_path(settings)) if local else None
        except GroupMembershipProviderUnavailable:
            directory = None
        return {
            "backend": "native_export_fixture_type_file",
            "read_only_show_operation": "Export FixtureType",
            "local_export_access": bool(directory),
            "fixture_type_library_path": str(directory) if directory else None,
            "remote_console_status": "REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM",
            "real_console_status": "REAL_CONSOLE_VERIFICATION_REQUIRED",
        }

    def export_and_bind(self, runtime: Any, fixture_type_label: object, settings: object) -> dict[str, Any]:
        identity = fixture_type_reference_from_list_label(fixture_type_label)
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_CONSOLE_BLOCKED_BY_FILESYSTEM")
        directory = self.resolver.resolve_library(_configured_path(settings))
        request_id = self.request_id_factory()
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", request_id):
            raise FixtureTypeExportError("INVALID_EXPORT_REQUEST_ID")
        filename = f"ZEN_AGENT_FT_{identity['fixture_type_id']}_{request_id}.xml"
        path = directory / filename
        started_at_ns = self.wall_clock_ns()
        feedback: str | None = None
        try:
            with _export_transaction(runtime):
                self._remove_owned_stale(path, directory)
                started_at_ns = self.wall_clock_ns()
                feedback = runtime.export_fixture_type_file(identity["fixture_type_id"], filename)
                raw = self._wait_for_fresh_stable_xml(path, started_at_ns, _timeout_seconds(settings))
                result = fixture_type_export_binding(raw, identity["list_label"])
        except (OSError, GroupMembershipProviderError) as exc:
            error = str(exc) if isinstance(exc, GroupMembershipProviderError) else "EXPORT_FILE_ACCESS_ERROR"
            self._record_diagnostic(runtime, path, identity, filename, started_at_ns, feedback, error)
            raise FixtureTypeExportError(error) from exc
        finally:
            self._cleanup(path, directory)
        result["export"] = {
            "filename": filename,
            "ma2_feedback": feedback,
            "cleanup": "AGENT_OWNED_TEMPORARY_FILE_REMOVED",
        }
        runtime.log("fixture_type_export_binding", {"fixture_type": identity, "status": result["status"], "channel_count": len(result["channels"])})
        return result

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
                                ET.fromstring(_profile_xml(raw))
                            except (ET.ParseError, FixtureTypeExportError):
                                malformed = True
                            else:
                                return raw
            except OSError:
                pass
            self.sleep(self.poll_seconds)
        raise FixtureTypeExportError("EXPORT_FIXTURE_TYPE_XML_MALFORMED" if malformed else "EXPORT_FILE_TIMEOUT")

    @staticmethod
    def _cleanup(path: Path, directory: Path) -> None:
        try:
            if path.parent.resolve() == directory.resolve() and _TEMPORARY_NAME.fullmatch(path.name):
                path.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _remove_owned_stale(path: Path, directory: Path) -> None:
        if path.exists() and path.parent.resolve() == directory.resolve() and _TEMPORARY_NAME.fullmatch(path.name):
            path.unlink()

    @staticmethod
    def _record_diagnostic(runtime: Any, path: Path, identity: dict[str, Any], filename: str, started_at_ns: int, feedback: str | None, error: str) -> None:
        log = getattr(runtime, "log", None)
        if callable(log):
            log("fixture_type_export_diagnostic", {
                "fixture_type": identity,
                "filename": filename,
                "actual_file_path": str(path),
                "request_started_at_ns": started_at_ns,
                "ma2_feedback": feedback,
                "error": error,
            })
