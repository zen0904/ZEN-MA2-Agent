"""Read-only Group membership provider backends.

The export-file backend is intentionally separate from the Lua mailbox. It is
only usable when the Agent and MA2 share an accessible importexport filesystem.
"""

from __future__ import annotations

import ipaddress
import os
import re
import secrets
import subprocess
import time
from contextlib import contextmanager, nullcontext
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree as ET
from shutil import copy2

from .group_export import GroupExportParseError, group_membership_from_export


class GroupMembershipProviderError(RuntimeError):
    """A Group membership backend could not return a verified result."""


class GroupMembershipProviderUnavailable(GroupMembershipProviderError):
    """The selected backend cannot safely operate in this environment."""


class GroupMembershipProvider(ABC):
    """Frontend-independent Group membership backend contract."""

    source: str

    @abstractmethod
    def get_group_membership(self, runtime: Any, group_no: int, settings: object) -> dict[str, Any]:
        """Return a verified membership model or raise a typed provider error."""


class ImportExportPathResolver:
    """Find MA2's active local importexport directory without a fixed version."""

    _version_dir = re.compile(r"^gma2_V_(\d+)\.(\d+)\.(\d+)$", re.I)
    _onpc_version = re.compile(r"(\d+\.\d+\.\d+)")

    def __init__(
        self,
        program_data: Path | None = None,
        running_onpc_paths: Callable[[], list[Path]] | None = None,
    ) -> None:
        base = program_data or Path(os.environ.get("PROGRAMDATA", r"C:\\ProgramData"))
        self.grandma_root = base / "MA Lighting Technologies" / "grandma"
        self.running_onpc_paths = running_onpc_paths or self._running_onpc_paths

    def resolve(self, configured_path: object = "auto") -> Path:
        value = "auto" if configured_path in (None, "") else str(configured_path).strip()
        if value.casefold() != "auto":
            path = Path(value).expanduser()
            if not path.is_dir():
                raise GroupMembershipProviderUnavailable("IMPORTEXPORT_PATH_UNAVAILABLE")
            return path.resolve()

        candidates = self._candidates()
        if not candidates:
            raise GroupMembershipProviderUnavailable("IMPORTEXPORT_PATH_UNAVAILABLE")
        for onpc_path in self.running_onpc_paths():
            match = self._onpc_version.search(str(onpc_path))
            if not match:
                continue
            version = tuple(int(part) for part in match.group(1).split("."))
            if version in candidates:
                return candidates[version]
        return candidates[max(candidates)]

    def _candidates(self) -> dict[tuple[int, int, int], Path]:
        if not self.grandma_root.is_dir():
            return {}
        result: dict[tuple[int, int, int], Path] = {}
        for child in self.grandma_root.iterdir():
            match = self._version_dir.fullmatch(child.name)
            export_dir = child / "importexport"
            if match and export_dir.is_dir():
                result[tuple(int(part) for part in match.groups())] = export_dir.resolve()
        return result

    @staticmethod
    def _running_onpc_paths() -> list[Path]:
        if os.name != "nt":
            return []
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", "(Get-Process -Name gma2onpc -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Path)"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


