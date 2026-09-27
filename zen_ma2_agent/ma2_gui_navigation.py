from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Callable, Mapping, Protocol

from .ma2_visual_observation import (
    MA2VisualObservationError,
    MA2VisualObservationService,
    MA2WindowInfo,
    WindowsMA2WindowCapture,
)


SCHEMA = "zen.ma2_stage_view_navigation.v0.1"
DEFAULT_WINDOW_CLASS = "_extdisplay_0_1_2_3_4_5_"
SUPPORTED_WINDOW_SIZE = (836, 524)
SCREEN_BUTTON_OUTER_POINTS = {
    2: (806, 274),
    3: (806, 319),
    4: (806, 364),
}


class MA2GuiNavigationError(RuntimeError):
    pass


class MA2Screen(IntEnum):
    SCREEN_2 = 2
    SCREEN_3 = 3
    SCREEN_4 = 4


@dataclass(frozen=True)
class NavigationDispatch:
    screen: int
    method: str
    status: str
    detail: str | None = None


class ScreenNavigator(Protocol):
    def show_screen(self, screen: MA2Screen) -> NavigationDispatch: ...


ObservationProvider = Callable[[], Mapping[str, Any]]
CandidateObservationProvider = Callable[[str], Mapping[str, Any]]


class WindowsMA2ScreenNavigator:
    """Narrow Windows input driver for the three onPC screen buttons only.

    It exposes no arbitrary coordinates, keys, text, or MA command input. The
    current prototype is calibrated only for the verified 836x524 grandMA2
    onPC 3.9 window layout. Any mismatch, foreground denial, or HWND ownership
    mismatch fails closed before mouse input is emitted.
    """

    def __init__(
        self,
        *,
        capture: WindowsMA2WindowCapture | None = None,
        window_class: str = DEFAULT_WINDOW_CLASS,
        restore_foreground: bool = True,
    ) -> None:
        self.capture = capture or WindowsMA2WindowCapture()
        self.window_class = window_class
        self.restore_foreground = restore_foreground

    def show_screen(self, screen: MA2Screen) -> NavigationDispatch:
        if not isinstance(screen, MA2Screen):
            raise MA2GuiNavigationError("Only Screen 2, Screen 3, and Screen 4 are allowed.")
        if os.name != "nt":
            raise MA2GuiNavigationError("MA2 GUI navigation is supported only on Windows.")

        window = self.capture.locate()
        self._verify_window(window)
        outer_x, outer_y = SCREEN_BUTTON_OUTER_POINTS[int(screen)]
        screen_x = window.left + outer_x
        screen_y = window.top + outer_y
        return self._click_verified_navigation_point(window, screen, screen_x, screen_y)

    def _verify_window(self, window: MA2WindowInfo) -> None:
        if (window.width, window.height) != SUPPORTED_WINDOW_SIZE:
            raise MA2GuiNavigationError(
                "FAIL_CLOSED_UNSUPPORTED_WINDOW_GEOMETRY: "
                f"expected {SUPPORTED_WINDOW_SIZE}, got {(window.width, window.height)}."
            )
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        buffer = ctypes.create_unicode_buffer(256)
        if not user32.GetClassNameW(window.hwnd, buffer, 256):
            raise MA2GuiNavigationError("FAIL_CLOSED_WINDOW_CLASS_UNREADABLE")
        if buffer.value != self.window_class:
            raise MA2GuiNavigationError(
                f"FAIL_CLOSED_WINDOW_CLASS_MISMATCH: {buffer.value!r}."
            )
        if not user32.IsWindowVisible(window.hwnd) or not user32.IsWindowEnabled(window.hwnd):
            raise MA2GuiNavigationError("FAIL_CLOSED_MA2_WINDOW_NOT_INTERACTIVE")

    def _click_verified_navigation_point(
        self,
        window: MA2WindowInfo,
        screen: MA2Screen,
        screen_x: int,
        screen_y: int,
    ) -> NavigationDispatch:
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        user32.SetCursorPos.restype = wintypes.BOOL
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow.restype = wintypes.BOOL
        user32.mouse_event.argtypes = [
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]

        # The calibrated target must remain inside the dedicated right-side
        # screen-navigation rail. It is never allowed to drift into the main UI.
        if not (
            window.right - 50 <= screen_x <= window.right - 10
            and window.top + 235 <= screen_y <= window.top + 395
        ):
            raise MA2GuiNavigationError("FAIL_CLOSED_TARGET_OUTSIDE_NAVIGATION_RAIL")

        old_foreground = int(user32.GetForegroundWindow())
        if not user32.SetForegroundWindow(window.hwnd):
            raise MA2GuiNavigationError(
                "FAIL_CLOSED_FOREGROUND_ACTIVATION_DENIED: no input was sent. "
                "A higher-integrity foreground window or Windows foreground-lock policy may be active."
            )
        try:
            time.sleep(0.15)
            if int(user32.GetForegroundWindow()) != int(window.hwnd):
                raise MA2GuiNavigationError(
                    "FAIL_CLOSED_FOREGROUND_ACTIVATION_UNVERIFIED: no input was sent."
                )
            if not user32.SetCursorPos(int(screen_x), int(screen_y)):
                raise MA2GuiNavigationError(
                    "FAIL_CLOSED_CURSOR_POSITION_DENIED: no click was sent."
                )

            point = wintypes.POINT(int(screen_x), int(screen_y))
            under = user32.WindowFromPoint(point)
            root = user32.GetAncestor(under, 2) if under else 0  # GA_ROOT
            if int(root) != int(window.hwnd):
                raise MA2GuiNavigationError(
                    "FAIL_CLOSED_TARGET_NOT_OWNED_BY_MA2: no click was sent."
                )

            # mouse_event is used only after exact HWND ownership verification. The
            # public API never accepts coordinates, button choice, key text, or MA
            # commands, so this driver cannot be repurposed as programming input.
            user32.mouse_event(0x0002, 0, 0, 0, None)  # MOUSEEVENTF_LEFTDOWN
            time.sleep(0.03)
            user32.mouse_event(0x0004, 0, 0, 0, None)  # MOUSEEVENTF_LEFTUP
            time.sleep(0.20)
        finally:
            if (
                self.restore_foreground
                and old_foreground
                and old_foreground != int(window.hwnd)
            ):
                user32.SetForegroundWindow(old_foreground)

        return NavigationDispatch(
            screen=int(screen),
            method="HWND_VERIFIED_SCREEN_BUTTON",
            status="SENT",
        )


