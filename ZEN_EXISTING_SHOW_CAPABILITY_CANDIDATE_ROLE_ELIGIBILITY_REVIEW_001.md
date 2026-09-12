# Existing Show Capability → Candidate Role Eligibility Review 001

**Status:** `READY_FOR_HUMAN_ELIGIBILITY_APPROVAL` — review only. No Group is
bound to a B3 role, no case role is assigned, and
`REAL_SONG_EXISTING_SHOW_AB_002` is **not run**.

## Purpose and non-promotion boundary

This review applies the real-console, Show-bound FixtureType channel evidence
to the current B3 role vocabulary. It answers only whether a Group can be
considered for a role in a future, explicitly approved song/case context.

```
technical capability
    != candidate-role eligibility
    != case-specific role assignment
    != permanent fixture role or priority
```

Design Intent still precedes selection. A Group may be suitable for different
roles in different sections, or be unused. `HYBRID`, `BEAM`, `WASH`, `B-EYE`,
`LED PAR`, and `STROBE` are exact Group labels, not role assignments.

All records below have `case_role_assignment = NONE` and `HUMAN REVIEW =
UNSET`. Nothing here changes the production Designer, experimental B3, MA2
objects, Presets, Effects, geometry, or semantic Position resources.

## Evidence and current constraints

- **Technical source:** real grandMA2 onPC `Export FixtureType` compound batch
  identity proof, recorded in
  [`ZEN_FIXTURE_TYPE_EXPORT_SCHEMA_RESEARCH_001.md`](ZEN_FIXTURE_TYPE_EXPORT_SCHEMA_RESEARCH_001.md).
  FixtureTypes 2–7 are `SHOW_BOUND_VERIFIED`; each Group-to-FixtureType
  membership is from the fresh Existing Show scan.
- **Provenance:** `MA2_EXPORT_FIXTURE_TYPE_XML_COMPOUND_IDENTITY` plus current
  Show Group membership. Group labels are not capability evidence.
- **Geometry:** `GEOMETRY_UNINITIALIZED`; no stage-axis inference.
- **Semantic Position Presets:** `NONE`.
- **Focus presets:** 6.1–6.5 exist, but applicability to a particular Group,
  target, performer, or spatial intent is not verified.
- **Color action resource:** no verified current-Show `Color` / `Color1`
  preset is available to B3.
- **Effect/timing source:** Effect labels and inventory do not prove behavior;
  no independently verified existing-Show timing/strobe action source exists.
- **Fixture 9999:** ungrouped, excluded, and untouched.

`SHOW_BOUND_VERIFIED` proves channel/profile facts, not a physical placement,
coverage, performer target, palette, texture, timing behavior, or artistic
function.

## Current B3 role semantics and realization boundary

The table describes the present vocabulary and action compiler; it does not
add roles or requirements.

| B3 role | Minimum technical basis | Spatial / semantic requirement | Current safe typed action path | Song / case requirement |
| --- | --- | --- | --- | --- |
| `PRIMARY_FOCUS` | Dimmer; a fixture may additionally have Pan/Tilt/Focus. | A verified target/area or safely applicable Focus/Position meaning is needed before calling it performer focus. | B3 can call a verified Focus preset then set dimmer only when a confirmed binding exists. Current preset applicability is not proven. | Design Intent must require focus; technical movement is not enough. |
| `MOVER_TEXTURE_LAYER` | A potentially useful controllable visual dimension beyond dimmer, where applicable. Pan/Tilt, gobo, color, zoom, frost, or a verified texture source can contribute, but none is mandatory by label. | Any spatial use needs verified semantics. | Current B3 emits only `SET_DIMMER` for this role; it has no safe typed movement/gobo/texture action path. | Atmosphere, contrast, sustained material, identity, or another actual context may justify texture; availability does not require use. |
| `COLOR_FIELD` | Dimmer plus verified Color capability. | Coverage, placement, and field suitability remain case facts, not FixtureType facts. | B3 requires a verified `Color`/`Color1` preset to emit color; none is currently action-ready. | Palette and section intent must justify use. |
| `DENSITY_LAYER` | Dimmer. | No geometry is inherent to the abstract compositional role. | `SET_DIMMER` is an existing typed path. | Density is a composition decision; it is not a fixture-family identity. |
| `TIMING_LAYER` | A controllable timing mechanism; shutter/strobe is technically relevant but not sufficient alone. | None inherent, unless a proposed pattern needs spatial semantics. | B3 may only retain an already verified baseline `CALL_EFFECT`; it does not create or validate a shutter/strobe/effect behavior. | A rhythmic or other context must justify timing; no automatic beat chasing. |

