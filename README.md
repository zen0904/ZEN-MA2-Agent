# ZEN MA2 Agent — MVP

Portable-first grandMA2 onPC assistant runtime. This MVP deliberately keeps AI
out of the control path: natural language is parsed into a typed intent, then a
deterministic command is safety-classified, previewed, and only sent after the
operator presses **Execute**.

## Run on Windows

```powershell
py -3 main.py
```

No grandMA2 instance is required to open the UI. Use **Connect** after starting
grandMA2 onPC Telnet (default `127.0.0.1:30000`). Connection settings live in
`data/user_preferences.json`, which is created beside the app so the folder can
travel on a USB drive.

## Included MVP flow

1. Rule parser: Chinese and English command phrases become `Intent` records.
2. Deterministic command builder: no LLM-generated command is executed.
3. Safety validator: `SAFE`, `MODIFY`, and `DANGEROUS` levels.
4. Preview pane: every command is shown before execution.
5. Telnet TCP transport, optional login command, result log, and small Tk UI.

Supported examples:

- `選 Group BEAM` → `Group "BEAM"`
- `Beam 亮 30%` → `Group "BEAM"; At 30`
- `Go Sequence 5` → `Go Sequence 5`
- `選 Fixture 1 到 10` → `Fixture 1 Thru 10`
- `Blackout` → preview only; it remains unconfigured until the show-specific
  BO command template is deliberately set in preferences.

Run automated checks with:

```powershell
py -3 -m unittest discover -s tests -v
```

See [architecture](docs/ARCHITECTURE.md) and the future
[geometry clone design](docs/GEOMETRY_CLONE.md).
