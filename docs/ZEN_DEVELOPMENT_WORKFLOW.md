# ZEN Development Workflow

## Purpose

This document controls development work, not show programming. It prevents a
new discovery from silently replacing the verified mainline. Git history,
durable documents, and the current control state are the project record.

## Development loop

```text
DISCOVER -> CLASSIFY -> TRIAGE / GATE -> EXECUTE -> VERIFY
  -> REVIEW -> CLOSE -> RETURN_TO_MAINLINE
```

| State | Meaning | Exit condition |
| --- | --- | --- |
| `DISCOVER` | Record a new finding, opportunity, contradiction, or question with its source. | It has enough evidence to classify, or is explicitly unknown. |
| `CLASSIFY` | Give it one priority classification and a scope/milestone. | Its impact and evidence boundary are clear. |
| `TRIAGE / GATE` | Decide whether it interrupts the active work, becomes the next acceptance gate, or is parked. | One bounded disposition is recorded. |
| `EXECUTE` | Perform only the approved bounded task. | The task output is available for verification. |
| `VERIFY` | Check deterministic behavior, provenance, safety, and the task-specific acceptance criteria. | Results are evidenced, including failures/limits. |
| `REVIEW` | Obtain required human, console, or case review without pre-filling an artistic outcome. | Review outcome or its absence is explicit. |
| `CLOSE` | Record result, limitations, next gate, and any newly discovered work. | The task is committed as complete, blocked, or deferred. |
| `RETURN_TO_MAINLINE` | Resume the active milestone from the recorded next acceptance gate. | The next task is selected by the rules below. |

`DISCOVER` is not authorization to implement. A discovery remains reversible
until it has passed triage and the appropriate verification/review boundary.

## Classification

| Classification | Meaning |
| --- | --- |
| `BLOCKER` | Prevents the current milestone from being completed truthfully or safely. |
| `REQUIRED` | Required for milestone acceptance, but not necessarily an interruption to the current bounded task. |
| `HIGH_LEVERAGE` | Helps several future capabilities materially; schedule only through normal triage. |
| `NICE_TO_HAVE` | Useful, but not required for current product acceptance. |
| `RESEARCH_UNKNOWN` | Needs bounded investigation before implementation can be justified. |
| `DEFERRED` | Valid work deliberately not pursued now. |
| `REJECTED` | Investigated and intentionally not pursued; preserve the reason. |

Classifications describe priority and evidence, not artistic truth or a promise
of implementation.

## Interrupt / scope gate

A discovery may interrupt the active task only when it is a:

- safety issue, data-corruption risk, false capability claim, or provenance
  failure;
- flaw that invalidates the current task's result or its acceptance evidence;
- real-console result that disproves an assumption the task presently relies
  on; or
- fact that makes the active milestone impossible to complete truthfully.

An interesting fixture, potential MA3 improvement, nicer interface, extra
data source, design idea, future production feature, or non-blocking
optimization is not sufficient. Record it in the control backlog and return
to the active milestone.

## Task selection

Select one bounded task in this order:

1. Read `CURRENT_MILESTONE` and `NEXT_ACCEPTANCE_GATE` in
   `data/zen_project_control.json`.
2. Identify the unmet acceptance criterion.
3. Find the smallest evidence-backed blocker to that criterion.
4. Reuse existing architecture/data before adding infrastructure.
5. Decide whether implementation is actually necessary; review or research can
   be the correct task.
6. Execute, verify, close, and update the control state.

Never select a task only because it is the newest idea in conversation.

## Continue behavior

When Zen says “continue”, “next”, “好了”, “完成”, or “去看”, recover the
latest committed repository state, current control state, and only the reports
directly relevant to the next gate. Do not re-plan from chat history or reread
every archive report. A newer explicit human decision overrides an older
repository conclusion and must be written back with provenance.

## Evidence and workflow boundaries

Industry knowledge is a general professional prior. Current Show/venue facts
are constraints. Song/script/performance context informs the current intent.
Zen preference is a reversible personalization layer among professionally
valid choices. Technical and safety facts win conflicts. A valid preference
that differs from common practice remains preference; it does not rewrite the
industry record.

Every task must preserve the existing product boundaries: Design Intent before
resource selection, typed plans before Builder output, and no production
activation without its separate acceptance decision. The active status report
records the relevant MA2 and runtime safety boundary for each task.
