import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from zen_ma2_agent.desktop import ZenDesktop


class DesktopCore:
    """Small stable core fixture for exercising the real PySide desktop widgets."""

    def __init__(self):
        self.runtime = SimpleNamespace(preferences={
            "ma2": {"host": "127.0.0.1", "port": 30000, "username": "MM"},
            "internet_access": "AUTO",
        })
        self.pairing = SimpleNamespace(code="123456")
        self.connection = {"state": "READY", "ready": True, "host": "127.0.0.1", "port": 30000, "user": "MM"}
        self.chat = []
        self.state_browser = {"groups": {"status": "Not available yet", "count": 0, "values": []}}

    def tick(self):
        pass

    def snapshot(self):
        return {
            "connection": dict(self.connection),
            "internet": "OFFLINE",
            "phone_connected": 0,
            "progress": "Idle",
            "chat": list(self.chat),
            "actions": [],
            "state_browser": self.state_browser,
            "skills": [],
            "proposals": [],
        }

    def phone_urls(self, _port):
        return []

    def set_internet_access(self, mode):
        self.runtime.preferences["internet_access"] = mode


class DesktopScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.core = DesktopCore()
        self.window = ZenDesktop(self.core, SimpleNamespace(port=8765))
        self.window.timer.stop()
        self.window.resize(960, 700)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def _load_long_chat(self):
        self.core.chat = [{"role": "assistant", "text": "\n".join(f"Chat line {index}" for index in range(260))}]
        self.window.refresh()
        self.app.processEvents()
        scrollbar = self.window.chat.verticalScrollBar()
        self.assertGreater(scrollbar.maximum(), 0)
        return scrollbar

    def _load_long_state(self):
        self.core.state_browser = {"groups": {"status": "available", "count": 180, "values": [f"Group {index}" for index in range(180)]}}
        self.window.refresh()
        self.window.nav.setCurrentRow(1)
        self.app.processEvents()
        scrollbar = self.window.state_list.verticalScrollBar()
        self.assertGreater(scrollbar.maximum(), 0)
        return scrollbar

    def test_connection_refresh_keeps_chat_scroll_position(self):
        scrollbar = self._load_long_chat()
        scrollbar.setValue(scrollbar.maximum() // 2)
        expected = scrollbar.value()
        self.core.connection["state"] = "AUTHENTICATING"
        self.window.refresh()
        self.assertEqual(scrollbar.value(), expected)

    def test_chat_only_follows_new_messages_when_already_at_bottom(self):
        scrollbar = self._load_long_chat()
        scrollbar.setValue(scrollbar.maximum() // 2)
        expected = scrollbar.value()
        self.core.chat.append({"role": "assistant", "text": "New message while reviewing history"})
        self.window.refresh()
        self.assertEqual(scrollbar.value(), expected)

        scrollbar.setValue(scrollbar.maximum())
        self.core.chat.append({"role": "assistant", "text": "New message at live edge"})
        self.window.refresh()
        self.assertEqual(scrollbar.value(), scrollbar.maximum())

    def test_state_refresh_and_repeated_timer_refresh_do_not_drift_scroll(self):
        scrollbar = self._load_long_state()
        scrollbar.setValue(scrollbar.maximum() // 2)
        expected = scrollbar.value()
        self.core.state_browser["groups"] = {"status": "available", "count": 181, "values": [f"Group {index}" for index in range(181)]}
        self.window.refresh()
        self.assertEqual(scrollbar.value(), expected)
        for _ in range(20):
            self.core.connection["state"] = "READY"
            self.window.refresh()
        self.assertEqual(scrollbar.value(), expected)

    def test_page_switch_preserves_chat_scroll_position(self):
        scrollbar = self._load_long_chat()
        scrollbar.setValue(scrollbar.maximum() // 2)
        expected = scrollbar.value()
        self.window.nav.setCurrentRow(1)
        self.app.processEvents()
        self.window.nav.setCurrentRow(0)
        self.app.processEvents()
        self.assertEqual(scrollbar.value(), expected)


if __name__ == "__main__":
    unittest.main()
