from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from .models import SafetyLevel
from .runtime import AgentRuntime


class AgentUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.runtime = AgentRuntime()
        root.title("ZEN MA2 Agent — MVP")
        root.geometry("660x460")
        root.attributes("-topmost", True)
        self.status = tk.StringVar(value="Disconnected")
        self.request = tk.StringVar()
        self.preview = tk.Text(root, height=15, wrap="word", state="disabled")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="ZEN MA2 Agent", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        bar = ttk.Frame(frame); bar.pack(fill="x", pady=(8, 8))
        ttk.Label(bar, textvariable=self.status).pack(side="left")
        ttk.Button(bar, text="Connect", command=self.connect).pack(side="right")
        ttk.Label(frame, text="Natural-language request").pack(anchor="w")
        entry = ttk.Entry(frame, textvariable=self.request)
        entry.pack(fill="x", pady=(2, 8)); entry.bind("<Return>", lambda _event: self.make_preview())
        buttons = ttk.Frame(frame); buttons.pack(fill="x")
        ttk.Button(buttons, text="Preview", command=self.make_preview).pack(side="left")
        self.execute_button = ttk.Button(buttons, text="Execute", command=self.execute, state="disabled")
        self.execute_button.pack(side="left", padx=(8, 0))
        ttk.Label(frame, text="Structured plan / command preview").pack(anchor="w", pady=(12, 2))
        self.preview.pack(fill="both", expand=True)

    def show_preview(self, value: dict) -> None:
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
        self.preview.configure(state="disabled")

    def connect(self) -> None:
        try:
            banner = self.runtime.connect()
            self.status.set(f"Connected: {self.runtime.client.host}:{self.runtime.client.port} {banner[:60]}")
        except Exception as exc:
            self.status.set("Disconnected")
            messagebox.showerror("Connection failed", str(exc))

    def make_preview(self) -> None:
        try:
            plan = self.runtime.preview(self.request.get())
            self.show_preview({**plan.as_dict(), "connection": "connected" if self.runtime.client.connected else "disconnected"})
            self.execute_button.configure(state="normal" if plan.executable else "disabled")
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
            self.status.set("Command sent")
            self.show_preview({**plan.as_dict(), "execution_result": response or "sent (no immediate response)"})
        except Exception as exc:
            messagebox.showerror("Execution failed", str(exc))


def run() -> None:
    root = tk.Tk()
    AgentUI(root)
    root.mainloop()
