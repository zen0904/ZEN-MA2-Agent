# ZEN Design Guidance Shadow 001

Status: `SHADOW_ONLY`. This is an evidence-preserving advisory layer around
the deterministic Designer. It does not alter `ZEN_SHOW_PLAN`, invoke the
Builder, or connect to MA2.

## Architecture and data flow

```text
Song Analysis ────────┐
Training Case Context ├─> zen.design_guidance_context.v0.1
Industry Evidence ────┤              │
Human Style Reviews ──┘              ├─> zen.design_advisory.v0.1
                                      │
Existing deterministic Designer ─────┴─> unchanged typed ZEN_SHOW_PLAN
```

The longstanding execution boundary is unchanged:

```text
Natural Language / Song / Script -> Song Analysis -> Designer -> ZEN_SHOW_PLAN
-> Resolver(s) -> Builder -> Preview -> Approval -> MA2 write -> Verification
```

The shadow layer is not in the Builder path and cannot emit MA2, Telnet, Lua,
plugin, or raw command fields.

## Guidance context

`zen.design_guidance_context.v0.1` keeps four input categories separate:

- **Song** — `SECTION_STRUCTURE`, `RHYTHMIC_ACCENT`, `DYNAMIC_CONTOUR`,
  `BUILDUP_RELEASE`, and `REPEATED_SECTION_DEVELOPMENT` remain distinct.
- **Case** — bounded Training Case identity, resource scale, fixture-group role
  hypotheses, visual layers, geometry status, constraints, and assumptions.
  `TRAINING_CASE_001` is case context, not a global rig model.
- **Industry** — Pack 001/002 observation, source, scope, reliability, stance,
  human industry-review state, limitation, and source bias. Unreviewed industry
  evidence is traceable advisory material, never an automatic Designer rule.
- **User Style** — only explicit `ACCEPT` and `ACCEPT_WITH_LIMITATION` human
  review records load as active style signals. Their acceptance is still only
  eligibility for future knowledge consideration, not runtime activation.

Context-dependent reviews remain outside fixed guidance:
`DOMINANT_THEME_COLOR`, `STRONG_TRANSIENT_IMPACT`, `HIGH_SECTION_DELTA`,
`RESTRAINT_BETWEEN_PEAKS`, `CONTROLLED_BUILDUP`, and
`GEOMETRIC_COMPOSITION`.

Rejected/non-global interpretations remain explicit:
`HIGH_IMPACT_ALWAYS`, `MAXIMALISM_EQUALS_CLUTTER`,
`MULTICOLOR_EQUALS_BAD`, `MINIMALISM_EQUALS_LOW_PREFERENCE`, and
`KPOP_YG_EQUALS_GLOBAL_STYLE_RULE`.

## Advisory schema and example

`zen.design_advisory.v0.1` carries a recommendation, rationale, source
categories, evidence references, human/industry review states, song/case
references, confidence, scope, limitations, structured conflicts, unresolved
conditions, and `SHADOW_ONLY_REVIEW_REQUIRED` actionability.

Example advisory:

> Preserve intentionally designed low-, medium-, and high-energy visual states;
> do not reduce a high-energy look only by dimming it.

This advisory cites the human `ACCEPT`, `HIGH` priority decision for
`EACH_ENERGY_STATE_NEEDS_A_COMPLETE_LOOK`, plus section and dynamic-contour
signals. It remains abstract: it selects no fixture, preset, effect, intensity,
fade, delay, or timing.

## Conflict handling

The layer records conflicts without averaging them into a fixed score. Supported
outcomes are `ALIGN`, `PARTIAL_ALIGN`,
`PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE`, `CONTEXT_OVERRIDES_STYLE`,
`RESOURCE_LIMITATION`, and `UNRESOLVED`.

For example, a limited case may constrain the preferred distinction between
complete energy states (`RESOURCE_LIMITATION`). An industry technique remains
professionally valid when it differs from a user preference
(`PROFESSIONAL_VALID_USER_STYLE_DIVERGENCE`); neither side is deleted.

## Style synthesis boundary

Zen style is not a large collection of fixed look recipes. The current,
transferable synthesis is design coherence: clean hierarchy, palette coherence,
musical alignment, intentional energy development, complete energy states,
restraint when appropriate, controlled density, and context-aware impact.

Song, rig, resources, staging, camera, geometry, and visual concept may
legitimately constrain a preferred implementation. The layer does not create
rules such as always using a dominant color, large chorus delta, geometry,
layered buildup, transient hit, energy reset, or maximal look.

## Baseline preservation proof

`tests/test_design_guidance.py` runs the existing `FirstSongDesigner` with the
existing deterministic song-analysis fixture, then runs it through the shadow
wrapper. The baseline `ZEN_SHOW_PLAN` and shadow `actual_show_plan` are asserted
structurally identical. The shadow result contains advisory records only.

## Not run

- Designer production guidance activation
- `ZEN_STYLE_PROFILE` creation
- Builder/Resolver changes
- MA2/Telnet/plugin execution
- Any MA2 object write
