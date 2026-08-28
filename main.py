import sys
from types import SimpleNamespace

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.desktop import ZenDesktop, run_desktop
from zen_ma2_agent.web_server import MobileServer


def main() -> int:
    core = AgentCore()
    if "--ui-smoke-request" in sys.argv:
        index = sys.argv.index("--ui-smoke-request")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--ui-smoke-request requires text")
        app = QApplication.instance() or QApplication([])
        window = ZenDesktop(core, SimpleNamespace(port=8765))
        window.request.setText(sys.argv[index + 1])
        window.submit()
        print(window.chat.toPlainText(), flush=True)
        window.close()
        QTimer.singleShot(0, app.quit)
        app.exec()
        return 0
    mobile = core.runtime.preferences.get("mobile", {})
    server = MobileServer(core, int(mobile.get("port", 8765)))
    if mobile.get("enabled", True):
        server.start()
    try:
        return run_desktop(core, server)
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
