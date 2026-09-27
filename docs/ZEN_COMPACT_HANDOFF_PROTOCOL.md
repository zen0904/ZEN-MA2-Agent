# ZEN Compact Handoff Protocol

Status: ACTIVE

Purpose: preserve complete ZEN continuity without spending model/context budget on repeated long chat handoffs.

## Authority order

When resuming ZEN work, recover state in this order:

1. committed repository state and current `git status`
2. `data/zen_project_control.json`
3. the report/evidence file named by the active objective or last closed task
4. original retained runtime evidence/logs only where the current task needs them
5. chat/assistant summaries only as navigation hints

A later summary never overrides contradictory original evidence. If facts conflict, stop and resolve them against the original artifact/log.

## Start of a substantial run

Read only what is needed:

- `AGENTS.md`
- `data/zen_project_control.json`
- the relevant current report/document
- `docs/CODING_AGENT_COLLABORATION.md` when applicable
- `git status` and current HEAD

Do not recursively reread every historical ZEN report or dump full runtime logs into context. Locate exact evidence by ID/path/pattern and read the smallest relevant range.

## During the run

- Keep normal chat progress sparse and state-based.
- Do not restate the entire task after every tool call.
- Store detailed technical evidence in the repo/report/log, not in user chat.
- Preserve raw logs unchanged; summarize them by timestamp/event/ID and point back to the source.
- Record any new safety boundary, forbidden Action, write count, acceptance result, or blocker in canonical project state before ending the run.

## End of the run

A substantial run is not handoff-complete until the canonical state needed by the next run is durable. Update `data/zen_project_control.json` and the relevant report when state changed. Commit/push when the workflow permits it.

The user-facing final should normally be compact and include only:

- `HEAD`
- `STATUS`
- `TESTS`
- `MA2_WRITES`
- `PREVIEW` / `ACTION` when relevant
- `BLOCKER`
- `NEXT`
- `EVIDENCE` paths/IDs

Use exact IDs instead of retelling long histories. Example:

```text
HEAD=fe10980
STATUS=OFFLINE_HARDENED
TESTS=939 PASS
MA2_WRITES=0
PREVIEW=NONE
BLOCKER=fresh native Sequence302 evidence required
NEXT=generate Preview only in authenticated Field Core
EVIDENCE=data/zen_project_control.json; EXISTING_CUE_DYNAMIC_PROGRAM_MERGE_001.md
```

## Continuation rule

When the owner says `繼續`, `continue`, `next`, or starts a new chat with a compact handoff, do not ask them to reconstruct prior work. Read the canonical repository state and continue from the recorded next acceptance gate. If the compact handoff disagrees with repository evidence, the repository/evidence wins and the discrepancy must be stated concisely.

## Token discipline

Do not spend context on material that can be referenced precisely. Prefer:

- one hash over a pasted diff
- one error code + log location over 200 log lines
- one Preview/Action ID over a repeated command list
- one evidence path over copied report text

Compact does not mean incomplete: any fact that changes safety, approval, write authority, or the next action must still be surfaced.
