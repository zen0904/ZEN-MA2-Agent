from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from .lean_design_adapter import _SYSTEM_PROMPT


DEFAULT_OPENCLAW_AGENT = "main"
DEFAULT_OPENCLAW_TIMEOUT_SECONDS = 90.0
DISABLED_VALUES = frozenset({"0", "false", "no", "off"})
_HELPER_NAME = "openclaw_sdk_infer.mjs"


@dataclass(frozen=True)
class OpenClawInferConfig:
    node_executable: str
    openclaw_root: str
    openclaw_config_path: str
    agent: str = DEFAULT_OPENCLAW_AGENT
    timeout_seconds: float = DEFAULT_OPENCLAW_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if not str(self.node_executable).strip():
            raise ValueError("Node executable must be non-empty.")
        if not str(self.openclaw_root).strip():
            raise ValueError("OpenClaw package root must be non-empty.")
        if not str(self.openclaw_config_path).strip():
            raise ValueError("OpenClaw config path must be non-empty.")
        if not str(self.agent).strip():
            raise ValueError("OpenClaw agent must be non-empty.")
        if not 1.0 <= float(self.timeout_seconds) <= 300.0:
            raise ValueError("OpenClaw inference timeout must be from 1 to 300 seconds.")


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _parse_helper_stdout(stdout: str) -> dict[str, Any]:
    """Extract the helper envelope after OpenClaw provider diagnostic lines.

    Some OpenClaw transports write ANSI diagnostic lines to stdout before the
    helper's final JSON envelope. The helper itself always emits its envelope
    as one compact final line, so scan from the end and accept only a model.run
    shaped object rather than treating arbitrary logged JSON as a result.
    """
    if not isinstance(stdout, str) or not stdout.strip():
        raise RuntimeError("OpenClaw SDK inference returned empty output.")
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("capability") == "model.run":
            return value
    raise RuntimeError("OpenClaw SDK inference returned invalid JSON.")


