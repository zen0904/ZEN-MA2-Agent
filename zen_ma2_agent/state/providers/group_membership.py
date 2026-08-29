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
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable

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
        if path.exists():
            raise GroupMembershipProviderError("EXPORT_FILE_NAME_COLLISION")

        started_at_ns = self.wall_clock_ns()
        try:
            runtime.export_group_file(group_no, filename)
            self._wait_for_fresh_file(path, started_at_ns, _timeout_seconds(settings))
            parsed = group_membership_from_export(path, group_no)
        except GroupExportParseError as exc:
            raise GroupMembershipProviderError(str(exc)) from exc
        except OSError as exc:
            raise GroupMembershipProviderError("EXPORT_FILE_ACCESS_ERROR") from exc

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

    def _wait_for_fresh_file(self, path: Path, started_at_ns: int, timeout_seconds: float) -> None:
        deadline = self.monotonic_clock() + timeout_seconds
        while self.monotonic_clock() <= deadline:
            try:
                if path.is_file() and path.stat().st_mtime_ns >= started_at_ns:
                    return
            except OSError:
                pass
            self.sleep(self.poll_seconds)
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
