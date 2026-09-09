# ZEN Real Song Design Report

Song: REAL_LIGHTING_DESIGN_TEST  
Source: manual/script-parsed deterministic integration input  
Real MA2 target: Sequence 205 — `ZEN_AI_TEST_REAL_LIGHTING_DESIGN_TEST`

## Deterministic progression

| Cue | Section | Energy | Fade | Preset | Effect |
|---:|---|---:|---:|---|---|
| 1 | INTRO | 0.18 | 2.00 | Focus 6.2 `normal` | None |
| 2 | VERSE_1 | 0.38 | 1.20 | Focus 6.2 `normal` | None |
| 3 | PRE_CHORUS_1 | 0.62 | 0.50 | Focus 6.2 `normal` | 3520 |
| 4 | CHORUS_1 | 0.86 | 0.50 | Focus 6.2 `normal` | 3520 |
| 5 | VERSE_2 | 0.46 | 1.20 | Focus 6.2 `normal` | None |
| 6 | PRE_CHORUS_2 | 0.72 | 0.50 | Focus 6.2 `normal` | 3520 |
| 7 | CHORUS_2 | 0.94 | 0.50 | Focus 6.2 `normal` | 3520 |
| 8 | SOLO | 0.68 | 0.50 | Focus 6.2 `normal` | None |
| 9 | FINAL_CHORUS | 1.00 | 0.50 | Focus 6.2 `normal` | 3520 |
| 10 | OUTRO | 0.28 | 2.00 | Focus 6.2 `normal` | None |

## Resources and safety boundaries

- Target Group: dynamically resolved Group 1 `HYBRID`.
- Effect: 3520 `ZEN_FX_DIM_CHASE_SLOW_GROUP1`, reused only after a fresh exact `List Effect 3520` label proof.
- No new Effect was created.
- Existing Sequences 201, 202, and 204 were excluded from allocation.
- The build created only Sequence 205 and its 10 new Cues.
- The normal Builder sent `ClearAll` before and after the build.

## Real-MA2 verification

The packaged Desktop path completed Preview → Approval → Builder on grandMA2.
Sequence identity, all 10 Cue labels, and all stored Fades were read back
successfully. Effect 3520 and Preset 6.2 were read again after the build and
their references remained present. Effect application commands returned no
MA2 error. Cue-content Effect read-back remains `PARTIAL` because no safe Cue
content provider exists; this does not invalidate the separately real-machine
verified `Group → Effect <id> → Store Cue` grammar.

## Design interpretation

The build intentionally leaves INTRO, verses, SOLO, and OUTRO without an
Effect. PRE/CHORUS sections reuse the single verified slow Dimmer Chase rather
than generating duplicate pool resources. Repeated sections receive bounded,
deterministic intensity uplift. Neutral numeric geometry is available to the
Designer, but this Group-based PoC does not claim unverified Stage Left/Right
semantics. No exact `POS_STAGE_*` semantic position preset was referenced, so
position actions were safely skipped.