The canonical B3 role-state representation remains authoritative. This review
does not create a role binding, action, or realization claim.

## Capability → candidate eligibility matrix

`CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` means the fixture's verified
technical facts can support consideration of the abstract role; it never means
selected, action-ready, or artistically appropriate. `BLOCKED_BY_*` records
why current B3 cannot safely realize the role. `ROLE_VOCABULARY_GAP` prevents
forcing a useful possible function into an inaccurate existing role.

| Group | FixtureType | SHOW_BOUND_VERIFIED capabilities relevant to B3 | Candidate B3 role | Technical eligibility | Remaining blocker / required context | Evidence provenance | Case role assignment |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 — HYBRID | 2 — ZEN BAW 20R Mode 2 | DIMMER, COLOR, PAN/TILT/POSITION, GOBO, PRISM, ZOOM, FOCUS, FROST, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and a human-approved case binding; no coverage/priority inference. | Show-bound FT 2 + fresh Group membership | `NONE` |
| 1 — HYBRID | 2 — ZEN BAW 20R Mode 2 | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Field coverage/palette are unknown; current realization is `BLOCKED_BY_ACTION_GRAMMAR` because no verified Color preset/action resource exists. | Show-bound FT 2 + fresh Group membership | `NONE` |
| 1 — HYBRID | 2 — ZEN BAW 20R Mode 2 | DIMMER, PAN/TILT/POSITION, FOCUS | `PRIMARY_FOCUS` | `BLOCKED_BY_SPATIAL_SEMANTICS` | No verified performer/area target, semantic position, geometry, or per-Group Focus-preset applicability. | Show-bound FT 2 + current geometry/preset evidence | `NONE` |
| 1 — HYBRID | 2 — ZEN BAW 20R Mode 2 | PAN/TILT, GOBO, PRISM, ZOOM, FROST, COLOR | `MOVER_TEXTURE_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Present B3 cannot emit a verified texture action; no movement/gobo/effect behavior is action-ready. | Show-bound FT 2 + B3 compiler boundary | `NONE` |
| 1 — HYBRID | 2 — ZEN BAW 20R Mode 2 | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Channel exists, but safe shutter/strobe/effect behavior and typed current-Show action source are unverified. | Show-bound FT 2 + Effect/action boundary | `NONE` |
| 2 — SPOT | 3 — ZEN DMH-160 St_Preset | DIMMER, COLOR, PAN/TILT/POSITION, GOBO, PRISM, FOCUS, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required; no fixture importance inferred. | Show-bound FT 3 + fresh Group membership | `NONE` |
| 2 — SPOT | 3 — ZEN DMH-160 St_Preset | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Coverage/palette unknown; B3 Color realization blocked by absent verified Color preset/action resource. | Show-bound FT 3 + B3 action-resource evidence | `NONE` |
| 2 — SPOT | 3 — ZEN DMH-160 St_Preset | DIMMER, PAN/TILT/POSITION, FOCUS | `PRIMARY_FOCUS` | `BLOCKED_BY_SPATIAL_SEMANTICS` | No verified target/area, semantic position, geometry, or Focus-preset applicability. | Show-bound FT 3 + current geometry/preset evidence | `NONE` |
| 2 — SPOT | 3 — ZEN DMH-160 St_Preset | PAN/TILT, GOBO, PRISM, COLOR | `MOVER_TEXTURE_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Existing B3 has no verified typed texture/movement/gobo action. | Show-bound FT 3 + B3 compiler boundary | `NONE` |
| 2 — SPOT | 3 — ZEN DMH-160 St_Preset | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Shutter capability alone is not an action-ready timing source. | Show-bound FT 3 + Effect/action boundary | `NONE` |
| 3 — BEAM | 2 — ZEN BAW 20R Mode 2 | DIMMER, COLOR, PAN/TILT/POSITION, GOBO, PRISM, ZOOM, FOCUS, FROST, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required. Identical FixtureType does not create identical artistic identity to Group 1. | Show-bound FT 2 + fresh Group membership | `NONE` |
| 3 — BEAM | 2 — ZEN BAW 20R Mode 2 | Beam/optics-relevant controllable attributes above | no faithful current B3 role | `ROLE_VOCABULARY_GAP` | Aerial/beam/impact visual function must not be forced into `MOVER_TEXTURE_LAYER`; no role expansion in this review. | Show-bound FT 2 + current B3 vocabulary | `NONE` |
| 3 — BEAM | 2 — ZEN BAW 20R Mode 2 | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Coverage/palette unknown; B3 Color action resource remains unverified. This is not a beam identity claim. | Show-bound FT 2 + B3 action-resource evidence | `NONE` |
| 3 — BEAM | 2 — ZEN BAW 20R Mode 2 | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | No safe verified timing/strobe/effect action path. | Show-bound FT 2 + Effect/action boundary | `NONE` |
| 4 — WASH | 5 — ZEN MAC AU XB Standard | DIMMER, COLOR, PAN/TILT/POSITION, ZOOM, FOCUS, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required; no coverage/role identity inferred from label. | Show-bound FT 5 + fresh Group membership | `NONE` |
| 4 — WASH | 5 — ZEN MAC AU XB Standard | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Field coverage/palette unknown; absent verified Color preset/action resource blocks realization. | Show-bound FT 5 + B3 action-resource evidence | `NONE` |
| 4 — WASH | 5 — ZEN MAC AU XB Standard | DIMMER, PAN/TILT/POSITION, FOCUS | `PRIMARY_FOCUS` | `BLOCKED_BY_SPATIAL_SEMANTICS` | No semantic target/positions/geometry or demonstrated Focus-preset applicability. | Show-bound FT 5 + current geometry/preset evidence | `NONE` |
| 4 — WASH | 5 — ZEN MAC AU XB Standard | PAN/TILT, ZOOM, COLOR | `MOVER_TEXTURE_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Current B3 does not safely express movement or texture action. | Show-bound FT 5 + B3 compiler boundary | `NONE` |
| 4 — WASH | 5 — ZEN MAC AU XB Standard | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Channel capability is not verified timing behavior/action grammar. | Show-bound FT 5 + Effect/action boundary | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | DIMMER, COLOR, PAN/TILT/POSITION, ZOOM, FOCUS, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required. | Show-bound FT 4 + fresh Group membership | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Field coverage/palette unknown; no verified B3 Color preset/action resource. | Show-bound FT 4 + B3 action-resource evidence | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | DIMMER, PAN/TILT/POSITION, FOCUS | `PRIMARY_FOCUS` | `BLOCKED_BY_SPATIAL_SEMANTICS` | No semantic target/positions/geometry or per-Group Focus-preset applicability. | Show-bound FT 4 + current geometry/preset evidence | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | PAN/TILT, ZOOM, COLOR | `MOVER_TEXTURE_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Current B3 cannot express a verified texture action. Pixel/shape is separately unclassified, not inferred from the label. | Show-bound FT 4 + B3 compiler boundary | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | PIXEL/SHAPE `UNCLASSIFIED_FROM_CHANNEL_INVENTORY` | no faithful current B3 role | `ROLE_VOCABULARY_GAP` | No pixel/shape capability claim; if later verified, B3 lacks a dedicated role/action model for it. | Show-bound FT 4 + current B3 vocabulary | `NONE` |
| 5 — B-EYE | 4 — ZEN K10 Shapes | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | No verified timing/strobe/effect behavior/action path. | Show-bound FT 4 + Effect/action boundary | `NONE` |
| 6 — LED PAR | 6 — ZEN LEDPar 9c 9Ch Mode A | DIMMER, COLOR, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required; no physical coverage inferred. | Show-bound FT 6 + fresh Group membership | `NONE` |
| 6 — LED PAR | 6 — ZEN LEDPar 9c 9Ch Mode A | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Coverage/palette unknown; no verified Color preset/action resource. | Show-bound FT 6 + B3 action-resource evidence | `NONE` |
| 6 — LED PAR | 6 — ZEN LEDPar 9c 9Ch Mode A | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | No safe current-show timing/strobe/effect action source. | Show-bound FT 6 + Effect/action boundary | `NONE` |
| 7 — STROBE | 7 — Atomic 3000 LED Extended | DIMMER, COLOR, SHUTTER/STROBE | `DENSITY_LAYER` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Design Intent and approved case binding required. The Group name does not authorize impact use. | Show-bound FT 7 + fresh Group membership | `NONE` |
| 7 — STROBE | 7 — Atomic 3000 LED Extended | DIMMER, COLOR | `COLOR_FIELD` | `CAPABILITY_ELIGIBLE_BUT_CONTEXT_REQUIRED` | Coverage/palette unknown; current Color realization is not action-ready. | Show-bound FT 7 + B3 action-resource evidence | `NONE` |
| 7 — STROBE | 7 — Atomic 3000 LED Extended | SHUTTER/STROBE | `TIMING_LAYER` | `BLOCKED_BY_ACTION_GRAMMAR` | Attribute presence does not validate behavior, safe timing grammar, or an existing Effect call. | Show-bound FT 7 + Effect/action boundary | `NONE` |