class MA2StageViewNavigationService:
    """Try only bounded screen navigation, then observe with zero MA authority."""

    def __init__(
        self,
        navigator: ScreenNavigator,
        observation_provider: ObservationProvider,
        *,
        candidate_observation_provider: CandidateObservationProvider | None = None,
        candidate_titles: tuple[str, ...] = (
            "Screen 2",
            "Screen 3",
            "Screen 4",
            "Screen 5",
            "Screen 6",
        ),
        screens: tuple[MA2Screen, ...] = (
            MA2Screen.SCREEN_2,
            MA2Screen.SCREEN_3,
            MA2Screen.SCREEN_4,
        ),
    ) -> None:
        self.navigator = navigator
        self.observation_provider = observation_provider
        self.candidate_observation_provider = candidate_observation_provider
        self.candidate_titles = candidate_titles
        self.screens = screens

    def navigate_and_observe(self) -> dict[str, Any]:
        initial = dict(self.observation_provider())
        self._validate_observation(initial)
        attempts: list[dict[str, Any]] = []
        if initial["stage_view_visible"]:
            return self._result("SUCCESS", initial, attempts, None)

        # Safest path first: inspect already-existing native MA2 screen windows
        # with background PrintWindow capture. No GUI input is needed and Vision
        # remains observe/verify-only.
        if self.candidate_observation_provider is not None:
            for title in self.candidate_titles:
                try:
                    observed = dict(self.candidate_observation_provider(title))
                except (MA2VisualObservationError, OSError, ValueError) as exc:
                    attempts.append(
                        {
                            "window_title": title,
                            "method": "BACKGROUND_NATIVE_WINDOW_CAPTURE",
                            "dispatch_status": "UNAVAILABLE",
                            "detail": str(exc)[:512],
                        }
                    )
                    continue
                self._validate_observation(observed)
                attempts.append(
                    {
                        "window_title": title,
                        "method": "BACKGROUND_NATIVE_WINDOW_CAPTURE",
                        "dispatch_status": "CAPTURED",
                        "capture_sha256": observed.get("image", {}).get("sha256"),
                        "stage_view_visible": observed["stage_view_visible"],
                    }
                )
                if observed["stage_view_visible"]:
                    return self._result("SUCCESS", observed, attempts, None)
                initial = observed

        for screen in self.screens:
            try:
                dispatch = self.navigator.show_screen(screen)
            except MA2GuiNavigationError as exc:
                attempts.append(
                    {
                        "screen": int(screen),
                        "method": "HWND_VERIFIED_SCREEN_BUTTON",
                        "dispatch_status": "BLOCKED",
                        "detail": str(exc)[:512],
                    }
                )
                return self._result(
                    "BLOCKED",
                    initial,
                    attempts,
                    {
                        "code": "GUI_NAVIGATION_FAIL_CLOSED",
                        "message": str(exc)[:512],
                    },
                )

            observed = dict(self.observation_provider())
            self._validate_observation(observed)
            attempts.append(
                {
                    "screen": dispatch.screen,
                    "method": dispatch.method,
                    "dispatch_status": dispatch.status,
                    "capture_sha256": observed.get("image", {}).get("sha256"),
                    "stage_view_visible": observed["stage_view_visible"],
                }
            )
            if observed["stage_view_visible"]:
                return self._result("SUCCESS", observed, attempts, None)
            initial = observed

        return self._result(
            "BLOCKED",
            initial,
            attempts,
            {
                "code": "STAGE_VIEW_NOT_FOUND_ON_ALLOWED_SCREENS",
                "message": "Screen 2, Screen 3, and Screen 4 were checked, but Stage/3D View was not verified.",
            },
        )

    @staticmethod
    def _validate_observation(observation: Mapping[str, Any]) -> None:
        if observation.get("schema") != "zen.ma2_visual_observation.v0.1":
            raise MA2GuiNavigationError("FAIL_CLOSED_INVALID_VISUAL_OBSERVATION_SCHEMA")
        if observation.get("ma2_writes") != 0:
            raise MA2GuiNavigationError("FAIL_CLOSED_VISUAL_PATH_REPORTED_MA2_WRITES")
        if not isinstance(observation.get("stage_view_visible"), bool):
            raise MA2GuiNavigationError("FAIL_CLOSED_STAGE_VIEW_FLAG_INVALID")

    @staticmethod
    def _result(
        status: str,
        observation: Mapping[str, Any],
        attempts: list[dict[str, Any]],
        failure: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": status,
            "action": "SHOW_STAGE_VIEW",
            "write_authority": "NONE",
            "ma2_show_writes": 0,
            "attempts": attempts,
            "observation": dict(observation),
            "failure": dict(failure) if failure is not None else None,
        }


def load_ma2_stage_view_navigation_service(
    visual_service: MA2VisualObservationService | None,
) -> MA2StageViewNavigationService | None:
    enabled = os.environ.get("ZEN_MA2_GUI_NAV_ENABLED", "0").strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return None
    if os.name != "nt" or visual_service is None:
        return None
    return MA2StageViewNavigationService(
        WindowsMA2ScreenNavigator(capture=visual_service.capture),
        visual_service.observe,
        candidate_observation_provider=visual_service.observe_title,
    )


__all__ = [
    "SCHEMA",
    "MA2GuiNavigationError",
    "MA2Screen",
    "NavigationDispatch",
    "WindowsMA2ScreenNavigator",
    "MA2StageViewNavigationService",
    "load_ma2_stage_view_navigation_service",
]
