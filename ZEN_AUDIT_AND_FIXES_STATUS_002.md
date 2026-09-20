# ZEN MA2 Agent Status Report 002 (supersedes ZEN_MA2_AGENT_STATUS_REPORT.md for current status)

> **Current-state supersession (2026-09-20):** This report is still useful as
> historical audit evidence, but several implementation statements below have
> been superseded by committed repository state. Before acting on any "missing"
> item in this file, check `data/zen_project_control.json`,
> `ZEN_MULTI_PROVIDER_PARALLEL_POOL_001.md`, and the actual code.
>
> Current committed truths include:
>
> - the bounded four-role runtime `RESEARCHER -> LIGHTING_DESIGNER -> CRITIC -> FINALIZER` exists;
> - Designer and Critic can generate bounded parallel candidates across
>   independent providers;
> - the Provider Router supports expandable slots, `FREE_FIRST`, priorities,
>   role routing, and a lightweight local fallback;
> - the legacy PySide6/mobile UI is retired; OpenClaw is the intended operator UI;
> - the autonomous design artifact still has **no production-authorized direct
>   MA write path**; Safety / Resolver / deterministic Builder boundaries remain;
> - the current project gate is the one recorded in
>   `data/zen_project_control.json`, presently
>   `SHEESH_TEST_SHOW_VISUAL_OPERATOR_REVIEW_001`.
>

Assessment date: 2026-09-13
Assessment implementation HEAD at time of writing: `94e0bed` (main)

> **Runtime update (2026-09-13):** The original audit correctly found no
> orchestration at its assessment HEAD. A later bounded implementation now
> provides the portable sequential MVP `RESEARCHER -> LIGHTING_DESIGNER ->
> CRITIC -> FINALIZER`, with per-step checkpoints and final
> `zen.autonomous_design.v0.1` validation. It remains LLM-only and has no
> Resolver, Builder, or MA2 write path; the rest of this audit's implementation
> boundaries remain in force.

This report exists because `ZEN_MA2_AGENT_STATUS_REPORT.md` (2026-09-08) is now
five days and several architectural findings out of date. Read this one first
for "what is true right now"; the older report is historical evidence, not
current status. Do not treat any older report's READY/VERIFIED claims as
current without re-checking the actual code path.

## 1. What this audit changed

An external, code-path-level audit (not a docs-level review) on `53026a3`
found several places where documentation had drifted ahead of, or around,
what the code actually did. The following fixes landed on `main` as a direct
result and are now true of the current HEAD:

- `zen_ma2_agent/llm/autonomous_designer.py`'s `build_designer_context()` now
  routes `external_lighting_knowledge_pack_001.json` through
  `external_lighting_knowledge.build_shadow_knowledge_context()` instead of
  embedding the raw file. The `SHADOW_ONLY` / `promotion_state` gate that
  already existed in the codebase is now actually applied to what reaches the
  LLM-facing Designer Context. Before this fix, that gate existed but was
  never called from the only code path that matters.
- `zen_ma2_agent/llm/router.py`: `ProviderSlot` has an `OPENAI_COMPATIBLE_LOCAL`
  provider type that does not require `api_key` to be considered configured.
  Cloud types (`OPENAI_COMPATIBLE`, `OPENAI`) still require a non-empty key.
  The adapter omits the `Authorization` header entirely when no key is set.
- `zen_ma2_agent/protected_objects.py` is new: a single source of truth for
  any Sequence/Fixture no code path may touch. `ShowPlanBuilder._allocate_sequence`
  now hard-blocks protected numbers regardless of scan completeness (previous
  behavior relied entirely on the scanned Show profile correctly reporting a
  Sequence as "used" -- silent scan gaps had no second line of defense).
  **Per the project owner (2026-09-13): the active working Show is disposable
  test data. `PROTECTED_SEQUENCES` is therefore currently empty. `PROTECTED_FIXTURE_IDS`
  keeps `{9999}` protected.** If a future Show reuses real production
  Sequences, populate `PROTECTED_SEQUENCES` in that one file -- every caller
  (`builder/draft.py`, the two standalone scripts) already enforces whatever
  is there.
- Fixed a real drift bug found during the above: `scripts/real_packaged_real_song_smoke.py`
  had its own local copy of the protected-Sequence list and was missing `205`
  that the other script had. Both scripts now import from `protected_objects.py`.
