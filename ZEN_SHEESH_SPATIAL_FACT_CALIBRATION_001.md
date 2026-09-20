# SHEESH Spatial Fact Calibration 001

## Owner review decision

`SHEESH_ZEN_SPATIAL_ARTIFACT_HUMAN_REVIEW_001` is closed as:

- `HUMAN_REVIEW_DECISION=REJECT_FOR_REVISION`
- `SPATIAL_WRITEBACK_APPROVED=NO`
- `CURRENT_POSITION_ARTIFACT=TECHNICALLY_VALID_ARTISTICALLY_UNACCEPTED`
- `CRITIC_BLOCKER_ACCEPTED=YES`

The completed six-role run remains unchanged at
`E:\ZEN_MA2_AGENT\projects\runs\SHEESH_CURRENT_SHOW_REDESIGN_001`.
Its legacy `status=COMPLETE` records technical execution only. Read-only
classification gives `execution_status=COMPLETE` and
`design_review_status=BLOCKED_BY_CRITIC`. The Position artifact is schema- and
reference-valid, but all 64 accepted placements and rotations exactly reproduce
the scanned geometry:

- `GEOMETRY_DELTA_FROM_SNAPSHOT=ZERO`
- `PLACEMENTS_EQUAL_TO_SCANNED_GEOMETRY=64/64`
- `ROTATIONS_EQUAL_TO_SCANNED_GEOMETRY=64/64`
- placements changed: 0; unchanged: 64; rotations changed: 0

The accepted Critic artifact classifies severity as `BLOCKER` and contains 10
revision requests. Finalizer completion does not clear that state. Writeback,
Resolver, and write-preview eligibility remain `NO`.

## Calibration evidence

The machine-readable fact matrix is [data/sheesh_spatial_fact_calibration_001.json](data/sheesh_spatial_fact_calibration_001.json).
It is bound to Show fingerprint
`b41d801b915cddfdd5017df787ad66b55941fbce415ab02ee8ec63acaa027bd5` and the
saved Phase A snapshot/profile and role-artifact hashes recorded there.

| Fact | Result |
|---|---|
| Coordinate frame | `PARTIAL`: numeric MA2 fixture-object coordinates are identified; venue-facing semantics are not |
| X / Y / Z semantics | `UNKNOWN` / `UNKNOWN` / `UNKNOWN` |
| Coordinate units | `UNKNOWN` |
| Stage View capture support / image | `NO` / `NO`; no supported read-only capture path or saved image was found |
| Stage bounds | `UNKNOWN`; numeric extents are not physical boundaries |
| Performer zone / audience direction | `UNKNOWN` / `UNKNOWN` |
| Upstage/downstage / stage-left/right | `UNKNOWN` / `UNKNOWN` |
| Fixture mounting positions | `UNKNOWN` |
| Fixture orientation readable / writable | `PARTIAL_NUMERIC_ROTATION_ONLY` / `NOT_TESTED` |
| Obstruction data / truss or support geometry | `NOT_AVAILABLE` / `NOT_AVAILABLE` |
| Current-fingerprint capability profiles | `NO`; saved Show profile marks fixture type profiles unavailable |

No generic MA2 coordinate convention was promoted into venue semantics. The
calibration is `BLOCKED_MISSING_EVIDENCE`; unknown facts are preserved as
unknown. Fixture 9999 remains protected and unavailable for placement.

## Review control and revision plumbing

Live-Show run metadata now separates `execution_status` from
`design_review_status`. A Critic `BLOCKER` is machine-readable, its artifact
hash and revision requests are retained, and a later Finalizer cannot clear
the blocker. Even a non-blocking review only advances to `REVIEW_PASSED`; it
does not authorize a write.

The read-only `run_spatial_revision_loop` plumbing passes the exact prior
Researcher, Rig, Position, Lighting Designer, and Critic artifacts plus the
fingerprinted live snapshot, fact calibration, and owner decision to ZEN roles.
The model remains the sole source of revised artistic/spatial content. The
bounded maximum is two cycles. A second `BLOCKER` yields
`BLOCKED_AFTER_REVISION_LIMIT`. No geometry-difference threshold is used as an
artistic validator.

No revision inference was launched: required physical semantics and visual
evidence are still missing. No MA2 transport, Resolver, Builder, Stage write,
or provider call was made. `MA2_WRITES=0` and
`CODEX_ARTISTIC_INTERVENTION=NONE`.

## Next gate

`SHEESH_SPATIAL_FACT_CALIBRATION_001=BLOCKED_MISSING_EVIDENCE`. Re-evaluate only
after fingerprint-bound coordinate semantics and units, a human-visible Stage
View, stage/performance/audience orientation and mounting evidence, and
current-fingerprint capability profiles are supplied. Spatial writeback stays
unapproved.
