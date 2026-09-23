# Skill system

ZEN Skills are workflow definitions, not a one-intent/one-command shortcut.
Each manifest declares its id, source, safety level, intent names and required
state. A core-owned implementation may then create a `Task`, break it into
`Subtask`s, calculate a dependency graph of `ActionStep`s, validate conflicts,
and build a `WorkflowPlan` with approval gates, verification and recovery
metadata.

```text
Intent → Skill → Task/Subtasks → WorkflowPlan → safety/preview → AgentCore execution → verification
```

Only builtin implementations are executable in this phase. They receive a
read-only StateStore and preferences, never the Telnet socket or password.
Their workflow can only return structured steps. AgentCore alone calls the
runtime's approved-command executor after the operator approves the plan.

`WorkflowPlan.skill_graph` records root and child Skill nodes. The registry's
`plan_intent` and `plan_subskill` entrypoints resolve a sub-Skill with the same
StateStore and safety constraints, then merge child subtasks/steps into the
parent workflow before any approval is requested.

`show.program` is the normal root orchestration Skill for bounded show/song
requests. Its semantic phases are represented as root subtasks; discovery,
research, resource resolution, design, compilation, and readback capabilities
remain internal. When a deterministic child is supported, the root composes
that child through the registry and `WorkflowPlan.with_child()`. The root does
not invent MA2 commands or bypass child validation.

`skills/builtin` ships the four initial command workflows plus disabled
placeholders. `skills/installed` is portable and discoverable, but installed
`skill.py` files are deliberately never imported or executed automatically.
This prevents a copied USB skill from escaping the safety boundary.

The Skills page reads the registry and supports Enable, Disable and Inspect.

For broad programming requests, an injected provider-independent one-call
artistic service may supply `LEAN_SINGLE_DESIGNER` intent. It is compiled by
ZEN and composed with the existing `show.builder` child; no provider is called
when the service is absent, and deterministic child requests stay model-free.
