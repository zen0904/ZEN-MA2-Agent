# grandMA2 Programming Intelligence

The active target is grandMA2. The Agent must reason about the cleanest,
safest, native and maintainable implementation, not merely whether a command
can work. Relevant capability areas include Store/Update, tracking and Cue
Only, Block/Unblock, presets and references, groups and fixture organization,
Sequence/Cue and executor architecture, Effects/MAtricks/Phase, Position/
Color/Beam/Focus, Macro/Plugin/UserVars, Clone/PSR, Worlds/Filters,
Timecode, import/export, capability differences, cleanup and recovery safety.

This is a discovery boundary rather than a completed checklist. A known method
does not end investigation when a cleaner native method may exist. Choose a
native feature, Macro, Plugin, Agent-side tool, or one-off operation according
to lifecycle and safety; never emit raw console text from Designer intent.

Current evidence remains capability-scoped. Real-console verification outranks
memory or documentation hypotheses, and unverified Programmer access,
Preset-internal values, binary show parsing and unsupported grammar remain
separate blockers.

Professional native-console choices must also satisfy `FOCUS_EXECUTE`: a
competent programmer should be able to rehearse, edit, recover and continue
the delivered Show with ordinary MA workflows. The operator-facing acceptance
test is maintained in `ZEN_WORKFLOW_CONTRACT.md`, rather than duplicated in
console capability research.


## Native-first solution reasoning

Knowing that a feature exists is not sufficient. The programmer layer should
reason about the smallest native, maintainable solution that satisfies the
actual problem.

A useful escalation model is:

```text
one-off console operation
  -> native command / existing object

repeated selection or distribution
  -> Group / Selection / MAtricks / Filter / World

repeated show-content transformation
  -> Clone / Search / Replace / Update / native reference behavior

repeated fixed workflow
  -> Macro

repeated workflow with operator input or reusable parameters
  -> Macro + variables + pop-up/user input + conditional/timed lines

stateful iteration, complex branching, reusable data processing, or a workflow
that has become materially harder to maintain as a Macro
  -> Lua Plugin

external orchestration / cross-system logic
  -> Agent-side tool, only when a native console mechanism is not the cleaner
     operator-facing solution
```

This is an escalation ladder, not a rigid rule. The correct result is the
cleanest native implementation for the case. A Plugin is not automatically
"more advanced" or preferable merely because it can perform the task.

Official grandMA2 documentation establishes that Macros support variables,
operator prompts, timing, command-line interaction and other reusable workflow
mechanisms. Plugins use Lua 5.3 and exist specifically for deeper custom logic,
including cases where complex Macros become a poor abstraction. Plugin use also
has a higher maintenance and migration burden and must therefore be justified,
not treated as the default automation mechanism.

## Capability composition

The Agent should reason over combinations of native features rather than
selecting one feature in isolation.

Examples of legitimate composition questions include:

- Can MAtricks express the required selection order or distribution before any
  custom automation is considered?
- Can a Filter or World constrain Store, At, playback, or programming scope
  instead of duplicating content?
- Can Clone preserve the intended references and dependencies while adapting
  an existing programmed structure to another fixture set?
- Can Search / SearchResult / Replace solve a bounded transformation more
  safely than repeated manual edits?
- Can Preset/reference structure preserve future editability instead of
  embedding fixture-specific values into many cues?
- Can an Executor/Sequence option or playback/input filter express behavior
  that would otherwise be duplicated across several sequences?
- Can a reusable Macro parameterize a repeated operation rather than creating
  many nearly-identical Macros?
- Has a Macro become sufficiently stateful or branch-heavy that a Lua Plugin
  is actually simpler and more maintainable?

The reasoning target is not "use more MA features." It is "use the smallest
combination of native features that preserves intent, editability, safety and
operator comprehension."

## Solution-pattern evidence

Programming knowledge should eventually be stored and retrieved as
problem/solution patterns, not as isolated feature definitions.

A pattern should preserve at least:

```text
problem shape
known Show constraints
candidate native mechanisms
selected mechanism(s)
why selected
why alternatives were rejected
required evidence / prerequisites
maintenance cost
operator impact
failure / rollback considerations
version / capability evidence
```

For example, a repetitive programming task should not automatically produce
many Macro objects. The Agent should first determine whether the variability is
selection, object identity, values, operator input, state, or branching. That
classification determines whether Group/MAtricks, Clone, Search/Replace,
parameterized Macro, or Lua is the cleaner abstraction.

## Programming anti-patterns

The Critic and future programmer reasoning should recognize technically working
but professionally weak implementations, including:

- many near-identical Macros where one parameterized Macro would remain clear;
- a Lua Plugin reimplementing a native MA feature without a concrete gap;
- fixture IDs hard-coded into reusable automation when current Show Groups or
  explicit parameters should supply identity;
- repeated embedded values where Preset/reference structure is appropriate;
- manual repeated edits where Search/Replace or Clone can express the
  transformation safely;
- automation that hides the resulting Show structure from an operator;
- clever automation whose recovery path is harder than the work it saves;
- using technical capability as evidence of artistic necessity;
- creating a custom abstraction that prevents normal native MA editing after
  ZEN is unavailable.

"Works" is not sufficient. The implementation must pass Focus Execute and the
Operator Handover Test.

## Evidence currently established from official MA2 documentation

The following capability relationships are documented and may be treated as
technical possibilities, while their use in a particular Show remains
case-specific:

- Macro variables can hold reusable command/text values and support simple
  arithmetic or text extension.
- Macro pop-ups can request operator input and suspend execution until input is
  supplied.
- Macro lines may execute immediately, after timing, or await later triggering.
- Clone can copy programming between fixture selections and can be limited in
  scope; referenced dependencies may be carried with the cloned structure.
- Search and Replace can locate and transform fixtures, presets, values and
  timing data within bounded object scopes; SearchResult can further constrain
  later operations.
- Filters can constrain Attributes and data layers for Store / At and can also
  participate in Sequence/Executor filtering behavior.
- Worlds can constrain fixtures and/or attributes for programming scope and
  can also be assigned in playback/input-filter contexts.
- Sequence and Executor options include behavior that should be checked before
  implementing duplicate custom logic.
- Lua 5.3 Plugins provide deeper custom logic than ordinary Macros, but they
  have stronger maintenance, support and migration implications.

These are capability facts, not design recipes and not authorization to emit
raw MA commands from an LLM.

## MA text compatibility boundary

Conversation and reasoning may use any human language. Any text intended to be
stored in or executed by grandMA2 must pass the deterministic MA text
compatibility boundary before it can reach execution.

Current policy:

```text
human conversation         -> any language
LLM reasoning              -> any language
ZEN symbolic identifiers   -> ASCII/English preferred
MA object names / labels   -> ASCII only
Macro text                 -> ASCII only
Plugin/Lua source for MA   -> ASCII only
raw MA command text        -> ASCII only
non-ASCII at MA boundary   -> FAIL CLOSED / NON_ASCII_MA_TEXT
```

Invalid text is rejected; it is never silently stripped or transliterated.
