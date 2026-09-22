# ZEN Current Show Resource Report

> **Historical snapshot notice (2026-09-22):** This report is evidence for the
> Show state/fingerprint captured when it was written. It is **not** current
> resource truth for the active FULL_ARTISTIC_PATH_001 mainline. Later Test Show
> work created native Color Presets and changed geometry. Always rescan the
> currently loaded Show before deciding whether Color, Position, Effect, or
> other resources exist.
>

**Scope:** fresh read-only discovery of the currently running grandMA2 Show.

## Show identity

- Current: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea` (SCANNED_SHOW_PROFILE_FINGERPRINT)
- Previous profile identity: `497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`
- Identity comparison: **SAME_FINGERPRINT**
- Previous Show-bound cache isolated: **YES**
- Old Effect/Preset/Group/Sequence references are not treated as current resources.

## Groups

| ID | Name | Members | Ordered fixture IDs | Fixture types | Freshness |
|---:|---|---:|---|---|---|
| 1 | HYBRID | 8 | 101, 102, 103, 104, 105, 106, 107, 108 | 2 ZEN BAW 20R Mode 2 ×8 | SUPPORTED |
| 2 | SPOT | 8 | 301, 302, 303, 304, 305, 306, 307, 308 | 3 ZEN DMH-160 St_Preset ×8 | SUPPORTED |
| 3 | BEAM | 8 | 201, 202, 203, 204, 205, 206, 207, 208 | 2 ZEN BAW 20R Mode 2 ×8 | SUPPORTED |
| 4 | WASH | 8 | 501, 502, 503, 504, 505, 506, 507, 508 | 5 ZEN MAC AU XB Standard ×8 | SUPPORTED |
| 5 | B-EYE | 8 | 401, 402, 403, 404, 405, 406, 407, 408 | 4 ZEN K10 Shapes ×8 | SUPPORTED |
| 6 | LED PAR | 8 | 601, 602, 603, 604, 605, 606, 607, 608 | 6 ZEN LEDPar 9c 9Ch Mode A ×8 | SUPPORTED |
| 7 | STROBE | 8 | 701, 702, 703, 704, 705, 706, 707, 708 | 7 Atomic 3000 LED Extended ×8 | SUPPORTED |

## Fixtures and Subfixtures

- Root Fixtures: **57**
- Geometry-bearing Subfixtures: **65**
- Grouped Fixture union: **56**

### Ungrouped Fixtures

- Fixture 9999 `461 G BSW 1` — type `2 ZEN BAW 20R Mode 2`, patch `(-)`, subfixtures 1; **UNGROUPED_FIXTURE / excluded from Auto Geometry**.

### Group membership overlap

- None detected.

### Fixture Types

- `2 ZEN BAW 20R Mode 2`: 17 fixture(s)
- `3 ZEN DMH-160 St_Preset`: 8 fixture(s)
- `4 ZEN K10 Shapes`: 8 fixture(s)
- `5 ZEN MAC AU XB Standard`: 8 fixture(s)
- `6 ZEN LEDPar 9c 9Ch Mode A`: 8 fixture(s)
- `7 Atomic 3000 LED Extended`: 8 fixture(s)

## Presets

### FOCUS

| Reference | ID | Exact name |
|---|---:|---|
| 6.1 | 1 | narrow |
| 6.2 | 2 | normal |
| 6.3 | 3 | wide |
| 6.4 | 4 | min Focus |
| 6.5 | 5 | max Focus |

## Semantic Position Presets

NONE — no registry label has a fresh exact match in this Show.

## Effects

- Total: 1781
- Verified Agent-owned reusable: 0
- Legacy catalog entries isolated: 1
- Strict semantic templates: 0
- Named unverified: 1781
- Unlabeled: 0

### Verified Agent-owned

- None

### Legacy catalog entries isolated

- 3520: `ZEN_FX_DIM_CHASE_SLOW_GROUP1`

### Strict semantic templates

- None

### Named unverified shortlist

- 1000: `DIM Low 1`
- 1001: `DIM Low 2`
- 1002: `DIM Low 3`
- 1003: `DIM Low 4`
- 1004: `DIM Low 5`
- 1005: `DIM Low 6`
- 1006: `DIM Low 7`
- 1007: `DIM Low 8`
- 1008: `DIM Low 9`
- 1009: `DIM Low 10`
- 1010: `DIM Low 11`
- 1011: `DIM Low 12`
- 1012: `DIM Low 13`
- 1013: `DIM Low 14`
- 1014: `XK-Form`
- 1015: `DimPwm >B`
- 1016: `DimPwm >B`
- 1017: `DimRam >B`
- 1018: `Dim ..<`
- 1019: `Dim ..>`
- 1020: `Dim TT >>`
- 1021: `Dim TT <<`
- 1022: `DIM ..`
- 1023: `DIM ...`
- 1024: `DIM ....`
- 1025: `DIM .....`
- 1026: `DIM Speed Low`
- 1027: `DIM Speed Low`
- 1028: `Dim Sin 0.-360 LH=0.20`
- 1029: `Dim Sin 0.-360 LW=0.20`

## Geometry

- State: **GEOMETRY_UNINITIALIZED** — All returned Fixtures overlap at a zero or single coordinate.
- Coverage: 65/65 (100%)
- Non-zero XYZ Subfixtures: 0
- Unique XYZ positions: 1
- Duplicate XYZ clusters: 1
- Terms are numeric X/Y/Z only; Stage Left/Right is intentionally unassigned.

## Sequence / Cue / Page / Executor / Timecode occupancy

- Sequences: 5
- Cue discovery: EXPECTED_EMPTY_USER_CONFIRMED (0 parsed)
- Pages: 1
- Executors: 0
- Timecodes: 0

### Existing Sequences

- 201: `ZEN_AI_TEST_ZEN_FIRST_SONG_TEST`
- 202: `ZEN_AI_TEST_ZEN_FIRST_SONG_TEST_R2`
- 203: `ZEN_AI_TEST_ZEN_REAL_SONG_ANALYSIS_TEST`
- 204: `ZEN_AI_EFFECT_CALL_TEST_204`
- 205: `ZEN_AI_TEST_REAL_LIGHTING_DESIGN_TEST`

### Cue inventory limitation

- The Show owner confirmed this template intentionally has no Cues. The generic Cue inventory reader is still not a portable enumeration backend because MA2 returned Error #28.

## Creative resource analysis

- Fresh non-empty Groups: 7 — 1 HYBRID, 2 SPOT, 3 BEAM, 4 WASH, 5 B-EYE, 6 LED PAR, 7 STROBE.
- Fixture-type diversity: 6 types across 57 Fixtures.
- Safe Preset inventory returned by MA2: 5 reference(s).
- Current verified reusable Effects: 0; legacy catalog entries remain isolated.
- Geometry strategies: NOT_AVAILABLE — no positioning, pairing, or row inference is safe while all XYZ values overlap.
- Auto-Geometry candidates: Group 1 HYBRID, Group 2 SPOT, Group 3 BEAM, Group 4 WASH, Group 5 B-EYE, Group 6 LED PAR, Group 7 STROBE.

## Designer resource readiness

- Overall: **PARTIAL**
- Without geometry: **READY**
- Auto Geometry readiness: **READY**
- Creative diversity: {'nonempty_groups': 7, 'preset_references': 5, 'verified_or_template_effects': 0, 'geometry_state': 'GEOMETRY_UNINITIALIZED'}
- Exact limitation: This template's empty Cue inventory is operator-confirmed. MA2 Error #28 means the generic Cue inventory reader remains unsuitable for inferring Cue emptiness in other Shows. Fixture geometry is GEOMETRY_UNINITIALIZED; it is not used as a creative placement guarantee.

## MA2 write audit

- **ZERO_WRITES**
- Allowed transport was Login, List, and Agent-owned `Export Group` only.
- Unexpected commands: none
