# ZEN MA2 Agent

Portable-first grandMA2 onPC assistant runtime. ZEN runs beside MA2 on the
Windows console and exposes the same guarded workflow to its PySide6 desktop
workspace and to a paired phone on the local LAN. This release deliberately keeps AI
out of the control path: natural language is parsed into a typed intent, then a
deterministic command is safety-classified, previewed, and only sent after the
operator presses **Execute**.

## Run on Windows

```powershell
.\.venv\Scripts\python.exe main.py
```

No grandMA2 instance is required to open the UI. Use **Connect** after starting
grandMA2 onPC Telnet. Connection settings live in `config/settings.json`, which
is created beside the app so the folder can travel on a USB drive. Host, port,
and username are editable in the UI; password is masked and never stored.

`config/settings.json` contains only durable, non-secret connection settings:

```json
{
  "ma2": {
    "host": "127.0.0.1",
    "port": 30000,
    "username": ""
  }
}
```

Connection moves through `DISCONNECTED → TCP_CONNECTED → NEGOTIATING →
AUTHENTICATING → READY`. An empty username is blocked with `USERNAME REQUIRED`.
Changing Host, Port, or User while connected never changes the active socket;
the UI instead shows `Settings changed — reconnect required`.

## Included MVP flow

1. Rule parser: Chinese and English command phrases become `Intent` records.
2. Deterministic command builder: no LLM-generated command is executed.
3. Safety validator: `SAFE`, `MODIFY`, and `DANGEROUS` levels.
4. Structured action plan: every command is shown before execution.
5. Shared AgentCore: Desktop and mobile call the same planner, safety engine,
   preview, approval, and Telnet transport.
6. PySide6 dark desktop workspace with Chat, MA2 State, Skills, Plugins, Phone,
   Logs, and Settings pages.
7. Paired local-LAN mobile PWA at port `8765` by default. The QR contains only
   the selected LAN address and a pairing nonce; it never exposes a permanent
   secret. A six-digit pairing code is still required.
8. General MA2 State cache: Groups and Fixture inventory can be read through
   core-owned generic `List Group` / `List Fixture` providers when MA2 is READY.
9. Workflow-first Skill registry: each Skill may describe state dependencies,
   subtasks, multi-step commands, approval gates, verification, and recovery
   metadata. User-installed code is never auto-imported.

## Desktop and Phone

The main window starts the local mobile server automatically (default
`0.0.0.0:8765`). Open **Phone** in the desktop sidebar, choose the correct LAN
address if more than one is listed, then scan the QR code and enter the
displayed six-digit pairing code. The phone never connects to MA2 directly:

```text
Phone PWA → paired HTTP/WebSocket → AgentCore → Planner/Safety/Preview → MA2 Telnet
Desktop UI ───────────────────────┘
```

Connection configuration remains in **Settings → MA2 Connection**. Password is
masked, session-only, and is not written to JSON or audit logging.

## Portable build

Install dependencies into a project virtual environment, then run:

```powershell
.\.venv\Scripts\python.exe scripts\build_portable.py
```

The portable bundle is `dist\ZEN_MA2_Agent\ZEN_MA2_Agent.exe`. Its `web`,
`lua`, `skills`, `config`, `logs`, and `cache` resources resolve relative to the EXE, so
moving the folder to another USB drive letter is supported.

## Skills and Show State

Use **MA2 State** to refresh Groups or Fixture inventory, or ask in Chat:
`現在 Show 裡有哪些 Group？` / `List Fixtures`.

The initial executable builtins are Group Select, Set Dimmer, Fixture Select,
and Go Sequence. Geometry Clone, Auto Position, Effect Builder, Timecode
Offset, Show Diagnostics, and Programmer Inspect are explicit placeholders;
they do not claim to run yet.

See [Skill system](docs/SKILL_SYSTEM.md) and
[self-extension](docs/SELF_EXTENSION.md) for the controlled install boundary.

Supported examples:

- `選 Group BEAM` → `Group "BEAM"`
- `Beam 亮 30%` → `Group "BEAM"; At 30`
- `Go Sequence 5` → `Go Sequence 5`
- `選 Fixture 1 到 10` → `Fixture 1 Thru 10`
- `Blackout` → preview only; it remains unconfigured until the show-specific
  BO command template is deliberately set in preferences.

Run automated checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

See [architecture](docs/ARCHITECTURE.md) and the future
[geometry clone design](docs/GEOMETRY_CLONE.md).
