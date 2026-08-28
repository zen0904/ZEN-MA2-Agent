# AgentCore architecture

```text
PySide6 Desktop ─┐
                 ├─> AgentCore → Rule parser → Intent schema → deterministic plan
Phone PWA/WS ────┘                                  ↓
                                      Intent router → Skill registry
                                                  ↓
                                    Task → subtasks → Workflow ActionPlan
                                                  ↓
                              Safety / approval gates / verification strategy
                                                  ↓
                                      Preview and approval lifecycle
                                                  ↓
                                      MA2 Telnet TCP client (user-configured)
```

The MVP never lets an LLM generate and immediately execute an MA command. A
future LLM may propose an `Intent`, but it must still use the same deterministic
builder, validator, preview, and explicit execution path.

`AgentCore` owns shared connection state, chat history, high-level progress,
state cache, Skills, workflow plans and their approval lifecycle. A workflow
may contain many ordered ActionSteps and graph dependencies, deterministic
calculation phases, conflict checks, batched commands, verification and
rollback/recovery metadata. The mobile LAN API may never call the
Telnet transport directly. Pairing tokens protect HTTP and WebSocket access;
the mobile PWA uses event push with reconnect rather than polling.

The initial generic state providers are read-only Groups and Fixture inventory.
They call core-owned `List Group` / `List Fixture` transports and cache parsed
records for every Skill; they are not tied to a particular show name.

The portable runtime resolves `config`, `data`, `logs`, `cache`, `web`, and
`lua` relative to the app folder. The frontend is PySide6, with a separate PWA
asset folder bundled by PyInstaller. Web research, local LLMs, advanced show
state and generated plugin installation remain explicitly future interfaces.
