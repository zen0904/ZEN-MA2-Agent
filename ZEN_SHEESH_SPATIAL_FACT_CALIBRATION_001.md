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

## Calibration evidence (schema v0.2)

The machine-readable fact matrix is [data/sheesh_spatial_fact_calibration_001.json](data/sheesh_spatial_fact_calibration_001.json).
It is bound to Show fingerprint
`b41d801b915cddfdd5017df787ad66b55941fbce415ab02ee8ec63acaa027bd5` and the
saved Phase A snapshot/profile and role-artifact hashes recorded there.

Evidence is kept in three distinct namespaces:

1. `SOFTWARE_COORDINATE_SEMANTICS`: official MA2 definitions. MA2 Stage X is
   horizontal, Stage Y is the toward/away-from-audience dimension and Stage Z
   is vertical. Fixture `Pos X/Y/Z` and `Rot X/Y/Z` are transforms in MA2's 3D
   environment; Stage Axis and Object Axis are separate setup modes. These
   software facts do not define signed venue mappings or the audience-facing
   side of this Show. Sources: [grandMA2 XYZ help](https://help.malighting.com/grandMA2/en/help/key_xyz.html)
   and [fixture position/rotation help](https://help.malighting.com/grandMA2/en/help/key_patch_position_fixtures.html).
2. `CURRENT_SHOW_MACHINE_FACTS`: Phase A has 64 available geometry-bearing
   resources and protects Fixture 9999. A later local read-only scan produced
   partial fingerprint `145be3835bf8d23cf4cb416535a7313d90240077954594e33c4c995337023340`,
   which does not match Phase A's `b41d...`. The existing exact-identity gate
   stopped the FixtureType export before the export ran. No profile from the
   mismatched Show is attached to the Phase A calibration.
3. `VENUE_OPERATOR_FACTS`: the operator verified this Test Show's Pan/Tilt
   convention: negative Tilt points toward the audience; positive Tilt points
   upstage or inward; negative Pan is stage right and positive Pan is stage
   left when facing the stage from the audience. This is scoped to this Show
   and operator convention only. It does not infer Pos X/Y/Z signs, nor does
   it resolve whether positive Tilt means upstage versus inward.

| Fact | Result |
|---|---|
| MA2 software X / Y / Z concepts | `HORIZONTAL_STAGE_COORDINATE` / `TOWARD_AWAY_FROM_AUDIENCE_DIMENSION` / `VERTICAL_STAGE_COORDINATE` |
| Current Show X / Y / Z sign mapping | `UNKNOWN` / `UNKNOWN` / `UNKNOWN`; Pan/Tilt calibration is not used as XYZ evidence |
| Exact fixture Pos X/Y/Z units | `UNKNOWN`; units from other MA2 XYZ features are not extrapolated |
| Stage View automatic capture / operator image input / image present | `NO` / `YES` / `NO`; no unsupported capture command was attempted |
| Stage bounds | `UNKNOWN`; numeric extents are not physical boundaries |
| Performer zone | `UNKNOWN` |
| Audience / stage-left-right convention | Operator verified for Tilt/Pan only; no XYZ sign mapping follows |
| Upstage/downstage | `PARTIAL`: positive Tilt is upstage OR inward |
| Fixture mounting positions | `UNKNOWN` |
| Fixture orientation readable / writable | `PARTIAL_NUMERIC_ROTATION_ONLY` / `NOT_TESTED` |
| Obstruction data / truss or support geometry | `NOT_AVAILABLE` / `NOT_AVAILABLE` |
| Current-fingerprint capability profiles | `NO`; profile export is supported, but identity mismatch prevented export; count `0` |

The accepted onPC read-only capability path is the existing
`fixture_type_profiles` State provider (native FixtureType export and exact
fixture-type identity binding). It is not a name-based lookup. The current live
scan identity mismatch made the path ineligible, so `Export FixtureType` was
not issued and no current-fingerprint capability profile was claimed.

The optional Stage View evidence input accepts an explicit operator-supplied
image artifact with Show fingerprint, capture time, media/hash checks, and
separately attributed operator annotations. Any image-only notes remain
`VISUAL_OBSERVATION`, not verified physical facts. No image was supplied.

Calibration remains `BLOCKED_MISSING_EVIDENCE`. The two machine identities do
not match; current Show XYZ signs, physical stage bounds and performer zone,
and exact-fingerprint capability profiles remain blockers. Unknown fixture
Pos units, absent obstruction/truss detail, and untested orientation writeback
are retained as limitations rather than fabricated facts. Fixture 9999 remains
protected and unavailable for placement.

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

`SHEESH_SPATIAL_FACT_CALIBRATION_001=BLOCKED_MISSING_EVIDENCE`. Re-evaluate
after the Show identity is safely aligned/rebound, independent current-Show XYZ
sign mapping and enough stage/performance-area context are available, and
exact-fingerprint FixtureType profiles are read. The operator's Pan/Tilt
convention must remain separate; it cannot satisfy XYZ mapping. A Stage View
image is one supported evidence path but is not mandatory if equivalent
verified evidence is supplied. No ZEN revision inference or spatial writeback
is approved by this calibration update.
