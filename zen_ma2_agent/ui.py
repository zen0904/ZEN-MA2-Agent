from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from .models import SafetyLevel
from .runtime import AgentRuntime
from .telnet_client import ConnectionState


class AgentUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.runtime = AgentRuntime()
        root.title("ZEN MA2 Agent — MVP")
        root.geometry("660x530")
        root.attributes("-topmost", True)
        ma2 = self.runtime.preferences["ma2"]
        self.host = tk.StringVar(value=ma2["host"])
        self.port = tk.StringVar(value=str(ma2["port"]))
        self.username = tk.StringVar(value=ma2["username"])
        self.password = tk.StringVar()
        self.status = tk.StringVar(value=self.runtime.status_text())
        self.request = tk.StringVar()
        self.preview = tk.Text(root, height=13, wrap="word", state="disabled")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="ZEN MA2 Agent", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        connection = ttk.LabelFrame(frame, text="MA2 Connection", padding=8)
        connection.pack(fill="x", pady=(8, 10))
        ttk.Label(connection, text="Host").grid(row=0, column=0, sticky="w")
        ttk.Entry(connection, textvariable=self.host, width=26).grid(row=0, column=1, sticky="ew", padx=(4, 12))
        ttk.Label(connection, text="Port").grid(row=0, column=2, sticky="w")
        ttk.Entry(connection, textvariable=self.port, width=8).grid(row=0, column=3, sticky="ew", padx=(4, 0))
        ttk.Label(connection, text="User").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(connection, textvariable=self.username, width=26).grid(row=1, column=1, sticky="ew", padx=(4, 12), pady=(6, 0))
        ttk.Label(connection, text="Password").grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Entry(connection, textvariable=self.password, width=8, show="•").grid(row=1, column=3, sticky="ew", padx=(4, 0), pady=(6, 0))
        actions = ttk.Frame(connection); actions.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 0))
        self.connect_button = ttk.Button(actions, text="Connect", command=self.connect)
        self.connect_button.pack(side="left")
        self.disconnect_button = ttk.Button(actions, text="Disconnect", command=self.disconnect)
        self.disconnect_button.pack(side="left", padx=(8, 0))
        connection.columnconfigure(1, weight=1)
        for variable in (self.host, self.port, self.username):
            variable.trace_add("write", self._settings_changed)
        for child in connection.winfo_children():
            if isinstance(child, ttk.Entry):
                child.bind("<FocusOut>", self._save_settings_on_focus_out)
        ttk.Label(frame, textvariable=self.status, justify="left").pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, text="Natural-language request").pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.request)
        entry.pack(fill="x", pady=(2, 8)); entry.bind("<Return>", lambda _event: self.make_preview())
        buttons = ttk.Frame(frame); buttons.pack(fill="x")
        ttk.Button(buttons, text="Preview", command=self.make_preview).pack(side="left")
        self.execute_button = ttk.Button(buttons, text="Execute", command=self.execute, state="disabled")
        self.execute_button.pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="Structured plan / command preview").pack(anchor="w", pady=(12, 2))
        self.preview.pack(fill="both", expand=True)
        self._refresh_controls()

    def _settings_changed(self, *_args) -> None:
        if self.runtime.state is not ConnectionState.DISCONNECTED:
            self.runtime.reconnect_required = True
            self.status.set(self.runtime.status_text())
            self._refresh_controls()

    def _save_settings_on_focus_out(self, _event=None) -> None:
        try:
            self.runtime.update_connection_settings(self.host.get(), self.port.get(), self.username.get())
            self.status.set(self.runtime.status_text())
        except Exception as exc:
            self.status.set(f"Settings invalid: {exc}")

    def _refresh_controls(self) -> None:
        connected = self.runtime.state is not ConnectionState.DISCONNECTED
        self.connect_button.configure(state="disabled" if connected else "normal")
        self.disconnect_button.configure(state="normal" if connected else "disabled")
        plan_ok = bool(self.runtime.current_plan and self.runtime.current_plan.executable)
        self.execute_button.configure(state="normal" if plan_ok and self.runtime.ready else "disabled")

    def show_preview(self, value: dict) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
        self.preview.configure(state="disabled")

    def connect(self) -> None:
        try:
            self.runtime.connect(self.host.get(), self.port.get(), self.username.get(), self.password.get())
            self.status.set(self.runtime.status_text())
            self._refresh_controls()
        except Exception as exc:
            self.status.set(self.runtime.status_text())
            messagebox.showerror("Connection failed", str(exc))

    def disconnect(self) -> None:
        self.runtime.disconnect()
        self.status.set(self.runtime.status_text())
        self._refresh_controls()

    def make_preview(self) -> None:
        try:
            plan = self.runtime.preview(self.request.get())
            self.show_preview({**plan.as_dict(), "connection": self.runtime.status_text()})
            self._refresh_controls()
        except Exception as exc:
            self.execute_button.configure(state="disabled")
            messagebox.showwarning("Cannot build plan", str(exc))

    def execute(self) -> None:
        plan = self.runtime.current_plan
        if not plan:
            return
        if plan.safety is SafetyLevel.DANGEROUS and not messagebox.askyesno("Dangerous command", "This is a dangerous operation. Execute the approved preview?"):
            return
        try:
            response = self.runtime.execute_current()
            self.show_preview({**plan.as_dict(), "execution_result": response or "sent (no immediate response)"})
        except Exception as exc:
            messagebox.showerror("Execution failed", str(exc))


def run() -> None:
    root = tk.Tk()
    AgentUI(root)
    root.mainloop()
