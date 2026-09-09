# ZEN Creative V2 Review Package

**Scope:** read-only creative review only  
**V1 baseline:** Sequence 205 `ZEN_AI_TEST_REAL_LIGHTING_DESIGN_TEST`  
**MA2 writes during this review:** none  
**Build readiness:** not approved

## Evidence and boundaries

This package reads the persisted Scanner/Profile artifacts, Effect Catalog,
Semantic Preset Registry, V1 real-build report, and the deterministic song
input. It does not query or alter MA2.

The current persisted Group inventory proves that Groups 1–7 exist, but their
fresh membership and fixture counts are unavailable in this snapshot. The
current profile also has no usable geometry snapshot bound to those Groups.
Those fields are shown as `UNAVAILABLE`, never as zero. A future build must
refresh them before treating a candidate as a resolved typed target.

The current `data/ZEN_SHOW_PLAN.json` is an earlier Effect Resolver example,
not the authoritative plan for Sequence 205; it is intentionally excluded from
the V1 factual table below. Sequence 205 is evaluated from the real-build
report and its deterministic input.

## Available show resources

### Groups

| Group | Name | Fixture count | Verified useful metadata | Current V2 status |
|---:|---|---|---|---|
| 1 | HYBRID | UNAVAILABLE | V1 target; Group and effect target were fresh-verified during the V1 build | **V1-proven reference**; refresh membership before another build |
| 2 | SPOT | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |
| 3 | BEAM | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |
| 4 | WASH | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |
| 5 | B-EYE | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |
| 6 | LED PAR | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |
| 7 | STROBE | UNAVAILABLE | Inventory name only | Candidate; fresh membership required |

No Group-level fixture type, count, selection order, or membership is claimed
from the present saved snapshot. This is why the candidates cannot yet be used
as a promised V2 layer.

### Presets

The current Scanner exposes five Focus entries. Their stored attributes and
fixture applicability remain unavailable, so labels are retained exactly and
are not given invented meanings.

| Category | Scanner reference | Exact scanner label | V2 status |
|---|---|---|---|
| Focus | FOCUS 1 | `narrow` | Candidate; fresh exact MA2 reference check required |
| Focus | FOCUS 2 | `normal` | V1 used the fresh-verified MA2 reference `Focus 6.2 normal` |
| Focus | FOCUS 3 | `wide` | Candidate; fresh exact MA2 reference check required |
| Focus | FOCUS 4 | `min Focus` | Candidate; fresh exact MA2 reference check required |
| Focus | FOCUS 5 | `max Focus` | Candidate; fresh exact MA2 reference check required |

No current Scanner entries are available for Dimmer, Position, Color, Gobo,
Beam, or other Preset Pools. They are therefore not proposed as V2 resources.

### Semantic Position Presets

The registry defines the exact allowed labels `POS_HOME`, `POS_STAGE_L`,
`POS_STAGE_C`, `POS_STAGE_R`, `POS_STAGE_U`, and `POS_STAGE_D`, but the current
Scanner snapshot contains no matching Position Preset. **Actual present
semantic-position resources: NONE.** No Stage Left/Right conclusion is made.

### Effects

| Classification | Effect | Evidence | V2 status |
|---|---|---|---|
| VERIFIED_AGENT_OWNED | 3520 `ZEN_FX_DIM_CHASE_SLOW_GROUP1` | Agent catalog; object and label verified; parameters partial | Reference only after fresh effect and show-identity check |
| STRICT_SEMANTIC_TEMPLATE | None | No strict template mapping is persisted | None available |
| UNVERIFIED_CANDIDATE | Other inventory effects | Names alone do not prove line parameters or compatibility | Deliberately excluded from automatic V2 use |

### Geometry

The codebase has real-machine-verified Fixture/Subfixture geometry capability:
numeric X/Y/Z ordering, CENTER detection, rows, layers, INNER/OUTER ranking,
and mirror-pair candidates. It does **not** verify Stage Left/Right semantics.

For this exact persisted show state, geometry cannot yet be mapped to an actual
V2 Group or fixture set: Group membership is unavailable and the saved profile
does not contain a usable current geometry snapshot. The only safe statement is
that geometry vocabulary is available to the system, while **no current Group
or fixture set is eligible for a geometry-driven V2 cue without refresh**.

## V1 factual cue table