## What is technically defensible now

- All seven Groups have `DIMMER`, so each is technically eligible to be
  considered for `DENSITY_LAYER`, subject to Design Intent and explicit
  case-level approval. The existing B3 `SET_DIMMER` action grammar can express
  that bounded choice.
- All seven Groups have `COLOR`, so each is technically eligible to be
  considered for `COLOR_FIELD`; this says nothing about field coverage. Its
  current B3 realization is blocked until a verified Color preset/action
  resource exists.
- Groups 1, 2, 4, and 5 have Pan/Tilt/Position and Focus, but none can be
  called `PRIMARY_FOCUS` in the performer/area sense until spatial semantics
  and preset applicability are evidenced.
- Those same technically movable Groups can be considered in a future texture
  discussion, but B3's present compiler cannot express a verified texture
  action. This is not an instruction to move them.
- No Group is timing-action-ready solely from SHUTTER/STROBE. No Group is
  assigned an Effect behavior.

## Vocabulary gaps and hypotheses explicitly downgraded

1. **BEAM / Group 3:** the verified technical profile can support useful
   beam/aerial/impact-style possibilities, but current B3 has no faithful
   abstract role for that function. It remains `ROLE_VOCABULARY_GAP`, not
   `MOVER_TEXTURE_LAYER` by convenience.
