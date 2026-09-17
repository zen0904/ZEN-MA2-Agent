from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from fastapi import FastAPI, HTTPException

WORKER_HEALTH_SCHEMA = "zen.worker.health.v0.1"
WORKER_CAPABILITIES_SCHEMA = "zen.worker.capabilities.v0.1"
WORKER_JOB_SCHEMA = "zen.worker.job.v0.1"
WORKER_RESULT_SCHEMA = "zen.worker.result.v0.1"
MAX_JOB_BYTES = 65536


@dataclass(frozen=True)
class WorkerConfig:
    worker_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.worker_id, str) or not self.worker_id or len(self.worker_id) > 128:
            raise ValueError("worker_id must be a non-empty string up to 128 characters")


def _ram_total_mb() -> Optional[int]:
    try:
        if hasattr(os, "sysconf"):
            pages = int(os.sysconf("SC_PHYS_PAGES"))
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            return (pages * page_size) // (1024 * 1024)
    except (ValueError, OSError, AttributeError):
        pass
    return None


def _nvidia_capability() -> tuple[Optional[str], Optional[int], Optional[bool]]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return None, None, None
    try:
        completed = subprocess.run(
            [
                executable,
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None, None
    if completed.returncode != 0:
        return None, None, False
    first = next((line.strip() for line in completed.stdout.splitlines() if line.strip()), "")
    if not first:
        return None, None, False
    parts = [part.strip() for part in first.split(",", 1)]
    name = parts[0] or None
    try:
        vram = int(parts[1]) if len(parts) > 1 else None
    except ValueError:
        vram = None
    return name, vram, True


def detect_capabilities(config: WorkerConfig) -> dict[str, Any]:
    gpu_name, vram_total_mb, cuda_available = _nvidia_capability()
    return {
        "schema_version": WORKER_CAPABILITIES_SCHEMA,
        "worker_id": config.worker_id,
        "node_role": "AI_WORKER",
        "os": platform.system() or "UNKNOWN",
        "architecture": platform.machine() or "UNKNOWN",
        "cpu_logical_threads": os.cpu_count(),
        "ram_total_mb": _ram_total_mb(),
        "gpu_present": gpu_name is not None,
        "gpu_name": gpu_name,
        "vram_total_mb": vram_total_mb,
        "cuda_available": cuda_available,
        "model_runtime_available": False,
    }


def _validate_job(job: Mapping[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(job, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="job must be JSON serializable") from exc
    if len(encoded) > MAX_JOB_BYTES:
        raise HTTPException(status_code=413, detail="job payload too large")

    required = {"schema_version", "job_id", "job_type", "request_hash", "payload", "created_at"}
    missing = required - set(job)
    if missing:
        raise HTTPException(status_code=400, detail=f"missing field: {sorted(missing)[0]}")
    unknown = set(job) - required
    if unknown:
        raise HTTPException(status_code=400, detail=f"unsupported field: {sorted(unknown)[0]}")
    if job.get("schema_version") != WORKER_JOB_SCHEMA:
        raise HTTPException(status_code=400, detail="unsupported job schema")
    for key, limit in (("job_id", 128), ("job_type", 64), ("request_hash", 128)):
        value = job.get(key)
        if not isinstance(value, str) or not value or len(value) > limit:
            raise HTTPException(status_code=400, detail=f"invalid {key}")
    return dict(job)


def create_worker_app(config: WorkerConfig) -> FastAPI:
    app = FastAPI(
        title="ZEN AI Worker",
        version="0.1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "schema_version": WORKER_HEALTH_SCHEMA,
            "worker_id": config.worker_id,
            "status": "ONLINE",
        }

    @app.get("/capabilities")
    def capabilities() -> dict[str, Any]:
        return detect_capabilities(config)

    @app.post("/jobs")
    def jobs(payload: dict[str, Any]) -> dict[str, Any]:
        job = _validate_job(payload)
        started = time.time()
        job_type = job["job_type"]
        if job_type == "ECHO_TEST":
            status = "SUCCESS"
            result = job["payload"]
            error = None
        elif job_type == "INFERENCE_RESERVED":
            status = "NOT_IMPLEMENTED"
            result = None
            error = None
        else:
            status = "REJECTED"
            result = None
            error = {"code": "UNKNOWN_JOB_TYPE", "message": "job_type is not supported"}
        completed = time.time()
        return {
            "schema_version": WORKER_RESULT_SCHEMA,
            "job_id": job["job_id"],
            "job_type": job_type,
            "status": status,
            "worker_id": config.worker_id,
            "request_hash": job["request_hash"],
            "result": result,
            "error": error,
            "started_at": started,
            "completed_at": completed,
            "elapsed_seconds": max(0.0, completed - started),
        }

    return app
