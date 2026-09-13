"""Portable, role-agnostic checkpoints for resumable Agent runs."""

from __future__ import annotations

import json
from pathlib import Path

from .portable import portable_state_path


def _step_artifact_path(run_id: str, role_name: str) -> Path:
    return portable_state_path("projects") / "runs" / run_id / "steps" / f"{role_name}.json"


def write_step_artifact(run_id: str, role_name: str, artifact: dict) -> Path:
    """Persist an opaque role artifact in portable project state."""
    path = _step_artifact_path(run_id, role_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_step_artifact(run_id: str, role_name: str) -> dict | None:
    """Return a stored role artifact, or ``None`` when that step has not run."""
    path = _step_artifact_path(run_id, role_name)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Step artifact must contain a JSON object: {path}")
    return value


def find_resume_point(run_id: str, role_sequence: list[str]) -> str | None:
    """Return the first incomplete role in sequence order, if any."""
    for role_name in role_sequence:
        if read_step_artifact(run_id, role_name) is None:
            return role_name
    return None
