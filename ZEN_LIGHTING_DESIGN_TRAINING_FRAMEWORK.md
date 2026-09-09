# ZEN Lighting Design Training Case Framework

## Training philosophy

A Training Case is a bounded design-learning context, not a fixed rig profile and not a global Designer rulebook. It records what a particular resource set makes possible, what was inferred, and which lessons generalize to other shows.

The pipeline boundary remains:

`ZEN_SHOW_PROFILE + Training Case knowledge + ZEN_SONG_ANALYSIS → Designer → typed ZEN_SHOW_PLAN → Builder`

Training Cases never contain MA2 commands. Designer remains command-free; Builder remains the only MA2 command-generation boundary.

## Global design principles

### RESERVE_HEADROOM

- Why: A look needs room to grow later.
- Useful when: Openings, verses, and any long-form build.
- Not automatically applicable when: A deliberately maximal one-shot cue.
- Scope: `GENERALIZABLE_LESSON`

### SECTION_CONTRAST

- Why: Section changes should be legible as changes in visual structure, not only level.
- Useful when: Verse/chorus and pre/final transitions.
- Not automatically applicable when: A deliberately static ambient passage.
- Scope: `GENERALIZABLE_LESSON`

### REPEATED_SECTION_DEVELOPMENT

- Why: Later occurrences should have a reason to feel related but not copied.
- Useful when: Repeated verses, choruses, or hooks.
- Not automatically applicable when: A conscious exact reprise.
- Scope: `GENERALIZABLE_LESSON`

### EFFECT_FATIGUE_AVOIDANCE

- Why: A motion effect loses impact when it is always present.
- Useful when: Chorus/impact planning.
- Not automatically applicable when: A continuous texture brief that explicitly demands it.
- Scope: `GENERALIZABLE_LESSON`

### LAYER_ESCALATION

- Why: Energy can rise through coverage, contrast, motion, focus, or added layers.
- Useful when: Builds and finales.
- Not automatically applicable when: When resources or song structure require restraint.
- Scope: `GENERALIZABLE_LESSON`

### FOCUS_HIERARCHY

- Why: The audience needs a readable subject even in a rich rig.
- Useful when: Solos, verses, and dense choruses.
- Not automatically applicable when: An intentionally environmental interlude.
- Scope: `GENERALIZABLE_LESSON`

### RESOURCE_AWARENESS

- Why: The same intent must degrade gracefully on limited or asymmetric rigs.
- Useful when: Every design decision.
- Not automatically applicable when: Never; the implementation may vary.
- Scope: `GENERALIZABLE_LESSON`

### ASYMMETRY_TOLERANCE

- Why: A designer should work with imperfect rigs instead of inventing symmetry.
- Useful when: Medium, small, and production shows.
- Not automatically applicable when: Only when symmetry is actually evidenced.
- Scope: `GENERALIZABLE_LESSON`

## Rig Role vocabulary

A Role describes the design job a Fixture can perform in context. `ROLE != FIXTURE TYPE`; one Fixture family may take different roles in another Case.

`AERIAL`, `KEY_LAYER`, `WASH_LAYER`, `TEXTURE`, `BEAM_LAYER`, `COLOR_LAYER`, `IMPACT`, `ACCENT`, `FLOOR`, `SIDE`, `BACKLIGHT`, `SILHOUETTE`, `EYE_CANDY`, `PERFORMER_FOCUS`, `ENVIRONMENT`, `UTILITY`

## Proposed Rig Zone vocabulary

These are design-language candidates only, not verified MA2 geometry: `PROPOSED_RIG_ZONE_NOT_VERIFIED_GEOMETRY`.

Allowed names: `UPSTAGE`, `MIDSTAGE`, `DOWNSTAGE`, `HIGH`, `MID`, `LOW`, `FLOOR`, `CENTER`, `INNER`, `OUTER`, `SIDE`, `EDGE`.

## Visual Layer model

- **BASE_LAYER** — Maintain a readable minimum look and headroom.
- **SUBJECT_LAYER** — Separate performers or the focal subject.
- **AERIAL_LAYER** — Add beams, silhouettes, or vertical scale when available.
- **TEXTURE_LAYER** — Add movement, pixel texture, or visual detail.
- **COLOR_LAYER** — Shape palette and environment without relying on intensity alone.
- **IMPACT_LAYER** — Reserve high-contrast accents for meaningful musical moments.
- **ACCENT_LAYER** — Deliver short hits or sectional punctuation.

A Cue may use only a subset of layers. Increased energy can come from adding coverage, contrast, movement, focus, geometry, or an impact layer—not just Dimmer.

## Anti-pattern evidence