class ExportFileGroupMembershipProvider(GroupMembershipProvider):
    """Local onPC backend: Export Group → wait for XML → parse → clean up."""

    source = "ma2_export_xml"
    _temporary_name = re.compile(r"^ZEN_AGENT_G[1-9]\d*_[A-Za-z0-9_-]{6,64}\.xml$")

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
        configured_path = _configured_path(settings)
        local_host = _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", ""))
        try:
            path = self.resolver.resolve(configured_path) if local_host else None
        except GroupMembershipProviderUnavailable:
            path = None
        return {
            "backend": "local_export_file",
            "local_export_access": bool(local_host and path),
            "importexport_path": str(path) if path else None,
        }

    def get_group_membership(self, runtime: Any, group_no: int, settings: object) -> dict[str, Any]:
        if isinstance(group_no, bool) or not isinstance(group_no, int) or group_no < 1:
            raise ValueError("Group membership requires a positive group number.")
        if not _is_loopback_host(runtime.preferences.get("ma2", {}).get("host", "")):
            raise GroupMembershipProviderUnavailable("REMOTE_EXPORT_ACCESS_UNAVAILABLE")
        export_dir = self.resolver.resolve(_configured_path(settings))
        request_id = self.request_id_factory()
        filename = self._filename(group_no, request_id)
        path = export_dir / filename
        started_at_ns = self.wall_clock_ns()
        feedback: str | None = None
        try:
            with _export_transaction(runtime):
                self._remove_owned_stale(path, export_dir)
                started_at_ns = self.wall_clock_ns()
                feedback = runtime.export_group_file(group_no, filename)
                xml = self._wait_for_fresh_stable_xml(path, started_at_ns, _timeout_seconds(settings))
                parsed = group_membership_from_export(xml, group_no)
        except GroupExportParseError as exc:
            error = GroupMembershipProviderError(str(exc))
            self._record_failed_export(runtime, path, export_dir, group_no, request_id, filename, started_at_ns, feedback, str(error))
            raise error from exc
        except GroupMembershipProviderError as exc:
            self._record_failed_export(runtime, path, export_dir, group_no, request_id, filename, started_at_ns, feedback, str(exc))
            raise
        except OSError as exc:
            error = GroupMembershipProviderError("EXPORT_FILE_ACCESS_ERROR")
            self._record_failed_export(runtime, path, export_dir, group_no, request_id, filename, started_at_ns, feedback, str(error))
            raise error from exc

        self._cleanup(path, export_dir)
        fixtures = list(parsed["fixtures"])
        return {
            "group_no": group_no,
            "name": parsed["name"],
            "group_name": parsed["name"],
            "fixtures": fixtures,
            "members": [{"fix_id": fix_id, "export_order": index} for index, fix_id in enumerate(fixtures)],
            "source": self.source,
        }

    def _wait_for_fresh_stable_xml(self, path: Path, started_at_ns: int, timeout_seconds: float) -> bytes:
        """Wait for a new, stable, well-formed MA2 Export file.

        The exporter can create the destination before its XML has finished
        writing.  A candidate must be fresh, non-empty, unchanged across two
        polls, and XML-well-formed before the membership parser sees it.
        """
        deadline = self.monotonic_clock() + timeout_seconds
        last_signature: tuple[int, int] | None = None
        stable_polls = 0
        saw_stable_malformed = False
        while self.monotonic_clock() <= deadline:
            try:
                stat = path.stat()
                if path.is_file() and stat.st_mtime_ns >= started_at_ns and stat.st_size > 0:
                    signature = (stat.st_mtime_ns, stat.st_size)
                    stable_polls = stable_polls + 1 if signature == last_signature else 1
                    last_signature = signature
                    if stable_polls >= 2:
                        xml = path.read_bytes()
                        after_read = path.stat()
                        if (after_read.st_mtime_ns, after_read.st_size) != signature:
                            stable_polls = 0
                            last_signature = None
                        else:
                            try:
                                ET.fromstring(xml)
                            except ET.ParseError:
                                saw_stable_malformed = True
                            else:
                                return xml
            except OSError:
                pass
            self.sleep(self.poll_seconds)
        if saw_stable_malformed:
            raise GroupMembershipProviderError("EXPORT_XML_MALFORMED")
        raise GroupMembershipProviderError("EXPORT_FILE_TIMEOUT")

    def _filename(self, group_no: int, request_id: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", request_id):
            raise GroupMembershipProviderError("INVALID_EXPORT_REQUEST_ID")
        return f"ZEN_AGENT_G{group_no}_{request_id}.xml"

    def _cleanup(self, path: Path, export_dir: Path) -> None:
        try:
            if path.parent.resolve() == export_dir.resolve() and self._temporary_name.fullmatch(path.name):
                path.unlink(missing_ok=True)
        except OSError:
            # Cleanup is best-effort; a verified parse result remains valid.
            pass

    def _remove_owned_stale(self, path: Path, export_dir: Path) -> None:
        """Remove only this provider's stale request file before Export."""
        if path.exists() and path.parent.resolve() == export_dir.resolve() and self._temporary_name.fullmatch(path.name):
            path.unlink()

    def _record_failed_export(
        self,
        runtime: Any,
        path: Path,
        export_dir: Path,
        group_no: int,
        request_id: str,
        filename: str,
        started_at_ns: int,
        feedback: str | None,
        error: str,
    ) -> None:
        """Keep a bounded, Agent-owned diagnostic copy without changing MA2."""
        details: dict[str, Any] = {
            "group_no": group_no,
            "request_id": request_id,
            "export_command": f'Export Group {group_no} "{filename}" /nc',
            "expected_temp_filename": filename,
            "actual_file_path": str(path),
            "request_started_at_ns": started_at_ns,
            "ma_feedback": feedback,
            "error": error,
        }
        if path.is_file():
            try:
                stat = path.stat()
                raw = path.read_bytes()
                details.update({"file_size": stat.st_size, "mtime_ns": stat.st_mtime_ns, **self._xml_diagnostics(raw)})
                root = getattr(runtime, "root", None)
                if isinstance(root, Path):
                    retained = root / "logs" / "group_export_diagnostics" / filename
                    retained.parent.mkdir(parents=True, exist_ok=True)
                    copy2(path, retained)
                    details["diagnostic_copy_path"] = str(retained)
            except OSError as exc:
                details["diagnostic_capture_error"] = exc.__class__.__name__
        log = getattr(runtime, "log", None)
        if callable(log):
            log("group_export_diagnostic", details)

    @staticmethod
    def _xml_diagnostics(raw: bytes) -> dict[str, Any]:
        sample = raw.decode("utf-8", errors="replace")[:2048]
        sample = re.sub(r'(showfile=")[^"]*(")', r'\1[redacted]\2', sample, flags=re.I)
        details: dict[str, Any] = {"raw_xml_sample": sample, "xml_well_formed": False}
        try:
            root = ET.fromstring(raw)
        except ET.ParseError:
            return details
        groups = [item for item in root.iter() if item.tag.rsplit("}", 1)[-1] == "Group"]
        tags = sorted({item.tag.rsplit("}", 1)[-1] for item in root.iter()})
        details.update({
            "xml_well_formed": True,
            "xml_root": root.tag.rsplit("}", 1)[-1],
            "xml_tags": tags,
            "group_indexes": [item.get("index") for item in groups],
            "has_subfixtures": any(any(child.tag.rsplit("}", 1)[-1] == "Subfixtures" for child in group) for group in groups),
            "membership_like_nodes": sorted({item.tag.rsplit("}", 1)[-1] for item in root.iter() if re.search(r"fixture|member|selection", item.tag.rsplit("}", 1)[-1], re.I)}),
        })
        return details


@contextmanager
def _export_transaction(runtime: Any):
    transaction = getattr(runtime, "export_transaction", None)
    if callable(transaction):
        with transaction():
            yield
    else:
        with nullcontext():
            yield


def _configured_path(settings: object) -> object:
    return settings.get("importexport_path", "auto") if isinstance(settings, dict) else "auto"


def _timeout_seconds(settings: object) -> float:
    try:
        timeout = float((settings or {}).get("timeout_seconds", 3.0)) if isinstance(settings, dict) else 3.0
    except (TypeError, ValueError) as exc:
        raise ValueError("Export timeout must be numeric.") from exc
    if not 0.1 <= timeout <= 30:
        raise ValueError("Export timeout must be from 0.1 to 30 seconds.")
    return timeout


def _is_loopback_host(host: object) -> bool:
    value = str(host).strip().casefold()
    if value == "localhost":
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False
