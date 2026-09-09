# ZEN Auto Geometry Proposal

**Mode:** read-only virtual proposal / preview. No MA2 object was modified.

- Show identity: `{'kind': 'SCANNED_SHOW_PROFILE_FINGERPRINT', 'value': '497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea', 'confidence': 'PARTIAL'}`
- Current geometry state: **GEOMETRY_UNINITIALIZED**
- Root Fixtures: **57**; grouped: **56**
- Subfixture policy: `ROOT_GEOMETRY_WITH_SUBFIXTURE_INHERITANCE_UNLESS_VERIFIED_INDEPENDENT_OFFSET`
- Coordinates use neutral numeric X/Y/Z axes. They do not claim Stage Left/Right, Front/Back, or real venue rigging.

## Fixture membership audit

- Group membership overlap: **NO**
- Ungrouped Fixtures: **1**
- Fixture 9999 `461 G BSW 1` — `2 ZEN BAW 20R Mode 2`, patch `(-)`: `UNGROUPED_FIXTURE` / excluded from Auto Geometry.

## Candidates

### Candidate A_LAYERED_ROWS — Layered Rows

- Spacing: `1.0` virtual units
- Creative usefulness: **BEST_GENERAL_DESIGN_INPUT**
- Advantages:
  - Preserves ordered Group membership on a clear symmetric row.
  - Separates Group rows without assigning real venue semantics.
- Disadvantages:
  - Row spacing is a virtual scale, not a measured rig distance.

#### Group 1 `HYBRID`

- Fixtures (verified membership order): `101, 102, 103, 104, 105, 106, 107, 108`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `-6.0`; Row: `ROW_1`
- Mirror pairs (normalizer): `101↔108, 102↔107, 103↔106, 104↔105`
- INNER candidates: `104, 105`
- OUTER candidates: `108, 101`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":104,"subfixture_id":1},{"fixture_id":105,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 2 `SPOT`

- Fixtures (verified membership order): `301, 302, 303, 304, 305, 306, 307, 308`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `-4.0`; Row: `ROW_2`
- Mirror pairs (normalizer): `301↔308, 302↔307, 303↔306, 304↔305`
- INNER candidates: `304, 305`
- OUTER candidates: `308, 301`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":304,"subfixture_id":1},{"fixture_id":305,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 3 `BEAM`

- Fixtures (verified membership order): `201, 202, 203, 204, 205, 206, 207, 208`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `-2.0`; Row: `ROW_3`
- Mirror pairs (normalizer): `201↔208, 202↔207, 203↔206, 204↔205`
- INNER candidates: `204, 205`
- OUTER candidates: `208, 201`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":204,"subfixture_id":1},{"fixture_id":205,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 4 `WASH`

- Fixtures (verified membership order): `501, 502, 503, 504, 505, 506, 507, 508`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `0.0`; Row: `ROW_4`
- Mirror pairs (normalizer): `501↔508, 502↔507, 503↔506, 504↔505`
- INNER candidates: `504, 505`
- OUTER candidates: `508, 501`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":504,"subfixture_id":1},{"fixture_id":505,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 5 `B-EYE`

- Fixtures (verified membership order): `401, 402, 403, 404, 405, 406, 407, 408`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `2.0`; Row: `ROW_5`
- Mirror pairs (normalizer): `401↔408, 402↔407, 403↔406, 404↔405`
- INNER candidates: `404, 405`
- OUTER candidates: `408, 401`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":404,"subfixture_id":1},{"fixture_id":405,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 6 `LED PAR`

- Fixtures (verified membership order): `601, 602, 603, 604, 605, 606, 607, 608`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `4.0`; Row: `ROW_6`
- Mirror pairs (normalizer): `601↔608, 602↔607, 603↔606, 604↔605`
- INNER candidates: `604, 605`
- OUTER candidates: `608, 601`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":604,"subfixture_id":1},{"fixture_id":605,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 7 `STROBE`

- Fixtures (verified membership order): `701, 702, 703, 704, 705, 706, 707, 708`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `6.0`; Row: `ROW_7`
- Mirror pairs (normalizer): `701↔708, 702↔707, 703↔706, 704↔705`
- INNER candidates: `704, 705`
- OUTER candidates: `708, 701`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":704,"subfixture_id":1},{"fixture_id":705,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