- **INTENSITY_ONLY_PROGRESSION** — Raising Dimmer while keeping every other layer identical. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **SAME_GROUP_EVERY_CUE** — Using one Group for all sections despite available alternatives. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **SAME_PRESET_EVERY_CUE** — Missing palette/focus development when verified resources exist. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **EFFECT_FATIGUE** — Repeating one Effect until it no longer marks a meaningful section. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **EFFECT_TOO_EARLY** — Spending a signature motion resource before the first major opening. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **FINAL_EQUALS_ONE_HUNDRED** — Treating Final Chorus escalation as Dimmer 100% only. (Current V1 creative review; `GENERALIZABLE_LESSON`)
- **GEOMETRY_IGNORED** — Failing to use verified numeric geometry when it is available. (Current V1 creative review; `GENERALIZABLE_LESSON`)

## Training Case 001

- Case: `TRAINING_CASE_001` — Resource-rich training rig — K-pop-oriented design study
- Type: `RESOURCE_RICH_KPOP_ORIENTED`
- Resource scale: `RESOURCE_RICH`
- Style orientation: `KPOP` (case context only)
- Show profile: `data/ZEN_CURRENT_SHOW_PROFILE.json`
- Confidence: `PARTIAL_CASE_CONTEXT`

### Current resource evidence

- Groups: 7 with fresh ordered membership
- Root Fixtures: 57
- Preset references: 5
- Effects: 1781 inventory entries; line parameters `PARTIAL`
- Geometry: `GEOMETRY_UNINITIALIZED`
- Semantic position labels: `NONE`

### Current Group role analysis

### Group 1 `HYBRID`

- Fixture IDs (verified selection order): `101, 102, 103, 104, 105, 106, 107, 108`
- Fixture Type(s): `2 ZEN BAW 20R Mode 2`
- Primary role: **AERIAL**
- Secondary roles: `KEY_LAYER, TEXTURE`
- Contextual roles: `IMPACT`
- Possible rig zones: `HIGH, MID, CENTER` (**PROPOSED_RIG_ZONE**)
- Rationale: A versatile case-specific moving layer that can bridge aerial and subject looks.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 2 `SPOT`

- Fixture IDs (verified selection order): `301, 302, 303, 304, 305, 306, 307, 308`
- Fixture Type(s): `3 ZEN DMH-160 St_Preset`
- Primary role: **KEY_LAYER**
- Secondary roles: `PERFORMER_FOCUS, ACCENT`
- Contextual roles: `BACKLIGHT`
- Possible rig zones: `MID, CENTER, SIDE` (**PROPOSED_RIG_ZONE**)
- Rationale: A focused source for subject separation; actual use depends on fixture capability and plot.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 3 `BEAM`

- Fixture IDs (verified selection order): `201, 202, 203, 204, 205, 206, 207, 208`
- Fixture Type(s): `2 ZEN BAW 20R Mode 2`
- Primary role: **BEAM_LAYER**
- Secondary roles: `AERIAL, SILHOUETTE`
- Contextual roles: `ACCENT`
- Possible rig zones: `HIGH, UPSTAGE, EDGE` (**PROPOSED_RIG_ZONE**)
- Rationale: A narrow-beam family can provide contrast and aerial punctuation in this case.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 4 `WASH`

- Fixture IDs (verified selection order): `501, 502, 503, 504, 505, 506, 507, 508`
- Fixture Type(s): `5 ZEN MAC AU XB Standard`
- Primary role: **WASH_LAYER**
- Secondary roles: `COLOR_LAYER, ENVIRONMENT`
- Contextual roles: `KEY_LAYER`
- Possible rig zones: `MID, DOWNSTAGE, CENTER` (**PROPOSED_RIG_ZONE**)
- Rationale: A broad source can establish coverage and color context without fixing a venue position.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 5 `B-EYE`

- Fixture IDs (verified selection order): `401, 402, 403, 404, 405, 406, 407, 408`
- Fixture Type(s): `4 ZEN K10 Shapes`
- Primary role: **TEXTURE**
- Secondary roles: `COLOR_LAYER, EYE_CANDY`
- Contextual roles: `IMPACT`
- Possible rig zones: `MID, HIGH, OUTER` (**PROPOSED_RIG_ZONE**)
- Rationale: Pixel/shape capability is a case hypothesis, not a global Fixture Type rule.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 6 `LED PAR`

- Fixture IDs (verified selection order): `601, 602, 603, 604, 605, 606, 607, 608`
- Fixture Type(s): `6 ZEN LEDPar 9c 9Ch Mode A`
- Primary role: **COLOR_LAYER**
- Secondary roles: `WASH_LAYER, UTILITY`
- Contextual roles: `BACKLIGHT`
- Possible rig zones: `LOW, MID, FLOOR` (**PROPOSED_RIG_ZONE**)
- Rationale: A compact color layer can support large looks or remain a restrained base.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### Group 7 `STROBE`