The `Dimmer intent` values are reconstructed from the committed deterministic
V1 Designer formula and the saved V1 song energies. They express the design
intent used to build V1; Cue-content read-back itself remains partial.

| Cue | Section | Energy | Groups | Preset | Effect | Geometry | Dimmer intent | Fade |
|---:|---|---:|---|---|---|---|---:|---:|
| 1 | INTRO | 0.18 | HYBRID | Focus 6.2 `normal` | None | None | 29 | 2.00 s |
| 2 | VERSE_1 | 0.38 | HYBRID | Focus 6.2 `normal` | None | None | 45 | 1.20 s |
| 3 | PRE_CHORUS_1 | 0.62 | HYBRID | Focus 6.2 `normal` | 3520 | None | 65 | 0.50 s |
| 4 | CHORUS_1 | 0.86 | HYBRID | Focus 6.2 `normal` | 3520 | None | 84 | 0.50 s |
| 5 | VERSE_2 | 0.46 | HYBRID | Focus 6.2 `normal` | None | None | 56 | 1.20 s |
| 6 | PRE_CHORUS_2 | 0.72 | HYBRID | Focus 6.2 `normal` | 3520 | None | 77 | 0.50 s |
| 7 | CHORUS_2 | 0.94 | HYBRID | Focus 6.2 `normal` | 3520 | None | 94 | 0.50 s |
| 8 | SOLO | 0.68 | HYBRID | Focus 6.2 `normal` | None | None | 69 | 0.50 s |
| 9 | FINAL_CHORUS | 1.00 | HYBRID | Focus 6.2 `normal` | 3520 | None | 100 | 0.50 s |
| 10 | OUTRO | 0.28 | HYBRID | Focus 6.2 `normal` | None | None | 37 | 2.00 s |

## V2 cue-by-cue creative proposal

This is a **design brief**, not an execution plan. `Conditional layer` means
the named candidate may be used only after a future read-only refresh proves
membership, ownership policy, and exact reference. If that proof is absent,
the cue must stay on the V1-proven HYBRID layer and report `RESOURCE_LIMITED`.

| Section | Purpose and energy | Groups | Preset(s) | Effect | Geometry strategy | Dimmer / intensity intent | Fade | Difference from prior cue | Why it is musically different |
|---|---|---|---|---|---|---|---|---|---|
| INTRO | Establish headroom; 0.18 | HYBRID | Focus 6.2 `normal` | None | None | Low, around V1 level | 2.0 s | Baseline | Keeps V1's deliberate, uncluttered entrance. |
| VERSE_1 | Establish the song's main visual language; 0.38 | HYBRID | Focus 6.2 `normal` | None | None | Low-to-mid | 1.2 s | Brighter, still restrained | Maintains continuity without using the payoff resource. |
| PRE_CHORUS_1 | Build tension without release; 0.62 | HYBRID plus conditional Group 2/3 layer | Focus 6.2 `normal`, or a freshly verified Focus candidate | None | Geometry only if fresh group-to-fixture mapping exists | Mid-high; layered contrast before volume | 0.8 s | Adds controlled density, not chase | Makes the chorus effect exclusive rather than predictable. |
| CHORUS_1 | First true opening; 0.86 | HYBRID; conditional second layer only if proven | Fresh-resolved Focus 6.2 `normal` | 3520, first use | None unless fresh data proves a grouping | High | 0.35–0.5 s | First effect, sharper arrival | Gives the single verified chase a recognisable first payoff. |
| VERSE_2 | Return with variation, not copy; 0.46 | Conditional Group 2/3 layer preferred; HYBRID fallback | Fresh-resolved `narrow` or `wide` candidate only if exact reference verified | None | Conditional INNER/OUTER or ROW only if currently resolved | Mid, below chorus | 1.0–1.2 s | Removes effect and changes one non-intensity dimension | A second verse should feel related but not reset identically. |
| PRE_CHORUS_2 | Push more strongly toward Chorus 2; 0.72 | HYBRID plus conditional layer | Same family as PRE 1, with proven alternate Focus if available | None by default | Conditional grouping only | High but below Chorus 2 | 0.55–0.7 s | Denser and quicker than PRE 1 | Escalates through layering and transition, while preserving the chase payoff. |
| CHORUS_2 | Open a second chapter; 0.94 | HYBRID plus a fresh-proven additional Group | Fresh-resolved Focus variation if available | 3520 only if layer differs from Chorus 1 | Conditional ROW / INNER-OUTER only if evidence exists | Very high | 0.25–0.4 s | Must change at least two dimensions | Prevents the current same-Group/same-Preset/same-Effect/higher-dimmer repetition. |
| SOLO | Create a focal reduction; 0.68 | A specific fresh-proven Group preferred; HYBRID fallback | `narrow` candidate only after exact resolution; otherwise normal | None | CENTER only when tied to actual current fixtures; no stage-side claim | Focused mid level; reduce surrounding layer only if proven | 0.8–1.0 s | Removes chase and narrows attention | Provides contrast before final lift without inventing a position look. |
| FINAL_CHORUS | The song's largest combined statement; 1.00 | Maximum coverage from all fresh-proven safe Groups | Brightest freshly verified Focus combination available | 3520, second or third and final use | Fresh-proven multi-layer geometry only | Full energy with layered support | 0.15–0.3 s | New maximum coverage plus unique transition | Must introduce a combination not previously used together, not merely 100%. |
| OUTRO | Clearly release the final energy; 0.28 | Return to HYBRID or proven minimal layer | Focus 6.2 `normal` fallback | None | None | Low release | 2.0 s | Effect off, density down, long fade | Retains V1's good resolution while responding to a larger final cue. |

