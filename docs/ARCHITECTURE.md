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

The General State layer is frontend-independent and read-only. Groups,
Fixtures, Layout Pool inventory, Sequences and Cue metadata use allow-listed
`List` commands. Local onPC Group membership uses a dedicated Export XML
provider; it is available only when the Agent can read the MA2 `importexport`
filesystem and otherwise reports `REMOTE_EXPORT_ACCESS_UNAVAILABLE`. Layout
object XY uses the bundled `ZEN_AGENT` Lua Echo protocol. Selection and
Programmer are never inferred by changing MA2 selection or clearing the
programmer: when no verified accessor is available they report `UNSUPPORTED`.

```text
Chat / Desktop / Mobile → AgentCore.refresh_state()
      → allow-listed List provider OR local Export XML provider OR read-only ZEN_AGENT adapter
      → parser validates only typed records
      → StateStore(resource, values, timestamp, source, stale, error)
```

`StateStore` currently holds `groups`, `fixtures`, `group_membership`,
`layouts`, `selection`, `programmer`, `sequences`, and `cues`. It is shared by
Desktop, mobile HTTP/WebSocket, and future Skills; no provider is Clone-specific.
Disconnect marks cached state stale. A successful refresh replaces that stale
entry. Provider errors are cached rather than converted into invented state.

The portable runtime resolves `config`, `data`, `logs`, `cache`, `web`, and
`lua` relative to the app folder. The frontend is PySide6, with a separate PWA
asset folder bundled by PyInstaller. Web research, local LLMs, advanced show
state and generated plugin installation remain explicitly future interfaces.
