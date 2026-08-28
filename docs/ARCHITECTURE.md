# AgentCore architecture

```text
PySide6 Desktop ─┐
                 ├─> AgentCore → Rule parser → Intent schema → deterministic plan
Phone PWA/WS ────┘                                  ↓
                                             Safety validator
                                                  ↓
                                      Preview and approval lifecycle
                                                  ↓
                                      MA2 Telnet TCP client (user-configured)
```

The MVP never lets an LLM generate and immediately execute an MA command. A
future LLM may propose an `Intent`, but it must still use the same deterministic
builder, validator, preview, and explicit execution path.

`AgentCore` owns shared connection state, chat history, high-level progress,
plans and their approval lifecycle. The mobile LAN API may never call the
Telnet transport directly. Pairing tokens protect HTTP and WebSocket access;
the mobile PWA uses event push with reconnect rather than polling.

The portable runtime resolves `config`, `data`, `logs`, `cache`, `web`, and
`lua` relative to the app folder. The frontend is PySide6, with a separate PWA
asset folder bundled by PyInstaller. Web research, local LLMs, advanced show
state and generated plugin installation remain explicitly future interfaces.
