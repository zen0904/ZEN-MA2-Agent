# Real MA2 Test Show — SHEESH Build 001

**Mode:** `TEST_SHOW_MODE = WRITE_ALLOWED` — current fingerprinted Existing
Show only. `PRODUCTION_SHOW_MODE = PREVIEW_APPROVAL_REQUIRED`.

## Actual MA2 result

- Song: `BABYMONSTER - SHEESH`.
- Sequence: `901` — `ZEN_SHEESH_TEST`.
- Executor: Page 1 Executor `201` (`1.201` read-back) — `ZEN_SHEESH_TEST`.
- Cues: `15`, all cue labels read back from Sequence 901.
- New native Color presets: `4.101`–`4.113`, all labels read back.
- New test geometry: `TEST_STAGE_LAYOUT_SHEESH_001`, all addressed primary
  subfixtures read back; Atomic `701`–`708` instances `.1` and `.2` both read
  back at their intended shared coordinate.
- Timecode: `NOT_WRITTEN_AUDIO_FILE_NOT_AVAILABLE`.

The sequence and executor intentionally share the visible label. In this MA2
Show, `Label Executor` also changed the attached Sequence's visible name; the
build preserves that native behavior instead of pretending the two labels are
independent.

## Design concept

The test is a contrast-led, editable SHEESH starting point: the intro and
bridge preserve negative space, the pre-chorus stages pressure rather than
full output, the first hook establishes a bounded red/amber statement, the
second hook redistributes visual material instead of simply becoming brighter,
and the final refrain expands without putting every Group at 100%. Group
labels were not used as permanent artistic roles: any Group can be quiet or
dark in a cue, and Group 2 receives Dimmer only because no safe RGB preset
action was assumed for its color-wheel profile.

This is a human-review test composition, not a permanent SHEESH recipe, B3
activation, style rule, or judgment that this is the correct visual design.

## Native editable palette

| Preset | Label | Test RGB values |
|---|---|---:|
| 4.101 | `ZEN_COLOR_01_RED` | 100 / 0 / 0 |
| 4.102 | `ZEN_COLOR_02_AMBER` | 100 / 35 / 0 |
| 4.103 | `ZEN_COLOR_03_YELLOW` | 100 / 100 / 0 |
| 4.104 | `ZEN_COLOR_04_LIME` | 55 / 100 / 0 |
| 4.105 | `ZEN_COLOR_05_GREEN` | 0 / 100 / 0 |
| 4.106 | `ZEN_COLOR_06_MINT` | 0 / 100 / 45 |
| 4.107 | `ZEN_COLOR_07_CYAN` | 0 / 100 / 100 |
| 4.108 | `ZEN_COLOR_08_BLUE` | 0 / 20 / 100 |
| 4.109 | `ZEN_COLOR_09_INDIGO` | 25 / 0 / 100 |
| 4.110 | `ZEN_COLOR_10_MAGENTA` | 100 / 0 / 100 |
| 4.111 | `ZEN_COLOR_11_PINK` | 100 / 0 / 35 |
| 4.112 | `ZEN_COLOR_12_WHITE` | 100 / 100 / 100 |
| 4.113 | `ZEN_COLOR_13_CTO_CHAMPAGNE` | 100 / 55 / 25 |

These are editable MA2 test values using the Show's MA2-exposed RGB control
representation. They are not a separate physical-CMY branch or permanent
palette truth. Unsupported profile behavior is intentionally not assumed.

## Provisional Stage / 3D arrangement

The existing geometry was all-origin. `Move3D` wrote a balanced test layout
that Stage View and 3D share. It is not a venue calibration and does not claim
any real-world stage-axis semantics.

- X row for each fixture family: `-5.25, -3.75, -2.25, -0.75, 0.75, 2.25,
  3.75, 5.25`.
- Group rows `(Y, Z)`: G1 `(3, 6)`, G2 `(3, 4)`, G3 `(3, 8)`, G4 `(1, 7)`,
  G5 `(0, 5)`, G6 `(-2, 1)`, G7 `(-1, 3)`.
- Each Group's ordered eight Fixture IDs retains its original identity. G7
  has two actual Atomic Subfixtures; both received the same parent fixture
  coordinate. Patch/address and rotation were not changed.

Zen should correct this directly after looking in Stage/3D; the geometry is
explicitly `TEST_STAGE_LAYOUT_SHEESH_001`, not Current Show venue evidence.

## Cue structure

The exact typed plan is
[`data/zen_real_ma2_test_show_sheesh_001_plan.json`](data/zen_real_ma2_test_show_sheesh_001_plan.json).
The dimmer tuple is `G1/G2/G3/G4/G5/G6/G7`; listed Color calls are only on
fixtures with the safe RGB preset route.