## V1 → V2 comparison

| Section | V1 | V2 proposal | Why improved |
|---|---|---|---|
| PRE_CHORUS_1 | Chase at 65%, 0.5 s | No chase; layer/intensity build, 0.8 s | Preserves anticipation and protects Chorus 1's signature. |
| CHORUS_1 | First chase use, 84%, but otherwise same vocabulary | First deliberate chase release, sharper entry | Makes the effect a recognisable musical event. |
| CHORUS_2 | Same Group, Preset, Effect, and fade as Chorus 1; 94% | Needs two changed dimensions, ideally coverage plus transition or Focus | Creates real progression instead of a brightness-only uplift. |
| SOLO | No effect, same Group/Preset, 0.5 s | Focused layer/narrow candidate only after proof, slower transition | Gives the solo a design role without making a false spatial claim. |
| FINAL_CHORUS | 100%, same resources as earlier choruses | Maximum fresh-proven coverage plus final-only combination | Delivers a clear climax rather than a small final increment. |

## V2 effect policy and repeated-section development

- Use 3520 at **CHORUS_1** and **FINAL_CHORUS** by default.
- Allow **CHORUS_2** only after an additional verified layer makes the visual
  result distinct; otherwise omit it rather than repeat it automatically.
- Do not use 3520 in either pre-chorus.
- Keep Verse 2 related to Verse 1, but change one proven visual dimension.
- Make Chorus 2 differ from Chorus 1 in at least two dimensions.
- Make Final Chorus combine a resource pattern not previously used together.

## Estimated V2 creative scores

These are conditional estimates for an approved V2 that successfully resolves
the proposed resource candidates. They are not a claim that V2 has been built.

| Measure | V1 | Estimated V2 | Basis |
|---|---:|---:|---|
| Lighting design variation | 3/10 | 6/10 | Pre/chorus separation, second-verse change, and distinct final policy. |
| Musical progression | 5/10 | 7/10 | Clearer payoff hierarchy and more meaningful repeated-section escalation. |
| Resource usage | 2/10 | 5/10 | Only if at least one additional Group or Focus reference passes refresh. |
| Live usability | 6/10 | 7/10 | Still simple enough to operate, with clearer section identities. |
| Overall creative | 4/10 | 6/10 | A purposeful V2 direction, still limited by current verified resource depth. |

## Remaining creative weaknesses

1. `RESOURCE_LIMITED`: current saved membership and Group-bound geometry data
   are insufficient to promise multi-group or INNER/OUTER implementation.
2. There is no scanned semantic Position Preset, so a solo cannot honestly be
   positioned on stage through the agent yet.
3. The only verified effect is one slow Dimmer Chase; that is acceptable, but
   it limits contrast until more resources are verified.
4. Preset content and effect-line read-back remain partial, so this package
   only uses exact references and avoids claims about internal visual values.

## Creative review decision

`USER_CREATIVE_REVIEW_REQUIRED` — use this package to decide whether the
proposed hierarchy matches the song and your staging taste. A future V2 must
first perform read-only resource resolution, then show a new Preview and obtain
approval before it can create a separate Agent-owned sequence.