- Fixture IDs (verified selection order): `701, 702, 703, 704, 705, 706, 707, 708`
- Fixture Type(s): `7 Atomic 3000 LED Extended`
- Primary role: **IMPACT**
- Secondary roles: `ACCENT, EYE_CANDY`
- Contextual roles: `AERIAL`
- Possible rig zones: `HIGH, EDGE, OUTER` (**PROPOSED_RIG_ZONE**)
- Rationale: Reserved impact capacity preserves contrast for high-energy sections.
- Confidence: `INFERRED_FROM_GROUP_IDENTITY`; scope: `CASE_SPECIFIC`

### K-pop-oriented virtual rig architecture

This is a case-specific design study. It is not a global rule such as CHORUS = BEAM + STROBE.

#### AERIAL

- Purpose: Create vertical scale and silhouette moments.
- Why this fixture: Hybrid/Beam families are plausible case resources, subject to capability evidence.
- Expected looks: controlled beam punctuation, silhouette layer, reserved chorus lift
- Scope: `CASE_SPECIFIC`

#### KEY_LAYER

- Purpose: Keep the performer readable.
- Why this fixture: Spot/Hybrid identity suggests a candidate subject layer; exact focus remains a design choice.
- Expected looks: restrained verse focus, solo focus, chorus subject separation
- Scope: `CASE_SPECIFIC`

#### WASH_LAYER

- Purpose: Provide broad environmental coverage.
- Why this fixture: Wash/LED PAR Groups are useful candidates, not exclusive roles.
- Expected looks: base wash, color field, release into outro
- Scope: `CASE_SPECIFIC`

#### TEXTURE

- Purpose: Add detail and visual density without consuming every impact resource.
- Why this fixture: B-EYE/Hybrid are plausible contextual sources in this training case.
- Expected looks: chorus texture, repeated-section variation, controlled eye-candy
- Scope: `CASE_SPECIFIC`

#### IMPACT

- Purpose: Mark high-value musical accents.
- Why this fixture: Strobe is an inferred impact candidate in this case.
- Expected looks: chorus punctuation, final accent, short hit
- Scope: `CASE_SPECIFIC`

#### COLOR_LAYER

- Purpose: Develop palette and contrast.
- Why this fixture: LED PAR/Wash/B-EYE can provide candidate color context where verified resources permit.
- Expected looks: pre-chorus build, chorus palette change, outro release
- Scope: `CASE_SPECIFIC`

### Case-specific assumptions

- Role assignments derive from Group identity and current Fixture inventory, not physical plot evidence. (`CASE_SPECIFIC`, confidence `INFERRED_FROM_GROUP_IDENTITY`)
- Each Group is modeled as a design layer candidate; Group names do not constrain future roles. (`CASE_SPECIFIC`, confidence `INFERRED_FROM_GROUP_IDENTITY`)
- No final XYZ, Stage Left/Right, Front/Back, or real hanging position is asserted. (`CASE_SPECIFIC`, confidence `UNKNOWN`)

### Generalizable lessons

- CHORUS should increase visual layers, contrast, coverage, or movement where available. (`GENERALIZABLE_LESSON`; evidence: V1 creative review)
- Impact resources should be reserved so high-energy sections retain contrast. (`GENERALIZABLE_LESSON`; evidence: V1 effect-fatigue review)
- A resource-rich rig is a training context, not a requirement for a valid design. (`GENERALIZABLE_LESSON`; evidence: Framework requirement)

## Future Case stubs

Only schema examples exist; no additional Cases are implemented.

- `CASE_002_MEDIUM_LIVE` — scale `MEDIUM`, orientation `BAND`, status `SCHEMA_STUB_ONLY`
- `CASE_003_SMALL_VENUE` — scale `SMALL`, orientation `GENERAL`, status `SCHEMA_STUB_ONLY`
- `CASE_004_LED_ONLY` — scale `LIMITED`, orientation `GENERAL`, status `SCHEMA_STUB_ONLY`
- `CASE_005_IMPERFECT_RIG` — scale `MEDIUM`, orientation `GENERAL`, status `SCHEMA_STUB_ONLY`

## Designer integration boundary

- Input: `ZEN_SHOW_PROFILE, Training Case design knowledge, ZEN_SONG_ANALYSIS`
- Output: `ZEN_SHOW_PLAN`
- Status: `INTERFACE_PLANNED_NOT_RUNTIME_WIRED`
- Boundary: Training Case supplies roles, layers, principles, and lessons; Designer emits typed intent; Builder remains the only MA2 command boundary.

## User-style separation

No `ZEN_STYLE_PROFILE` was created. General professional design competence stays separate from future user preferences and review feedback.

## Safety

- Read-only/local-only case artifact.
- No Move3D, Rotate3D, Store, Assign, Clone, Delete, Preset, Effect, Sequence, Cue, or Patch operation.
- Prior A/B/C Auto Geometry proposals remain proposal-only and were not applied.