### Candidate B_FIXTURE_FAMILY_STAGING — Fixture-family staging

- Spacing: `1.0` virtual units
- Creative usefulness: **GOOD_FAMILY_LAYER_EXPLORATION**
- Advantages:
  - Makes fixture-family layers visually distinguishable in virtual geometry.
  - Keeps deterministic symmetry inside each Group.
- Disadvantages:
  - Family placement is an assumption based on Group/Fixture Type identity only.

#### Group 1 `HYBRID`

- Fixtures (verified membership order): `101, 102, 103, 104, 105, 106, 107, 108`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `-2.0`; Z: `0.0`; Row: `ROW_1`
- Mirror pairs (normalizer): `101↔108, 102↔107, 103↔106, 104↔105`
- INNER candidates: `104, 105`
- OUTER candidates: `108, 101`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":104,"subfixture_id":1},{"fixture_id":105,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 2 `SPOT`

- Fixtures (verified membership order): `301, 302, 303, 304, 305, 306, 307, 308`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `0.0`; Row: `ROW_2`
- Mirror pairs (normalizer): `301↔308, 302↔307, 303↔306, 304↔305`
- INNER candidates: `304, 305`
- OUTER candidates: `308, 301`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":304,"subfixture_id":1},{"fixture_id":305,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 3 `BEAM`

- Fixtures (verified membership order): `201, 202, 203, 204, 205, 206, 207, 208`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `-2.0`; Z: `0.0`; Row: `ROW_3`
- Mirror pairs (normalizer): `201↔208, 202↔207, 203↔206, 204↔205`
- INNER candidates: `204, 205`
- OUTER candidates: `208, 201`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":204,"subfixture_id":1},{"fixture_id":205,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 4 `WASH`

- Fixtures (verified membership order): `501, 502, 503, 504, 505, 506, 507, 508`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `2.0`; Z: `0.0`; Row: `ROW_4`
- Mirror pairs (normalizer): `501↔508, 502↔507, 503↔506, 504↔505`
- INNER candidates: `504, 505`
- OUTER candidates: `508, 501`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":504,"subfixture_id":1},{"fixture_id":505,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 5 `B-EYE`

- Fixtures (verified membership order): `401, 402, 403, 404, 405, 406, 407, 408`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `-2.0`; Z: `2.0`; Row: `ROW_5`
- Mirror pairs (normalizer): `401↔408, 402↔407, 403↔406, 404↔405`
- INNER candidates: `404, 405`
- OUTER candidates: `408, 401`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":404,"subfixture_id":1},{"fixture_id":405,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 6 `LED PAR`

- Fixtures (verified membership order): `601, 602, 603, 604, 605, 606, 607, 608`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `0.0`; Z: `2.0`; Row: `ROW_6`
- Mirror pairs (normalizer): `601↔608, 602↔607, 603↔606, 604↔605`
- INNER candidates: `604, 605`
- OUTER candidates: `608, 601`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":604,"subfixture_id":1},{"fixture_id":605,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 7 `STROBE`

- Fixtures (verified membership order): `701, 702, 703, 704, 705, 706, 707, 708`
- X positions: `-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5`
- Y: `2.0`; Z: `2.0`; Row: `ROW_7`
- Mirror pairs (normalizer): `701↔708, 702↔707, 703↔706, 704↔705`
- INNER candidates: `704, 705`
- OUTER candidates: `708, 701`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":704,"subfixture_id":1},{"fixture_id":705,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

### Candidate C_COMPACT_SYMMETRIC — Compact Symmetric

- Spacing: `0.75` virtual units
- Creative usefulness: **GOOD_COMPACT_PREVIEW**
- Advantages:
  - Small coordinate footprint for compact virtual inspection.
  - Maintains an even center gap and mirror pairs.
- Disadvantages:
  - Groups are vertically compressed and less separated for large-show browsing.

#### Group 1 `HYBRID`

- Fixtures (verified membership order): `101, 102, 103, 104, 105, 106, 107, 108`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `-2.25`; Z: `0.0`; Row: `ROW_1`
- Mirror pairs (normalizer): `101↔108, 102↔107, 103↔106, 104↔105`
- INNER candidates: `104, 105`
- OUTER candidates: `108, 101`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":104,"subfixture_id":1},{"fixture_id":105,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 2 `SPOT`

