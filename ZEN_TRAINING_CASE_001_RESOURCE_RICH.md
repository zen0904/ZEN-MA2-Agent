# TRAINING_CASE_001 — Resource-rich K-pop-oriented Training Case

Case type: `RESOURCE_RICH_KPOP_ORIENTED`
Show profile: `data/ZEN_CURRENT_SHOW_PROFILE.json`

This document describes a virtual design study; it is not a physical XYZ layout and contains no MA2 commands.

## Resource snapshot

Groups: 7; Fixtures: 57; Preset references: 5; Effects: 1781; Geometry: `GEOMETRY_UNINITIALIZED`

## Role assignments
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

## KPOP_ORIENTED_RIG_ARCHITECTURE_V1

The following is case-specific and intentionally does not become a global Designer rule.

### AERIAL

Purpose: Create vertical scale and silhouette moments.
Why: Hybrid/Beam families are plausible case resources, subject to capability evidence.
Expected looks: controlled beam punctuation, silhouette layer, reserved chorus lift

### KEY_LAYER

Purpose: Keep the performer readable.
Why: Spot/Hybrid identity suggests a candidate subject layer; exact focus remains a design choice.
Expected looks: restrained verse focus, solo focus, chorus subject separation

### WASH_LAYER

Purpose: Provide broad environmental coverage.
Why: Wash/LED PAR Groups are useful candidates, not exclusive roles.
Expected looks: base wash, color field, release into outro

### TEXTURE

Purpose: Add detail and visual density without consuming every impact resource.
Why: B-EYE/Hybrid are plausible contextual sources in this training case.
Expected looks: chorus texture, repeated-section variation, controlled eye-candy

### IMPACT

Purpose: Mark high-value musical accents.
Why: Strobe is an inferred impact candidate in this case.
Expected looks: chorus punctuation, final accent, short hit

### COLOR_LAYER

Purpose: Develop palette and contrast.
Why: LED PAR/Wash/B-EYE can provide candidate color context where verified resources permit.
Expected looks: pre-chorus build, chorus palette change, outro release

## Layer combinations

- Intro/Verse: BASE + selective SUBJECT; reserve headroom.
- Pre: add COLOR or TEXTURE gradually; protect IMPACT resources.
- Chorus: open additional coverage and AERIAL/TEXTURE where verified.
- Final Chorus: combine the broadest available layers with a reserved impact accent.
- Outro: remove layers deliberately and resolve the look.

## Evidence and limits

- Role assignments derive from Group identity and current Fixture inventory, not physical plot evidence. — `CASE_SPECIFIC` / `INFERRED_FROM_GROUP_IDENTITY`
- Each Group is modeled as a design layer candidate; Group names do not constrain future roles. — `CASE_SPECIFIC` / `INFERRED_FROM_GROUP_IDENTITY`
- No final XYZ, Stage Left/Right, Front/Back, or real hanging position is asserted. — `CASE_SPECIFIC` / `UNKNOWN`

## Generalizable lessons extracted

- CHORUS should increase visual layers, contrast, coverage, or movement where available.
- Impact resources should be reserved so high-energy sections retain contrast.
- A resource-rich rig is a training context, not a requirement for a valid design.

## Review status

`CASE_SPECIFIC` decisions require user creative review. No geometry write, MA2 Preview write, or Sequence build was performed.