- Fixed a second, independent real risk found while writing tests for the
  above: the shipped example/template inputs (`examples/FIRST_SONG_INPUT.json`,
  `examples/REALISTIC_SONG_ANALYSIS.json`, `examples/ZEN_REAL_LIGHTING_DESIGN_TEST.json`,
  and a shadow-advisory test fixture) all defaulted `active_sequence_range` to
  `[201, 300]` -- directly overlapping the (at the time) protected production
  Sequences. The only thing preventing an allocation collision was scan
  completeness. Examples now default to `[301, 400]`.
- `config/providers.private.env.example` and `zen_windows_start.ps1`'s
  `Open-ProviderSetup` now default to a CPU-only local llama.cpp setup
  (`OPENAI_COMPATIBLE_LOCAL`, `127.0.0.1:8080`, no API key, 180s timeout)
  matching the project owner's actual development machine (2014 MacBook Pro
  under Bootcamp: i7-4770HQ, 16GB DDR3, no discrete GPU), instead of a blank
  cloud-provider template.
- `portable.py`: `models` added to the allowed `portable_state_path` directories
  so downloaded GGUF weights live under `ZEN_HOME` and never enter Git.

Full test suite at time of writing: 362 passed. The 2 remaining failures
(`test_connection_settings`, `test_portable_resources`) are pre-existing,
Windows-path-format assertions that only pass on Windows and are unrelated to
any of the above.

## 2. What is still genuinely unverified or missing (do not assume otherwise)

These were true on `53026a3` and remain true after the fixes above -- none of
them were touched:

- **`main.py` does not import anything from `zen_ma2_agent.llm`.** "Start ZEN"
  from the desktop app or the Windows launcher menu runs the deterministic
  `AgentCore` / Qt desktop chat path only. The autonomous LLM Designer
  (`design_with_provider`, `ProviderRouter`) is only reachable via the
  `launcher/zen_portable_launcher.py --design-request` CLI flag. These two
  paths do not call each other.
- **There is no Resolver/Builder for the `zen.autonomous_design.v0.1` schema.**
  `design_with_provider()` validates the LLM's output and writes it to
  `projects/runs/<run_id>/design.json` via `write_run_provenance()`. Nothing
  downstream turns that JSON into MA2 actions. The only working Builder
  (`builder/draft.py: ShowPlanBuilder`) consumes a different, older, simpler
  schema (`designer/schema.py: SHOW_PLAN_SCHEMA`) that has no `virtual_rig`,
  `position_vocabulary`, or `free_cue_layer` fields. Writing this Resolver is
  the single highest-leverage next step and needs the project owner in the
  loop for the actual field-to-resource mapping decisions -- it is not a pure
  mechanical task.
- **No multi-agent orchestration exists anywhere in the codebase.** A repo-wide
  search for role names from the product vision (`RESEARCH_AGENT`,
  `SONG_ANALYSIS_AGENT`, `RIG_DESIGN_AGENT`, `CRITIC_AGENT`, `FINALIZER_AGENT`,
  etc.) returns zero matches. `design_with_provider()` is a single LLM call
  with one system prompt that asks for the entire Show Plan JSON at once.
  See `docs/MULTI_AGENT_DESIGN_PLAN.md` for the intended sequential-role
  design and why it is now also the right shape for the project owner's
  CPU-only hardware, independent of the original "act like a real department"
  motivation.
- **No research/retrieval pipeline exists.** The only outbound network call in
  the entire codebase is the LLM chat-completions POST in `llm/router.py`.
  `external_lighting_knowledge_pack_001.json` is a static, hand-authored set
  of 25 records, not the output of any research process.
- **No K-pop-style asymmetric virtual rig, no real Position Design, and no
  multi-pass Critic/Revise loop exist.** These remain design work, not code
  gaps that can be closed by writing more infrastructure alone.

## 3. How to use this file

If you are a coding agent (Claude Code or Codex) picking this project up:
read this file, then `docs/MULTI_AGENT_DESIGN_PLAN.md` and
`docs/CODING_AGENT_COLLABORATION.md`, before touching the Resolver/Builder
work in Section 2. Do not re-derive project status from the 2026-09-08 report
or from any `ZEN_*_00N.md` report whose date predates this file.
