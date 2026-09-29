# Artistic Mechanism Selection Policy

Status: ACTIVE GLOBAL ARTISTIC CONTRACT

Owner decision: 2026-09-30

## Purpose

ZEN must let the Primary Lighting Designer reason with the full professional
lighting repertoire without turning that repertoire into a completion checklist.
The problem has two symmetric failure modes:

1. the Designer never considers a useful mechanism because it was hidden from
   context;
2. the Designer uses a mechanism merely because it was listed, available, or
   technically executable.

Both are design failures.

## Global rule

```text
KNOWING A TOOL EXISTS != HAVING TO USE IT
RESOURCE AVAILABLE != ARTISTIC REQUIREMENT
DELIBERATE NON-USE == VALID DESIGN CHOICE
```

The complete artistic vocabulary should remain visible to the Primary Lighting
Designer for reasoning. Every mechanism is optional unless the song, section,
performance, choreography, narrative, spatial state, show language, neighboring
Cues, or an explicit owner brief gives it a real artistic reason to exist.

There is no global requirement that a song or Cue use Movement, Effect, Gobo,
Prism, Strobe, Zoom, Frost, Iris, Position change, Color change, or any other
mechanism. There is also no global maximum count. Density is a design decision,
not a schema-completion target.

## Repertoire versus executable resources

ZEN keeps two different ideas separate:

### Artistic repertoire

The mechanisms the Designer may think with:

- Dimmer
- Color
- Position
- Focus
- Beam
- Gobo / Gobo rotation
- Prism / Prism rotation
- Zoom
- Frost
- Iris
- Shutter / Strobe
- Effect
- Movement

The repertoire is intentionally broad. It is not reduced merely because the
current Show cannot yet execute one dimension through a verified typed path.

### Current executable resources

The Presets, Effects, semantic Position bindings, direct typed operations, and
other resources that have current-Show evidence and are legal in the active
execution route.

Executable resources constrain what ZEN may write to MA2. They do not constrain
what the Designer is allowed to imagine or describe artistically.

If the Designer asks for a useful artistic behavior that is not currently
executable, ZEN must preserve that intent as unsupported/intent-only and fail
closed at execution. It must not silently replace it with a different effect,
Dimmer chase, Preset, raw Attribute command, or another mechanism merely because
that substitute is available.

## Selection reasoning

A mechanism should be selected because it contributes to the design. Relevant
reasons can include, without becoming a mandatory scoring system:

- music and arrangement structure;
- rhythm, phrasing, impact, release, tension, restraint, or silence;
- lyrics or narrative;
- choreography, blocking, pose, or performer focus;
- stage geometry and spatial relationships;
- scale, depth, height, silhouette, texture, negative space, or hierarchy;
- relationship to neighboring Cues;
- song identity and show-level visual language;
- intentional callback, development, contrast, reset, or withholding;
- explicit operator/client brief.

The Designer does not need to justify every unchanged parameter. The purpose of
reasoning is to avoid arbitrary mechanism use, not to produce bureaucratic prose
for every Cue.

## Review rule

Review must look in both directions:

- **under-use:** a musically or visually valuable mechanism appears to have been
  ignored even though the known rig and artistic context make it relevant;
- **over-use:** a mechanism is repeated, stacked, or inserted without a clear
  design function, or because the resource happened to be available.

The review must not reward maximum mechanism count or maximum difference between
Cues/songs. Restraint, stillness, darkness, a held Position, a static palette,
no Effect, or no Movement can be the stronger design.

## Effects and Movement

Effect and Movement are not special exceptions to this policy. They are optional
artistic mechanisms.

The Designer should ultimately be able to express desired behavior rather than
being forced to choose only from existing pool IDs. For example, artistic intent
may describe phase, direction, speed character, acceleration, distribution,
entry/exit behavior, or interaction with a musical event.

That artistic freedom does **not** authorize raw MA2 commands. Until a typed,
verified native authoring grammar exists for a requested behavior, execution
remains fail-closed. Existing verified Effects may be reused when they genuinely
match the intent; the pool must not dictate the art.

## Production integration

`zen_ma2_agent.artistic_capabilities.artistic_selection_policy()` is the
machine-readable version of this contract.

The ordinary Primary Design context and Delta Revision context must carry that
policy so an interactive ChatGPT Primary Brain and an autonomous provider model
receive the same mechanism-selection rules.

This policy changes artistic reasoning only. It does not change the Operator
Workflow, Preview/Approval boundary, protected-object rules, deterministic
Builder authority, or native readback requirements.
