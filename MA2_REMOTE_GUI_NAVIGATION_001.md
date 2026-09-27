# MA2_REMOTE_GUI_NAVIGATION_001

Status: `PROTOTYPE_IMPLEMENTED / LIVE_STAGE_VIEW_EVIDENCE_PASS`

Canonical starting commit: `8714441269f3f70b154b14126d18ba1b888d56f2`

Scope: `CURRENT_SHOW_SPATIAL_EVIDENCE` only. This work did not replay Action
`97d3a82f1220`, did not rewrite or clean up Sequence 302, and did not touch
Fixture 9999.

## CURRENT_CAPABILITIES

- `zen_ma2_agent.ma2_visual_observation.WindowsMA2WindowCapture` already uses
  Win32 `EnumWindows`, exact top-level-window title matching, process ID
  capture, `GetWindowRect`, and background `PrintWindow(..., 2)`
  (`PW_RENDERFULLCONTENT`).
- The current grandMA2 process exposes several native top-level windows with
  class `_extdisplay_0_1_2_3_4_5_`: `grandMA2 onPC`, `Screen 2`, `Screen 3`,
  `Screen 4`, `Screen 5`, and `Screen 6`.
- `Screen 6` already contains an actual Stage View. It was previously missed
  because `zen.ma.visual` targeted only the exact title `grandMA2 onPC`, whose
  visible content was the Executor view.
- Native child-control enumeration returns zero controls for the MA2 renderer.
  Windows UI Automation exposes only the top-level Window element and zero
  children. Therefore UIA cannot safely identify Stage View or screen buttons.
- `pywin32`, `pywinauto`, `uiautomation`, and AutoHotkey are not installed.
  They are not required for HWND enumeration or `PrintWindow`; the prototype
  uses Python `ctypes` and Win32 directly.
- Background `SendMessage` / `PostMessage` mouse and keyboard experiments did
  not change MA2 state. The custom renderer does not accept those messages as
  equivalent to real interactive input.
- Foreground pointer input can work, but Windows foreground-lock/UIPI rules can
  block it when a higher-integrity foreground window is active. The prototype
  treats any such denial as a fail-closed condition.

## WINDOW_TARGETING_METHOD

1. Enumerate visible top-level windows.
2. Match an exact MA2-owned native title from a fixed allowlist:
   `grandMA2 onPC`, `Screen 2` through `Screen 6`.
3. Retain HWND, PID, title, bounds, and class.
4. Capture the selected HWND with `PRINTWINDOW_RENDERFULLCONTENT`, including
   when covered or outside the currently visible desktop region.
5. Prefer passive capture of already-existing native screen windows before
   any GUI input.
6. If input is ever required, accept only the three compiled Screen 2/3/4
   targets, require the calibrated `836x524` main-window geometry and expected
   MA2 class, activate the exact HWND, verify `WindowFromPoint(...)->GA_ROOT`
   equals that HWND, then emit one left click inside the dedicated screen rail.
   The public interface accepts no coordinate, key, text, command, or button.

## STAGE_VIEW_NAVIGATION_OPTIONS

### 1. Passive native-window discovery and capture — selected

Enumerate and capture `Screen 2..6`, then let Vision classify only the captured
pixels. This requires no focus, mouse, keyboard, MA command, or Show mutation.
On the current machine, `Screen 6` is the Stage View.

### 2. HWND-verified Screen 2/3/4 button click — bounded fallback

Use only the fixed right-side screen-navigation rail in the calibrated current
onPC layout. Fail closed on any class, geometry, foreground, cursor, or
HWND-under-point mismatch. This changes only which existing native screen is
shown; it has no MA command or programming interface.

### 3. Official onPC keyboard shortcuts — researched, not selected

The official grandMA2 3.9 manual documents `Ctrl+Alt+F2/F3/F4` for Screen
2/3/4:
<https://help.malighting.com/grandMA2/en/help/key_ws_keyboard_shortcuts.html>

These shortcuts are customizable, so the prototype does not treat their
current mapping as immutable proof of view-only behavior. Posted background
key messages were also ignored by the current MA2 renderer.

### 4. MA command-line View recall — rejected for this prototype

A typed/whitelisted View command might be technically possible, but it crosses
into the MA command path. It is unnecessary because native Screen 6 can be
captured directly, and it would weaken the requested separation from
programming authority.

### 5. UI Automation / AutoHotkey / pywin32

UI Automation has no usable descendant elements. AutoHotkey and pywin32 would
ultimately still face the same custom-renderer, focus, integrity, and target
verification constraints. Adding them would increase dependencies without
improving the current passive-capture path.

## SAFEST_OPTION

`ENUMERATE MA2 PROCESS WINDOWS -> BACKGROUND PRINTWINDOW CAPTURE -> VISION VERIFY`

This is safer than switching the desktop at all. The implementation first
checks already-existing native windows and returns immediately when Stage View
is verified. GUI input remains a last-resort, fixed-target fallback and is not
needed for the current Test Show acceptance.

## WRITE_AUTHORITY=NONE

The new OpenClaw-facing operation is `zen.ma.stage.visual` / plugin tool
`zen_ma_stage_visual`.

