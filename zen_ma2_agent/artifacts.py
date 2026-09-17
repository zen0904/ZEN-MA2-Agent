from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

ARTIFACT_METADATA_SCHEMA = "zen.artifact_metadata.v0.1"
_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


@dataclass(frozen=True)
class ArtifactMetadata:
    artifact_id: str
    request_hash: str
    show_context_hash: Optional[str]
    schema_version: str
    created_at: str
    source_worker_id: Optional[str]
    producer_version: str

    def to_dict(self) -> dict[str, Any]:
        if not _ARTIFACT_ID_RE.fullmatch(self.artifact_id):
            raise ValueError("artifact_id contains unsupported characters")
        for field_name, value, limit in (
            ("request_hash", self.request_hash, 128),
            ("schema_version", self.schema_version, 128),
            ("created_at", self.created_at, 128),
            ("producer_version", self.producer_version, 128),
        ):
            if not isinstance(value, str) or not value or len(value) > limit:
                raise ValueError(f"invalid {field_name}")
        if self.show_context_hash is not None and len(self.show_context_hash) > 128:
            raise ValueError("show_context_hash too long")
        if self.source_worker_id is not None and len(self.source_worker_id) > 128:
            raise ValueError("source_worker_id too long")
        return {
            "schema": ARTIFACT_METADATA_SCHEMA,
            "artifact_id": self.artifact_id,
            "request_hash": self.request_hash,
            "show_context_hash": self.show_context_hash,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "source_worker_id": self.source_worker_id,
            "producer_version": self.producer_version,
        }


class StaleArtifactError(ValueError):
    pass


def validate_remote_result(
    result: Mapping[str, Any],
    *,
    expected_job_id: str,
    expected_job_type: str,
    expected_request_hash: str,
    expected_show_context_hash: Optional[str] = None,
    expected_schema_version: Optional[str] = None,
) -> None:
    checks = (
        ("job_id", expected_job_id),
        ("job_type", expected_job_type),
        ("request_hash", expected_request_hash),
    )
    for field_name, expected in checks:
        if result.get(field_name) != expected:
            raise StaleArtifactError(f"{field_name} mismatch")
    if expected_show_context_hash is not None and result.get("show_context_hash") != expected_show_context_hash:
        raise StaleArtifactError("show_context_hash mismatch")
    if expected_schema_version is not None and result.get("schema_version") != expected_schema_version:
        raise StaleArtifactError("schema_version mismatch")


class ArtifactCache:
    """Small local filesystem cache using atomic replace for metadata+payload envelopes."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, artifact_id: str) -> Path:
        if not _ARTIFACT_ID_RE.fullmatch(artifact_id):
            raise ValueError("artifact_id contains unsupported characters")
        return self.root / f"{artifact_id}.json"

    def put(self, metadata: ArtifactMetadata, payload: Any) -> Path:
        target = self._path(metadata.artifact_id)
        envelope = {
            "metadata": metadata.to_dict(),
            "payload": payload,
        }
        encoded = json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.root,
            prefix=f".{metadata.artifact_id}.",
            suffix=".tmp",
            delete=False,
        )
        temp_path = Path(handle.name)
        try:
            with handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
        return target

    def get(self, artifact_id: str) -> dict[str, Any]:
        path = self._path(artifact_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def exists(self, artifact_id: str) -> bool:
        return self._path(artifact_id).is_file()
