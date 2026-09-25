from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image, ImageStat

from .portable import portable_state_path


SCHEMA = "zen.ma2_visual_observation.v0.1"
MODEL_SCHEMA = "zen.ma2_visual_observation.model.v0.1"
DEFAULT_WINDOW_TITLE = "grandMA2 onPC"
MAX_OBSERVATIONS = 12
MAX_LIMITATIONS = 12


class MA2VisualObservationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MA2WindowInfo:
    hwnd: int
    pid: int
    title: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True)
class MA2Capture:
    window: MA2WindowInfo
    image_path: Path
    sha256: str
    media_type: str = "image/png"
    capture_method: str = "PRINTWINDOW_RENDERFULLCONTENT"


@dataclass(frozen=True)
class OpenClawVisionConfig:
    executable: str
    agent: str = "main"
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not str(self.executable).strip():
            raise ValueError("OpenClaw executable must be non-empty.")
        if not str(self.agent).strip():
            raise ValueError("OpenClaw agent must be non-empty.")
        if not 1.0 <= float(self.timeout_seconds) <= 180.0:
            raise ValueError("OpenClaw vision timeout must be from 1 to 180 seconds.")


Runner = Callable[..., subprocess.CompletedProcess[str]]


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


def _strip_json_fence(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].strip().lower() in {"```", "```json"}:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _bounded_strings(value: object, *, field: str, maximum: int) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise MA2VisualObservationError(f"{field} must be an array of at most {maximum} strings.")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 300:
            raise MA2VisualObservationError(f"{field} contains an invalid string.")
        result.append(item.strip())
    return result


class WindowsMA2WindowCapture:
    """Read-only background capture of the visible grandMA2 onPC top-level window."""

    def __init__(self, *, title: str = DEFAULT_WINDOW_TITLE) -> None:
        self.title = title

    def locate(self) -> MA2WindowInfo:
        if os.name != "nt":
            raise MA2VisualObservationError("MA2 window capture is supported only on Windows.")

        from ctypes import wintypes

        user32 = ctypes.windll.user32
        enum_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        matches: list[MA2WindowInfo] = []

        def callback(hwnd: int, _lparam: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title != self.title:
                return True
            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            matches.append(
                MA2WindowInfo(
                    hwnd=int(hwnd),
                    pid=int(pid.value),
                    title=title,
                    left=int(rect.left),
                    top=int(rect.top),
                    right=int(rect.right),
                    bottom=int(rect.bottom),
                )
            )
            return True

        user32.EnumWindows(enum_proc(callback), 0)
        valid = [item for item in matches if item.width >= 320 and item.height >= 240]
        if not valid:
            raise MA2VisualObservationError("No visible grandMA2 onPC window was found.")
        return max(valid, key=lambda item: item.width * item.height)

    def capture(self, output_path: Path) -> MA2Capture:
        if os.name != "nt":
            raise MA2VisualObservationError("MA2 window capture is supported only on Windows.")

        from ctypes import wintypes

        window = self.locate()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        class BITMAPINFO(ctypes.Structure):
            _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]

        source_dc = user32.GetWindowDC(window.hwnd)
        if not source_dc:
            raise MA2VisualObservationError("GetWindowDC failed for grandMA2 onPC.")
        memory_dc = gdi32.CreateCompatibleDC(source_dc)
        bitmap = gdi32.CreateCompatibleBitmap(source_dc, window.width, window.height)
        old_object = gdi32.SelectObject(memory_dc, bitmap)

        try:
            if not user32.PrintWindow(window.hwnd, memory_dc, 2):
                raise MA2VisualObservationError("PrintWindow failed for grandMA2 onPC.")

            info = BITMAPINFO()
            info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            info.bmiHeader.biWidth = window.width
            info.bmiHeader.biHeight = -window.height
            info.bmiHeader.biPlanes = 1
            info.bmiHeader.biBitCount = 32
            info.bmiHeader.biCompression = 0

            raw = ctypes.create_string_buffer(window.width * window.height * 4)
            rows = gdi32.GetDIBits(
                memory_dc,
                bitmap,
                0,
                window.height,
                raw,
                ctypes.byref(info),
                0,
            )
            if rows != window.height:
                raise MA2VisualObservationError(
                    f"GetDIBits returned {rows} rows; expected {window.height}."
                )

            image = Image.frombuffer(
                "RGB",
                (window.width, window.height),
                raw,
                "raw",
                "BGRX",
                0,
                1,
            )
            luminance = ImageStat.Stat(image.convert("L"))
            if not image.getbbox() or not luminance.stddev or luminance.stddev[0] < 1.0:
                raise MA2VisualObservationError("Captured MA2 window is blank or unreadable.")

            temporary = output_path.with_name(output_path.name + ".tmp")
            image.save(temporary, format="PNG")
            os.replace(temporary, output_path)
        finally:
            gdi32.SelectObject(memory_dc, old_object)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(memory_dc)
            user32.ReleaseDC(window.hwnd, source_dc)

        digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        return MA2Capture(window=window, image_path=output_path, sha256=digest)


