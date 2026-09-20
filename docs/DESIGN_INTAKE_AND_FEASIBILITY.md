# Design Intake and Feasibility

## Purpose

ZEN must accept incomplete, informal and imperfect real-world design inputs.

Common inputs include:

- artist + song title;
- audio file;
- arrangement note;
- section structure;
- event flow;
- lighting cue sheet;
- choreography note;
- client / student request;
- visual reference;
- little or no source material beyond a design request.

The existence of an input does not make it technically feasible, artistically
appropriate, or authoritative.

ZEN should preserve the requester's intent where possible while remaining free
to adapt, reinterpret or reject details that do not fit the real rig, stage,
timing, safety boundary or production context.

## Two-axis interpretation

Every external request should be reasoned about on two independent axes:

```text
AXIS A — REQUEST AUTHORITY
What does the requester mean this item to be?

AXIS B — FEASIBILITY
Can the current production actually realize it?
```

Do not collapse these into one "hard / soft cue" field.

A student can write something as though it were mandatory while the actual
fixture, stage, timing or safety context makes it impossible. Conversely, a
casual suggestion may be easy and useful to preserve.

## Request-authority classes

These are reasoning classes, not yet mandatory schema values.

### REQUIRED_PRODUCTION_CONSTRAINT

A requirement established by an authorized production source or safety /
venue / operator boundary.

Examples:

- blackout before a scenic move;
- performer must remain visible for a judged routine;
- venue restriction;
- camera or broadcast requirement;
- explicit operator-approved safety constraint.

These are not silently redesigned away.

### REQUESTED_DESIGN_INTENT

A requester clearly wants this visual outcome, but implementation may change.

Examples:

- "this section should feel red";
- "make the chorus explode";
- "solo should feel isolated";
- "ending should disappear suddenly."

Preserve the intent, not necessarily the literal mechanism.

### REFERENCE_SUGGESTION

Useful source material that can be changed freely when a better solution exists.

Examples:

- student cue-sheet color suggestion;
- rough effect request;
- an approximate cue time;
- an example look from rehearsal notes.

### OPEN_SPACE

No meaningful direction was supplied.

ZEN may design freely within verified production constraints and the current
show language.

## Feasibility classes

### FEASIBLE_AS_WRITTEN

The requested outcome can be achieved with verified current resources and does
not conflict with higher-priority constraints.

### FEASIBLE_WITH_ADAPTATION

The literal request should not be followed exactly, but its underlying intent
can be realized another way.

Example:

```text
request:
"tight white spot on dancer"

current rig:
no suitable followspot / mover position target is verified

possible adaptation:
use the best verified front / top isolation available
while preserving the intent of isolating the dancer
```

### NOT_FEASIBLE_CURRENT_RIG

The requested effect depends on a resource or capability that is absent or
unverified.

ZEN must not invent the capability.

### CONFLICTS_WITH_PRODUCTION_CONSTRAINT

The request conflicts with safety, venue, operator, camera, choreography,
scenic or another higher-priority verified requirement.

The higher-priority constraint wins.

### TIMING_OR_SOURCE_CONFLICT

The supplied cue timing / structure conflicts with stronger evidence such as
the actual provided audio or an approved production timeline.

ZEN should preserve both pieces of provenance and decide whether to adapt,
flag or request review based on authority.

### UNKNOWN_NEEDS_REVIEW

Available evidence is insufficient to judge feasibility honestly.

Unknown is not equivalent to impossible and is not permission to guess.

## Cue-sheet interpretation

A lighting cue sheet is normally an input to design, not executable truth.

A student or client cue sheet may contain:

- useful artistic intention;
- approximate timing;
- impossible requests;
- unavailable fixture behavior;
- contradictory instructions;
- technically achievable but visually weak solutions;
- language that describes emotion rather than implementation.

ZEN should extract the intent first.

For each cue-sheet item:

```text
original request
→ request authority
→ intended visual result
→ verified current resources
→ feasibility
→ preserve / adapt / reject / flag
→ resulting design proposal
```

The final design should remain traceable to the supplied cue sheet without
being mechanically constrained by it.

## Adaptation principle

When the literal request is weak or impossible:

```text
PRESERVE INTENT
DO NOT PRESERVE A BAD MECHANISM MERELY BECAUSE IT WAS WRITTEN DOWN
```

Examples:

- "rainbow" may mean energetic / colorful rather than literal rainbow chase;
- "spotlight" may mean performer isolation rather than a physical followspot;
- "all lights flashing" may mean high-impact punctuation rather than every
  available fixture running strobe;
- "blue here" may be a mood suggestion, not a mandatory hue;
- a written cue at 01:24 may be adapted to the actual musical event at 01:26
  when the cue sheet is only approximate and no higher-authority timing
  requirement fixes 01:24.

ZEN should record meaningful adaptations rather than silently pretending it
followed the request exactly.

## No-input / open-design mode

ZEN must also work when almost nothing is supplied.

Examples:

- "design something usable";
- a song title only;
- artist + song title;
- an audio file with no cue sheet.

Lack of direction increases uncertainty but does not prevent design.

The system may create an artistic proposal from professional design knowledge,
song/performance evidence and current show context, while clearly separating:

```text
VERIFIED FACT
PROVIDED REQUEST
INFERRED CONTEXT
ARTISTIC PROPOSAL
```

## Input precedence

Precedence is not a single flat list because authority and factual strength are
different dimensions.

A practical default is:

```text
safety / venue / authorized production constraints
    >
verified current Show / rig / stage facts
    >
explicit owner-approved requirements
    >
actual supplied audio / approved timeline evidence
    >
cue-sheet intent and structure
    >
artist / song metadata
    >
external references
    >
free artistic proposal
```

A lower item may still shape the design strongly when it does not conflict with
higher evidence.

Student cue sheets do not automatically become
`REQUIRED_PRODUCTION_CONSTRAINT`.

## Audio and arrangement handling

When an audio file is provided, it is the primary evidence for the actual
arrangement being designed.

Artist / song metadata may provide cultural or stylistic context, but must not
override the supplied recording.

If the supplied version is a remix, cut, cover, dance edit or other
arrangement:

```text
original-song knowledge
= contextual only

actual supplied audio / structure
= arrangement truth for this case
```

Do not assume the original song's section lengths, drops, accents or energy
curve remain intact.

## Review output

For externally supplied cue sheets or design briefs, a useful review artifact
should be able to show:

```text
PRESERVED
request kept substantially as written

ADAPTED
intent preserved, mechanism / timing / implementation changed

NOT_USED
request intentionally omitted with reason

UNRESOLVED
needs real-stage / rehearsal / operator evidence
```

This is not an invitation to over-explain every cue. Surface only adaptations
that matter to production, approval or operator understanding.

## Product boundary

This document defines intake and reasoning behavior only.

It does not:

- change production role prompts by itself;
- authorize autonomous MA writes;
- authorize fixture / stage facts that have not been verified;
- make a student / client cue sheet production truth;
- allow the Agent to bypass Preview / Approval;
- change protected Builder / Resolver behavior.

Any future schema or prompt implementation of these concepts remains an
owner-reviewed product decision.
