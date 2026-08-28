"""PyInstaller runtime hook for the bundled PySide6 wheel on Windows.

Qt and shiboken DLLs stay inside the one-folder bundle. Keeping their DLL
directories registered for this process avoids any dependency on the host PATH.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


if sys.platform.startswith("win") and hasattr(sys, "_MEIPASS"):
    _bundle = Path(sys._MEIPASS)
    _dll_handles = []
    _directories = (_bundle, _bundle / "PySide6", _bundle / "shiboken6")
    for _directory in _directories:
        if _directory.is_dir():
            _dll_handles.append(os.add_dll_directory(str(_directory)))
    os.environ["PATH"] = os.pathsep.join([str(path) for path in _directories if path.is_dir()] + [os.environ.get("PATH", "")])