| Cue | Label | Fade | Color calls | Dimmer tuple |
|---:|---|---:|---|---|
| 1 | `INTRO_NEGATIVE_SPACE` | 1.8 | G6 Indigo | 12/0/0/0/0/18/0 |
| 2 | `INTRO_REVEAL` | 1.2 | G1 Indigo; G5 Magenta; G6 Indigo | 22/0/0/0/18/28/0 |
| 3 | `VERSE_1_TENSION` | 0.8 | G1 Red; G3 Indigo; G4 Blue; G6 Indigo | 34/16/20/25/0/32/0 |
| 4 | `PRE_CHORUS_1_COMPRESS` | 1.0 | G1/G4 Magenta; G3/G6 Blue; G5 Indigo | 42/20/34/38/30/38/0 |
| 5 | `HOOK_1_SHEESH` | 0.25 | G1/G4/G6 Red; G3/G5 Amber | 72/34/68/58/52/44/0 |
| 6 | `HOOK_1_ACCENT` | 0 | G1/G3/G4/G5/G6/G7 White | 78/40/74/64/58/50/25 |
| 7 | `RAP_1_REFRAME` | 0.5 | G1/G6 Indigo; G4 Blue | 35/42/18/22/0/20/0 |
| 8 | `VERSE_2_DRIVE` | 0.6 | G1/G6 Red; G3 Magenta; G5 Indigo | 45/25/35/0/30/30/0 |
| 9 | `PRE_CHORUS_2_BUILD` | 0.9 | G1/G4/G5 Magenta; G3/G6 Blue | 56/30/48/45/44/40/0 |
| 10 | `HOOK_2_SHEESH` | 0.25 | repeat hook palette | 72/34/68/58/52/44/0 |
| 11 | `HOOK_2_DEVELOP` | 0.35 | G1/G4 Red; G3/G5 Magenta; G6 Amber | 65/35/84/50/66/35/18 |
| 12 | `BRIDGE_RESET` | 1.5 | G1/G6 Blue; G4 Indigo | 15/0/0/22/0/28/0 |
| 13 | `FINAL_BUILD` | 1.0 | G1/G4/G6 Amber; G3/G5 Magenta | 54/25/46/42/45/40/0 |
| 14 | `FINAL_REFRAIN` | 0.2 | G1/G4/G6 Red; G3/G5 Amber; G7 White | 84/58/78/74/72/63/38 |
| 15 | `OUTRO_RELEASE` | 2.2 | G1/G4/G6 CTO/Champagne | 18/0/0/24/0/20/0 |

No Timecode or fake internet-derived timestamps were created. Cue placement is
intended to be aligned to the real audio during console rehearsal.

## Read-back and exceptions

- 13/13 Color preset labels: `VERIFIED`.
- 56/56 fixture primary geometry targets plus Atomic secondary subfixtures:
  `VERIFIED`.
- 15/15 cue labels, Sequence 901 and Executor `1.201`: `VERIFIED`.
- Fixture 9999: `UNTOUCHED`.
- Existing Sequences 201, 202, 204 and 205: not targeted or modified.
- Patch/address/fixture IDs/rotation: not modified.
- Effects, Speed Masters, movement, gobo/prism/zoom/frost, semantic positions,
  pixel/shape behavior, strobe behavior and Timecode: `NOT_USED`.

Two MA2 errors were retained and corrected rather than hidden:

1. `Move3D` on an Atomic parent Fixture returned `Error #72`; the successful
   build addresses its verified `.1` and `.2` Subfixtures explicitly.
2. `Assign ... Executor 1.901` and `1.240` returned `Error #9`; MA2 accepted
   local Executor number `201`, read back as Page 1 Executor `1.201`.

The real-console command audit, including these failed attempts and final
read-back, is retained locally in the Agent-owned ignored run evidence. The
executed test-build attempts totalled `560` console write commands, including
`ClearAll`, individual fixture geometry, preset creation, cue programming,
two rejected Executor attempts and their successful recovery. No writes target
unrelated production object IDs.

## What Zen should inspect now

1. Open Stage/3D and correct the provisional coordinates if the composition
   is visually misleading.
2. Run Executor `1.201` with the real SHEESH audio and place/trim the 15 cues.
3. Mark specific cues as too busy, too empty, too flat, too bright, poorly
   colored, too similar, or structurally wrong.
4. Check whether the repeated second hook develops usefully, and whether the
   bridge/final refrain retain enough contrast.
5. Check that native Preset, Sequence, Cue and Executor organization is quick
   to edit manually — the Focus Execute handover test.

The next task is Zen's visual/operator feedback, not another automatic
research gate or production activation.
