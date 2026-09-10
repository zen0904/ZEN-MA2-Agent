# ZEN Design Pipeline Integrity 001

Status: `COMPLETE` (integrity-only; no artistic behavior change)

## Persistent project context

The repository now carries a concise startup contract in `AGENTS.md` and six
living documents under `docs/`. `AGENTS.md` is navigation/control, not an
encyclopedia: substantial work starts with the Product Constitution, Workflow
Contract, relevant console intelligence, Learning Policy when applicable, and
the current status report, then reads only task-relevant evidence. The current
committed repository state outranks stale chat handoffs; a newer explicit human
decision must be recorded in the appropriate living document.

The documents record the product definition, Stable Operator Contract,
Evolvable Implementation, handover readability, grandMA2-first/grandMA3-future
separation, evidence lifecycle, and local-first GitHub/storage policy. No
workflow migration, MA3 implementation, expensive CI, or Git LFS was started.

## Integrity changes

### Unique section occurrence identity

The typed plan now carries deterministic identity on every generated cue:

| Field | Meaning |
| --- | --- |
| `section_instance_id` | Stable role occurrence such as `drop_2`; shared by the base and accent cues of that section |
| `section_role` | Normalized role used to derive the occurrence |
| `occurrence_index` | One-based occurrence of that role in song order |
| `cue_occurrence_index` | Zero for the section cue, one-based for additional accent cues |
| `id` / `cue_number` | Unique cue identity within the plan |

The review trace carries `SECTION_INSTANCE_ID`, `CUE_ID`, and
`CUE_OCCURRENCE_INDEX`. Human-review extraction first resolves the exact cue
id, then uses typed identity fallbacks; it no longer relies on the first cue
whose string label happens to match. Repeated sections and multiple cues within
one section are therefore distinguishable without fuzzy matching.

Existing consumers may continue using `source_section_id` during migration,
but new review/plan consumers should use the occurrence fields. Existing
single-occurrence inputs remain valid and receive occurrence `1`.

### Design Intent realizability

Experimental designs retain the requested development in `development`, while
`intent_realizability` records the observed typed result independently:

- `REALIZED`: requested composition/change is expressed by a changed typed
  action shape;
- `PARTIALLY_REALIZED`: only typed levels changed, not the composition needed
  for the requested visual delta;
- `NOT_EXPRESSIBLE_WITH_CURRENT_CAPABILITIES`: the requested delta has no
  resulting typed action change with current bindings/resources;
- `INTENTIONAL_SIMILARITY`: continuity was the explicit repeat decision.

The record includes `desired_development`, `actual_action_delta`, and a reason.
Case C is consequently not falsely represented as a successfully realized
texture change when the available actions cannot express one. No new texture,
preset, or MA2 capability was invented.

### Canonical role-state semantics

`role_states` is the authoritative typed list, using one state per role:
`KEEP`, `CHANGE`, `REDUCE`, `OMIT`, or `SUBSTITUTE` (the current adapter emits
the states applicable to its choices). Legacy `selected_roles` and
`reduced_roles` remain for backward compatibility, but their projection is
explicitly documented as:

`selected_roles_INCLUDES_KEEP_AND_REDUCE_ACTIVE`

Thus a reduced role may remain active at a lower multiplier without being
ambiguous. Downstream code must consume `role_states` rather than infer state
from overlapping legacy lists.

## Compatibility and safety

The production `FirstSongDesigner`, Song Analysis, Design Guidance, Industry
Evidence, User Style Evidence, and experimental B3 artistic reasoning were not
changed. The integrity additions are metadata, extraction and tests only.
The typed plan still rejects command/Telnet/Lua fields, and Builder remains the
sole MA2 command-generation boundary. No `ZEN_STYLE_PROFILE` was created and
no Guidance-Assisted mode was activated.

No MA2/Telnet/plugin/live Builder path was invoked. No Sequence, Cue, Effect,
Preset, Group, Fixture, or showfile object was written. Existing untracked
research/cache directories were left untouched and are not part of this
commit.

## Verification

Targeted tests cover exact section/cue identity, review trace mapping, partial
or unavailable realization, and canonical role-state invariants. The full
repository suite passes. The production plan comparison remains deterministic;
metadata is added to the experimental path without changing production
artistic decisions.

## Remaining blockers before Real Song + Existing Show A/B

No integrity blocker remains in this round. Before a production-facing A/B with
a real existing Show, the experiment still needs a fresh existing-show fixture
and human review of the experimental design. Real venue validation remains
`WAIT_FOR_REAL_CASE`; richer instrumentation, harmony, performance, camera and
venue-response analysis remain unavailable. Guidance-Assisted production
activation and `ZEN_STYLE_PROFILE` remain explicitly deferred.

## Next step

Use the new occurrence and realizability metadata in a human-review-ready Real
Song + Existing Show A/B fixture, without enabling it in the default Designer.
