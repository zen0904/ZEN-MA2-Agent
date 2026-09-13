# Portable USB Runtime

`ZEN_HOME` is the directory containing `run_zen_windows.cmd` or
`run_zen_macos.command`. Launchers derive it from their own location; neither a
drive letter nor a user home directory is part of the contract.

The source working copy lives at `ZEN_HOME/repo/ZEN-MA2-Agent` and retains its
`.git` history. Mutable state stays at `ZEN_HOME/{config,knowledge,show_context,
projects,logs,cache,temp,secrets}`. `secrets/providers.private.env` is
USB-local, ignored by Git, and must never be copied into reports or logs.

## Providers

Three configurable slots are supported. Set a slot's `TYPE`, `MODEL`,
`BASE_URL`, and `API_KEY` in `secrets/providers.private.env`; the current
implemented adapter accepts `OPENAI_COMPATIBLE` endpoints. `PRIMARY_ONLY`,
`FALLBACK`, and `ROUTED` select eligible configured slots without embedding a
vendor in artistic logic. A missing or unreachable provider means
`AUTONOMOUS_DESIGNER_AVAILABLE = NO`; deterministic legacy designers must not
be represented as autonomous LLM output.

Use `run_zen_windows.cmd --provider-self-test` before an autonomous design
run. The launcher never emits keys. `--git-status`, `--update`, and `--push`
operate on the USB copy only; automatic pull is limited to a clean, behind,
fast-forward-able `main`. Dirty or diverged work is preserved for review.

## Autonomous boundary

The provider receives a bounded, provenance-bearing Designer Context, not a
repository dump. It must return `zen.autonomous_design.v0.1` JSON. Raw MA2,
Telnet, Lua, and shell command fields are rejected. A separate deterministic
compiler/approval layer remains the only MA2 command boundary.

`runtime/*` may contain a portable Python environment. If unavailable, use
`--bootstrap-runtime` to create one on the USB with an installed host Python;
the host Python is a bootstrap dependency, not durable Agent state.
