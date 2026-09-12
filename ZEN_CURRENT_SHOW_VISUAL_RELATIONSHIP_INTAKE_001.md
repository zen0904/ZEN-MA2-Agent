# Current Show Visual Relationship Intake 001

## Purpose and boundary

This is the smallest human-confirmation layer for describing what the current
Existing Show visually is. It is not a rig planner, auto-geometry writer,
fixture-role mapper, or Designer activation.

The machine-readable intake is
[`data/current_show_visual_relationships_001.json`](data/current_show_visual_relationships_001.json)
and validates as `zen.current_show_visual_relationships.v0.1`. It is bound to
the scanned Show fingerprint
`497dfae11821c10eebc54a614fa66e81339cb79d789d50c112fcdfc33134f4ea`.

Every visual field begins `UNKNOWN`. This is valid and intentional: the current
scanner confirms inventory, not visual placement, coverage, dominance, or
artistic meaning. No Group label, FixtureType, numeric Group ID, current raw
XYZ, external knowledge, or Training Case is used to fill a field.

## One-pass review matrix

Zen may confirm only facts that are known. Leave every other cell `UNKNOWN`.
The allowed values are documented below the matrix; no B3 role is requested.

| Group | Fixtures | Physical presence | Coverage | Visual weight | Symmetry | Primary visual domain | Human review |
| --- | ---: | --- | --- | --- | --- | --- | --- |
| 1 — HYBRID | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 2 — SPOT | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 3 — BEAM | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 4 — WASH | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 5 — B-EYE | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 6 — LED PAR | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |
| 7 — STROBE | 8 | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNSET |

Fixture `9999` is excluded. It is not represented, selected, or modified.

### Allowed observed descriptors

- `physical_presence` may contain one or more of: `CENTER_BIASED`,
  `SIDE_BIASED`, `WIDE_STAGE`, `NARROW_AREA`, `OVERHEAD`, `FLOOR_LEVEL`,
  `REAR_STAGE`, `FRONT_STAGE`, `MIXED`; otherwise exactly `UNKNOWN`.
- `coverage_scope`: `LOCAL`, `MEDIUM`, `BROAD`, or `UNKNOWN`.
- `visual_weight_relative`: `LIGHT`, `MEDIUM`, `HEAVY`,
  `CONTEXT_DEPENDENT`, or `UNKNOWN`.
- `symmetry`: `SYMMETRIC`, `ASYMMETRIC`, `MIXED`, or `UNKNOWN`.
- `primary_visual_domain`: `STAGE_SURFACE`, `PERFORMER_AREA`,
  `AUDIENCE_FACING`, `AERIAL_SPACE`, `BACKGROUND_FRAME`, `MIXED`, or
  `UNKNOWN`.

These are observed relationship descriptors only. They are not technical
capabilities, B3 roles, priorities, permanent artistic assignments, or a
requirement to use a Group.

## Optional relationship confirmation

Only add a relationship when it is actually known and can be marked
`HUMAN_CONFIRMED`. Supported relationship types are:

- `VISUALLY_OVERLAPS_WITH`
- `VISUALLY_COMPLEMENTS`
- `VISUALLY_COMPETES_WITH`
- `SPATIALLY_SEPARATE_FROM`
- `VISUALLY_DOMINATES`
- `VISUALLY_SUBORDINATE_TO`

No relationship needs to be supplied. Absence means no statement is being
made; `UNKNOWN` is also supported but cannot masquerade as a known relation.
A valid later confirmation records both Group IDs, type, `HUMAN_CONFIRMED`,
and human provenance. It never derives a relationship from labels or
FixtureTypes.

## Preexisting evidence — not human confirmation

| Evidence | State | What it proves | What it cannot prove |
| --- | --- | --- | --- |
| Current Show inventory | `PREEXISTING_EVIDENCE` | Exact Groups 1–7 and eight-fixture membership per Group | Placement, coverage, visual weight, symmetry, domain, or role |
| Geometry analysis | `PREEXISTING_EVIDENCE` | Current values overlap at origin | Stage axes, center, side, depth, height, rows, or any visual relation |
| Semantic Position presets | `PREEXISTING_EVIDENCE` | `NONE` | Performer targets or position meaning |
| Auto-geometry A/B/C | `PREEXISTING_EVIDENCE` | Historical virtual proposals exist | Current physical geometry or human confirmation |

The current geometry remains `GEOMETRY_UNINITIALIZED`; the virtual A/B/C
proposals remain unapplied. This intake neither writes geometry nor adopts one
of those proposals.

## Future evidence boundary

A later intake revision may carry a user-confirmed plot, Stage View screenshot,
venue CAD/PDF, rig photo, coordinate export, or manually confirmed zones.
Photographs must remain observations: they cannot establish safe hanging,
structural load, power capacity, or certified rigging points. No computer
vision, photogrammetry, stage-axis inference, or safety claim is implemented.

## Conceptual shadow use only

After humans confirm some observed fields, the relationship evidence could be
paired with External Lighting Knowledge Pack 001 and Design Intent to review
the A/B 002 findings `GROUP_LEVEL_HOMOGENEITY_UNRESOLVED` and
`FINAL_COHORT_SATURATION_RISK`. The current helper returns only this
conceptual boundary; it cannot alter A/B 002 actions, select B3 roles, infer
missing relationships, or write MA2.

```text
Current Show human-confirmed visual evidence
 + external shadow knowledge
 + Design Intent
 -> future Visual Strategy review
 -> later case-specific selection consideration
```

This pathway is `NOT_RUN`; Production Designer and B3 are not wired to the
intake.

## Safety and status

- Production Designer: `UNCHANGED`.
- B3: `GUIDANCE_ASSISTED_AB_ONLY`.
- A/B 002 actions: `UNCHANGED`.
- MA2 objects modified: `NONE`; MA2 write audit: `ZERO_WRITES`.
- Auto geometry: not run.
- Permanent Group-to-Role mapping: none.
- `ZEN_STYLE_PROFILE`: `DEFERRED`.
- Human review status: `READY_FOR_HUMAN_INPUT`.

**Next step:** Zen can complete any known cells in the one-pass matrix and
optionally add only known Group-to-Group visual relationships. That review will
describe the rig; it still will not decide what the Designer should do.
