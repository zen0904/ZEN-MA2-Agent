from __future__ import annotations

import io
import json
from pathlib import Path

import qrcode
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget)

from .core import AgentCore
from .desktop_automation import DesktopAutomationBridge
from .build_identity import display_build_identity
from .telnet_client import ConnectionState
from .web_server import MobileServer


THEME = """
QWidget{background:#0b0f14;color:#e8edf2;font:13px 'Segoe UI';}QFrame#top{background:#121922;border-bottom:1px solid #2a3643;}QListWidget{background:#10161e;border:0;color:#b9c4cf;padding:8px;}QListWidget::item{padding:10px 12px;}QListWidget::item:selected{background:#19222d;color:#fff;border-left:3px solid #5fa8ff;}QTextEdit,QLineEdit,QComboBox{background:#121922;border:1px solid #2a3643;padding:8px;color:#e8edf2;}QPushButton{background:#19222d;border:1px solid #2a3643;padding:8px 13px;color:#e8edf2;}QPushButton:hover{border-color:#5fa8ff;}QPushButton#execute{background:#1d5f4a;border-color:#44c98a;}QLabel#muted{color:#93a1af;}QFrame#card{background:#121922;border-left:3px solid #e3ad54;padding:10px;}
"""


CHAT_BOTTOM_THRESHOLD = 36