It accepts no arguments and exposes no:

- arbitrary coordinates;
- arbitrary key or text input;
- MA command line;
- Telnet/raw command path;
- Preview or Approval transition;
- Builder, Resolver, Cue, Executor, Patch, Address, Fixture, Store, Update,
  Delete, Assign, Go, or playback operation.

Vision still receives no tools and reports observations with
`verified_physical_fact=false`.

## MA2_SHOW_WRITES=0

Live evidence:

- target HWND: `6816168`
- PID: `9852`
- title: `Screen 6`
- capture method: `PRINTWINDOW_RENDERFULLCONTENT`
- capture size: `896x589`
- image SHA-256:
  `fdb237dd3950a71306276dbed49d248c8a9d32c97b0b65b5e0ec1aad715b8e71`
- `capture_readable=true`
- `stage_view_visible=true`
- `visible_screen_or_panel="Stage View"`
- `vision.ma_write_authority="NONE"`
- `ma2_writes=0`
- service result `write_authority="NONE"`
- service result `ma2_show_writes=0`

No MA transport, Preview approval, Action replay, or Show write occurred.

## FAILURE_MODES

- No exact grandMA2 process/window match: fail closed.
- Duplicate or too-small matching windows: fail closed or skip that candidate.
- `PrintWindow` failure or blank/unreadable image: fail closed.
- No visible Stage/3D window among existing Screen 2..6 windows: bounded screen
  fallback may run; otherwise return `STAGE_VIEW_NOT_FOUND_ON_ALLOWED_SCREENS`.
- Main-window class or calibrated geometry mismatch before pointer fallback:
  fail closed before input.
- Foreground activation denied, including higher-integrity foreground/UIPI
  mismatch: fail closed before input.
- Target point not owned by the exact MA2 root HWND: fail closed before click.
- Windows session locked, secure desktop active, or input desktop unavailable:
  passive capture may still work; GUI input must not be attempted or claimed.
- Vision cannot verify Stage View: return blocked; never infer it from window
  title alone.
- Any visual result reports a nonzero MA write count: fail closed.
- Screen shortcuts customized or MA command route required: do not use the
  shortcut/command path automatically.

## IMPLEMENTATION_PLAN

Implemented minimum bounded prototype:

1. Extend visual observation with exact-title capture for existing native MA2
   Screen 2..6 windows.
2. Add `MA2StageViewNavigationService` that passively scans existing native
   screens first.
3. Add an opt-in `WindowsMA2ScreenNavigator` fallback exposing only Screen
   2/3/4 and no arbitrary input surface.
4. Require `ZEN_MA2_GUI_NAV_ENABLED=1` before Field Host exposes the navigation
   provider.
5. Add Operator API contract `zen.ma.stage.visual` and OpenClaw plugin tool
   `zen_ma_stage_visual`.
6. Preserve `WRITE_AUTHORITY=NONE` and `MA2_SHOW_WRITES=0` in every result.

## TEST_PLAN

Automated regression coverage verifies:

- Stage already visible causes zero GUI input.
- Existing native Screen 6 Stage View is captured before any GUI input.
- Scanning stops immediately after Stage View verification.
- GUI denial returns `BLOCKED` and does not continue clicking.
- Only Screen 2/3/4 enum values are accepted by the input driver.
- Nonzero visual-path MA write count fails closed.
- Operator API and OpenClaw tool contracts expose only the bounded provider.
- No raw shell/MA command tool is introduced.

Focused Python result: `58 passed`, plus `3 subtests`, with one pre-existing
Starlette/httpx deprecation warning.

Authoritative repository command
`python -m unittest discover -s tests -q`: **904 tests / OK**.

An ad-hoc repository-root `pytest -q` run was not the project-authoritative
command and produced three collection errors by treating the imported helper
`test_show_palette_manifest(plan)` as a pytest fixture-based test; 904 actual
tests passed in that run. The documented CI command above then completed OK.

The initial plugin test command failed because PowerShell blocked `npm.ps1`.
The `npm.cmd` retry reached the project script but could not run because local
`vitest` dependencies are not installed. No dependency installation was
performed implicitly.

Live acceptance test:

```text
OpenClaw/ZEN local request
 -> enumerate grandMA2 native windows
 -> Screen 2/3 unavailable
 -> capture Screen 4 (not Stage)
 -> capture Screen 5 (not Stage)
 -> capture Screen 6
 -> Vision: stage_view_visible=true
 -> MA2_SHOW_WRITES=0
```

## 手機 / 外網可行性

Yes, with the existing OpenClaw/Gateway path: the phone sends the request over
4G/5G to OpenClaw, while HWND enumeration, `PrintWindow`, and Vision invocation
run locally on the Windows host. The phone does not need direct desktop or MA2
network access.

Current verified path does not require the user to be at home and does not
require the MA2 window to be foreground, because Stage View already exists as
native `Screen 6` and is captured in the background. If a future Show has no
existing Stage/3D window, the bounded pointer fallback requires an unlocked
interactive Windows desktop and successful exact-HWND activation; otherwise it
returns `BLOCKED` rather than clicking blindly.
