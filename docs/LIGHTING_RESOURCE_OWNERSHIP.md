# Lighting Resource Ownership

## Purpose

ZEN should not assume that every patched lighting fixture belongs to the
autonomous design layer.

The default operating model separates visibility-critical lighting from
effect/design lighting while allowing the same physical fixture to change role
when the operator explicitly intends it to be used as an effect resource.

Ownership is based on the fixture's current functional role, not merely its
physical position, fixture type, or Group name.

## Default responsibility boundary

### HUMAN_RESERVED_VISIBILITY

Lighting whose primary current purpose is reliable performer visibility remains
under operator responsibility by default.

Examples can include:

- conventional face light;
- camera / key light;
- judged-performance visibility;
- safety-critical illumination;
- any other layer the operator explicitly reserves for manual control.

ZEN must not redesign, recolor, move, dim, strobe, or otherwise repurpose a
reserved visibility layer unless the design request explicitly includes it.

### ZEN_EFFECT_RESOURCE

A verified lighting resource whose intended role is expressive design may be
used by ZEN.

Examples can include:

- side light used as graphic or sculptural material;
- backlight;
- aerial beam;
- texture;
- color layer;
- movement layer;
- rhythmic punctuation;
- silhouette;
- audience / scenic effect;
- other verified expressive use.

A fixture being physically positioned at the front or side of stage does not,
by itself, determine ownership.

### SHARED_RESOURCE

A physical fixture may support both visibility and expressive use.

Shared use requires explicit scoped reasoning.

ZEN should preserve the reserved visibility function and only use the
attributes / cues / contexts that are actually available for expressive work.

Example:

```text
fixture role during dialogue:
performer key light
→ HUMAN_RESERVED_VISIBILITY

same fixture during a non-visibility-critical transition:
graphic side / front effect
→ may become ZEN_EFFECT_RESOURCE if explicitly allowed
```

The resource does not become permanently "owned" by either side merely because
it served one role earlier.

## Role-before-fixture principle

Do not infer:

```text
front position -> human only
side position -> ZEN only
wash -> visibility
beam -> effect
moving light -> effect
conventional -> human
```

Instead determine:

```text
verified capability
+ current production role
+ operator reservation
+ cue context
= usable ownership scope
```

## Visibility preservation

When a shared fixture contributes to performer visibility, ZEN must not
silently destroy that function in pursuit of an effect.

If expressive use would conflict with required visibility, the visibility
requirement wins unless the operator explicitly authorizes a different design
for that moment.

Examples of conflicts include:

- recoloring a key-light layer so skin rendering becomes unacceptable;
- moving a shared fixture away from a performer who still needs coverage;
- reducing intensity below a required camera / judging threshold;
- applying strobe or movement to a fixture currently serving stable key light.

## Intake behavior

The operator may explicitly request that visibility lighting be included in a
design.

Examples:

- "include face light in this design";
- "you can use the side key lights as effects in the bridge";
- "leave my front light alone";
- "only design the effects; I will handle performer visibility."

These instructions should be treated as case-specific ownership evidence, not
as permanent rules for future shows.

## Product boundary

This document defines design-resource ownership reasoning only.

It does not:

- authorize new MA writes;
- infer fixture geometry from names;
- classify all front or side fixtures permanently;
- change protected Builder / Resolver behavior;
- replace operator approval.

Future schema or prompt implementation remains an owner-reviewed product
decision.