class ZenDesktop(QMainWindow):
    def __init__(self, core: AgentCore, server: MobileServer):
        super().__init__()
        self.core, self.server = core, server
        self.setWindowTitle("ZEN MA2 Agent")
        self.resize(1180, 760)
        self.setMinimumSize(960, 620)
        self._build()
        self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(120)
        self.refresh()

    def _build(self) -> None:
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        top = QFrame(); top.setObjectName("top"); bar = QHBoxLayout(top); bar.setContentsMargins(18, 12, 18, 12)
        title = QLabel("ZEN MA2 Agent"); title.setStyleSheet("font-size:18px;font-weight:700;"); bar.addWidget(title); bar.addStretch()
        self.status = QLabel(); self.status.setStyleSheet("color:#44c98a;font-weight:600;"); bar.addWidget(self.status)
        outer.addWidget(top)
        split = QSplitter(); split.setChildrenCollapsible(False)
        self.nav = QListWidget(); self.nav.addItems(["Chat", "MA2 State", "Skills", "Plugins", "Phone", "Logs", "Settings"]); self.nav.setFixedWidth(175)
        self.pages = QStackedWidget(); self.pages.addWidget(self._chat_page()); self.pages.addWidget(self._state_page()); self.pages.addWidget(self._skills_page()); self.pages.addWidget(self._plugins_page()); self.pages.addWidget(self._phone_page()); self.pages.addWidget(self._logs_page()); self.pages.addWidget(self._settings_page())
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex); self.nav.setCurrentRow(0)
        split.addWidget(self.nav); split.addWidget(self.pages); split.setStretchFactor(1, 1); outer.addWidget(split); self.setCentralWidget(root)

    def _chat_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(18, 16, 18, 16)
        self.chat = QTextEdit(readOnly=True); self.chat.setPlaceholderText("Conversation history appears here."); layout.addWidget(self.chat, 1)
        self.plan = QFrame(); self.plan.setObjectName("card"); plan_layout = QVBoxLayout(self.plan); self.plan_text = QLabel("No action plan pending."); self.plan_text.setWordWrap(True); plan_layout.addWidget(self.plan_text); actions = QHBoxLayout(); self.cancel = QPushButton("Cancel"); self.execute = QPushButton("Execute"); self.execute.setObjectName("execute"); actions.addWidget(self.cancel); actions.addStretch(); actions.addWidget(self.execute); plan_layout.addLayout(actions); layout.addWidget(self.plan)
        input_bar = QHBoxLayout(); self.request = QLineEdit(); self.request.setPlaceholderText("Ask ZEN about your MA2 show or type a command…"); send = QPushButton("Send"); send.clicked.connect(self.submit); self.request.returnPressed.connect(self.submit); input_bar.addWidget(self.request, 1); input_bar.addWidget(send); layout.addLayout(input_bar)
        self.cancel.clicked.connect(self.cancel_action); self.execute.clicked.connect(self.execute_action); return page

    def _state_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 20); title = QLabel("MA2 State"); title.setStyleSheet("font-size:18px;font-weight:700;"); layout.addWidget(title); buttons = QHBoxLayout()
        for label, resource in [("Groups","groups"),("Fixtures","fixtures"),("Layouts","layouts"),("Sequences","sequences"),("Presets","presets"),("Effects","effects"),("Timecodes","timecodes"),("Pages","pages"),("Executors","executors")]:
            button=QPushButton(f"Refresh {label}"); button.clicked.connect(lambda _checked=False, name=resource: self.refresh_state(name)); buttons.addWidget(button)
        buttons.addStretch(); layout.addLayout(buttons); self.state_list = QTextEdit(readOnly=True); layout.addWidget(self.state_list); return page

    def _skills_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 20)
        title = QLabel("Skills"); title.setStyleSheet("font-size:18px;font-weight:700;"); layout.addWidget(title)
        self.skill_picker = QComboBox(); self.skill_picker.currentIndexChanged.connect(self.inspect_skill); layout.addWidget(self.skill_picker)
        self.skills_view = QTextEdit(readOnly=True); layout.addWidget(self.skills_view, 1)
        buttons = QHBoxLayout(); enable = QPushButton("Enable"); disable = QPushButton("Disable"); inspect = QPushButton("Inspect"); enable.clicked.connect(lambda: self.set_skill_enabled(True)); disable.clicked.connect(lambda: self.set_skill_enabled(False)); inspect.clicked.connect(self.inspect_skill); buttons.addWidget(enable); buttons.addWidget(disable); buttons.addStretch(); buttons.addWidget(inspect); layout.addLayout(buttons)
        return page

    def _plugins_page(self) -> QWidget:
        return self._info_page("Plugins", "Built-in Plugins\nZEN_AGENT.lua — grandMA2 adapter scaffold — Not installed / not verified\n\nGenerated Plugins\nNot available yet")

    def _logs_page(self) -> QWidget:
        page = self._info_page("Logs", "Audit and debug records are written under portable logs/. Raw Telnet output is not shown in the primary workspace."); return page

    def _info_page(self, title: str, text: str) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 20); label = QLabel(title); label.setStyleSheet("font-size:18px;font-weight:700;"); layout.addWidget(label); content = QLabel(text); content.setWordWrap(True); content.setObjectName("muted"); layout.addWidget(content); layout.addStretch(); return page

    def _phone_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 20); title = QLabel("Mobile Control"); title.setStyleSheet("font-size:18px;font-weight:700;"); layout.addWidget(title); self.addresses = QComboBox(); self.addresses.currentIndexChanged.connect(self.refresh_qr); layout.addWidget(self.addresses); self.phone_url = QLabel(); self.phone_url.setTextInteractionFlags(Qt.TextSelectableByMouse); layout.addWidget(self.phone_url); self.pairing = QLabel(); self.pairing.setStyleSheet("font-size:25px;font-weight:700;letter-spacing:5px;"); layout.addWidget(self.pairing); self.qr = QLabel(); self.qr.setAlignment(Qt.AlignLeft); layout.addWidget(self.qr); note = QLabel("Pairing code is required after scanning QR. QR contains only a short-lived pairing nonce, never a permanent control secret."); note.setWordWrap(True); note.setObjectName("muted"); layout.addWidget(note); layout.addStretch(); return page

    def _settings_page(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 20, 22, 20); title = QLabel("Settings — MA2 Connection"); title.setStyleSheet("font-size:18px;font-weight:700;"); layout.addWidget(title); form = QFormLayout(); ma2 = self.core.runtime.preferences["ma2"]; self.host = QLineEdit(ma2["host"]); self.port = QLineEdit(str(ma2["port"])); self.user = QLineEdit(ma2["username"]); self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password); form.addRow("Host", self.host); form.addRow("Port", self.port); form.addRow("Username", self.user); form.addRow("Password", self.password); layout.addLayout(form); buttons = QHBoxLayout(); connect = QPushButton("Connect"); disconnect = QPushButton("Disconnect"); connect.clicked.connect(self.connect); disconnect.clicked.connect(self.disconnect); buttons.addWidget(connect); buttons.addWidget(disconnect); layout.addLayout(buttons); self.internet_mode = QComboBox(); self.internet_mode.addItems(["AUTO", "OFFLINE", "ONLINE"]); self.internet_mode.setCurrentText(self.core.runtime.preferences.get("internet_access", "AUTO")); self.internet_mode.currentTextChanged.connect(self.core.set_internet_access); form.addRow("Internet access", self.internet_mode); note = QLabel("Research engine is not implemented in this release."); note.setObjectName("muted"); layout.addWidget(note); build = QLabel(display_build_identity(getattr(self.core, "build_identity", {}))); build.setObjectName("muted"); build.setTextInteractionFlags(Qt.TextSelectableByMouse); layout.addWidget(build); layout.addStretch(); return page

    def submit(self) -> None:
        text = self.request.text().strip()
        if text: self.core.handle_request(text, source="desktop"); self.request.clear(); self.refresh()

    def preview_real_song_test(self) -> None:
        """Preview the one bundled integration fixture through the Desktop Core.

        This is deliberately not exposed in the operator UI. The localhost
        automation bridge uses it only for packaged real-machine verification;
        the fixture is fixed, typed JSON and cannot carry raw MA commands.
        """
        source = self.core.runtime.root / "examples" / "ZEN_REAL_LIGHTING_DESIGN_TEST.json"
        analysis = json.loads(source.read_text(encoding="utf-8"))
        self.core.preview_song_analysis(analysis)
        self.refresh()

    def execute_action(self) -> None:
        action = next((item for item in self.core.actions.values() if item.status == "PENDING_APPROVAL"), None)
        if not action: return
        try:
            dangerous = action.plan["safety"] == "DANGEROUS"
            if dangerous and QMessageBox.question(self, "Confirm dangerous action", "This action is marked DANGEROUS. Execute it?") != QMessageBox.Yes:
                return
            self.core.approve_action(action.id, danger_confirmed=dangerous)
        except Exception as exc: QMessageBox.warning(self, "Cannot execute", str(exc))
        self.refresh()

    def cancel_action(self) -> None:
        action = next((item for item in self.core.actions.values() if item.status == "PENDING_APPROVAL"), None)
        if action: self.core.cancel_action(action.id)
        self.refresh()

    def connect(self) -> None:
        try: self.core.connect(self.host.text(), self.port.text(), self.user.text(), self.password.text())
        except Exception as exc: QMessageBox.warning(self, "Connection", str(exc))
        self.refresh()

    def disconnect(self) -> None:
        self.core.disconnect(); self.refresh()

    def refresh_state(self, resource: str) -> None:
        try:
            self.core.refresh_state(resource)
        except Exception as exc:
            QMessageBox.warning(self, "MA2 State", str(exc))
        self.refresh()

    def set_skill_enabled(self, enabled: bool) -> None:
        skill_id = self.skill_picker.currentData()
        if not skill_id:
            return
        try:
            self.core.set_skill_enabled(skill_id, enabled)
        except Exception as exc:
            QMessageBox.warning(self, "Skill", str(exc))
        self.refresh()

    def inspect_skill(self) -> None:
        skill_id = self.skill_picker.currentData()
        if not skill_id or not hasattr(self, "skills_view"):
            return
        try:
            manifest = self.core.skills.get(skill_id).summary()
            self._update_text(self.skills_view, "\n".join(f"{key}: {value}" for key, value in manifest.items()))
        except Exception:
            pass

    def refresh_qr(self) -> None:
        url = self.addresses.currentData()
        if not url: return
        self.phone_url.setText(url); image = qrcode.make(url); buffer = io.BytesIO(); image.save(buffer, format="PNG"); pix = QPixmap(); pix.loadFromData(buffer.getvalue()); self.qr.setPixmap(pix.scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    @staticmethod
    def _update_text(view: QTextEdit, text: str, *, follow_bottom: bool = False) -> bool:
        """Update a document without stealing a user's scroll position.

        QTextEdit.setPlainText() replaces the QTextDocument and normally resets its
        vertical scrollbar.  Refreshes run frequently for connection status, so a
        no-op update must stay a no-op.  Chat is the sole view allowed to follow
        new content, and only when the operator was already reading its bottom.
        """
        if view.toPlainText() == text:
            return False
        scrollbar = view.verticalScrollBar()
        previous_value = scrollbar.value()
        was_near_bottom = scrollbar.maximum() - previous_value < CHAT_BOTTOM_THRESHOLD
        view.setPlainText(text)
        if follow_bottom and was_near_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(min(previous_value, scrollbar.maximum()))
        return True

    def _refresh_skills(self, skills: list[dict]) -> None:
        """Keep the existing picker and details document when registry data is unchanged."""
        entries = [(item["name"], item["source"], item["safety"], item["enabled"], item["id"]) for item in skills]
        if entries == getattr(self, "_skill_entries", None):
            return
        self._skill_entries = entries
        old_skill = self.skill_picker.currentData()
        self.skill_picker.blockSignals(True)
        self.skill_picker.clear()
        for name, source, safety, enabled, skill_id in entries:
            self.skill_picker.addItem(f"{name} — {source} — {safety} — {'Enabled' if enabled else 'Disabled'}", skill_id)
        self.skill_picker.blockSignals(False)
        if skills:
            self.skill_picker.setCurrentIndex(next((index for index, item in enumerate(skills) if item["id"] == old_skill), 0))
            self.inspect_skill()

    def refresh(self) -> None:
        self.core.tick(); snap = self.core.snapshot(); c = snap["connection"]; color = {"READY":"#44c98a", "AUTHENTICATING":"#e3ad54", "AUTH_FAILED":"#e16868"}.get(c["state"], "#93a1af"); self.status.setStyleSheet(f"color:{color};font-weight:600;"); self.status.setText(f"● MA2 {c['state']} | {c['user'] or c['host']} | {c['host']}:{c['port']}   Internet ● {snap['internet']}   Phone ● {snap['phone_connected']} Connected")
        self._update_text(self.chat, "\n\n".join(f"{m['role'].upper()}\n{m['text']}" for m in snap["chat"]), follow_bottom=True)
        pending = next((item for item in snap["actions"] if item["status"] == "PENDING_APPROVAL"), None); self.execute.setEnabled(bool(pending and c["ready"])); self.cancel.setEnabled(bool(pending)); self.plan_text.setText("No action plan pending." if not pending else f"ACTION PLAN\nTarget: {pending['intent']['parameters']}\nCommand: {pending['command']}\nSafety: {pending['safety']}\n{pending['preview_note']}")
        state_lines = []
        diagnostics = snap.get("diagnostics")
        if diagnostics:
            checked = next((item["updated_at"] for item in snap["state_browser"].values() if item["updated_at"]), "Not checked")
            counts = diagnostics["counts"]
            state_lines.append(f"Show Diagnostics — {diagnostics['status']}\nErrors: {counts['ERROR']}  Warnings: {counts['WARNING']}  Info: {counts['INFO']}\nLast checked: {checked}")
        for name, value in snap["state_browser"].items():
            if value["status"] == "available":
                state_lines.append(f"{name.title()} — {value['count']} items\n" + "\n".join(str(item) for item in value["values"]))
            else:
                state_lines.append(f"{name.title()} — {value['status']}")
        self._update_text(self.state_list, "\n\n".join(state_lines))
        self._refresh_skills(snap["skills"])
        urls = self.core.phone_urls(self.server.port); old = self.addresses.currentData(); self.addresses.blockSignals(True); self.addresses.clear(); [self.addresses.addItem(url, url) for url in urls]; self.addresses.blockSignals(False); self.pairing.setText(f"Pairing code: {self.core.pairing.code}");
        if urls and old not in urls: self.addresses.setCurrentIndex(0); self.refresh_qr()


def run_desktop(core: AgentCore, server: MobileServer, *, automation_port: int | None = None) -> int:
    app = QApplication.instance() or QApplication([]); app.setStyleSheet(THEME); window = ZenDesktop(core, server)
    bridge = DesktopAutomationBridge(window, port=automation_port) if automation_port is not None else None
    if bridge:
        bridge.start()
    window.show()
    try:
        return app.exec()
    finally:
        if bridge:
            bridge.stop()