class OpenClawInferLeanDesignIntelligence:
    """Use OpenClaw's authenticated zero-tool completion as ZEN's Designer.

    The request context is written to a short-lived local JSON file and consumed
    by a tiny Node helper using OpenClaw's public plugin SDK simple-completion
    runtime. This avoids Windows command-line length limits while keeping
    credentials owned by OpenClaw.

    The model receives no OpenClaw/ZEN tools. Its output remains artistic JSON
    only and still passes through ZEN's existing typed validation/compiler and
    Preview/Approval boundary before any MA2 mutation is possible.
    """

    def __init__(
        self,
        config: OpenClawInferConfig,
        *,
        runner: Runner = subprocess.run,
    ) -> None:
        self.config = config
        self._runner = runner
        self.last_diagnostics: dict[str, Any] | None = None

    @property
    def helper_path(self) -> Path:
        return Path(__file__).with_name(_HELPER_NAME)

    def design(self, request: str, context: Mapping[str, Any]) -> str:
        if not isinstance(request, str) or not request.strip() or len(request) > 2048:
            raise ValueError("Lean design request must be a non-empty bounded string.")
        if not isinstance(context, Mapping):
            raise ValueError("Lean design context must be a mapping.")

        user_payload = json.dumps(
            {"request": request, "context": dict(context)},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        envelope = {
            "system_prompt": _SYSTEM_PROMPT,
            "user_prompt": f"INPUT_JSON:\n{user_payload}",
        }

        helper = self.helper_path
        if not helper.is_file():
            raise RuntimeError("OpenClaw SDK inference helper is missing.")

        temp_path: Path | None = None
        completed: subprocess.CompletedProcess[str]
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                prefix="zen-openclaw-infer-",
                delete=False,
            ) as handle:
                json.dump(
                    envelope,
                    handle,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                temp_path = Path(handle.name)

            command = [
                self.config.node_executable,
                str(helper),
                str(temp_path),
                self.config.openclaw_root,
                self.config.openclaw_config_path,
                self.config.agent,
            ]
            kwargs: dict[str, Any] = {
                "capture_output": True,
                "text": True,
                "encoding": "utf-8",
                "errors": "replace",
                "timeout": float(self.config.timeout_seconds),
                "check": False,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            completed = self._runner(command, **kwargs)
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

        if completed.returncode != 0:
            raise RuntimeError(
                f"OpenClaw SDK inference failed with exit code {completed.returncode}."
            )

        payload = _parse_helper_stdout(completed.stdout)
        if not isinstance(payload, dict) or payload.get("ok") is not True:
            raise RuntimeError("OpenClaw SDK inference did not report success.")
        if payload.get("capability") != "model.run" or payload.get("transport") != "sdk-local":
            raise RuntimeError("OpenClaw inference returned an unexpected capability/transport.")

        outputs = payload.get("outputs")
        if not isinstance(outputs, list) or not outputs:
            raise RuntimeError("OpenClaw SDK inference returned no text output.")
        first = outputs[0]
        if not isinstance(first, dict) or not isinstance(first.get("text"), str):
            raise RuntimeError("OpenClaw SDK inference returned an invalid text output.")
        text = first["text"].strip()
        if not text:
            raise RuntimeError("OpenClaw SDK inference returned empty text.")

        self.last_diagnostics = {
            "source": "openclaw_sdk_isolated_completion",
            "agent": self.config.agent,
            "provider": str(payload.get("provider") or ""),
            "model": str(payload.get("model") or ""),
            "transport": "sdk-local",
            "tools_available_to_model": False,
            "credential_owner": "openclaw",
            "provider_cost_policy": "OPENCLAW_HOST_MANAGED",
            "parallel_candidates": False,
        }
        return text

    def safe_summary(self) -> dict[str, Any]:
        return {
            "source": "openclaw_sdk_isolated_completion",
            "agent": self.config.agent,
            "transport": "sdk-local",
            "one_shot": True,
            "tools_available_to_model": False,
            "credential_owner": "openclaw",
            "parallel_candidates": False,
        }


def _resolve_openclaw_executable() -> str | None:
    configured = os.environ.get("ZEN_OPENCLAW_INFER_BIN", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return str(candidate)
        return shutil.which(configured)

    resolved = shutil.which("openclaw") or shutil.which("openclaw.cmd")
    if resolved:
        return resolved

    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        candidate = Path(appdata) / "npm" / "openclaw.cmd"
        if candidate.is_file():
            return str(candidate)
    return None


def _resolve_node_executable() -> str | None:
    configured = os.environ.get("ZEN_OPENCLAW_NODE_BIN", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return str(candidate)
        return shutil.which(configured)

    resolved = shutil.which("node") or shutil.which("node.exe")
    if resolved:
        return resolved

    if os.name == "nt":
        candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "node.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _resolve_openclaw_package_root(executable: str) -> Path | None:
    configured = os.environ.get("ZEN_OPENCLAW_PACKAGE_ROOT", "").strip()
    if configured:
        root = Path(configured).expanduser()
        if (root / "package.json").is_file():
            return root
        return None

    executable_path = Path(executable).expanduser()
    candidates = [
        executable_path.parent / "node_modules" / "openclaw",
        executable_path.resolve().parent,
    ]
    for candidate in candidates:
        if (
            (candidate / "package.json").is_file()
            and (candidate / "dist" / "plugin-sdk" / "simple-completion-runtime.js").is_file()
        ):
            return candidate
    return None


def _resolve_openclaw_config_path() -> Path | None:
    configured = os.environ.get("ZEN_OPENCLAW_CONFIG", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_file() else None

    path = Path.home() / ".openclaw" / "openclaw.json"
    return path if path.is_file() else None


def load_openclaw_infer_design_intelligence() -> OpenClawInferLeanDesignIntelligence | None:
    """Configure the OpenClaw SDK fallback without performing inference."""

    enabled = os.environ.get("ZEN_OPENCLAW_INFER_ENABLED", "1").strip().lower()
    if enabled in DISABLED_VALUES:
        return None

    executable = _resolve_openclaw_executable()
    node_executable = _resolve_node_executable()
    config_path = _resolve_openclaw_config_path()
    if executable is None or node_executable is None or config_path is None:
        return None

    package_root = _resolve_openclaw_package_root(executable)
    if package_root is None:
        return None

    agent = os.environ.get("ZEN_OPENCLAW_INFER_AGENT", DEFAULT_OPENCLAW_AGENT).strip()
    raw_timeout = os.environ.get(
        "ZEN_OPENCLAW_INFER_TIMEOUT_SECONDS",
        str(DEFAULT_OPENCLAW_TIMEOUT_SECONDS),
    ).strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ValueError("ZEN_OPENCLAW_INFER_TIMEOUT_SECONDS must be numeric.") from exc

    return OpenClawInferLeanDesignIntelligence(
        OpenClawInferConfig(
            node_executable=node_executable,
            openclaw_root=str(package_root),
            openclaw_config_path=str(config_path),
            agent=agent,
            timeout_seconds=timeout,
        )
    )


__all__ = [
    "OpenClawInferConfig",
    "OpenClawInferLeanDesignIntelligence",
    "load_openclaw_infer_design_intelligence",
]