2. **B-EYE / Group 5:** `PIXEL/SHAPE` is unclassified from the actual channel
   inventory. Product or Group labels do not establish pixel/shape capability;
   a future verified capability would also expose a B3 vocabulary/action gap.
3. **All prior identity-origin hypotheses:** `HYBRID=PRIMARY_FOCUS`,
   `WASH=COLOR_FIELD`, `STROBE=TIMING_LAYER`, and equivalent label-derived
   shortcuts are downgraded to non-evidence. The prior mapping review remains
   historical only.
4. **Training Case 001:** its role observations are not imported as Existing
   Show bindings.

## Human eligibility review

The requested decision is deliberately narrow: approve, reject, or limit
individual **case-specific eligibility** candidates. It is not a request to
approve a global fixture habit, a priority order, an artistic look, or a
physical layout.

| Review item | Current evidence | Human review |
| --- | --- | --- |
| Make a named Group eligible for a future `DENSITY_LAYER` binding in a named song/case | Show-bound DIMMER and existing typed `SET_DIMMER`; composition remains contextual. | `UNSET` |
| Make a named Group eligible for a future `COLOR_FIELD` binding | Show-bound COLOR, but coverage and current B3 Color action resource remain unresolved. | `UNSET` |
| Treat Pan/Tilt/Focus Groups as performer/area `PRIMARY_FOCUS` | Blocked by semantic target/geometry/Position and preset-applicability evidence. | `UNSET — NOT READY TO APPROVE AS ACTION-READY` |
| Treat a movable Group as `MOVER_TEXTURE_LAYER` | Blocked by the present B3 texture action grammar. | `UNSET — NOT READY TO APPROVE AS ACTION-READY` |
| Treat any Group as `TIMING_LAYER` | Blocked by unverified behavior/action grammar despite SHUTTER/STROBE. | `UNSET — NOT READY TO APPROVE AS ACTION-READY` |
| Add an aerial/beam/impact or pixel/shape role | Explicit B3 vocabulary gap; outside this review's scope. | `UNSET — OUT OF SCOPE` |

## Readiness and safety

There is now enough provenance-safe technical evidence to seek
`READY_FOR_HUMAN_ELIGIBILITY_APPROVAL`: a human can review bounded,
case-specific `DENSITY_LAYER` eligibility without guessing fixture capability.
This is not approval to run `REAL_SONG_EXISTING_SHOW_AB_002` yet. That run
requires an explicit approved case binding and must still respect the present
action-resource limits.

- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- `REAL_VENUE_VALIDATION`: `WAIT_FOR_REAL_CASE`.
- MA2 objects modified: `NONE`.
- MA2 write audit: `ZERO_WRITES`.
- Fixture 9999 touched: `NO`.