class OpenClawMA2VisionObserver:
    """Zero-MA-authority image interpretation through OpenClaw's current model."""

    PROMPT = """Return only minified JSON exactly like {"is_grandma2":true,"capture_readable":true,"stage_view_visible":false,"panel":"...","observations":["..."],"limitations":["..."]}. Use only visible pixels. stage_view_visible=true only if an actual Stage/3D view is visible. Never infer patch/address, fixture capabilities, preset applicability, or physical geometry from appearance. No markdown."""

    def __init__(self, config: OpenClawVisionConfig, *, runner: Runner = subprocess.run) -> None:
        self.config = config
        self._runner = runner

    def observe(self, image_path: Path) -> dict[str, Any]:
        command = [
            self.config.executable,
            "infer",
            "model",
            "run",
            "--agent",
            self.config.agent,
            "--local",
            "--json",
            "--file",
            str(image_path),
            "--prompt",
            self.PROMPT,
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
        if completed.returncode != 0:
            raise MA2VisualObservationError(
                f"OpenClaw vision failed with exit code {completed.returncode}."
            )
        try:
            envelope = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MA2VisualObservationError("OpenClaw vision returned invalid envelope JSON.") from exc
        if (
            not isinstance(envelope, dict)
            or envelope.get("ok") is not True
            or envelope.get("capability") != "model.run"
            or envelope.get("transport") != "local"
        ):
            raise MA2VisualObservationError("OpenClaw vision returned an unexpected envelope.")

        outputs = envelope.get("outputs")
        if not isinstance(outputs, list) or not outputs or not isinstance(outputs[0], Mapping):
            raise MA2VisualObservationError("OpenClaw vision returned no text output.")
        raw_text = outputs[0].get("text")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise MA2VisualObservationError("OpenClaw vision returned empty text output.")
        try:
            model = json.loads(_strip_json_fence(raw_text))
        except json.JSONDecodeError as exc:
            raise MA2VisualObservationError("Vision model output is not JSON.") from exc
        if not isinstance(model, dict):
            raise MA2VisualObservationError("Vision model output must be an object.")

        required = {
            "is_grandma2",
            "capture_readable",
            "stage_view_visible",
            "panel",
            "observations",
            "limitations",
        }
        if set(model) != required:
            raise MA2VisualObservationError("Vision model output contains unexpected or missing fields.")
        for field in ("is_grandma2", "capture_readable", "stage_view_visible"):
            if not isinstance(model.get(field), bool):
                raise MA2VisualObservationError(f"Vision model field {field} must be boolean.")
        panel = model.get("panel")
        if not isinstance(panel, str) or not panel.strip() or len(panel) > 300:
            raise MA2VisualObservationError("panel must be a bounded string.")

        return {
            "is_grandma2": bool(model["is_grandma2"]),
            "capture_readable": bool(model["capture_readable"]),
            "stage_view_visible": bool(model["stage_view_visible"]),
            "visible_screen_or_panel": panel.strip(),
            "observations": _bounded_strings(
                model.get("observations"),
                field="observations",
                maximum=MAX_OBSERVATIONS,
            ),
            "limitations": _bounded_strings(
                model.get("limitations"),
                field="limitations",
                maximum=MAX_LIMITATIONS,
            ),
            "provider": str(envelope.get("provider") or ""),
            "model": str(envelope.get("model") or ""),
            "transport": "local",
        }


class MA2VisualObservationService:
    """Capture + interpret current MA2 pixels without gaining MA write authority."""

    def __init__(
        self,
        capture: WindowsMA2WindowCapture,
        vision: OpenClawMA2VisionObserver,
        *,
        evidence_dir: Path | None = None,
    ) -> None:
        self.capture = capture
        self.vision = vision
        self.evidence_dir = evidence_dir or (portable_state_path("runtime") / "visual")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def observe(self) -> dict[str, Any]:
        captured_at = datetime.now(timezone.utc).isoformat()
        image_path = self.evidence_dir / "latest_ma2_window.png"
        capture = self.capture.capture(image_path)
        vision = self.vision.observe(capture.image_path)

        evidence = {
            "schema": SCHEMA,
            "source_type": "MACHINE_CAPTURED_MA2_WINDOW",
            "captured_at": captured_at,
            "show_binding_status": "UNBOUND_VISUAL_OBSERVATION",
            "window": {
                **asdict(capture.window),
                "width": capture.window.width,
                "height": capture.window.height,
                "capture_method": capture.capture_method,
            },
            "image": {
                "relative_path": capture.image_path.name,
                "sha256": capture.sha256,
                "media_type": capture.media_type,
            },
            "vision": {
                "provider": vision["provider"],
                "model": vision["model"],
                "transport": vision["transport"],
                "tools_available_to_model": False,
                "ma_write_authority": "NONE",
            },
            "is_grandma2": vision["is_grandma2"],
            "capture_readable": vision["capture_readable"],
            "stage_view_visible": vision["stage_view_visible"],
            "visible_screen_or_panel": vision["visible_screen_or_panel"],
            "visual_observations": [
                {
                    "observation": item,
                    "evidence_class": "VISUAL_OBSERVATION",
                    "verified_physical_fact": False,
                    "source_image_sha256": capture.sha256,
                }
                for item in vision["observations"]
            ],
            "limitations": list(vision["limitations"]),
            "ma2_writes": 0,
        }
        latest_json = self.evidence_dir / "latest_ma2_visual_observation.json"
        temp_json = latest_json.with_name(latest_json.name + ".tmp")
        temp_json.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temp_json, latest_json)
        return evidence


def load_ma2_visual_observation_service() -> MA2VisualObservationService | None:
    enabled = os.environ.get("ZEN_MA2_VISION_ENABLED", "1").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return None
    if os.name != "nt":
        return None
    executable = _resolve_openclaw_executable()
    if executable is None:
        return None
    agent = os.environ.get("ZEN_OPENCLAW_INFER_AGENT", "main").strip() or "main"
    return MA2VisualObservationService(
        WindowsMA2WindowCapture(),
        OpenClawMA2VisionObserver(OpenClawVisionConfig(executable=executable, agent=agent)),
    )


__all__ = [
    "MA2VisualObservationError",
    "MA2WindowInfo",
    "MA2Capture",
    "OpenClawVisionConfig",
    "WindowsMA2WindowCapture",
    "OpenClawMA2VisionObserver",
    "MA2VisualObservationService",
    "load_ma2_visual_observation_service",
]
