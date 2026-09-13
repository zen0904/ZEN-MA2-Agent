# Coding Agent Collaboration: Claude Code and Codex on This Repo

The project owner uses both Claude Code and Codex (and this chat surface) on
this repository, sometimes in the same session with the project owner, and
sometimes as a longer unattended run. Both tools read `AGENTS.md` on startup;
this file adds the working agreement that `AGENTS.md` alone does not fully
cover.

## Rule 1: alternate, do not run concurrently

Do not run Claude Code and Codex against this repository at the same time.
Two agents editing the same working tree at once produces git conflicts, and
on the project owner's current hardware (see
`docs/MULTI_AGENT_DESIGN_PLAN.md`) it also means two agentic processes
competing for the same 16GB of RAM and 4 CPU cores that local-model inference
will also need. Whichever tool is not actively being used should not be left
running against this repo.

## Rule 2: git commit is the handoff, not a shared file or verbal summary

Whoever is working finishes a change at a point where the test suite passes,
commits, and stops there. The next agent or session (Claude Code, Codex, or
this chat) starts from `git log` and the current working tree state, per
`AGENTS.md`'s existing instruction to recover state from the repository
rather than from what was "discussed most recently." Do not leave
uncommitted work and describe it in prose for the next session to
reconstruct -- reconstruct-from-conversation is exactly the failure mode
`AGENTS.md` already warns against.

## Rule 3: risk-tiered task assignment

**Keep in an interactive, one-step-at-a-time session with the project owner
present** (this chat, or an interactive Claude Code/Codex session where the
owner is watching and approving each step):

- Any change to `zen_ma2_agent/protected_objects.py`, the write path in
  `builder/draft.py`, or provider authentication in `llm/router.py`.
- Designing the Resolver/Builder for `zen.autonomous_design.v0.1`
  (`ZEN_AUDIT_AND_FIXES_STATUS_002.md` Section 2) -- the field-to-resource
  mapping is a design decision, not a mechanical port.
- Writing the per-role system prompts for the multi-agent pipeline
  (`docs/MULTI_AGENT_DESIGN_PLAN.md`) -- wording is what decides what each
  role believes it is allowed to decide.

**Safe to hand to an unattended agent session** (e.g. a Codex run started
before the project owner steps away, checked on later):

- Adding test coverage for already-existing, already-decided behavior.
- Implementing one already-agreed, already-schema'd role artifact validator
  once its JSON shape has been decided in an interactive session.
- Documentation cleanup, or updating a stale report once the current one
  supersedes it (see `ZEN_AUDIT_AND_FIXES_STATUS_002.md`'s own note about
  the 2026-09-08 report).
- Small, independently testable utility functions whose spec is already
  written down (e.g. a single new state-adapter read-only query).

If it is unclear which tier a task falls into, treat it as the interactive
tier. Getting this wrong in the safe direction costs a delay; getting it
wrong in the other direction risks an unsupervised agent making an artistic
or safety-relevant decision it should not be making, which is the exact
failure this project's `CODEX_ARTISTIC_INTERVENTION = NONE` rule exists to
prevent.

## Rule 4: unattended runs are scheduled around, not alongside, active use

Unattended agent sessions (task-queue-style Codex runs, etc.) belong in a
window when the project owner is not actively using the machine for
something else -- overnight, or while away -- both to avoid Rule 1's
resource contention and because an unattended session cannot ask a
clarifying question if it hits a Rule 3 decision it should not make alone.
If an unattended session reaches a point that requires an interactive-tier
decision, it should stop and record that in its final commit message or a
short note, not guess.
