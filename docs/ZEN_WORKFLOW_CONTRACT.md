# ZEN Workflow Contract

## Stable operator contract

The Agent adapts to ZEN's real operating habits and mental model. Where
confirmed, this includes song-oriented programming, generally one Sequence per
song, Timecode where applicable, predictable executor/fader access, familiar
preset/effect access, readable naming and fast live modification.

This is an operator contract, not a copy of every current implementation.

## Evolvable implementation

Internal implementation may improve while preserving the familiar workflow.
Any change that materially alters operator interaction is a
`PROPOSED_WORKFLOW_CHANGE` and needs explicit human approval. Do not silently
create a new workflow version or require ZEN to relearn the system.

Produced Shows must remain understandable and editable by a competent console
programmer who has never seen Agent internals.

## Focus Execute and Operator Handover Test

`FOCUS_EXECUTE` means the Agent hands over a Show ready for ZEN to begin
rehearsal, refinement, modification and live execution immediately. It does
not mean replacing the operator or optimizing only for generation speed. It
minimizes `TIME_TO_REFINEMENT` so the operator's time can be spent on the show
rather than recovering hidden Agent structure.

A generated Show is not production-quality unless ZEN can, using normal native
MA workflows:

- understand the Show structure without Agent internals;
- run it predictably;
- locate and edit relevant Presets, Sequences, Cues, Effects and Executors;
- make normal rehearsal/live changes and recover safely; and
- continue programming manually if the Agent is unavailable.

This test extends rather than replaces HANDOVER_READABILITY, the Stable
Operator Contract and Evolvable Implementation. An implementation improvement
that materially changes this operator-facing contract remains a
`PROPOSED_WORKFLOW_CHANGE` requiring explicit human approval.