- Fixtures (verified membership order): `301, 302, 303, 304, 305, 306, 307, 308`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `-1.5`; Z: `0.0`; Row: `ROW_2`
- Mirror pairs (normalizer): `301↔308, 302↔307, 303↔306, 304↔305`
- INNER candidates: `304, 305`
- OUTER candidates: `308, 301`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":304,"subfixture_id":1},{"fixture_id":305,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 3 `BEAM`

- Fixtures (verified membership order): `201, 202, 203, 204, 205, 206, 207, 208`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `-0.75`; Z: `0.0`; Row: `ROW_3`
- Mirror pairs (normalizer): `201↔208, 202↔207, 203↔206, 204↔205`
- INNER candidates: `204, 205`
- OUTER candidates: `208, 201`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":204,"subfixture_id":1},{"fixture_id":205,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 4 `WASH`

- Fixtures (verified membership order): `501, 502, 503, 504, 505, 506, 507, 508`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `0.0`; Z: `0.0`; Row: `ROW_4`
- Mirror pairs (normalizer): `501↔508, 502↔507, 503↔506, 504↔505`
- INNER candidates: `504, 505`
- OUTER candidates: `508, 501`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":504,"subfixture_id":1},{"fixture_id":505,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 5 `B-EYE`

- Fixtures (verified membership order): `401, 402, 403, 404, 405, 406, 407, 408`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `0.75`; Z: `0.0`; Row: `ROW_5`
- Mirror pairs (normalizer): `401↔408, 402↔407, 403↔406, 404↔405`
- INNER candidates: `404, 405`
- OUTER candidates: `408, 401`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":404,"subfixture_id":1},{"fixture_id":405,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 6 `LED PAR`

- Fixtures (verified membership order): `601, 602, 603, 604, 605, 606, 607, 608`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `1.5`; Z: `0.0`; Row: `ROW_6`
- Mirror pairs (normalizer): `601↔608, 602↔607, 603↔606, 604↔605`
- INNER candidates: `604, 605`
- OUTER candidates: `608, 601`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":604,"subfixture_id":1},{"fixture_id":605,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

#### Group 7 `STROBE`

- Fixtures (verified membership order): `701, 702, 703, 704, 705, 706, 707, 708`
- X positions: `-2.625, -1.875, -1.125, -0.375, 0.375, 1.125, 1.875, 2.625`
- Y: `2.25`; Z: `0.0`; Row: `ROW_7`
- Mirror pairs (normalizer): `701↔708, 702↔707, 703↔706, 704↔705`
- INNER candidates: `704, 705`
- OUTER candidates: `708, 701`
- Center: `{"x":0.0,"fixture_subfixtures":[{"fixture_id":704,"subfixture_id":1},{"fixture_id":705,"subfixture_id":1}],"between_fixtures":true}`
- Assumption: `VIRTUAL_LAYOUT_ASSUMPTION`; no Stage Left/Right meaning is assigned.

## Recommendation

**RECOMMENDED_CANDIDATE:** `A_LAYERED_ROWS`

It gives each verified Group a separate deterministic row, retains membership order, produces an even center gap for eight Fixtures, and makes no physical venue claim.

## Designer simulation

After a future approved application, the Designer could use numeric X ordering, CENTER, INNER/OUTER ranks, ROW identifiers, and MIRROR_PAIR candidates per Group. The current uninitialized geometry remains unchanged.

## Typed write plan (not executable)

- Schema: `zen.auto_geometry_write_plan.v0.1`
- Mode: `PREVIEW_ONLY`
- Operations: **56** typed Fixture references
- Safety: `MODIFY`; approval required: `YES`
- Raw MA2 commands: **none**
- Future precondition: fresh scan must still report `GEOMETRY_UNINITIALIZED`; otherwise `STATE_CHANGED_SINCE_PREVIEW`.

## Audit

- MA2 write audit: **ZERO_WRITES**
- MA2 objects modified: **NONE**
- Ready for user geometry review: **YES**
- Ready for MA2 write: **NO — USER APPROVAL REQUIRED**
