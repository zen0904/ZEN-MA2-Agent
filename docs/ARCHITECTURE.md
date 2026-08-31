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
`layouts`, `layout_items`, `selection`, `programmer`, `sequences`, `cues`,
`presets`, `effects`, `pages`, and `executors`. It is shared by
Desktop, mobile HTTP/WebSocket, and future Skills; no provider is Clone-specific.
Disconnect marks cached state stale. A successful refresh replaces that stale
entry. Provider errors are cached rather than converted into invented state.

Show Diagnostics v1 is a frontend-independent SAFE read-only workflow inside
`AgentCore`. It refreshes supported snapshots, keeps provider errors and stale
timestamps as findings, then evaluates deterministic rules. `DiagnosticFinding`
contains an id, category, severity, summary, details, object identity, source,
confidence, and suggested action. Empty Preset/Effect/Sequence pools are valid;
unsupported Layout fixture geometry is capability information, never evidence
that a Layout has no fixture items. Desktop and mobile render the same report.

For test-only packaged Desktop verification, an optional localhost bridge can
be enabled with an explicit command-line flag or environment variable. Its
socket worker posts fixed test actions to the `ZenDesktop` QObject, so actual
Connect and Send handlers run on the Qt GUI thread. It is absent in normal
startup, binds only `127.0.0.1`, and deliberately exposes neither preferences,
passwords, raw Telnet, code execution, nor filesystem access.

The portable runtime resolves `config`, `data`, `logs`, `cache`, `web`, and
`lua` relative to the app folder. The frontend is PySide6, with a separate PWA
asset folder bundled by PyInstaller. Web research, local LLMs, advanced show
state and generated plugin installation remain explicitly future interfaces.
